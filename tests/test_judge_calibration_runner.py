"""Tests for the judge calibration runner (thesis section 5.7). Fake backend, no network."""

from __future__ import annotations

import json
from typing import Any

import pytest

from afg.domain.question import QuestionStratum
from afg.evaluation.judge import JudgeConfigurationError
from afg.evaluation.judge_calibration import CalibrationThresholds
from afg.evaluation.judge_calibration_runner import (
    load_candidates,
    pad_to_double_length,
    run_calibration,
    run_candidate,
)
from afg.evaluation.judge_calibration_set import CalibrationItem, CalibrationSetError

THRESHOLDS = CalibrationThresholds(
    min_kappa_correct=0.70,
    min_position_consistency=0.90,
    min_seed_consistency=0.95,
    min_e4_accuracy=0.80,
    min_json_valid_rate=0.99,
    max_verbosity_flip_rate=0.10,
    seeds=(42, 43, 44),
)


def _item(n: int, *, good: bool, stratum: QuestionStratum | None = None) -> CalibrationItem:
    e4 = stratum is QuestionStratum.E4_UNANSWERABLE
    return CalibrationItem(
        id=f"i{n}",
        series_id="ES2015",
        stratum=stratum or QuestionStratum.E1_POINT_FACT,
        question=f"question {n}",
        reference_answer=None if e4 else f"reference {n}",
        answer_text=f"GOOD answer {n}" if good else f"BAD answer {n}",
        correct=good,
        evidence_supported=good,
    )


def _items() -> list[CalibrationItem]:
    items = [_item(i, good=i % 2 == 0) for i in range(8)]
    items.append(_item(8, good=True, stratum=QuestionStratum.E4_UNANSWERABLE))
    items.append(_item(9, good=False, stratum=QuestionStratum.E4_UNANSWERABLE))
    return items


def _reply(correct: bool) -> str:
    return json.dumps({"correct": correct, "evidence_supported": correct, "rationale": "r"})


class FakeBackend:
    """Judges ``GOOD`` answers correct; subclasses bend that to simulate biases."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def verdict(self, user: str) -> str:
        candidate = user.split("Candidate answer:\n")[1].split("\n\n")[0]
        return _reply("GOOD" in candidate)

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        seed: int,
        temperature: float,
        format_schema: dict[str, Any],
    ) -> str:
        self.calls.append({"user": user, "model": model, "seed": seed, "temperature": temperature})
        return self.verdict(user)


class PositionBiasedBackend(FakeBackend):
    def verdict(self, user: str) -> str:
        return _reply(user.index("Reference answer:") < user.index("Candidate answer:"))


class VerbosityBiasedBackend(FakeBackend):
    def verdict(self, user: str) -> str:
        candidate = user.split("Candidate answer:\n")[1].split("\n\n")[0]
        return _reply("GOOD" in candidate or len(candidate) > 20)


class BrokenBackend(FakeBackend):
    def verdict(self, user: str) -> str:
        return "not json"


class TickClock:
    """Each call to the clock advances by 0.5 s, so every judge call lasts 0.5 s."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        self.now += 0.5
        return self.now


def _run(backend: FakeBackend, **kwargs: Any) -> Any:
    return run_candidate(
        _items(),
        judge_model="judge:1",
        generative_model="qwen3:8b",
        backend=backend,
        thresholds=THRESHOLDS,
        n_resamples=50,
        **kwargs,
    )


class TestPadding:
    def test_doubles_the_length_deterministically(self) -> None:
        padded = pad_to_double_length("BAD answer")
        assert padded.startswith("BAD answer") and len(padded) >= 2 * len("BAD answer")
        assert padded == pad_to_double_length("BAD answer")


class TestRunCandidate:
    def test_perfect_judge_passes_every_criterion(self) -> None:
        run = _run(FakeBackend())
        metrics = run.metrics
        assert metrics.model == "judge:1"
        assert metrics.kappa_correct.point_estimate == 1.0
        assert metrics.position_consistency == 1.0
        assert metrics.seed_consistency == 1.0
        assert metrics.e4_accuracy == 1.0
        assert metrics.json_valid_rate == 1.0
        assert metrics.verbosity_flip_rate == 0.0
        assert metrics.failed_criteria(THRESHOLDS) == ()
        assert run.failures == 0

    def test_every_item_runs_in_both_orders_for_every_seed_plus_the_padding_probe(self) -> None:
        backend = FakeBackend()
        run = _run(backend)
        incorrect = sum(1 for i in _items() if i.correct is False)
        assert len(backend.calls) == len(_items()) * 2 * 3 + incorrect
        assert run.calls == len(backend.calls)
        assert {c["seed"] for c in backend.calls} == {42, 43, 44}
        assert {c["temperature"] for c in backend.calls} == {0.0}
        assert {c["model"] for c in backend.calls} == {"judge:1"}

    def test_position_biased_judge_is_caught(self) -> None:
        metrics = _run(PositionBiasedBackend()).metrics
        assert metrics.position_consistency == 0.0
        assert "position_consistency" in metrics.failed_criteria(THRESHOLDS)

    def test_verbosity_biased_judge_flips_on_padded_wrong_answers(self) -> None:
        metrics = _run(VerbosityBiasedBackend()).metrics
        assert metrics.verbosity_flip_rate == 1.0
        assert "verbosity_flip_rate" in metrics.failed_criteria(THRESHOLDS)

    def test_unusable_output_is_counted_not_raised(self) -> None:
        run = _run(BrokenBackend())
        assert run.metrics.json_valid_rate == 0.0
        assert run.failures == run.calls
        # With no usable verdict every metric takes its worst value instead of aborting.
        assert run.metrics.kappa_correct.point_estimate == 0.0
        assert run.metrics.e4_accuracy == 0.0
        assert run.metrics.verbosity_flip_rate == 1.0
        assert run.evidence_supported is None
        assert len(run.metrics.failed_criteria(THRESHOLDS)) == 6

    def test_latency_is_the_mean_seconds_per_call(self) -> None:
        run = _run(FakeBackend(), clock=TickClock())
        assert run.metrics.latency_seconds == pytest.approx(0.5)

    def test_unlabeled_items_are_refused(self) -> None:
        items = _items()
        items[0] = items[0].model_copy(update={"correct": None})
        with pytest.raises(CalibrationSetError, match="i0"):
            run_candidate(
                items,
                judge_model="judge:1",
                generative_model="qwen3:8b",
                backend=FakeBackend(),
                thresholds=THRESHOLDS,
            )

    def test_a_set_without_e4_items_is_refused(self) -> None:
        items = [i for i in _items() if i.stratum is not QuestionStratum.E4_UNANSWERABLE]
        with pytest.raises(ValueError, match="E4"):
            run_candidate(
                items,
                judge_model="judge:1",
                generative_model="qwen3:8b",
                backend=FakeBackend(),
                thresholds=THRESHOLDS,
            )

    def test_a_set_without_incorrect_answers_is_refused(self) -> None:
        items = [i for i in _items() if i.correct]
        with pytest.raises(ValueError, match="incorrect"):
            run_candidate(
                items,
                judge_model="judge:1",
                generative_model="qwen3:8b",
                backend=FakeBackend(),
                thresholds=THRESHOLDS,
            )

    def test_the_family_guard_still_applies(self) -> None:
        with pytest.raises(JudgeConfigurationError):
            run_candidate(
                _items(),
                judge_model="qwen3:8b",
                generative_model="qwen3:8b",
                backend=FakeBackend(),
                thresholds=THRESHOLDS,
            )


class TestRunCalibration:
    def test_decides_across_candidates(self) -> None:
        backends = {"good:1": FakeBackend(), "biased:1": PositionBiasedBackend()}
        result = run_calibration(
            _items(),
            candidates=list(backends),
            generative_model="qwen3:8b",
            backend_for=backends.__getitem__,
            thresholds=THRESHOLDS,
            n_resamples=50,
        )
        assert [r.metrics.model for r in result.runs] == ["good:1", "biased:1"]
        assert result.decision.selected == "good:1"
        assert "position_consistency" in result.decision.failures["biased:1"]


def test_candidates_come_from_the_config() -> None:
    assert load_candidates() == (
        "mistral-small3.2:24b",
        "atla/selene-mini:q8_0",
        "gpt-oss:20b",
    )
