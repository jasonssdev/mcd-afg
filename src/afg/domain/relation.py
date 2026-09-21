"""Cross-meeting temporal relations between decisions, per thesis section 3 (OE1) and 5.2.

This is the annotation this thesis adds on top of AMI's existing layers (thesis section
1.6): no published AMI-derived resource links a decision in one meeting to its revision,
reaffirmation, or reversal in a later meeting of the same series. ``RelationType`` is the
closed label set for that new annotation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from afg.domain.decision import EvidenceSpan


class RelationType(StrEnum):
    """Closed set of cross-meeting temporal relation labels (thesis section 3, OE1).

    Values are kept in Spanish verbatim because they are the annotation labels defined by
    the thesis itself, not a translatable implementation detail -- changing them would
    break comparability with the gold annotation guidelines
    (``docs/anotacion/annotation-guidelines.md``).
    """

    INTRODUCE = "introduce"
    """The source decision is the first occurrence of this decision object in the series."""

    REAFIRMA = "reafirma"
    """The source decision restates the target decision without changing its content."""

    REFINA = "refina"
    """The source decision narrows or elaborates the target decision's content."""

    REVIERTE = "revierte"
    """The source decision explicitly reverses the target decision."""

    REEMPLAZA = "reemplaza"
    """The source decision supersedes the target decision with different content."""

    NO_RELACIONADA = "no_relacionada"
    """The pair was evaluated as a candidate but has no temporal relation."""


class DirectionOk(StrEnum):
    """The ``direction_ok`` column's closed value set in the Task-B annotation CSV.

    Annotation-file contract, like :class:`~afg.domain.decision.AnnotationStatus`: these
    are the two words an annotator types (manual section 4), not a boolean. ``si`` confirms
    that the pair, as the CSV orders it, respects the direction convention
    (``later`` acts on ``earlier``); ``no`` says the file's chronological order is wrong
    and the annotator explains why in ``notes``.

    Kept as an enum rather than a ``bool`` so ``afg gold validate`` can tell an empty cell
    (not yet annotated) apart from a considered ``no``, and so a typo like ``yes`` or
    ``TRUE`` is rejected instead of silently coerced.
    """

    SI = "si"
    NO = "no"


class Confidence(StrEnum):
    """The ``confidence`` column's closed value set in the Task-B annotation CSV.

    Annotation-file contract (manual section 4). Three ordered levels, in Spanish, because
    that is what the annotator types. No numeric mapping is defined here: nothing consumes
    one yet, and picking 1.0/0.66/0.33 would invent a scale the manual never claimed.
    """

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class TemporalRelation(BaseModel):
    """A directed, typed link between two decisions in the same series.

    Direction matters: ``source_decision_id`` is the later decision (the one doing the
    introducing/reaffirming/refining/reversing/replacing) and ``target_decision_id`` is
    the earlier one it relates to. Direction accuracy (thesis H3) is measured against
    :meth:`inverted`.
    """

    model_config = ConfigDict(frozen=True)

    source_decision_id: str = Field(description="Id of the later decision (the relating one).")
    target_decision_id: str = Field(description="Id of the earlier decision (the related-to one).")
    relation: RelationType
    evidence: EvidenceSpan = Field(
        description="Meeting id and dialogue-act segment supporting this relation; "
        "evidence is mandatory (thesis section 3, OE1)."
    )
    annotator: str | None = Field(
        default=None, description="Annotator id, when human-annotated; None if system-extracted."
    )

    def inverted(self) -> TemporalRelation:
        """Return the same relation with source and target swapped.

        Used to score direction accuracy (thesis H3): a system that identifies the correct
        relation type but swaps which decision relates to which produces exactly this
        inverted relation, and thesis section 5.6 requires that failure mode to be counted
        separately from a wrong relation type.
        """
        return self.model_copy(
            update={
                "source_decision_id": self.target_decision_id,
                "target_decision_id": self.source_decision_id,
            }
        )
