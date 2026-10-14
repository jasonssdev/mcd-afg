"""Tests for the judge calibration metrics and decision rule (thesis section 5.7)."""

from __future__ import annotations

import pytest

from afg.evaluation.judge import JudgeFailure, JudgeVerdict
from afg.evaluation.judge_calibration import (
    CalibrationThresholds,
    CandidateMetrics,
    decide_judge,
    field_agreement,
    flip_rate,
    json_valid_rate,
    kappa_confidence_interval,
    load_thresholds,
    negative_class_recall,
    paired_consistency,
    seed_consistency,
    stratum_accuracy,
)
from afg.evaluation.metrics import BootstrapCI


def _verdict(correct: bool = True) -> JudgeVerdict:
    return JudgeVerdict("q1", "C1", correct, True, None, "r")


class TestThresholds:
    def test_loaded_from_config(self) -> None:
        t = load_thresholds()
        assert t.min_kappa_correct == 0.70
        assert t.min_position_consistency == 0.90
        assert t.min_seed_consistency == 0.95
        assert t.min_e4_accuracy == 0.80
        assert t.min_json_valid_rate == 0.99
        assert t.max_verbosity_flip_rate == 0.10
        assert t.seeds == (42, 43, 44)


class TestFieldAgreement:
    def test_kappa_and_accuracy(self) -> None:
        result = field_agreement([True, True, False, False], [True, False, False, False])
        assert result.n == 4
        assert result.accuracy == 0.75
        assert result.kappa == pytest.approx(0.5)

    def test_identical_single_class_is_perfect_not_nan(self) -> None:
        result = field_agreement([True, True], [True, True])
        assert result.kappa == 1.0 and result.accuracy == 1.0

    def test_none_pairs_are_dropped(self) -> None:
        result = field_agreement([True, None, False], [True, True, None])
        assert result.n == 1
        assert result.accuracy == 1.0

    def test_no_comparable_pairs_raises(self) -> None:
        with pytest.raises(ValueError):
            field_agreement([None], [True])

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            field_agreement([True], [True, False])


class TestNegativeClassRecall:
    def test_share_of_human_negatives_caught(self) -> None:
        assert negative_class_recall([False, True, True], [False, False, True]) == 0.5

    def test_no_human_negatives_raises(self) -> None:
        with pytest.raises(ValueError):
            negative_class_recall([True], [True])


class TestConsistency:
    def test_position_swap(self) -> None:
        assert paired_consistency([True, False, True, True], [True, False, False, True]) == 0.75

    def test_invalid_verdict_counts_as_inconsistent(self) -> None:
        assert paired_consistency([True, None], [True, None]) == 0.5

    def test_seed_consistency_requires_all_seeds_to_agree(self) -> None:
        runs = [[True, True, False], [True, False, False], [True, True, False]]
        assert seed_consistency(runs) == pytest.approx(2 / 3)

    def test_seed_consistency_needs_two_runs(self) -> None:
        with pytest.raises(ValueError):
            seed_consistency([[True]])

    def test_seed_runs_must_be_same_length(self) -> None:
        with pytest.raises(ValueError):
            seed_consistency([[True], [True, False]])


class TestStratumAccuracy:
    def test_only_the_requested_stratum_counts(self) -> None:
        acc = stratum_accuracy(
            strata=["E4_unanswerable", "E1_point_fact", "E4_unanswerable"],
            judge=[True, False, False],
            human=[True, True, True],
            stratum="E4_unanswerable",
        )
        assert acc == 0.5

    def test_missing_stratum_raises(self) -> None:
        with pytest.raises(ValueError):
            stratum_accuracy(["E1_point_fact"], [True], [True], "E4_unanswerable")


class TestJsonAndFlips:
    def test_json_valid_rate_counts_typed_failures(self) -> None:
        outcomes = [_verdict(), JudgeFailure("q2", "C1", "invalid_json", "{"), _verdict()]
        assert json_valid_rate(outcomes) == pytest.approx(2 / 3)

    def test_json_valid_rate_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            json_valid_rate([])

    def test_flip_rate_ignores_pairs_with_an_invalid_side(self) -> None:
        assert flip_rate([False, False, None, False], [True, False, True, None]) == 0.5


class TestKappaCI:
    def test_interval_brackets_point_estimate_and_is_reproducible(self) -> None:
        judge = [True, True, False, False, True, False, True, False, True, True]
        human = [True, True, False, True, True, False, True, False, False, True]
        first = kappa_confidence_interval(judge, human, n_resamples=300)
        again = kappa_confidence_interval(judge, human, n_resamples=300)
        assert first == again
        assert first.lower <= first.point_estimate <= first.upper
        assert first.confidence_level == 0.95


def _ci(point: float, lower: float, upper: float) -> BootstrapCI:
    return BootstrapCI(point, lower, upper, 0.95, 100)


def _metrics(model: str, **overrides: object) -> CandidateMetrics:
    base: dict[str, object] = {
        "model": model,
        "kappa_correct": _ci(0.70, 0.60, 0.80),
        "position_consistency": 0.95,
        "seed_consistency": 0.98,
        "e4_accuracy": 0.90,
        "json_valid_rate": 1.0,
        "verbosity_flip_rate": 0.05,
        "latency_seconds": 5.0,
    }
    base.update(overrides)
    return CandidateMetrics(**base)  # type: ignore[arg-type]


class TestDecision:
    def test_failed_criteria_lists_each_miss(self) -> None:
        t = load_thresholds()
        m = _metrics("a", position_consistency=0.5, json_valid_rate=0.9)
        assert m.failed_criteria(t) == ("position_consistency", "json_valid_rate")

    def test_boundary_values_pass(self) -> None:
        t = load_thresholds()
        m = _metrics(
            "a",
            kappa_correct=_ci(0.70, 0.6, 0.8),
            position_consistency=0.90,
            seed_consistency=0.95,
            e4_accuracy=0.80,
            json_valid_rate=0.99,
            verbosity_flip_rate=0.10,
        )
        assert m.failed_criteria(t) == ()

    def test_highest_kappa_wins_when_intervals_are_disjoint(self) -> None:
        a = _metrics("a", kappa_correct=_ci(0.95, 0.90, 0.99), latency_seconds=20.0)
        b = _metrics("b", kappa_correct=_ci(0.70, 0.62, 0.78), latency_seconds=1.0)
        decision = decide_judge([b, a], load_thresholds())
        assert decision.selected == "a"

    def test_overlapping_intervals_pick_lowest_latency(self) -> None:
        a = _metrics("a", kappa_correct=_ci(0.80, 0.65, 0.92), latency_seconds=20.0)
        b = _metrics("b", kappa_correct=_ci(0.75, 0.62, 0.88), latency_seconds=4.0)
        c = _metrics("c", kappa_correct=_ci(0.50, 0.2, 0.6), latency_seconds=1.0)
        decision = decide_judge([a, b, c], load_thresholds())
        assert decision.selected == "b"
        assert decision.failures["c"] == ("kappa_correct",)

    def test_none_passing_is_an_explicit_no_judge_outcome(self) -> None:
        t = load_thresholds()
        decision = decide_judge([_metrics("a", e4_accuracy=0.1)], t)
        assert decision.selected is None
        assert decision.outcome == "no_judge"
        assert decision.failures == {"a": ("e4_accuracy",)}

    def test_selected_outcome_label(self) -> None:
        decision = decide_judge([_metrics("a")], load_thresholds())
        assert decision.outcome == "selected"

    def test_no_candidates_raises(self) -> None:
        with pytest.raises(ValueError):
            decide_judge([], load_thresholds())


def test_thresholds_dataclass_is_frozen() -> None:
    t = load_thresholds()
    assert isinstance(t, CalibrationThresholds)
    with pytest.raises(AttributeError):
        t.min_kappa_correct = 0.0  # type: ignore[misc]
