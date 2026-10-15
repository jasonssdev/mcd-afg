"""C1 -- document RAG over raw transcripts (thesis section 5.3, "floor" condition).

C1 answers exactly like ``openkos query`` v0.5.4 answers (ADR 0006), except that the context
blocks are transcript chunks retrieved by C1's own hybrid retriever instead of compiled
concepts. The flow below mirrors ``src/openkos/retrieval/answer.py`` at tag ``v0.5.4``
(``answer()``), read with ``git show``; nothing is imported from OpenKOS:

1. Retrieve K chunks (K and chunking pinned by ADR 0007).
2. Number the blocks ``[n] <label><body>``, bounding bodies to the shared context window
   (``_bound_bodies`` -> :mod:`afg.conditions.c1_prompt_budget`).
3. Sufficiency call (``_context_holds_the_answer``), on by default as in the shipped
   ``DEFAULT_SUFFICIENCY_CHECK``: a reply that is exactly ``NONE`` abstains; a transient
   backend error fails open; a fatal one propagates.
4. Synthesis call with the same ``user`` message, then ``USED:`` parsing
   (``_split_attribution``) and scaffolding strip (``_strip_concept_id_scaffolding``).

Temperature and seed must be fixed (ADR 0006 point 7); the condition refuses to exist without
them. Every call records an :class:`AnswerTrace` for OE4 mirroring ``openkos query --json``
schema v1 as far as it applies to chunks.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from afg.conditions.answer_prompts import (
    ATTRIBUTION_KEYWORD,
    ATTRIBUTION_NONE,
    SUFFICIENCY_NONE,
    sent_prompt_sha256,
    sufficiency_prompt,
    system_prompt,
)
from afg.conditions.c1_chunking import Chunk, chunk_meetings
from afg.conditions.c1_prompt_budget import (
    CONTEXT_CHUNK_TARGET,
    ELISION_MARKER,
    bounded_text,
    budget_chars,
    chunk_lines,
    fair_shares,
)
from afg.conditions.c1_retrieval import Embedder, HybridRetriever, OllamaEmbedder
from afg.conditions.c1_tuning import PinnedC1Params, load_pinned_c1_params, series_meetings
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question
from afg.shared.config import load_experiments_config
from afg.shared.paths import TRANSCRIPTS_DIR

# openkos.retrieval.answer.NO_MATCH / NO_ANSWER_IN_CONTEXT (stable texts).
NO_MATCH = "No matching concepts were found in the compiled bundle for this question."
NO_ANSWER_IN_CONTEXT = (
    "Matching concepts were found in the compiled bundle, but none of them answers this question."
)

# openkos.application.query_report: OUTCOME_*.
OUTCOME_ANSWERED = "answered"
OUTCOME_NO_MATCH = "no_match"
OUTCOME_NO_ANSWER_IN_CONTEXT = "no_answer_in_context"

OMIT_REASON_BUDGET = "context_budget"  # openkos.retrieval.answer.OMIT_REASON_BUDGET

Attribution = Literal["reported", "absent", "unparsed"]


# --- generation backend ----------------------------------------------------------------


class ChatError(RuntimeError):
    """Transient generation failure (OpenKOS ``BackendError``): the sufficiency check fails open."""


class ChatUnavailableError(ChatError):
    """Fatal: the server is unreachable or the model is not pulled. Always propagates."""


class ChatBackend(Protocol):
    """One chat completion: ``messages`` (system + user) in, the reply content out."""

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, model: str, options: Mapping[str, Any]
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    """Model and sampling settings of the shared budget; temperature and seed must be fixed."""

    model: str
    temperature: float | None
    seed: int | None
    context_window: int
    max_generation_tokens: int

    def __post_init__(self) -> None:
        # ADR 0006 point 7: OpenKOS reports an unfixed temperature/seed as null and the
        # experiment rejects such a run.
        if self.temperature is None:
            raise ValueError("temperature must be fixed explicitly (ADR 0006 point 7).")
        if self.seed is None:
            raise ValueError("seed must be fixed explicitly (ADR 0006 point 7).")

    @classmethod
    def from_config(cls, experiments: dict[str, Any] | None = None) -> GenerationSettings:
        """Read ``[shared_budget]`` of ``config/experiments.toml``."""
        section = (experiments or load_experiments_config())["shared_budget"]
        return cls(
            model=str(section["generative_model"]),
            temperature=section.get("temperature"),
            seed=section.get("seed"),
            context_window=int(section["context_window_tokens"]),
            max_generation_tokens=int(section["max_generation_tokens"]),
        )

    @property
    def options(self) -> dict[str, Any]:
        """The Ollama ``options`` of ``openkos.llm.ollama.OllamaClient.chat`` (v0.5.4).

        ``num_predict``, ``temperature``, ``seed`` and ``num_ctx`` are the only four options
        OpenKOS sends; ``top_p`` of the config is deliberately not sent because OpenKOS does
        not send it either (Ollama's model default applies in both).
        """
        return {
            "num_predict": self.max_generation_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "num_ctx": self.context_window,
        }


class OllamaChatBackend:
    """Chat through a local Ollama server, like ``openkos.llm.ollama.OllamaClient.chat``.

    Sends ``stream=False`` and ``think=False`` (OpenKOS ``ollama.py``: request body of
    ``chat()``) so qwen3 does not emit a reasoning trace, with the ``options`` it is given.
    Needs the optional ``llm`` extra; the client is imported on first use.
    """

    # openkos.llm.ollama.DEFAULT_TIMEOUT
    timeout: float = 600.0

    def __init__(self, host: str | None = None, client: Any | None = None) -> None:
        self._host = host
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import ollama
            except ImportError as exc:
                raise RuntimeError(
                    "OllamaChatBackend needs the optional `llm` extra: `uv sync --extra llm`."
                ) from exc
            from afg.conditions.c1_retrieval import resolve_ollama_host

            self._client = ollama.Client(
                host=self._host or resolve_ollama_host(), timeout=self.timeout
            )
        return self._client

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, model: str, options: Mapping[str, Any]
    ) -> str:
        client = self._get_client()
        try:
            response = client.chat(
                model=model,
                messages=[dict(m) for m in messages],
                stream=False,
                think=False,
                options=dict(options),
            )
        except ConnectionError as exc:
            raise ChatUnavailableError(f"Cannot reach Ollama: {exc}") from exc
        except Exception as exc:  # map the client's own errors by status below
            status = getattr(exc, "status_code", None)
            if status == 404:
                raise ChatUnavailableError(f"Model {model!r} is not installed in Ollama.") from exc
            raise ChatError(f"Ollama chat request failed: {exc}") from exc
        # openkos.llm.ollama: a reply cut for length is loud, never silently truncated.
        if getattr(response, "done_reason", None) == "length":
            raise ChatError(
                "Ollama stopped generation for length before the reply finished "
                "(num_predict or num_ctx reached)."
            )
        return str(response.message.content or "")


# --- USED: attribution and scaffolding (openkos.retrieval.answer, v0.5.4) --------------

_ATTRIBUTION_LINE_RE = re.compile(
    rf"(?im)^[ \t]*{re.escape(ATTRIBUTION_KEYWORD)}[ \t]*:[ \t]*(?P<payload>[^\n]*)$"
)
_ATTRIBUTION_INDEX_RE = re.compile(r"\d+")

_CONCEPT_ID_SCAFFOLD = r"""
      \[[ \t]*concept_id[ \t]*:[^\]\n]*\]
    | \([ \t]*concept_id[ \t]*:[^)\n]*\)
    | concept_id[ \t]*:[ \t]*[^\s,;:!?)\]]+(?<![.])
"""
_SCAFFOLD_AT_LINE_START_RE = re.compile(rf"(?m)^[ \t]*(?:{_CONCEPT_ID_SCAFFOLD})[ \t]*", re.VERBOSE)
_SCAFFOLD_INLINE_RE = re.compile(rf"[ \t]*(?:{_CONCEPT_ID_SCAFFOLD})", re.VERBOSE)


def split_attribution(
    reply: str, block_count: int
) -> tuple[str, frozenset[int] | None, Attribution]:
    """Split ``reply`` into prose, the 1-based blocks it reports, and how (``_split_attribution``).

    The last ``USED:`` line wins and is stripped whether or not it parsed. Out-of-range
    numbers are dropped; a report with none left is ``unparsed`` (``None``), while
    ``USED: none`` is a positive claim (empty set).
    """
    matches = list(_ATTRIBUTION_LINE_RE.finditer(reply))
    if not matches:
        return reply, None, "absent"
    last = matches[-1]
    prose = (reply[: last.start()] + reply[last.end() :]).strip()
    payload = last.group("payload").strip()
    if payload.casefold() == ATTRIBUTION_NONE.casefold():
        return prose, frozenset(), "reported"
    reported = {
        index
        for raw in _ATTRIBUTION_INDEX_RE.findall(payload)
        if 1 <= (index := int(raw)) <= block_count
    }
    if not reported:
        return prose, None, "unparsed"
    return prose, frozenset(reported), "reported"


def strip_concept_id_scaffolding(text: str) -> str:
    """Remove leaked ``[concept_id: ...]`` labels (``_strip_concept_id_scaffolding``)."""
    return _SCAFFOLD_INLINE_RE.sub("", _SCAFFOLD_AT_LINE_START_RE.sub("", text))


# --- prompt assembly (openkos.retrieval.answer, v0.5.4) --------------------------------


def _user_content(context_blocks: Sequence[str], question: str) -> str:
    """``_user_content``: numbered ``[n] `` blocks inside the ``CONTEXT:``/``QUESTION:`` frame."""
    numbered = [f"[{position}] {block}" for position, block in enumerate(context_blocks, 1)]
    return "CONTEXT:\n\n" + "\n\n".join(numbered) + f"\n\nQUESTION:\n{question}"


def _label(chunk: Chunk) -> str:
    """Block label. OpenKOS heads a block ``[concept_id: <id> -- <title>]\\n``; a chunk's id is
    the chunk id and its title the meeting id, so the frame (and the system prompt's remark
    about bracketed labels) stays as OpenKOS shows it to the model."""
    return f"[concept_id: {chunk.chunk_id} — {chunk.meeting_id}]\n"


def _sufficiency_holds(reply: str) -> bool:
    """A refusal only when the reply IS the sentinel, modulo whitespace, punctuation, case."""
    return reply.strip().strip("\"'`*. \t\n").upper() != SUFFICIENCY_NONE


def assemble_context(
    question: str, chunks: Sequence[Chunk], *, context_window: int, max_generation_tokens: int
) -> tuple[list[str], list[tuple[Chunk, bool]], list[Chunk]]:
    """``_bound_bodies`` + the no-history tail of ``_assemble_context``.

    Returns the block strings, the ``(chunk, excerpted)`` pairs kept, and the chunks the
    budget left no room for (dropped from the prompt and never citable). Pure and public so
    the C1 tuning measures the text the model actually receives with this very function.
    """
    labels = [_label(c) for c in chunks]
    bodies = [c.text for c in chunks]
    if not bodies:
        return [], [], []
    overhead = len(_user_content(labels, question)) + max(
        len(system_prompt()), len(sufficiency_prompt())
    )
    budget = budget_chars(
        planning=context_window,
        generation_reserve_tokens=max_generation_tokens,
        overhead_chars=overhead,
    )
    shares = fair_shares([len(b) for b in bodies], budget=budget)
    blocks: list[str] = []
    kept: list[tuple[Chunk, bool]] = []
    omitted: list[Chunk] = []
    for chunk, label, body, share in zip(chunks, labels, bodies, shares, strict=True):
        text, was_bounded = bounded_text(
            body,
            budget=share,
            windows=chunk_lines(body, CONTEXT_CHUNK_TARGET),
            marker=ELISION_MARKER,
        )
        if was_bounded and not text and body:
            omitted.append(chunk)
            continue
        blocks.append(label + text)
        kept.append((chunk, was_bounded))
    return blocks, kept, omitted


# --- trace -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetrievedRow:
    """One fused hit as the retriever ranked it (``openkos.retrieval.answer.RetrievedRow``)."""

    rank: int
    chunk_id: str
    meeting_id: str
    lexical_rank: int | None
    dense_rank: int | None
    rrf_score: float


@dataclass(frozen=True, slots=True)
class ContextBlockTrace:
    """One block of the synthesis prompt; ``text`` is exactly what follows ``[n] ``."""

    index: int
    chunk_id: str
    meeting_id: str
    excerpted: bool
    text: str


@dataclass(frozen=True, slots=True)
class OmittedTrace:
    """A retrieved chunk the context budget dropped entirely."""

    chunk_id: str
    meeting_id: str
    reason: str = OMIT_REASON_BUDGET


@dataclass(frozen=True, slots=True)
class AnswerTrace:
    """Observability record of one answer (OE4), mirroring ``openkos query --json`` v1.

    Hashes are the SHA-256 of the message content as sent. ``system_sha256`` is ``None``
    unless synthesis ran, ``sufficiency_sha256`` unless the check ran, ``user_sha256`` when
    no context was assembled.
    """

    outcome: str
    question: str
    model: str
    temperature: float | None
    seed: int | None
    context_window: int
    max_generation_tokens: int
    retrieved: tuple[RetrievedRow, ...] = ()
    context_blocks: tuple[ContextBlockTrace, ...] = ()
    omitted: tuple[OmittedTrace, ...] = ()
    used_indices: tuple[int, ...] = ()
    attribution: Attribution = "absent"
    cited_chunk_ids: tuple[str, ...] = ()
    cited_acts: dict[str, tuple[str, ...]] = field(default_factory=dict)
    sufficiency_invoked: bool = False
    sufficiency_degraded: bool = False
    sufficiency_raw_reply: str | None = None
    raw_reply: str | None = None
    system_sha256: str | None = None
    user_sha256: str | None = None
    sufficiency_sha256: str | None = None


# --- the condition ---------------------------------------------------------------------


@dataclass(slots=True)
class DocumentRagCondition:
    """C1: hybrid lexical + dense retrieval over rendered meeting transcripts."""

    chat: ChatBackend
    embedder: Embedder
    settings: GenerationSettings
    params: PinnedC1Params
    transcripts_dir: Path = TRANSCRIPTS_DIR
    condition_id: str = "C1"
    sufficiency_check: bool = True
    _indexes: dict[str, HybridRetriever] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_config(cls, transcripts_dir: Path = TRANSCRIPTS_DIR) -> DocumentRagCondition:
        """Wire the condition from ``config/experiments.toml`` and the local Ollama."""
        return cls(
            chat=OllamaChatBackend(),
            embedder=OllamaEmbedder.from_config(),
            settings=GenerationSettings.from_config(),
            params=load_pinned_c1_params(),
            transcripts_dir=transcripts_dir,
        )

    def _index(self, series: str) -> HybridRetriever:
        """The index of the whole series (D15), built once and cached."""
        if series not in self._indexes:
            meetings = series_meetings(series, self.transcripts_dir)
            chunks = chunk_meetings(
                meetings, self.params.max_chars, self.params.overlap_turns, self.transcripts_dir
            )
            self._indexes[series] = HybridRetriever.from_config(chunks, self.embedder)
        return self._indexes[series]

    def _trace(self, question: Question, outcome: str, **fields: Any) -> AnswerTrace:
        s = self.settings
        return AnswerTrace(
            outcome=outcome,
            question=question.text,
            model=s.model,
            temperature=s.temperature,
            seed=s.seed,
            context_window=s.context_window,
            max_generation_tokens=s.max_generation_tokens,
            **fields,
        )

    def answer(self, question: Question) -> Answer:
        """Answer ``question``; see :meth:`answer_with_trace` for the recorded trace."""
        return self.answer_with_trace(question)[0]

    def _abstention(
        self, question: Question, text: str, trace: AnswerTrace
    ) -> tuple[Answer, AnswerTrace]:
        answer = Answer(
            question_id=question.id, condition=self.condition_id, text=text, abstained=True
        )
        return answer, trace

    def answer_with_trace(self, question: Question) -> tuple[Answer, AnswerTrace]:
        """Mirror of ``openkos.retrieval.answer.answer`` over chunks, returning the OE4 trace."""
        if not question.text.split():
            return self._abstention(question, NO_MATCH, self._trace(question, OUTCOME_NO_MATCH))

        hits = self._index(question.series_id).retrieve(question.text, self.params.k)
        retrieved = tuple(
            RetrievedRow(
                rank=h.rank,
                chunk_id=h.chunk.chunk_id,
                meeting_id=h.chunk.meeting_id,
                lexical_rank=h.lexical_rank,
                dense_rank=h.dense_rank,
                rrf_score=h.rrf_score,
            )
            for h in hits
        )
        blocks, kept, omitted = assemble_context(
            question.text,
            [h.chunk for h in hits],
            context_window=self.settings.context_window,
            max_generation_tokens=self.settings.max_generation_tokens,
        )
        base: dict[str, Any] = {
            "retrieved": retrieved,
            "omitted": tuple(OmittedTrace(c.chunk_id, c.meeting_id) for c in omitted),
        }
        if not blocks:
            trace = self._trace(question, OUTCOME_NO_MATCH, **base)
            return self._abstention(question, NO_MATCH, trace)
        base["context_blocks"] = tuple(
            ContextBlockTrace(i, c.chunk_id, c.meeting_id, excerpted, text)
            for i, (text, (c, excerpted)) in enumerate(zip(blocks, kept, strict=True), 1)
        )
        chunks = [c for c, _ in kept]

        user_content = _user_content(blocks, question.text)
        base["user_sha256"] = sent_prompt_sha256(user_content)
        suff_system = sufficiency_prompt()
        degraded = False
        if self.sufficiency_check:
            holds, degraded, sufficiency_reply = self._check_sufficiency(suff_system, user_content)
            base.update(
                sufficiency_invoked=True,
                sufficiency_degraded=degraded,
                sufficiency_raw_reply=sufficiency_reply,
                sufficiency_sha256=sent_prompt_sha256(suff_system),
            )
            if not holds:
                trace = self._trace(question, OUTCOME_NO_ANSWER_IN_CONTEXT, **base)
                return self._abstention(question, NO_ANSWER_IN_CONTEXT, trace)

        system = system_prompt()
        reply = self.chat.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
            model=self.settings.model,
            options=self.settings.options,
        )
        prose, reported, attribution = split_attribution(reply, len(blocks))
        if reported is None:
            cited = chunks  # no usable report: every block sent is cited (pre-#753 behaviour)
        else:
            cited = [c for position, c in enumerate(chunks, 1) if position in reported]
        trace = self._trace(
            question,
            OUTCOME_ANSWERED,
            used_indices=tuple(sorted(reported)) if reported is not None else (),
            attribution=attribution,
            cited_chunk_ids=tuple(c.chunk_id for c in cited),
            cited_acts={c.chunk_id: c.dialogue_act_ids for c in cited},
            raw_reply=reply,
            system_sha256=sent_prompt_sha256(system),
            **base,
        )
        answer = Answer(
            question_id=question.id,
            condition=self.condition_id,
            text=strip_concept_id_scaffolding(prose),
            cited_evidence=_evidence_spans(cited),
        )
        return answer, trace

    def _check_sufficiency(self, system: str, user_content: str) -> tuple[bool, bool, str | None]:
        """``_context_holds_the_answer``: ``(holds, degraded, reply)``; fails open on ChatError."""
        try:
            reply = self.chat.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
                model=self.settings.model,
                options=self.settings.options,
            )
        except ChatUnavailableError:
            raise
        except ChatError:
            return True, True, None
        return _sufficiency_holds(reply), False, reply


def _evidence_spans(chunks: Sequence[Chunk]) -> tuple[EvidenceSpan, ...]:
    """Dialogue acts of the cited chunks, grouped by meeting (first-seen order, no repeats)."""
    by_meeting: dict[str, dict[str, None]] = {}
    for chunk in chunks:
        acts = by_meeting.setdefault(chunk.meeting_id, {})
        acts.update(dict.fromkeys(chunk.dialogue_act_ids))
    return tuple(
        EvidenceSpan(meeting_id=meeting, dialogue_act_ids=tuple(acts))
        for meeting, acts in sorted(by_meeting.items())
        if acts
    )


__all__ = [
    "NO_ANSWER_IN_CONTEXT",
    "NO_MATCH",
    "AnswerTrace",
    "ChatBackend",
    "ChatError",
    "ChatUnavailableError",
    "DocumentRagCondition",
    "GenerationSettings",
    "OllamaChatBackend",
    "assemble_context",
    "split_attribution",
    "strip_concept_id_scaffolding",
]
