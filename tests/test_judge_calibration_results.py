"""Tests for storing and reading the raw judge calibration results (issue #82)."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.evaluation.judge_calibration import CandidateMetrics, FieldAgreement, JudgeDecision
from afg.evaluation.judge_calibration_results import (
    CalibrationResultsError,
    load_calibration_results,
    save_calibration_results,
)
from afg.evaluation.judge_calibration_runner import CalibrationResult, CandidateRun
from afg.evaluation.metrics import BootstrapCI


def _run(model: str, kappa: float, evidence: FieldAgreement | None) -> CandidateRun:
    return CandidateRun(
        metrics=CandidateMetrics(
            model=model,
            kappa_correct=BootstrapCI(kappa, kappa - 0.1, kappa + 0.1, 0.95, 1000),
            position_consistency=0.95,
            seed_consistency=0.99,
            e4_accuracy=0.9,
            json_valid_rate=1.0,
            verbosity_flip_rate=0.05,
            latency_seconds=1.5,
        ),
        evidence_supported=evidence,
        calls=120,
        failures=1,
    )


@pytest.fixture
def result() -> CalibrationResult:
    return CalibrationResult(
        runs=(_run("a", 0.8, FieldAgreement(kappa=0.6, accuracy=0.8, n=40)), _run("b", 0.5, None)),
        decision=JudgeDecision(selected="a", failures={"a": (), "b": ("kappa_correct",)}),
    )


def test_roundtrip_keeps_metrics_decision_and_size(
    tmp_path: Path, result: CalibrationResult
) -> None:
    path = tmp_path / "reports" / "judge" / "results.json"
    save_calibration_results(path, result, n_items=40)

    stored = load_calibration_results(path)

    assert stored.n_items == 40
    assert [c.model for c in stored.candidates] == ["a", "b"]
    first = stored.candidates[0]
    assert (first.kappa, first.kappa_lower, first.kappa_upper) == (
        0.8,
        pytest.approx(0.7),
        pytest.approx(0.9),
    )
    assert first.evidence_kappa == 0.6 and stored.candidates[1].evidence_kappa is None
    assert first.calls == 120 and first.failures == 1 and first.latency_seconds == 1.5
    assert stored.outcome == "selected" and stored.selected == "a"
    assert stored.failures == {"a": (), "b": ("kappa_correct",)}


def test_no_judge_outcome(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    save_calibration_results(
        path,
        CalibrationResult(
            runs=(_run("a", 0.2, None),),
            decision=JudgeDecision(selected=None, failures={"a": ("kappa_correct",)}),
        ),
        n_items=10,
    )
    stored = load_calibration_results(path)
    assert stored.outcome == "no_judge" and stored.selected is None


def test_unreadable_file_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(CalibrationResultsError):
        load_calibration_results(path)
