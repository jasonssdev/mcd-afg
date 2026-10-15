"""Monte Carlo power of the two candidate D16 criteria (synthetic data; no experiment is run).

D16 declares the project hypothesis "supported" when C2 beats C1 on answer correctness in E3.
Two ways of deciding that are compared here, on simulated experiments whose truth is known:

* **non-overlap**: the independent 95 % bootstrap intervals of C1 and C2 do not overlap and C2's
  lies above (the literal wording preregistered on 2026-10-13);
* **paired**: the 95 % bootstrap interval of the per-question difference C2 - C1 lies above 0.

Simulated design, as the real analysis sees it (:mod:`afg.experiments.analysis`):

* ``n_questions`` questions answered by both conditions, ``runs_per_question`` runs each, the
  runs averaged into one score per question and condition;
* each question has a difficulty shared by both conditions (a normal shift on the logit scale
  with standard deviation ``difficulty_sd``), which is what makes the two scores of a question
  correlated; the intercepts are calibrated so that the MEAN accuracy of C1 is
  ``base_accuracy`` and that of C2 is ``base_accuracy + difference``;
* every run is a Bernoulli draw with the question's probability, independent across runs and
  conditions given the difficulty.

Both criteria use :func:`afg.experiments.analysis.bootstrap_mean_interval`, the function that
produces every reported interval, so the simulation studies the reported machinery. The only
liberty is the number of resamples, which is smaller here (``[power_simulation]`` in
``config/experiments.toml``) to keep the study affordable; the false-positive and power rates
therefore carry a small Monte Carlo error, which the notebook reports.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from statistics import NormalDist

from afg.evaluation.scoring import IntervalSettings
from afg.experiments.analysis import bootstrap_mean_interval, intervals_disjoint_above
from afg.shared.config import load_experiments_config

__all__ = [
    "PowerResult",
    "PowerScenario",
    "PowerSettings",
    "calibrate_intercept",
    "power_settings_from_config",
    "question_probabilities",
    "scenarios_from_config",
    "score_correlation",
    "simulate_grid",
    "simulate_scenario",
]

_GRID_POINTS = 400
_NORMAL = NormalDist()
_QUANTILES = tuple(_NORMAL.inv_cdf((k + 0.5) / _GRID_POINTS) for k in range(_GRID_POINTS))


@dataclass(frozen=True, slots=True)
class PowerScenario:
    """One true state of the world to simulate."""

    n_questions: int
    runs_per_question: int
    base_accuracy: float
    """Mean accuracy of C1 over the question population."""
    difference: float
    """True mean accuracy of C2 minus that of C1 (0 gives the false-positive rate)."""
    difficulty_sd: float
    """Spread of the per-question difficulty shared by both conditions (logit scale)."""


@dataclass(frozen=True, slots=True)
class PowerSettings:
    n_simulations: int
    n_resamples: int
    confidence_level: float
    seed: int


@dataclass(frozen=True, slots=True)
class PowerResult:
    scenario: PowerScenario
    n_simulations: int
    power_nonoverlap: float
    """Share of simulated experiments where the independent intervals are disjoint, C2 above."""
    power_paired: float
    """Share where the paired difference interval lies above 0."""


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


@lru_cache(maxsize=256)
def calibrate_intercept(target_mean: float, difficulty_sd: float) -> float:
    """The logit intercept whose mean probability over the difficulty distribution is the target."""
    if not 0.0 < target_mean < 1.0:
        raise ValueError("target_mean must be strictly between 0 and 1.")
    if difficulty_sd < 0.0:
        raise ValueError("difficulty_sd must not be negative.")
    if difficulty_sd == 0.0:
        return _logit(target_mean)

    def mean_probability(intercept: float) -> float:
        return sum(_sigmoid(intercept + difficulty_sd * z) for z in _QUANTILES) / _GRID_POINTS

    low, high = -30.0, 30.0
    for _ in range(80):
        middle = (low + high) / 2.0
        if mean_probability(middle) < target_mean:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def question_probabilities(
    intercept: float, difficulty_sd: float, *, n_questions: int, seed: int
) -> list[float]:
    """Per-question success probabilities for one condition (difficulties drawn from ``seed``)."""
    rng = random.Random(seed)
    return [_sigmoid(intercept + rng.gauss(0.0, difficulty_sd)) for _ in range(n_questions)]


def power_settings_from_config() -> PowerSettings:
    """Simulation size from ``[power_simulation]``; seed and confidence from the experiment."""
    config = load_experiments_config()
    section = config["power_simulation"]
    return PowerSettings(
        n_simulations=int(section["n_simulations"]),
        n_resamples=int(section["n_resamples"]),
        confidence_level=float(config["evaluation"]["bootstrap_confidence_level"]),
        seed=int(config["shared_budget"]["seed"]),
    )


def scenarios_from_config() -> list[PowerScenario]:
    """Every scenario of ``[power_simulation]``: n x spread x base accuracy x difference."""
    config = load_experiments_config()
    section = config["power_simulation"]
    runs = int(config["shared_budget"]["runs_per_config"])
    return [
        PowerScenario(
            n_questions=int(n),
            runs_per_question=runs,
            base_accuracy=float(base),
            difference=float(difference),
            difficulty_sd=float(sd),
        )
        for n in section["n_questions"]
        for sd in section["difficulty_sd"]
        for base in section["base_accuracies"]
        for difference in section["differences"]
    ]


def score_correlation(scenario: PowerScenario, *, seed: int, n_questions: int = 5000) -> float:
    """Correlation, across questions, between the observed C1 and C2 scores of the scenario.

    Simulated on a large question sample with the same generator as :func:`simulate_scenario`.
    It is what the shared difficulty leaves after the run-to-run noise of each score; it is 0
    without a shared difficulty.
    """
    c1, c2 = _draw_scores(random.Random(seed), scenario, n_questions)
    m1, m2 = sum(c1) / n_questions, sum(c2) / n_questions
    cov = sum((x - m1) * (y - m2) for x, y in zip(c1, c2, strict=True))
    v1 = sum((x - m1) ** 2 for x in c1)
    v2 = sum((y - m2) ** 2 for y in c2)
    return cov / math.sqrt(v1 * v2) if v1 > 0.0 and v2 > 0.0 else 0.0


def _validate(scenario: PowerScenario, settings: PowerSettings) -> None:
    if scenario.n_questions < 2:
        raise ValueError("n_questions must be at least 2.")
    if scenario.runs_per_question < 1:
        raise ValueError("runs_per_question must be at least 1.")
    if not 0.0 < scenario.base_accuracy < 1.0:
        raise ValueError("base_accuracy must be strictly between 0 and 1.")
    if not 0.0 < scenario.base_accuracy + scenario.difference < 1.0:
        raise ValueError("base_accuracy + difference must be strictly between 0 and 1.")
    if scenario.difficulty_sd < 0.0:
        raise ValueError("difficulty_sd must not be negative.")
    if settings.n_simulations < 1 or settings.n_resamples < 1:
        raise ValueError("n_simulations and n_resamples must be at least 1.")


def _scores(rng: random.Random, probabilities: list[float], runs: int) -> list[float]:
    return [sum(rng.random() < p for _ in range(runs)) / runs for p in probabilities]


def _draw_scores(
    rng: random.Random, scenario: PowerScenario, n_questions: int
) -> tuple[list[float], list[float]]:
    """Per-question run-averaged scores of C1 and C2 for one simulated experiment."""
    sd = scenario.difficulty_sd
    intercept_c1 = calibrate_intercept(scenario.base_accuracy, sd)
    intercept_c2 = calibrate_intercept(scenario.base_accuracy + scenario.difference, sd)
    difficulty = [rng.gauss(0.0, sd) for _ in range(n_questions)]
    runs = scenario.runs_per_question
    c1 = _scores(rng, [_sigmoid(intercept_c1 + d) for d in difficulty], runs)
    c2 = _scores(rng, [_sigmoid(intercept_c2 + d) for d in difficulty], runs)
    return c1, c2


def simulate_scenario(scenario: PowerScenario, settings: PowerSettings) -> PowerResult:
    """Share of simulated experiments declared "supported" by each criterion.

    Deterministic for ``settings.seed``: the data of experiment ``i`` and its bootstrap seed are
    functions of the seed and ``i`` only, so scenarios share random numbers and compare cleanly.
    """
    _validate(scenario, settings)
    rng = random.Random(settings.seed)

    nonoverlap = paired = 0
    for index in range(settings.n_simulations):
        c1, c2 = _draw_scores(rng, scenario, scenario.n_questions)
        interval = IntervalSettings(
            n_resamples=settings.n_resamples,
            confidence_level=settings.confidence_level,
            seed=settings.seed + index,
        )
        ci1 = bootstrap_mean_interval(c1, interval)
        ci2 = bootstrap_mean_interval(c2, interval)
        diff = bootstrap_mean_interval([b - a for a, b in zip(c1, c2, strict=True)], interval)
        nonoverlap += intervals_disjoint_above((ci2.lower, ci2.upper), (ci1.lower, ci1.upper))
        paired += diff.lower > 0.0
    return PowerResult(
        scenario=scenario,
        n_simulations=settings.n_simulations,
        power_nonoverlap=nonoverlap / settings.n_simulations,
        power_paired=paired / settings.n_simulations,
    )


def _simulate_pair(args: tuple[PowerScenario, PowerSettings]) -> PowerResult:
    return simulate_scenario(*args)


def simulate_grid(
    scenarios: Sequence[PowerScenario], settings: PowerSettings, *, workers: int = 1
) -> list[PowerResult]:
    """:func:`simulate_scenario` over many scenarios, in order; ``workers`` only changes speed."""
    if workers <= 1 or len(scenarios) < 2:
        return [simulate_scenario(scenario, settings) for scenario in scenarios]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_simulate_pair, [(s, settings) for s in scenarios]))
