"""Tests for the judge calibration runner (thesis section 5.7). Fake backend, no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.evaluation.judge import JudgeConfigurationError, MissingTranscriptExcerptError
from afg.evaluation.judge_calibration import CalibrationThresholds
from afg.evaluation.judge_calibration_runner import (
    load_candidates,
    load_think_settings,
    pad_to_double_length,
    run_calibration,
    run_candidate,
    stored_excerpt_for,
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


def _evidence_item(excerpt: str | None) -> CalibrationItem:
    return _item(0, good=True).model_copy(
        update={
            "reference_evidence": (
                EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.1",)),
            ),
            "transcript_excerpt": excerpt,
        }
    )


def _calibrate(backends: dict[str, FakeBackend], **kwargs: Any) -> Any:
    return run_calibration(
        _items(),
        candidates=list(backends),
        generative_model="qwen3:8b",
        backend_for=lambda model: backends[model],
        thresholds=THRESHOLDS,
        n_resamples=50,
        **kwargs,
    )


class TestProgressAndResume:
    def test_progress_reports_every_call_up_to_the_known_total(self) -> None:
        seen: list[tuple[str, int, int]] = []
        _run(FakeBackend(), progress=lambda model, done, total: seen.append((model, done, total)))
        total = 10 * 2 * 3 + 5  # items x orders x seeds + padded wrong answers
        assert [d for _, d, _ in seen] == list(range(1, total + 1))
        assert {(m, t) for m, _, t in seen} == {("judge:1", total)}

    def test_each_candidate_is_saved_as_soon_as_it_finishes(self) -> None:
        events: list[str] = []

        class Tracking(FakeBackend):
            def __init__(self, name: str) -> None:
                super().__init__()
                self.name = name

            def complete(self, *args: Any, **kwargs: Any) -> str:
                if not any(e == f"start:{self.name}" for e in events):
                    events.append(f"start:{self.name}")
                return super().complete(*args, **kwargs)

        _calibrate(
            {"a": Tracking("a"), "b": Tracking("b")},
            save_run=lambda model, run: events.append(f"save:{model}"),
        )
        assert events == ["start:a", "save:a", "start:b", "save:b"]

    def test_candidates_with_a_stored_run_are_skipped_and_the_decision_covers_all(self) -> None:
        stored: dict[str, Any] = {}
        first = _calibrate({"a": FakeBackend(), "b": FakeBackend()}, save_run=stored.__setitem__)
        backend_a, backend_b = FakeBackend(), FakeBackend()
        reused: list[str] = []
        second = _calibrate(
            {"a": backend_a, "b": backend_b},
            load_run=stored.get,
            on_done=lambda model, run, was_reused: reused.append(model) if was_reused else None,
        )
        assert backend_a.calls == [] and backend_b.calls == []
        assert reused == ["a", "b"]
        assert second.runs == first.runs and second.decision == first.decision

    def test_only_the_missing_candidate_is_run_on_resume(self) -> None:
        stored: dict[str, Any] = {}
        _calibrate({"a": FakeBackend()}, save_run=stored.__setitem__)
        backend_a, backend_b = FakeBackend(), FakeBackend()
        result = _calibrate({"a": backend_a, "b": backend_b}, load_run=stored.get)
        assert backend_a.calls == [] and backend_b.calls != []
        assert [r.metrics.model for r in result.runs] == ["a", "b"]

    def test_on_done_reports_fresh_runs_too(self) -> None:
        done: list[tuple[str, bool]] = []
        _calibrate(
            {"a": FakeBackend()}, on_done=lambda model, run, reused: done.append((model, reused))
        )
        assert done == [("a", False)]


class TestStoredExcerpt:
    def test_the_stored_excerpt_wins_over_rebuilding(self, tmp_path: Path) -> None:
        item = _evidence_item("[ES2015a]\nPM: what the labeler saw")
        assert stored_excerpt_for(item, transcripts_dir=tmp_path) == item.transcript_excerpt

    def test_it_is_built_from_the_transcript_only_when_the_column_is_absent(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "ES2015a.jsonl").write_text(
            json.dumps(
                {
                    "meeting_id": "ES2015a",
                    "turn_index": 0,
                    "speaker": "A",
                    "role": "PM",
                    "text": "built",
                    "start": 0.0,
                    "end": 1.0,
                    "char_start": 0,
                    "char_end": 1,
                    "dialogue_act_ids": ["ES2015a.A.dialog-act.x.1"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        assert stored_excerpt_for(_evidence_item(None), transcripts_dir=tmp_path) == (
            "[ES2015a]\nPM: built"
        )

    def test_an_empty_stored_excerpt_on_an_answerable_item_makes_the_run_fail(self) -> None:
        items = [_evidence_item(""), *_items()[1:]]
        with pytest.raises(MissingTranscriptExcerptError):
            run_candidate(
                items,
                judge_model="judge:1",
                generative_model="qwen3:8b",
                backend=FakeBackend(),
                thresholds=THRESHOLDS,
                n_resamples=50,
            )


class TestExcerpt:
    def test_every_call_gets_the_item_excerpt_in_both_orders_and_in_the_padded_probe(
        self,
    ) -> None:
        backend = FakeBackend()
        _run(backend, excerpt_for=lambda item: f"EXCERPT-OF-{item.id}")
        assert len(backend.calls) == 10 * 2 * 3 + 5
        for call in backend.calls:
            user = call["user"]
            item_id = user.split("question ")[1].split("\n")[0]
            assert f"Transcript excerpt:\nEXCERPT-OF-i{item_id}" in user

    def test_default_excerpt_is_built_from_the_reference_evidence(self) -> None:
        backend = FakeBackend()
        _run(backend)  # test items have no reference evidence
        assert all("Transcript excerpt:\nNone:" in call["user"] for call in backend.calls)


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


class TestThinkSettings:
    def test_shipped_config_bounds_the_reasoning_of_gpt_oss_only(self) -> None:
        settings = load_think_settings()
        assert settings == {"gpt-oss:20b": "low"}
        assert set(settings) <= set(load_candidates())
