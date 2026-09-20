"""Tests for evaluation metrics (thesis section 5.6)."""

from __future__ import annotations

import statistics

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.relation import RelationType, TemporalRelation
from afg.evaluation.metrics import (
    bootstrap_ci,
    cohen_kappa,
    precision_recall_f1,
    recall_at_k,
    relation_direction_accuracy,
    relation_label_accuracy,
    wilson_interval,
)


def _relation(
    source: str, target: str, relation: RelationType = RelationType.REFINA
) -> TemporalRelation:
    return TemporalRelation(
        source_decision_id=source,
        target_decision_id=target,
        relation=relation,
        evidence=EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=("d1",)),
    )


class TestPrecisionRecallF1:
    def test_perfect_score(self) -> None:
        precision, recall, f1 = precision_recall_f1(
            true_positives=10, false_positives=0, false_negatives=0
        )
        assert (precision, recall, f1) == (1.0, 1.0, 1.0)

    def test_zero_predictions_is_zero_precision(self) -> None:
        precision, _, _ = precision_recall_f1(
            true_positives=0, false_positives=0, false_negatives=5
        )
        assert precision == 0.0

    def test_known_values(self) -> None:
        # tp=3, fp=1 -> precision=0.75; tp=3, fn=2 -> recall=0.6
        precision, recall, f1 = precision_recall_f1(
            true_positives=3, false_positives=1, false_negatives=2
        )
        assert precision == pytest.approx(0.75)
        assert recall == pytest.approx(0.6)
        assert f1 == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))


class TestCohenKappa:
    def test_perfect_agreement(self) -> None:
        labels = ["a", "b", "a", "c"]
        assert cohen_kappa(labels, labels) == pytest.approx(1.0)

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            cohen_kappa(["a"], ["a", "b"])

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            cohen_kappa([], [])


class TestRelationLabelAccuracy:
    def test_all_correct(self) -> None:
        assert relation_label_accuracy(["revierte", "refina"], ["revierte", "refina"]) == 1.0

    def test_half_correct(self) -> None:
        assert relation_label_accuracy(["revierte", "refina"], ["revierte", "reemplaza"]) == 0.5

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            relation_label_accuracy([], [])


class TestRelationDirectionAccuracy:
    def test_correct_direction(self) -> None:
        reference = _relation("d2", "d1")
        predicted = _relation("d2", "d1")
        assert relation_direction_accuracy([(predicted, reference)]) == 1.0

    def test_inverted_direction_scores_zero(self) -> None:
        reference = _relation("d2", "d1")
        predicted = reference.inverted()
        assert relation_direction_accuracy([(predicted, reference)]) == 0.0

    def test_mixed_pairs(self) -> None:
        reference = _relation("d2", "d1")
        correct_pair = (_relation("d2", "d1"), reference)
        inverted_pair = (reference.inverted(), reference)
        assert relation_direction_accuracy([correct_pair, inverted_pair]) == 0.5

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            relation_direction_accuracy([])


class TestRecallAtK:
    def test_all_relevant_in_top_k(self) -> None:
        assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0

    def test_none_in_top_k(self) -> None:
        assert recall_at_k(["x", "y", "z"], {"a", "b"}, k=3) == 0.0

    def test_partial(self) -> None:
        assert recall_at_k(["a", "x", "y"], {"a", "b"}, k=3) == 0.5

    def test_k_limits_the_window(self) -> None:
        assert recall_at_k(["x", "a"], {"a"}, k=1) == 0.0

    def test_empty_relevant_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            recall_at_k(["a"], set(), k=3)


class TestBootstrapCi:
    def test_ci_contains_point_estimate(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = bootstrap_ci(values, statistic=statistics.mean, n=2_000, seed=42)

        assert result.lower <= result.point_estimate <= result.upper

    def test_reproducible_with_seed(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]
        first = bootstrap_ci(values, statistic=statistics.mean, n=1_000, seed=7)
        second = bootstrap_ci(values, statistic=statistics.mean, n=1_000, seed=7)

        assert first == second

    def test_degenerate_single_value(self) -> None:
        result = bootstrap_ci([5.0], statistic=statistics.mean, n=500, seed=1)
        assert result.lower == result.upper == result.point_estimate == 5.0

    def test_empty_values_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            bootstrap_ci([], statistic=statistics.mean)

    def test_invalid_confidence_level_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence_level"):
            bootstrap_ci([1.0, 2.0], statistic=statistics.mean, confidence_level=1.5)


class TestWilsonInterval:
    """The project's first positive-rate estimate had n = 11; Wald is unusable there."""

    def test_matches_hand_computed_value_for_the_dev_positive_rate(self) -> None:
        ci = wilson_interval(5, 11)
        assert ci.point_estimate == pytest.approx(5 / 11)
        assert ci.lower == pytest.approx(0.2133, abs=1e-3)
        assert ci.upper == pytest.approx(0.7200, abs=1e-3)

    def test_stays_inside_unit_interval_at_the_extremes(self) -> None:
        """Wald would give a zero-width interval at 0/n and n/n, and can escape [0, 1]."""
        for successes in (0, 8):
            ci = wilson_interval(successes, 8)
            assert 0.0 <= ci.lower <= ci.upper <= 1.0
            assert ci.upper > ci.lower

    def test_wider_confidence_gives_wider_interval(self) -> None:
        narrow = wilson_interval(5, 11, confidence_level=0.80)
        wide = wilson_interval(5, 11, confidence_level=0.99)
        assert (wide.upper - wide.lower) > (narrow.upper - narrow.lower)

    def test_more_trials_at_the_same_rate_narrows_the_interval(self) -> None:
        small = wilson_interval(5, 11)
        large = wilson_interval(50, 110)
        assert (large.upper - large.lower) < (small.upper - small.lower)

    def test_scaled_to_projects_rate_onto_a_population(self) -> None:
        point, lower, upper = wilson_interval(5, 11).scaled_to(81)
        assert round(point) == 37
        assert round(lower) == 17
        assert round(upper) == 58

    @pytest.mark.parametrize(
        ("successes", "trials"), [(0, 0), (-1, 10), (11, 10)]
    )
    def test_rejects_invalid_counts(self, successes: int, trials: int) -> None:
        with pytest.raises(ValueError):
            wilson_interval(successes, trials)

    def test_rejects_invalid_confidence_level(self) -> None:
        with pytest.raises(ValueError):
            wilson_interval(5, 11, confidence_level=1.0)
