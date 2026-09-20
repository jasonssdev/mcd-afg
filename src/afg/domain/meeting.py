"""Meetings and series, per thesis section 5.0.

AMI's remote-control design scenario organizes meetings into series of four, held by the
same four participants, moving through four fixed phases. See ``config/corpus.toml`` for
the phase-letter mapping and its verification status.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MeetingPhase(StrEnum):
    """The four fixed phases of an AMI scenario-design series (thesis section 5.0)."""

    KICKOFF = "kickoff"
    FUNCTIONAL_DESIGN = "functional_design"
    CONCEPTUAL_DESIGN = "conceptual_design"
    DETAILED_DESIGN = "detailed_design"


class Meeting(BaseModel):
    """A single AMI meeting."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="AMI meeting id, e.g. 'ES2015a'.")
    series_id: str = Field(description="AMI series id, e.g. 'ES2015'.")
    phase: MeetingPhase | None = Field(
        default=None,
        description="Meeting phase, when known. None until the letter-to-phase mapping is "
        "verified for this series at paso cero (see config/corpus.toml).",
    )
    has_decision_discussion_segmentation: bool = Field(
        default=False,
        description="Whether this meeting carries the DDS annotation layer (47/170 meetings).",
    )


class Series(BaseModel):
    """An AMI series: four meetings held by the same four participants."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="AMI series id, e.g. 'ES2015'.")
    meetings: tuple[Meeting, ...] = Field(description="Meetings in chronological order.")

    @property
    def is_complete(self) -> bool:
        """True if all four meetings of the series are present."""
        return len(self.meetings) == 4

    @property
    def meeting_ids(self) -> tuple[str, ...]:
        return tuple(meeting.id for meeting in self.meetings)
