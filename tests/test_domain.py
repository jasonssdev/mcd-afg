"""Tests for the domain package: decisions, relations, and the annotation cascade."""

from __future__ import annotations

import pytest

from afg.annotation.goldset import classify_decision_status
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.domain.relation import RelationType, TemporalRelation


def _evidence(meeting_id: str = "ES2015a") -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=("d1", "d2"))


class TestRelationType:
    def test_values_are_spanish_annotation_labels(self) -> None:
        assert {member.value for member in RelationType} == {
            "introduce",
            "reafirma",
            "refina",
            "revierte",
            "reemplaza",
            "no_relacionada",
        }


class TestTemporalRelation:
    def test_inverted_swaps_source_and_target(self) -> None:
        relation = TemporalRelation(
            source_decision_id="d2",
            target_decision_id="d1",
            relation=RelationType.REVIERTE,
            evidence=_evidence(),
        )
        inverted = relation.inverted()

        assert inverted.source_decision_id == "d1"
        assert inverted.target_decision_id == "d2"
        assert inverted.relation == RelationType.REVIERTE

    def test_double_inversion_is_identity(self) -> None:
        relation = TemporalRelation(
            source_decision_id="d2",
            target_decision_id="d1",
            relation=RelationType.REFINA,
            evidence=_evidence(),
        )
        assert relation.inverted().inverted() == relation

    def test_is_frozen(self) -> None:
        relation = TemporalRelation(
            source_decision_id="d2",
            target_decision_id="d1",
            relation=RelationType.REFINA,
            evidence=_evidence(),
        )
        with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError subtype
            relation.source_decision_id = "changed"  # type: ignore[misc]


class TestDecision:
    def test_is_decision_true_only_for_accepted(self) -> None:
        accepted = Decision(
            id="d1",
            series_id="ES2015",
            meeting_id="ES2015a",
            decision_object="casing material",
            content="use titanium",
            status=DecisionStatus.ACCEPTED,
            evidence=_evidence(),
        )
        proposal = accepted.model_copy(update={"status": DecisionStatus.OPEN_PROPOSAL})

        assert accepted.is_decision is True
        assert proposal.is_decision is False


class TestClassifyDecisionStatus:
    @pytest.mark.parametrize(
        ("explicit", "accepted", "anchored", "expected"),
        [
            (True, True, True, DecisionStatus.ACCEPTED),
            (False, True, True, DecisionStatus.OPEN_PROPOSAL),
            (True, False, True, DecisionStatus.OPEN_PROPOSAL),
            (True, True, False, DecisionStatus.OPEN_PROPOSAL),
            (False, False, False, DecisionStatus.OPEN_PROPOSAL),
        ],
    )
    def test_three_condition_cascade(
        self, explicit: bool, accepted: bool, anchored: bool, expected: DecisionStatus
    ) -> None:
        result = classify_decision_status(explicit=explicit, accepted=accepted, anchored=anchored)
        assert result == expected
