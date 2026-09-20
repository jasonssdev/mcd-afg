"""Extractor interface: anything that can turn a meeting transcript into decisions and
temporal relations, used by both C2 (compiled-automatic) and the OE2 extraction runner.

Defined as a :class:`typing.Protocol` rather than an ABC so any extractor implementation
(OpenKOS-backed, a mock for tests, a future alternative engine) can satisfy it structurally
without inheriting from a shared base class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from afg.domain.decision import Decision
from afg.domain.relation import TemporalRelation


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Output of one extraction run over one meeting (or series)."""

    decisions: tuple[Decision, ...] = field(default_factory=tuple)
    relations: tuple[TemporalRelation, ...] = field(default_factory=tuple)


@runtime_checkable
class Extractor(Protocol):
    """Anything that extracts decisions and temporal relations from meeting transcripts."""

    def extract(self, meeting_id: str, transcript: str) -> ExtractionResult:
        """Extract decisions and temporal relations from one meeting's transcript.

        Implementations should be safe to call repeatedly with the same input (thesis
        section 5.8 requires >=3 repeated runs per configuration to measure variance) and
        should not mutate shared state between calls.
        """
        ...
