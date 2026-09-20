"""Computation layer for the thesis section 5.1 data audit.

Every public function here takes ``ami_root: Path`` (default
:data:`afg.shared.paths.AMI_DIR`) and returns a pandas ``DataFrame`` or a frozen
dataclass -- never prints, never writes a file as a side effect of import. The notebook
that consumes this package only calls and plots; every number it shows must trace back to
a tested function in this package, not to an ad-hoc notebook cell.

Submodules:

- :mod:`afg.audit.coverage` -- annotation-layer coverage and OE1 series eligibility.
- :mod:`afg.audit.decisions` -- decision-sentence counts, shape, and marker hints.
- :mod:`afg.audit.evidence` -- summlink anchoring rates and role authorship.
- :mod:`afg.audit.topics` -- decision/topic boundary coincidence (an own measurement).
- :mod:`afg.audit.blocker` -- blocker operating-point sensitivity grid.
"""

from __future__ import annotations

from afg.audit.blocker import TURBO_BUTTON_PAIR, blocker_sensitivity
from afg.audit.coverage import layer_coverage, series_eligibility
from afg.audit.decisions import (
    NON_DECISION_MARKERS,
    decision_counts,
    decisions_by_meeting_position,
    non_decision_markers,
    sentence_shape,
)
from afg.audit.evidence import anchoring_rates, role_authorship
from afg.audit.topics import TopicBoundaryOverlapResult, topic_decision_boundary_overlap

__all__ = [
    "NON_DECISION_MARKERS",
    "TURBO_BUTTON_PAIR",
    "TopicBoundaryOverlapResult",
    "anchoring_rates",
    "blocker_sensitivity",
    "decision_counts",
    "decisions_by_meeting_position",
    "layer_coverage",
    "non_decision_markers",
    "role_authorship",
    "sentence_shape",
    "series_eligibility",
    "topic_decision_boundary_overlap",
]
