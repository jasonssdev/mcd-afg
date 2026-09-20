"""The decision object, per thesis section 5.2.

Thesis section 5.2 defines a decision as a commitment on an action or product property
that satisfies three conditions: explicit (formulated or ratified in at least one dialogue
act), accepted (not left as an open proposal at segment close), and anchored (identifies
both a decision object -- what is being decided -- and its content -- what was decided).

Proposals that are never accepted, open questions, and opinions are deliberately kept in
the reference set as *non-decisions*: they are needed to measure false positives, not
discarded.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DecisionStatus(StrEnum):
    """Status of an annotated or extracted decision object.

    ``ACCEPTED`` is the only status that satisfies the full definition in thesis section
    5.2 and counts as a decision proper. The other three statuses are *non-decisions*,
    kept in the reference set to measure false positives (thesis section 5.2).
    """

    ACCEPTED = "accepted"
    """Explicit, accepted, and anchored -- a decision proper."""

    OPEN_PROPOSAL = "open_proposal"
    """Proposed but not accepted by the close of the discussion segment."""

    OPEN_QUESTION = "open_question"
    """An unresolved question raised but never settled in the segment."""

    OPINION = "opinion"
    """A stated preference or opinion that never became a commitment."""


class EvidenceSpan(BaseModel):
    """Pointer from a decision to the dialogue acts that support it.

    Modeled as an ordered list of dialogue act identifiers rather than a numeric
    start/end pair: AMI dialogue act ids are not guaranteed to be contiguous integers, and
    asserting a specific id format here would violate the "no unverified AMI facts" rule.
    See ``src/afg/corpus/nxt.py`` for how these ids are discovered from the corpus.
    """

    model_config = ConfigDict(frozen=True)

    meeting_id: str = Field(description="AMI meeting id, e.g. 'ES2015a'.")
    dialogue_act_ids: tuple[str, ...] = Field(
        min_length=1,
        description="Ordered dialogue act ids that constitute the evidence for this decision.",
    )


class Decision(BaseModel):
    """A decision (or non-decision) entity, gold-annotated or extracted.

    See thesis section 5.2 for the operational definition and
    ``src/afg/annotation/goldset.py`` for how the gold set is built from existing AMI
    annotation layers.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable identifier, unique within a series.")
    series_id: str = Field(description="AMI series id, e.g. 'ES2015'.")
    meeting_id: str = Field(description="AMI meeting id of origin, e.g. 'ES2015a'.")
    decision_object: str = Field(description="What is being decided (thesis 5.2: 'objeto').")
    content: str = Field(description="What was decided about the object (thesis 5.2: 'contenido').")
    status: DecisionStatus
    evidence: EvidenceSpan
    annotator: str | None = Field(
        default=None, description="Annotator id, when human-annotated; None if system-extracted."
    )

    @property
    def is_decision(self) -> bool:
        """True only for ``ACCEPTED`` decisions; non-decisions exist to measure false positives."""
        return self.status is DecisionStatus.ACCEPTED
