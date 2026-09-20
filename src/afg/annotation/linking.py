"""Chronological cross-meeting relation annotation (thesis sections 3 OE1, 5.1).

Two things are fully specified and corpus-independent, so they are implemented and tested
here: which (source, target) decision pairs are even eligible for a relation (same series,
source's meeting no earlier than target's), and validating that a proposed relation
respects the anti-leakage constraint (thesis section 5.1: annotation proceeds in
chronological order, without access to meetings after the one being annotated).

Actually assigning a :class:`~afg.domain.relation.RelationType` to a pair is a human
annotation act (or, later, a model's extraction) and is out of scope for this module.
"""

from __future__ import annotations

from itertools import combinations

from afg.domain.decision import Decision
from afg.domain.meeting import Meeting
from afg.domain.relation import TemporalRelation

# AMI scenario-design series run through four meetings in a fixed letter order (thesis
# section 5.0: kickoff, functional design, conceptual design, detailed design). This
# ordering is stated directly in the thesis, not an inferred corpus schema detail, so it
# is safe to encode here without an ASSUMPTION marker.
_MEETING_LETTER_ORDER = {"a": 0, "b": 1, "c": 2, "d": 3}


def meeting_order_index(meeting_id: str) -> int:
    """Return the chronological index (0-3) of a meeting within its series.

    Raises:
        ValueError: if ``meeting_id`` does not end in one of the four expected letters.
    """
    if not meeting_id or meeting_id[-1] not in _MEETING_LETTER_ORDER:
        raise ValueError(
            f"Cannot determine chronological order for meeting id {meeting_id!r}: "
            "expected it to end in one of 'a', 'b', 'c', 'd'."
        )
    return _MEETING_LETTER_ORDER[meeting_id[-1]]


def chronological_candidate_pairs(decisions: list[Decision]) -> list[tuple[Decision, Decision]]:
    """Generate candidate (source, target) pairs eligible for a temporal relation.

    A pair is eligible only if both decisions belong to the same series and the source's
    meeting is chronologically at or after the target's meeting -- never the reverse,
    which enforces the thesis section 5.1 anti-leakage rule structurally rather than
    relying on annotators to self-police it.
    """
    candidates: list[tuple[Decision, Decision]] = []
    by_series: dict[str, list[Decision]] = {}
    for decision in decisions:
        by_series.setdefault(decision.series_id, []).append(decision)

    for series_decisions in by_series.values():
        for a, b in combinations(series_decisions, 2):
            order_a = meeting_order_index(a.meeting_id)
            order_b = meeting_order_index(b.meeting_id)
            if order_a == order_b:
                continue
            source, target = (a, b) if order_a > order_b else (b, a)
            candidates.append((source, target))

    return candidates


def validate_no_leakage(relation: TemporalRelation, decisions_by_id: dict[str, Decision]) -> bool:
    """Check that a proposed relation's source is not chronologically before its target.

    Returns False (rather than raising) for a relation whose decision ids are not found in
    ``decisions_by_id``, since that indicates a data-consistency problem for the caller to
    surface, not a leakage violation per se.
    """
    source = decisions_by_id.get(relation.source_decision_id)
    target = decisions_by_id.get(relation.target_decision_id)
    if source is None or target is None:
        return False
    return meeting_order_index(source.meeting_id) >= meeting_order_index(target.meeting_id)


def meetings_visible_when_annotating(
    decision: Decision, series_meetings: list[Meeting]
) -> list[Meeting]:
    """Meetings an annotator may consult while annotating relations for ``decision``.

    Thesis section 5.1: annotation happens in chronological order, without access to
    meetings after the one being annotated. Returns every meeting whose order index is
    less than or equal to ``decision``'s meeting.
    """
    decision_order = meeting_order_index(decision.meeting_id)
    return [m for m in series_meetings if meeting_order_index(m.id) <= decision_order]
