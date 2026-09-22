"""The question bank and answers, per thesis section 5.5.

The question bank is built from the OE1 gold annotation so every question has a reference
answer derivable from evidence, and is stratified into four categories that discriminate
between the three conditions (thesis section 5.5 table).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from afg.domain.decision import EvidenceSpan


class QuestionStratum(StrEnum):
    """The four question strata (thesis section 5.5). Order matches the thesis table."""

    E1_POINT_FACT = "E1_point_fact"
    """Point fact: parity is expected across conditions; a loss here signals a regression."""

    E2_CURRENT_STATE = "E2_current_state"
    """Current state: requires knowing which of several versions of a decision prevails."""

    E3_EVOLUTION = "E3_evolution"
    """Evolution: did the decision change, when, and why. The stratum that tests the thesis."""

    E4_UNANSWERABLE = "E4_unanswerable"
    """Unanswerable: adjacent-domain questions with no answer in the material; measures
    whether the system abstains or fabricates."""


class Question(BaseModel):
    """A single question in the evaluation bank."""

    model_config = ConfigDict(frozen=True)

    id: str
    series_id: str
    stratum: QuestionStratum
    text: str
    reference_answer: str | None = Field(
        default=None,
        description="Reference answer derived from OE1 evidence. None for E4 "
        "(unanswerable) questions, where the reference is the absence of an answer.",
    )
    reference_evidence: tuple[EvidenceSpan, ...] = Field(default_factory=tuple)
    author: str | None = Field(
        default=None, description="Person who wrote the question (must differ from the validator)."
    )
    validated_by: str | None = Field(default=None)
    validation_notes: str | None = Field(
        default=None,
        description="Reason the validator writes when returning a question that did not "
        "pass, instead of correcting it. The author clears it when re-submitting the "
        "corrected question.",
    )


class Answer(BaseModel):
    """A system-produced answer to a :class:`Question`, under one condition (C1/C2/C3)."""

    model_config = ConfigDict(frozen=True)

    question_id: str
    condition: str = Field(
        description="Condition id that produced this answer: 'C1', 'C2', or 'C3'."
    )
    text: str
    cited_evidence: tuple[EvidenceSpan, ...] = Field(default_factory=tuple)
    abstained: bool = Field(
        default=False, description="True if the system declined to answer rather than fabricate."
    )
