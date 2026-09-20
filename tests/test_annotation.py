"""Tests for OE1 annotation helpers: chronological linking and agreement (thesis section 3)."""

from __future__ import annotations

import pytest

from afg.annotation.agreement import (
    agreement_meets_threshold,
    build_adjudication_log,
    compute_agreement,
)
from afg.annotation.linking import (
    chronological_candidate_pairs,
    meeting_order_index,
    validate_no_leakage,
)
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.domain.relation import RelationType, TemporalRelation


def _decision(id_: str, meeting_id: str, series_id: str = "ES2015") -> Decision:
    return Decision(
        id=id_,
        series_id=series_id,
        meeting_id=meeting_id,
        decision_object="casing material",
        content="use titanium",
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=("d1",)),
    )


class TestMeetingOrderIndex:
    @pytest.mark.parametrize(
        ("meeting_id", "expected"), [("ES2015a", 0), ("ES2015b", 1), ("ES2015c", 2), ("ES2015d", 3)]
    )
    def test_letter_order(self, meeting_id: str, expected: int) -> None:
        assert meeting_order_index(meeting_id) == expected

    def test_invalid_meeting_id_raises(self) -> None:
        with pytest.raises(ValueError, match="chronological order"):
            meeting_order_index("ES2015z")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="chronological order"):
            meeting_order_index("")


class TestChronologicalCandidatePairs:
    def test_pairs_are_ordered_later_to_earlier(self) -> None:
        d_a = _decision("d1", "ES2015a")
        d_b = _decision("d2", "ES2015b")

        pairs = chronological_candidate_pairs([d_a, d_b])

        assert pairs == [(d_b, d_a)]

    def test_no_pairs_across_series(self) -> None:
        d_a = _decision("d1", "ES2015a", series_id="ES2015")
        d_other = _decision("d2", "IS1004a", series_id="IS1004")

        assert chronological_candidate_pairs([d_a, d_other]) == []

    def test_same_meeting_produces_no_pair(self) -> None:
        d1 = _decision("d1", "ES2015a")
        d2 = _decision("d2", "ES2015a")

        assert chronological_candidate_pairs([d1, d2]) == []

    def test_four_meeting_series_produces_six_pairs(self) -> None:
        decisions = [_decision(f"d{i}", f"ES2015{letter}") for i, letter in enumerate("abcd")]
        pairs = chronological_candidate_pairs(decisions)
        assert len(pairs) == 6  # C(4, 2)


class TestValidateNoLeakage:
    def test_valid_relation_passes(self) -> None:
        target = _decision("d1", "ES2015a")
        source = _decision("d2", "ES2015b")
        relation = TemporalRelation(
            source_decision_id="d2",
            target_decision_id="d1",
            relation=RelationType.REFINA,
            evidence=EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=("x",)),
        )
        decisions_by_id = {"d1": target, "d2": source}

        assert validate_no_leakage(relation, decisions_by_id) is True

    def test_leaking_relation_fails(self) -> None:
        earlier = _decision("d1", "ES2015a")
        later = _decision("d2", "ES2015b")
        # source is the earlier meeting relating to a later one: this leaks the future.
        relation = TemporalRelation(
            source_decision_id="d1",
            target_decision_id="d2",
            relation=RelationType.REFINA,
            evidence=EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("x",)),
        )
        decisions_by_id = {"d1": earlier, "d2": later}

        assert validate_no_leakage(relation, decisions_by_id) is False

    def test_unknown_decision_id_returns_false(self) -> None:
        relation = TemporalRelation(
            source_decision_id="missing",
            target_decision_id="also-missing",
            relation=RelationType.REFINA,
            evidence=EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("x",)),
        )
        assert validate_no_leakage(relation, {}) is False


class TestAgreement:
    def test_compute_agreement_perfect(self) -> None:
        labels = ["revierte", "refina", "no_relacionada"]
        assert compute_agreement(labels, labels) == pytest.approx(1.0)

    def test_build_adjudication_log_only_includes_disagreements(self) -> None:
        log = build_adjudication_log(
            item_ids=["p1", "p2", "p3"],
            labels_a=["revierte", "refina", "no_relacionada"],
            labels_b=["revierte", "reemplaza", "no_relacionada"],
            annotator_a="alice",
            annotator_b="bob",
        )

        assert len(log) == 1
        assert log[0].item_id == "p2"
        assert log[0].label_a == "refina"
        assert log[0].label_b == "reemplaza"

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            build_adjudication_log(
                item_ids=["p1"],
                labels_a=["a", "b"],
                labels_b=["a"],
                annotator_a="alice",
                annotator_b="bob",
            )

    def test_agreement_meets_threshold(self) -> None:
        assert agreement_meets_threshold(0.65) is True
        assert agreement_meets_threshold(0.59) is False
        assert agreement_meets_threshold(-0.1) is False  # negative kappa precedent, thesis 1.4
