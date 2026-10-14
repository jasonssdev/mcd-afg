"""LLM judge protocol for answer evaluation (thesis section 5.7).

Thesis section 5.7: answers are anonymized and order-randomized before judging (Wang et
al., 2024, position bias), the judge model must belong to a different family than the
extractor (Panickssery et al., 2024, self-preference bias), and at least 20% of judged
answers receive human validation with judge-human concordance reported; if concordance is
low, automatic judging is discarded in favor of the human subsample alone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from afg.domain.question import Answer, Question


class JudgeConfigurationError(ValueError):
    """Raised when the judge and extractor models are not from different families."""


@dataclass(frozen=True, slots=True)
class JudgeVerdict:
    question_id: str
    condition: str
    correct: bool
    evidence_supported: bool
    citation_correct: bool | None
    rationale: str


@dataclass(frozen=True, slots=True)
class JudgeFailure:
    """A judge call whose output could not be turned into a :class:`JudgeVerdict`.

    Returned instead of raised so one malformed output never aborts a batch, and so the
    calibration metrics can count it toward the JSON-validity rate (thesis section 5.7).
    """

    question_id: str
    condition: str
    reason: str
    raw_output: str


def require_distinct_model_families(judge_model: str, generative_model: str) -> None:
    """Enforce thesis section 5.7: judge and extractor must not share a model family.

    This is a structural guard, not a full family-detection heuristic: it only rejects the
    trivial and most dangerous case of running the exact same model id as both judge and
    extractor. It does not attempt to infer family membership across different model ids
    (e.g. two different Qwen sizes) -- that judgment belongs to whoever configures
    ``config/experiments.toml`` and ``.env``, not to string matching here.

    Raises:
        JudgeConfigurationError: if ``judge_model`` is empty or identical to
            ``generative_model``.
    """
    if not judge_model:
        raise JudgeConfigurationError(
            "AFG_JUDGE_MODEL is not set. Thesis section 5.7 requires a judge model from a "
            "different family than the extractor; set it explicitly before judging."
        )
    if judge_model == generative_model:
        raise JudgeConfigurationError(
            f"Judge model {judge_model!r} is identical to the generative/extractor model "
            f"{generative_model!r}. Thesis section 5.7 requires them to differ to avoid "
            "self-preference bias (Panickssery et al., 2024)."
        )


PresentationOrder = Literal["reference_first", "answer_first"]

DEFAULT_SEED = 42
"""Fallback only; experiments pass the seed from ``config/experiments.toml``."""

_NO_REFERENCE_TEXT = "None: the material contains no answer to this question."


class _JudgeOutput(BaseModel):
    """The JSON object the judge must return; also the Ollama ``format`` schema."""

    model_config = ConfigDict(extra="forbid", strict=True)

    correct: bool
    evidence_supported: bool
    rationale: str


class JudgeBackend(Protocol):
    """Runs one judge call and returns the raw text of the reply.

    Injectable so tests use a fake and the harness can swap inference clients.
    """

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        seed: int,
        temperature: float,
        format_schema: dict[str, Any],
    ) -> str: ...


class OllamaJudgeBackend:
    """Judge calls through a local Ollama server (thesis section 5.9, local-first).

    Needs the optional ``llm`` extra; the client is imported on first use so the rest of
    the package works without it.
    """

    def __init__(self, host: str | None = None) -> None:
        self._host = host

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        seed: int,
        temperature: float,
        format_schema: dict[str, Any],
    ) -> str:
        try:
            import ollama
        except ImportError as exc:
            raise RuntimeError(
                "OllamaJudgeBackend needs the optional `llm` extra: `uv sync --extra llm`."
            ) from exc
        from afg.conditions.c1_retrieval import resolve_ollama_host

        client = ollama.Client(host=self._host or resolve_ollama_host())
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            format=format_schema,
            options={"temperature": temperature, "seed": seed},
        )
        return str(response.message.content or "")


def _system_prompt() -> str:
    path = resources.files("afg.evaluation") / "prompts" / "judge.md"
    return path.read_bytes().decode("utf-8")


def _user_prompt(question: Question, answer: Answer, order: PresentationOrder) -> str:
    """Render the material to judge. The condition id is never shown (anonymization)."""
    reference = question.reference_answer or _NO_REFERENCE_TEXT
    candidate = answer.text
    if answer.abstained:
        candidate = f"{candidate}\n(The system abstained from answering.)"
    blocks = {
        "reference_first": [("Reference answer", reference), ("Candidate answer", candidate)],
        "answer_first": [("Candidate answer", candidate), ("Reference answer", reference)],
    }
    if order not in blocks:
        raise ValueError(f"unknown presentation order {order!r}; expected {sorted(blocks)}")
    parts = [f"Question:\n{question.text}"]
    parts.extend(f"{title}:\n{body}" for title, body in blocks[order])
    return "\n\n".join(parts)


def judge_answer(
    question: Question,
    answer: Answer,
    *,
    judge_model: str,
    generative_model: str,
    backend: JudgeBackend,
    order: PresentationOrder = "reference_first",
    seed: int = DEFAULT_SEED,
    temperature: float = 0.0,
) -> JudgeVerdict | JudgeFailure:
    """Judge one answer against its reference, per thesis section 5.7.

    The judge/extractor family guard runs first. Output that is not valid JSON, or that does
    not match the verdict schema, comes back as a :class:`JudgeFailure` so one bad reply
    never aborts a batch and the calibration metrics can count it. Backend errors
    (connection, missing model) propagate: they are not a judgment about the output.

    ``order`` controls whether the reference or the candidate is shown first, for the
    position-bias check (Wang et al., 2024); randomizing it across a batch is the caller's
    job. ``citation_correct`` is always ``None``: the judge sees no source text, so it
    cannot verify citations.
    """
    require_distinct_model_families(judge_model, generative_model)
    raw = backend.complete(
        _system_prompt(),
        _user_prompt(question, answer, order),
        model=judge_model,
        seed=seed,
        temperature=temperature,
        format_schema=_JudgeOutput.model_json_schema(),
    )
    try:
        parsed = _JudgeOutput.model_validate(json.loads(raw))
    except json.JSONDecodeError:
        return JudgeFailure(question.id, answer.condition, "invalid_json", raw)
    except ValidationError:
        return JudgeFailure(question.id, answer.condition, "schema_violation", raw)
    return JudgeVerdict(
        question_id=question.id,
        condition=answer.condition,
        correct=parsed.correct,
        evidence_supported=parsed.evidence_supported,
        citation_correct=None,
        rationale=parsed.rationale,
    )
