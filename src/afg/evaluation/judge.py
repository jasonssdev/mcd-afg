"""LLM judge protocol for answer evaluation (thesis section 5.7).

Thesis section 5.7: answers are anonymized and order-randomized before judging (Wang et
al., 2024, position bias), the judge model must belong to a different family than the
extractor (Panickssery et al., 2024, self-preference bias), and at least 20% of judged
answers receive human validation with judge-human concordance reported; if concordance is
low, automatic judging is discarded in favor of the human subsample alone.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def judge_answer(question: Question, answer: Answer, *, judge_model: str) -> JudgeVerdict:
    """Judge one answer against its reference, per thesis section 5.7.

    Not implemented: requires a running judge model backend (local, per thesis section
    5.9's local-first requirement) and the anonymization/order-randomization harness
    around a full evaluation batch, not a single answer in isolation. Implement once the
    `llm` optional dependency group is wired to a concrete local inference client.
    """
    raise NotImplementedError(
        "judge_answer requires a local judge model backend (thesis section 5.7) that is "
        "not wired up yet. require_distinct_model_families() is implemented and tested "
        "independently of the backend; implement the actual judging call once the `llm` "
        "optional dependency is connected to a real client."
    )
