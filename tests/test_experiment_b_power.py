"""Tests for the Monte Carlo power simulation behind the D16 criterion (synthetic data only)."""

from __future__ import annotations

import pytest

from afg.evaluation.scoring import IntervalSettings
from afg.experiments.analysis import bootstrap_mean_interval, intervals_disjoint_above
from afg.experiments.power import (
    PowerResult,
    PowerScenario,
    PowerSettings,
    calibrate_intercept,
    false_positive_range,
    power_by_question_count,
    power_settings_from_config,
    power_table,
    question_probabilities,
    scenarios_from_config,
    score_correlation,
    simulate_grid,
    simulate_scenario,
)

FAST = PowerSettings(n_simulations=60, n_resamples=120, confidence_level=0.95, seed=11)


def _scenario(**overrides: float | int) -> PowerScenario:
    base = {
        "n_questions": 25,
        "runs_per_question": 3,
        "base_accuracy": 0.5,
        "difference": 0.2,
        "difficulty_sd": 1.0,
    }
    return PowerScenario(**{**base, **overrides})  # type: ignore[arg-type]


def test_calibrated_intercept_reproduces_the_target_mean_accuracy() -> None:
    for target in (0.2, 0.5, 0.75):
        for sd in (0.0, 1.0, 2.0):
            intercept = calibrate_intercept(target, sd)
            probabilities = question_probabilities(intercept, sd, n_questions=2000, seed=1)
            assert sum(probabilities) / len(probabilities) == pytest.approx(target, abs=0.03)


def test_zero_spread_gives_every_question_the_same_probability() -> None:
    intercept = calibrate_intercept(0.4, 0.0)
    probabilities = question_probabilities(intercept, 0.0, n_questions=10, seed=3)
    assert probabilities == pytest.approx([0.4] * 10)


def test_intervals_disjoint_above_is_strict_and_directional() -> None:
    assert intervals_disjoint_above((0.6, 0.8), (0.2, 0.5)) is True
    assert intervals_disjoint_above((0.4, 0.8), (0.2, 0.5)) is False
    assert intervals_disjoint_above((0.2, 0.5), (0.6, 0.8)) is False


def test_bootstrap_mean_interval_matches_the_analysis_settings() -> None:
    settings = IntervalSettings(n_resamples=200, confidence_level=0.95, seed=5)
    ci = bootstrap_mean_interval([0.0, 1.0, 1.0, 0.5], settings)
    assert ci.point_estimate == pytest.approx(0.625)
    assert ci.lower <= ci.point_estimate <= ci.upper
    assert ci.n_resamples == 200


def test_simulation_is_deterministic_for_a_seed() -> None:
    assert simulate_scenario(_scenario(), FAST) == simulate_scenario(_scenario(), FAST)


def test_rates_are_proportions_of_the_simulated_experiments() -> None:
    result = simulate_scenario(_scenario(), FAST)
    assert result.n_simulations == 60
    for rate in (result.power_nonoverlap, result.power_paired):
        assert 0.0 <= rate <= 1.0
        assert (rate * 60) == pytest.approx(round(rate * 60))


def test_a_very_large_true_effect_is_detected_by_the_paired_criterion() -> None:
    result = simulate_scenario(_scenario(base_accuracy=0.3, difference=0.5), FAST)
    assert result.power_paired > 0.9


def test_no_true_effect_rarely_declares_support() -> None:
    result = simulate_scenario(_scenario(difference=0.0), FAST)
    assert result.power_paired < 0.2
    assert result.power_nonoverlap < 0.2


@pytest.mark.parametrize(
    "overrides",
    [
        {"n_questions": 1},
        {"runs_per_question": 0},
        {"base_accuracy": 0.0},
        {"base_accuracy": 0.9, "difference": 0.2},
        {"difficulty_sd": -0.1},
    ],
)
def test_invalid_scenarios_are_rejected(overrides: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        simulate_scenario(_scenario(**overrides), FAST)


def test_settings_come_from_the_experiment_config() -> None:
    settings = power_settings_from_config()
    assert settings.confidence_level == pytest.approx(0.95)
    assert settings.seed == 42
    assert settings.n_simulations > 0
    assert 0 < settings.n_resamples <= 10_000


def test_shared_difficulty_correlates_the_observed_scores_of_the_two_conditions() -> None:
    none = score_correlation(_scenario(difficulty_sd=0.0), seed=3)
    some = score_correlation(_scenario(difficulty_sd=1.0), seed=3)
    large = score_correlation(_scenario(difficulty_sd=2.0), seed=3)
    assert none == pytest.approx(0.0, abs=0.05)
    assert 0.2 < some < large < 1.0


def test_scenarios_from_config_cover_the_full_grid() -> None:
    scenarios = scenarios_from_config()
    assert len(scenarios) == len(set(scenarios))
    assert {s.n_questions for s in scenarios} == {25, 40, 50}
    assert {s.difference for s in scenarios} >= {0.0, 0.15, 0.20}
    assert {s.difficulty_sd for s in scenarios} >= {1.0, 2.0}
    assert {s.runs_per_question for s in scenarios} == {3}


def test_grid_results_do_not_depend_on_the_number_of_workers() -> None:
    scenarios = [_scenario(difference=0.0), _scenario(difference=0.3)]
    small = PowerSettings(n_simulations=20, n_resamples=60, confidence_level=0.95, seed=2)
    assert simulate_grid(scenarios, small, workers=1) == simulate_grid(scenarios, small, workers=2)
    assert simulate_grid(scenarios, small, workers=1)[1] == simulate_scenario(scenarios[1], small)


def _result(n: int, sd: float, base: float, diff: float, a: float, b: float) -> PowerResult:
    return PowerResult(PowerScenario(n, 3, base, diff, sd), 1000, a, b)


RESULTS = [
    _result(25, 0.0, 0.5, 0.0, 0.008, 0.026),
    _result(25, 0.0, 0.5, 0.15, 0.215, 0.503),
    _result(25, 1.0, 0.5, 0.0, 0.0, 0.033),
    _result(25, 1.0, 0.5, 0.15, 0.104, 0.575),
    _result(25, 1.0, 0.4, 0.15, 0.09, 0.576),
    _result(40, 1.0, 0.5, 0.15, 0.174, 0.757),
    _result(40, 1.0, 0.5, 0.2, 0.491, 0.938),
    _result(25, 1.0, 0.5, 0.2, 0.278, 0.795),
]


class TestPowerTable:
    def test_one_row_per_spread_and_criterion_with_percentages_per_difference(self) -> None:
        table = power_table(RESULTS, 25, 0.5)
        assert list(table.index.names) == ["difficulty_sd", "criterion"]
        assert list(table.index) == [
            (0.0, "nonoverlap"),
            (0.0, "paired"),
            (1.0, "nonoverlap"),
            (1.0, "paired"),
        ]
        assert list(table.columns) == ["+0.00", "+0.15", "+0.20"]
        assert table.loc[(1.0, "paired"), "+0.15"] == 57.5
        assert table.loc[(1.0, "nonoverlap"), "+0.15"] == 10.4

    def test_only_the_requested_size_and_base_accuracy_are_used(self) -> None:
        table = power_table(RESULTS, 40, 0.5)
        assert list(table.index) == [(1.0, "nonoverlap"), (1.0, "paired")]
        assert table.loc[(1.0, "paired"), "+0.20"] == 93.8

    def test_a_scenario_missing_a_difference_leaves_a_gap(self) -> None:
        table = power_table(RESULTS, 25, 0.4)
        assert table.loc[(1.0, "paired"), "+0.15"] == 57.6
        assert "+0.20" not in table.columns


class TestFalsePositiveRange:
    def test_min_and_max_over_the_scenarios_without_true_effect(self) -> None:
        fp = false_positive_range(RESULTS)
        assert fp.n_scenarios == 2
        assert (fp.nonoverlap_min, fp.nonoverlap_max) == (0.0, 0.008)
        assert (fp.paired_min, fp.paired_max) == (0.026, 0.033)

    def test_no_null_scenarios_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="no scenario"):
            false_positive_range([_result(25, 1.0, 0.5, 0.15, 0.1, 0.5)])


class TestPowerByQuestionCount:
    def test_one_row_per_size_with_both_criteria_per_difference(self) -> None:
        table = power_by_question_count(
            RESULTS, base=0.5, difficulty_sd=1.0, differences=(0.15, 0.2)
        )
        assert list(table.index) == [25, 40]
        assert table.index.name == "n_questions"
        assert table.loc[25, ("paired", 0.15)] == 57.5
        assert table.loc[40, ("nonoverlap", 0.2)] == 49.1
        assert table.loc[40, ("paired", 0.2)] == 93.8
