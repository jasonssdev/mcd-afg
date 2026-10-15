"""Tuning of C1 segmentation and of the common K on development data (ADR 0005).

The experiment fixes how many blocks (K) reach the answer prompt and how C1 cuts the
transcripts (``max_chars``, ``overlap_turns``). Both are chosen here, before any evaluation
series is touched, by measuring **evidence recall** and nothing generative: the fraction of
the dialogue acts that support the reference answer (``reference_evidence``) which reach the
model. Two figures are computed:

* **delivered recall** (primary, drives the selection): an act counts only if every turn
  that carries it is present, whole, in the text OpenKOS v0.5.4 would send, i.e. after the
  context budget is split across the K blocks (``fair_shares``) and each block trimmed
  (``bounded_text``). It reuses :func:`afg.conditions.c1_document_rag.assemble_context`, the
  very function C1 answers with, so the measurement cannot drift from the condition;
* **full-chunk recall** (secondary): the act is anywhere in the retrieved chunk, trimmed or
  not. It was the only figure of the first tuning (ADR 0007) and is kept for comparison.

A chunk contains the acts of the turns it covers (``Chunk.dialogue_act_ids``).

The grid, the character budget and the tie margin live in ``[retrieval.tuning]`` of
``config/experiments.toml`` and are committed before any result is seen. The selection rule
(:func:`select_winner`) is a pure function of the results.

Cost: the index is built once per ``(max_chars, overlap_turns)`` and each question is
retrieved once with the largest K of the grid; the ranking for a smaller K is its prefix.
That holds only while the retriever's candidate pool is fixed, i.e. K <= ``MIN_POOL``
(``max(limit, MIN_POOL)`` candidates per channel); above that the pool grows with the limit
and the ranking can change, so the grid retrieves once per K instead.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.conditions.c1_chunking import (
    Chunk,
    chunk_meetings,
    load_frozen_turns,
    render_turn,
)
from afg.conditions.c1_retrieval import MIN_POOL, Embedder, HybridRetriever, configured_rrf_k
from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.shared.config import load_experiments_config
from afg.shared.paths import REPORTS_DIR, TRANSCRIPTS_DIR

RESULTS_PATH: Path = REPORTS_DIR / "c1-tuning" / "resultados.json"


class NoEligibleConfigError(ValueError):
    """Raised when no configuration fits the character budget."""


# --- metrics ---------------------------------------------------------------------------


def _acts(evidence: Sequence[EvidenceSpan]) -> set[tuple[str, str]]:
    return {(span.meeting_id, act) for span in evidence for act in span.dialogue_act_ids}


def evidence_recall(retrieved: Sequence[Chunk], evidence: Sequence[EvidenceSpan]) -> float:
    """Fraction of the reference dialogue acts contained in the union of ``retrieved``.

    Raises:
        ValueError: if ``evidence`` is empty (unanswerable questions are excluded upstream).
    """
    wanted = _acts(evidence)
    if not wanted:
        raise ValueError("evidence_recall needs reference evidence; E4 questions have none.")
    found = {(c.meeting_id, act) for c in retrieved for act in c.dialogue_act_ids}
    return len(wanted & found) / len(wanted)


def first_hit_rank(retrieved: Sequence[Chunk], evidence: Sequence[EvidenceSpan]) -> int | None:
    """1-based rank of the first chunk holding any reference act; ``None`` if none does."""
    wanted = _acts(evidence)
    for rank, c in enumerate(retrieved, start=1):
        if any((c.meeting_id, act) in wanted for act in c.dialogue_act_ids):
            return rank
    return None


ActTurns = Mapping[tuple[str, str], Sequence[tuple[int, str]]]
"""``(meeting_id, act_id)`` -> the ``(turn_index, rendered line)`` of every turn carrying it."""


def load_act_turns(meeting_ids: Sequence[str], transcripts_dir: Path = TRANSCRIPTS_DIR) -> ActTurns:
    """Index the frozen transcripts by dialogue act, with each turn as C1 renders it."""
    acts: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for meeting_id in meeting_ids:
        for turn in load_frozen_turns(meeting_id, transcripts_dir):
            line = render_turn(turn)
            for act in turn.dialogue_act_ids:
                acts.setdefault((meeting_id, act), []).append((turn.turn_index, line))
    return acts


def _present(line: str, text: str, lines: set[str]) -> bool:
    """Whether the whole ``line`` is in ``text`` (a multi-line turn is checked as a substring)."""
    return line in lines if "\n" not in line else line in text


def delivered_recall(
    delivered: Sequence[tuple[Chunk, str]], evidence: Sequence[EvidenceSpan], act_turns: ActTurns
) -> float:
    """Fraction of the reference acts whose full text is in the delivered blocks.

    ``delivered`` pairs each chunk with the block text sent to the model (after the budget
    trimming). An act is delivered when some block of a chunk holding it contains, as whole
    lines, every turn of the act that lies inside that chunk; a turn is a line of the chunk
    (``ROLE: text``) and the trimming keeps or drops whole lines, so no normalisation is
    needed and a short turn cannot match inside a longer one.

    Raises:
        ValueError: if ``evidence`` is empty (unanswerable questions are excluded upstream).
    """
    wanted = _acts(evidence)
    if not wanted:
        raise ValueError("delivered_recall needs reference evidence; E4 questions have none.")
    split = [(chunk, text, set(text.split("\n"))) for chunk, text in delivered]
    found = 0
    for meeting_id, act in wanted:
        turns = act_turns.get((meeting_id, act), ())
        for chunk, text, lines in split:
            if chunk.meeting_id != meeting_id or act not in chunk.dialogue_act_ids:
                continue
            inside = [t for t in turns if chunk.first_turn <= t[0] <= chunk.last_turn]
            if inside and all(_present(line, text, lines) for _, line in inside):
                found += 1
                break
    return found / len(wanted)


# --- configuration ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TuningConfig:
    """The pre-registered grid and selection parameters (``[retrieval.tuning]``)."""

    series: tuple[str, ...]
    max_chars: tuple[int, ...]
    overlap_turns: tuple[int, ...]
    k: tuple[int, ...]
    char_budget: int
    tie_margin: float


def load_tuning_config(
    experiments: dict[str, Any] | None = None, development: frozenset[str] | None = None
) -> TuningConfig:
    """Read ``[retrieval.tuning]``, refusing any series outside the development split.

    Raises:
        ValueError: if a listed series is not a development series (ADR 0005) or a list is
            empty.
    """
    from afg.evaluation.judge_calibration_set import development_series

    section = (experiments or load_experiments_config())["retrieval"]["tuning"]
    allowed = development if development is not None else development_series()
    series = tuple(section["series"])
    outside = sorted(set(series) - allowed)
    if outside:
        raise ValueError(
            f"[retrieval.tuning].series lists {outside}, which are not development series "
            f"{sorted(allowed)} (ADR 0005): C1 is tuned on development data only."
        )
    config = TuningConfig(
        series=series,
        max_chars=tuple(int(v) for v in section["max_chars"]),
        overlap_turns=tuple(int(v) for v in section["overlap_turns"]),
        k=tuple(int(v) for v in section["k"]),
        char_budget=int(section["char_budget"]),
        tie_margin=float(section["tie_margin"]),
    )
    if not (config.series and config.max_chars and config.overlap_turns and config.k):
        raise ValueError("[retrieval.tuning] needs non-empty series, max_chars, overlap_turns, k.")
    return config


@dataclass(frozen=True, slots=True)
class PinnedC1Params:
    """The C1 segmentation and K chosen by the tuning (``[retrieval.c1]``)."""

    max_chars: int
    overlap_turns: int
    k: int


def load_pinned_c1_params(experiments: dict[str, Any] | None = None) -> PinnedC1Params:
    """Read ``[retrieval.c1]``, the parameters C1 runs with (ADR 0007).

    Raises:
        ValueError: if the section or one of its keys is missing.
    """
    try:
        section = (experiments or load_experiments_config())["retrieval"]["c1"]
        return PinnedC1Params(
            max_chars=int(section["max_chars"]),
            overlap_turns=int(section["overlap_turns"]),
            k=int(section["k"]),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"[retrieval.c1] is missing or incomplete ({exc!r}).") from exc


# --- questions -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TuningQuestion:
    question_id: str
    stratum: QuestionStratum
    question: str
    evidence: tuple[EvidenceSpan, ...]


def load_tuning_questions(path: Path, series: Sequence[str]) -> list[TuningQuestion]:
    """Answerable (E1-E3) questions of ``series`` from the calibration set, once each.

    The calibration set carries every question twice or more (one row per answer variant,
    ``<series>.<question>.<variant>``); the question id is the id without the variant.
    """
    from afg.evaluation.judge_calibration_set import load_calibration_items

    questions: dict[str, TuningQuestion] = {}
    for item in load_calibration_items(path):
        if item.series_id not in series or item.stratum is QuestionStratum.E4_UNANSWERABLE:
            continue
        question_id = item.id.rsplit(".", 1)[0]
        questions.setdefault(
            question_id,
            TuningQuestion(question_id, item.stratum, item.question, item.reference_evidence),
        )
    return list(questions.values())


def series_meetings(series: str, transcripts_dir: Path = TRANSCRIPTS_DIR) -> list[str]:
    """Meeting ids of ``series`` with a frozen transcript, sorted (D15: the whole series)."""
    ids = sorted(
        p.stem for p in transcripts_dir.glob(f"{series}?.jsonl") if len(p.stem) == len(series) + 1
    )
    if not ids:
        raise FileNotFoundError(
            f"No frozen transcripts for series {series} in {transcripts_dir}. "
            "Render them first (`uv run afg corpus transcripts`)."
        )
    return ids


# --- grid ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfigResult:
    """Recall of one ``(max_chars, overlap_turns, k)`` configuration.

    ``mean_recall`` / ``recalls`` / ``mean_context_chars`` are over the full retrieved chunks;
    the ``delivered`` figures are over the text left after OpenKOS's context budget (primary).
    """

    max_chars: int
    overlap_turns: int
    k: int
    mean_recall: float
    recalls: dict[str, float]
    mean_delivered_recall: float
    delivered_recalls: dict[str, float]
    mean_delivered_chars: float
    first_hit_ranks: dict[str, int | None]
    mean_context_chars: float
    n_chunks: int
    eligible: bool


def questions_with_any_hit(result: ConfigResult) -> int:
    """Number of questions for which at least one retrieved chunk holds a reference act."""
    return sum(1 for rank in result.first_hit_ranks.values() if rank is not None)


def questions_with_any_delivered_hit(result: ConfigResult) -> int:
    """Number of questions with at least one reference act delivered to the model."""
    return sum(1 for value in result.delivered_recalls.values() if value > 0)


ProgressFn = Callable[[int, int, int, int], None]
"""``(max_chars, overlap_turns, done, total)`` after each chunking configuration."""


def evaluate_grid(
    questions: Sequence[TuningQuestion],
    meeting_ids: Sequence[str],
    config: TuningConfig,
    embedder: Embedder,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    *,
    rrf_k: int | None = None,
    progress: ProgressFn | None = None,
    context_window: int | None = None,
    max_generation_tokens: int | None = None,
) -> list[ConfigResult]:
    """Measure evidence recall for every ``(max_chars, overlap_turns, k)`` of the grid.

    ``context_window`` and ``max_generation_tokens`` default to ``[shared_budget]``, the
    values C1 answers with, and set the text budget the retrieved blocks are trimmed to.
    """
    # Imported here: c1_document_rag imports this module for the pinned parameters.
    from afg.conditions.c1_document_rag import assemble_context

    if not questions:
        raise ValueError("evaluate_grid needs at least one question (got no questions).")
    if context_window is None or max_generation_tokens is None:
        shared = load_experiments_config()["shared_budget"]
        context_window = context_window or int(shared["context_window_tokens"])
        max_generation_tokens = max_generation_tokens or int(shared["max_generation_tokens"])
    act_turns = load_act_turns(meeting_ids, transcripts_dir)
    ks = sorted(set(config.k))
    # Top-K is a prefix of top-maxK only while the candidate pool is fixed (see module doc).
    prefix_stable = ks[-1] <= MIN_POOL
    fusion_k = rrf_k if rrf_k is not None else configured_rrf_k()
    pairs = [(m, o) for m in config.max_chars for o in config.overlap_turns]
    results: list[ConfigResult] = []
    for done, (max_chars, overlap) in enumerate(pairs, start=1):
        chunks = chunk_meetings(meeting_ids, max_chars, overlap, transcripts_dir)
        retriever = HybridRetriever(chunks, embedder, rrf_k=fusion_k)
        rankings: dict[str, dict[int, list[Chunk]]] = {}
        for q in questions:
            if prefix_stable:
                full = [h.chunk for h in retriever.retrieve(q.question, ks[-1])]
                rankings[q.question_id] = {k: full[:k] for k in ks}
            else:
                rankings[q.question_id] = {
                    k: [h.chunk for h in retriever.retrieve(q.question, k)] for k in ks
                }
        for k in ks:
            recalls = {
                q.question_id: evidence_recall(rankings[q.question_id][k], q.evidence)
                for q in questions
            }
            ranks = {
                q.question_id: first_hit_rank(rankings[q.question_id][k], q.evidence)
                for q in questions
            }
            context = [sum(len(c.text) for c in rankings[q.question_id][k]) for q in questions]
            delivered_recalls: dict[str, float] = {}
            delivered_chars: list[int] = []
            for q in questions:
                retrieved = rankings[q.question_id][k]
                blocks, kept, _ = assemble_context(
                    q.question,
                    retrieved,
                    context_window=context_window,
                    max_generation_tokens=max_generation_tokens,
                )
                delivered_recalls[q.question_id] = delivered_recall(
                    [(c, text) for (c, _), text in zip(kept, blocks, strict=True)],
                    q.evidence,
                    act_turns,
                )
                delivered_chars.append(sum(len(b) for b in blocks))
            results.append(
                ConfigResult(
                    max_chars=max_chars,
                    overlap_turns=overlap,
                    k=k,
                    mean_recall=sum(recalls.values()) / len(recalls),
                    recalls=recalls,
                    mean_delivered_recall=sum(delivered_recalls.values()) / len(delivered_recalls),
                    delivered_recalls=delivered_recalls,
                    mean_delivered_chars=sum(delivered_chars) / len(delivered_chars),
                    first_hit_ranks=ranks,
                    mean_context_chars=sum(context) / len(context),
                    n_chunks=len(chunks),
                    eligible=k * max_chars <= config.char_budget,
                )
            )
        if progress is not None:
            progress(max_chars, overlap, done, len(pairs))
    return results


# --- selection -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Selection:
    winner: ConfigResult
    best_recall: float
    near_ties: int
    reason: str


def select_winner(results: Sequence[ConfigResult], tie_margin: float) -> Selection:
    """The pre-registered rule: highest delivered recall among eligible, ties by smaller cost.

    The rule is unchanged from the first tuning; only the recall it ranks is now the one
    measured over the text that reaches the model (``mean_delivered_recall``). Among eligible
    configurations whose mean delivered recall is within ``tie_margin`` (inclusive) of
    the best, the winner has the smaller ``k``, then smaller ``max_chars``, then smaller
    ``overlap_turns``.

    Raises:
        NoEligibleConfigError: if no configuration fits the character budget.
    """
    eligible = [r for r in results if r.eligible]
    if not eligible:
        raise NoEligibleConfigError(
            "No configuration fits the char_budget (k * max_chars <= char_budget); "
            "the pre-registered grid has no admissible point."
        )
    best = max(r.mean_delivered_recall for r in eligible)
    # Small epsilon so a gap of exactly tie_margin is not lost to float rounding.
    near = [r for r in eligible if best - r.mean_delivered_recall <= tie_margin + 1e-12]
    winner = min(near, key=lambda r: (r.k, r.max_chars, r.overlap_turns))
    reason = (
        f"best eligible mean delivered recall {best:.3f}; {len(near)} eligible config(s) "
        f"within {tie_margin:g}; chose the smallest k, then max_chars, then overlap_turns "
        f"(delivered recall {winner.mean_delivered_recall:.3f})."
    )
    return Selection(winner=winner, best_recall=best, near_ties=len(near), reason=reason)


# --- results file ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoredTuning:
    config: TuningConfig
    n_questions: int
    results: tuple[ConfigResult, ...]
    winner: ConfigResult
    reason: str


def _result_to_json(r: ConfigResult) -> dict[str, Any]:
    return {
        "max_chars": r.max_chars,
        "overlap_turns": r.overlap_turns,
        "k": r.k,
        "mean_recall": r.mean_recall,
        "recalls": r.recalls,
        "mean_delivered_recall": r.mean_delivered_recall,
        "delivered_recalls": r.delivered_recalls,
        "mean_delivered_chars": r.mean_delivered_chars,
        "first_hit_ranks": r.first_hit_ranks,
        "mean_context_chars": r.mean_context_chars,
        "n_chunks": r.n_chunks,
        "eligible": r.eligible,
    }


def save_tuning_results(
    path: Path,
    results: Sequence[ConfigResult],
    selection: Selection,
    *,
    config: TuningConfig,
    n_questions: int,
) -> None:
    """Write the grid results and the decision as JSON (UTF-8, LF), creating the folder."""
    w = selection.winner
    payload = {
        "n_questions": n_questions,
        "config": {
            "series": list(config.series),
            "max_chars": list(config.max_chars),
            "overlap_turns": list(config.overlap_turns),
            "k": list(config.k),
            "char_budget": config.char_budget,
            "tie_margin": config.tie_margin,
        },
        "results": [_result_to_json(r) for r in results],
        "decision": {
            "max_chars": w.max_chars,
            "overlap_turns": w.overlap_turns,
            "k": w.k,
            "reason": selection.reason,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_tuning_results(path: Path) -> StoredTuning:
    """Read what :func:`save_tuning_results` wrote."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data["config"]
        config = TuningConfig(
            series=tuple(raw["series"]),
            max_chars=tuple(raw["max_chars"]),
            overlap_turns=tuple(raw["overlap_turns"]),
            k=tuple(raw["k"]),
            char_budget=int(raw["char_budget"]),
            tie_margin=float(raw["tie_margin"]),
        )
        results = tuple(ConfigResult(**r) for r in data["results"])
        d = data["decision"]
        winner = next(
            r
            for r in results
            if (r.max_chars, r.overlap_turns, r.k) == (d["max_chars"], d["overlap_turns"], d["k"])
        )
        return StoredTuning(config, int(data["n_questions"]), results, winner, str(d["reason"]))
    except (ValueError, KeyError, TypeError, StopIteration, OSError) as exc:
        raise ValueError(f"{path.name}: could not be read ({exc!r}).") from exc
