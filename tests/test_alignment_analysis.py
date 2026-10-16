"""Tests for the alignment-scope analysis helpers (issue #99): matches, clusters, similarity."""

from __future__ import annotations

import numpy as np
import pytest

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.alignment_analysis import (
    embedding_similarity,
    meeting_cluster_intervals,
    scored_matches,
)
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import IntervalSettings, pair_text

SETTINGS = IntervalSettings(n_resamples=400, confidence_level=0.95, seed=3)


def _ref(i: int, meeting: str) -> ReferenceDecision:
    return ReferenceDecision(
        decision_id=f"{meeting}.d{i}",
        series_id="S",
        meeting_id=meeting,
        decision_object=f"obj{i}",
        content=f"cont{i}",
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"da.{i}",)),
        evidence_method="sentence_id",
        role="PM",
        roles=("PM",),
    )


def _pred(i: int, meeting: str, status: DecisionStatus = DecisionStatus.ACCEPTED) -> Decision:
    return Decision(
        id=f"p{i}",
        series_id="S",
        meeting_id=meeting,
        decision_object=f"obj{i}",
        content=f"cont{i}",
        status=status,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"da.{i}",)),
    )


def _by_text(references: list[ReferenceDecision]):
    """Similarity 1 between texts with the same index, 0 otherwise."""

    def similarity(pred_texts, ref_texts):
        return np.array([[1.0 if p == r else 0.0 for r in ref_texts] for p in pred_texts])

    return similarity


def test_scored_matches_series_scope_crosses_meetings() -> None:
    reference = [_ref(1, "Sa")]
    predicted = [_pred(1, "Sb")]
    found = scored_matches(
        reference, predicted, _by_text(reference), tau=0.5, alignment_scope="series"
    )
    assert len(found) == 1
    assert found[0].predicted.id == "p1"
    assert found[0].reference.decision_id == "Sa.d1"
    assert found[0].similarity == pytest.approx(1.0)
    assert found[0].crosses_meetings is True


def test_scored_matches_origin_scope_masks_other_meetings() -> None:
    reference = [_ref(1, "Sa")]
    predicted = [_pred(1, "Sb")]
    assert (
        scored_matches(reference, predicted, _by_text(reference), tau=0.5) == ()
    )  # default scope is origin_meetings


def test_scored_matches_same_meeting_is_not_a_crossing_and_skips_non_decisions() -> None:
    reference = [_ref(1, "Sa")]
    predicted = [_pred(1, "Sa"), _pred(2, "Sa", DecisionStatus.OPINION)]
    found = scored_matches(reference, predicted, _by_text(reference), tau=0.5)
    assert [m.crosses_meetings for m in found] == [False]


def test_cluster_intervals_point_estimates_and_bounds() -> None:
    predicted = [("a", True), ("a", False), ("b", True), ("b", True)]
    reference = [("a", True), ("b", True), ("b", False)]
    out = meeting_cluster_intervals(predicted, reference, SETTINGS)
    assert out.n_clusters == 2
    assert out.precision == pytest.approx(3 / 4)
    assert out.recall == pytest.approx(2 / 3)
    for lower, upper in (out.precision_interval, out.recall_interval, out.f1_interval):
        assert 0.0 <= lower <= upper <= 1.0


def test_cluster_intervals_are_wider_than_independent_when_clusters_differ() -> None:
    # Meeting "a" is all hits, meeting "b" is all misses: resampling meetings swings a lot.
    predicted = [("a", True)] * 10 + [("b", False)] * 10
    reference = [("a", True)] * 10 + [("b", False)] * 10
    out = meeting_cluster_intervals(predicted, reference, SETTINGS)
    assert out.precision_interval == (0.0, 1.0)


def test_cluster_intervals_deterministic_for_a_seed() -> None:
    predicted = [("a", True), ("b", False), ("c", True)]
    reference = [("a", True), ("b", True), ("c", False)]
    assert meeting_cluster_intervals(predicted, reference, SETTINGS) == meeting_cluster_intervals(
        predicted, reference, SETTINGS
    )


def test_cluster_intervals_empty_side_gives_zero() -> None:
    out = meeting_cluster_intervals([], [("a", False)], SETTINGS)
    assert (out.precision, out.f1) == (0.0, 0.0)
    assert out.f1_interval == (0.0, 0.0)


def test_embedding_similarity_is_cosine() -> None:
    vectors = {"x": [1.0, 0.0], "y": [0.0, 2.0], "z": [3.0, 0.0]}
    similarity = embedding_similarity(lambda texts: [vectors[t] for t in texts])
    matrix = similarity(["x", "y"], ["z"])
    assert matrix.shape == (2, 1)
    assert matrix[0, 0] == pytest.approx(1.0)
    assert matrix[1, 0] == pytest.approx(0.0)


def test_pair_text_is_the_embedding_text() -> None:
    assert pair_text("o", "c") == "o: c"
