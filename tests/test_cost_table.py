"""Tests for the consolidated cost/latency table. Fixtures are tiny stored-result shapes."""

from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd
import pytest

from afg.evaluation.judge_calibration_results import StoredCalibration, StoredCandidate
from afg.experiments.cost_table import (
    CostRow,
    answer_and_judge_costs,
    compare_to_baseline,
    cost_frame,
    extraction_manifest_cost,
    judge_calibration_costs,
    screen_by_model,
    screen_costs,
    screen_quality,
    screen_rule,
    screen_winner,
    tau_judge_cost,
)


def _record(
    condition: str = "C1",
    *,
    answer: float | None = 10.0,
    judge: float | None = 4.0,
    model: str = "qwen3:8b",
    judge_model: str = "gpt-oss:20b",
) -> dict[str, Any]:
    return {
        "condition": condition,
        "generative_model": model,
        "judge": {"model": judge_model},
        "answer_seconds": answer,
        "judge_seconds": judge,
    }


class TestAnswerAndJudgeCosts:
    def test_one_answer_row_per_condition_and_one_judge_row(self) -> None:
        records = [
            _record("C1", answer=10.0, judge=4.0),
            _record("C1", answer=20.0, judge=6.0),
            _record("C2", answer=30.0, judge=8.0),
        ]
        rows = answer_and_judge_costs(records, label="humo")
        by = {(r.role, r.activity): r for r in rows}
        c1 = by[("answer", "humo / C1")]
        assert c1.model == "qwen3:8b"
        assert c1.units == 2
        assert c1.mean_seconds == pytest.approx(15.0)
        assert c1.total_seconds == pytest.approx(30.0)
        judge = by[("judge", "humo")]
        assert judge.model == "gpt-oss:20b"
        assert judge.units == 3
        assert judge.total_seconds == pytest.approx(18.0)
        assert judge.mean_seconds == pytest.approx(6.0)

    def test_records_without_timings_are_not_counted(self) -> None:
        records = [_record(answer=None, judge=None), _record(answer=10.0, judge=2.0)]
        rows = answer_and_judge_costs(records, label="x")
        assert {r.units for r in rows} == {1}

    def test_no_records_no_rows(self) -> None:
        assert answer_and_judge_costs([], label="x") == []


def _scored() -> dict[str, dict[str, Any]]:
    return {
        "qwen3:8b|ES2015": {
            "model": "qwen3:8b",
            "series": "ES2015",
            "runs": 2,
            "meeting_runs": 8,
            "failed_meeting_runs": 1,
            "wall_s_per_run": [100.0, 120.0],
            "decisions_per_meeting_mean": 15.0,
        },
        "qwen3.6:27b|ES2015": {
            "model": "qwen3.6:27b",
            "series": "ES2015",
            "runs": 2,
            "meeting_runs": 8,
            "failed_meeting_runs": 0,
            "wall_s_per_run": [300.0, 400.0],
            "decisions_per_meeting_mean": 9.0,
        },
    }


class TestScreenCosts:
    def test_one_row_per_model_and_series(self) -> None:
        rows = screen_costs(_scored(), phase="screen", baseline="qwen3:8b")
        assert [(r.model, r.units) for r in rows] == [("qwen3:8b", 2), ("qwen3.6:27b", 2)]
        big = rows[1]
        assert big.role == "extraction"
        assert big.mean_seconds == pytest.approx(350.0)
        assert big.total_seconds == pytest.approx(700.0)
        assert "screen" in big.activity and "ES2015" in big.activity

    def test_ratio_against_the_baseline_of_the_same_series(self) -> None:
        rows = screen_costs(_scored(), phase="screen", baseline="qwen3:8b")
        assert rows[0].ratio == pytest.approx(1.0)
        assert rows[1].ratio == pytest.approx(350.0 / 110.0)

    def test_detail_reports_volume_and_failures(self) -> None:
        rows = screen_costs(_scored(), phase="screen", baseline="qwen3:8b")
        assert "15.0 decisiones/reunión" in rows[0].detail
        assert "1 de 8" in rows[0].detail

    def test_missing_baseline_leaves_the_ratio_empty(self) -> None:
        rows = screen_costs(_scored(), phase="screen", baseline="not-there")
        assert all(r.ratio is None for r in rows)


class TestOtherSources:
    def test_judge_calibration_rows(self) -> None:
        stored = StoredCalibration(
            n_items=42,
            candidates=(
                StoredCandidate(
                    model="gpt-oss:20b",
                    kappa=0.95,
                    kappa_lower=0.8,
                    kappa_upper=1.0,
                    position_consistency=0.95,
                    seed_consistency=1.0,
                    e4_accuracy=1.0,
                    json_valid_rate=1.0,
                    verbosity_flip_rate=0.0,
                    latency_seconds=3.0,
                    evidence_kappa=None,
                    calls=270,
                    failures=0,
                ),
            ),
            outcome="selected",
            selected="gpt-oss:20b",
            failures={},
        )
        (row,) = judge_calibration_costs(stored)
        assert (row.role, row.model, row.units) == ("judge", "gpt-oss:20b", 270)
        assert row.mean_seconds == pytest.approx(3.0)
        assert row.total_seconds == pytest.approx(810.0)

    def test_tau_judge_row(self) -> None:
        meta = {"judge_model": "gpt-oss:20b", "judge_seconds_total": 1080.0, "n_pairs": 200}
        row = tau_judge_cost(meta)
        assert row.units == 200
        assert row.mean_seconds == pytest.approx(5.4)
        assert row.total_seconds == pytest.approx(1080.0)

    def test_extraction_manifest_cost_uses_the_manifest_timestamps(self) -> None:
        manifest = {
            "created_at": "2026-10-16T16:53:59+00:00",
            "updated_at": "2026-10-16T17:19:41+00:00",
            "runs": 1,
            "openkos": {"generative_model": "qwen3:8b", "versions": ["0.5.5"]},
            "series": "ES2015",
        }
        row = extraction_manifest_cost(manifest, label="es2015-explora-r1")
        assert row.model == "qwen3:8b"
        assert row.units == 1
        assert row.total_seconds == pytest.approx(25 * 60 + 42)
        assert "0.5.5" in row.detail

    def test_batch_manifest_counts_one_unit_per_series_and_run(self) -> None:
        manifest = {
            "created_at": "2026-10-16T16:00:00+00:00",
            "updated_at": "2026-10-16T17:00:00+00:00",
            "kind": "batch",
            "runs": 3,
            "series": "ES2015,TS3009",
            "series_ids": ["ES2015", "TS3009"],
            "openkos": {"generative_model": "qwen3:8b", "versions": ["0.6.0"]},
        }
        row = extraction_manifest_cost(manifest, label="lote")
        assert row.units == 6
        assert row.mean_seconds == pytest.approx(600.0)

    def test_extraction_manifest_without_update_time_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="updated_at"):
            extraction_manifest_cost({"created_at": "2026-10-16T16:53:59+00:00"}, label="x")


class TestCostFrame:
    def test_frame_has_one_row_per_cost_row_and_stable_columns(self) -> None:
        rows = [
            CostRow("answer", "qwen3:8b", "C1", 2, 10.0, 20.0, source="a"),
            CostRow("judge", "gpt-oss:20b", "j", 2, 5.0, 10.0, source="b"),
        ]
        frame = cost_frame(rows)
        assert isinstance(frame, pd.DataFrame)
        assert list(frame.columns) == [
            "role",
            "model",
            "activity",
            "units",
            "mean_seconds",
            "total_seconds",
            "ratio",
            "detail",
            "source",
        ]
        assert len(frame) == 2

    def test_empty_frame_keeps_the_columns(self) -> None:
        assert "mean_seconds" in cost_frame([]).columns


def _scored_with_curve() -> dict[str, dict[str, Any]]:
    scored = _scored()
    curves = {
        "qwen3:8b|ES2015": (0.50, 0.30, 0.45),
        "qwen3.6:27b|ES2015": (0.60, 0.50, 0.40),
    }
    for key, (recall, f1, precision) in curves.items():
        scored[key]["curve"] = [
            {
                "tau": 0.5,
                "recall": {"mean": 0.9},
                "f1": {"mean": 0.6, "min": 0.5, "max": 0.7},
                "precision": {"mean": 0.4},
            },
            {
                "tau": 0.6,
                "recall": {"mean": recall},
                "f1": {"mean": f1, "min": f1 - 0.05, "max": f1 + 0.05},
                "precision": {"mean": precision},
            },
        ]
    return scored


class TestScreenQuality:
    def test_quality_at_the_requested_tau_next_to_cost(self) -> None:
        frame = screen_quality(_scored_with_curve(), tau=0.60, phase="screen")
        row = frame[frame["model"] == "qwen3.6:27b"].iloc[0]
        assert row["f1"] == pytest.approx(0.50)
        assert row["f1_min"] == pytest.approx(0.45)
        assert row["recall"] == pytest.approx(0.60)
        assert row["precision"] == pytest.approx(0.40)
        assert row["seconds_per_run"] == pytest.approx(350.0)
        assert row["decisions_per_meeting"] == pytest.approx(9.0)
        assert row["phase"] == "screen"

    def test_a_tau_outside_the_curve_is_an_error(self) -> None:
        with pytest.raises(ValueError, match=r"0.77"):
            screen_quality(_scored_with_curve(), tau=0.77, phase="screen")

    def test_by_model_averages_the_series(self) -> None:
        scored = _scored_with_curve()
        scored["qwen3:8b|TS3009"] = {
            **scored["qwen3:8b|ES2015"],
            "series": "TS3009",
            "wall_s_per_run": [300.0],
            "runs": 1,
        }
        scored["qwen3:8b|TS3009"]["curve"] = [
            {
                "tau": 0.6,
                "recall": {"mean": 0.7},
                "f1": {"mean": 0.4, "min": 0.3, "max": 0.5},
                "precision": {"mean": 0.3},
            }
        ]
        frame = screen_by_model(screen_quality(scored, tau=0.60, phase="screen"))
        base = frame.loc["qwen3:8b"]
        assert base["f1"] == pytest.approx(0.35)
        assert base["seconds_per_run"] == pytest.approx((110.0 + 300.0) / 2)


def _quality(rows: list[tuple[str, str, float, float, float, float, float, float, int]]):
    """(model, series, f1, f1_min, f1_max, recall, decisions/meeting, seconds, failed)."""
    return pd.DataFrame(
        [
            {
                "model": m,
                "series": s,
                "f1": f1,
                "f1_min": lo,
                "f1_max": hi,
                "recall": r,
                "decisions_per_meeting": d,
                "seconds_per_run": sec,
                "failed_meeting_runs": failed,
                "meeting_runs": 20,
            }
            for m, s, f1, lo, hi, r, d, sec, failed in rows
        ]
    )


class TestScreenRule:
    ROWS: ClassVar[list] = [
        ("base", "S1", 0.30, 0.25, 0.35, 0.50, 10.0, 100.0, 0),
        ("good", "S1", 0.50, 0.45, 0.55, 0.60, 9.0, 300.0, 0),
        ("noisy", "S1", 0.40, 0.20, 0.60, 0.60, 9.0, 300.0, 0),
        ("verbose", "S1", 0.50, 0.45, 0.55, 0.60, 12.0, 300.0, 0),
        ("fragile", "S1", 0.50, 0.45, 0.55, 0.60, 9.0, 300.0, 5),
        ("lossy", "S1", 0.50, 0.45, 0.55, 0.40, 9.0, 300.0, 0),
    ]

    def test_each_condition_of_the_preregistered_rule_is_checked_apart(self) -> None:
        rule = screen_rule(_quality(self.ROWS), baseline="base").set_index("candidate")
        assert bool(rule.loc["good", "passes"])
        assert rule.loc["good", "d_f1"] == pytest.approx(0.20)
        assert not rule.loc["noisy", "margin_ok"]  # 0.10 gain < spread 0.40
        assert rule.loc["noisy", "needed"] == pytest.approx(0.40)
        assert not rule.loc["verbose", "volume_ok"]  # 12 > 1.10 x 10
        assert not rule.loc["fragile", "failures_ok"]  # 5 > max(2, 0)
        assert not rule.loc["lossy", "recall_ok"]

    def test_margin_needs_at_least_the_floor_even_with_no_spread(self) -> None:
        rows = [
            ("base", "S1", 0.30, 0.30, 0.30, 0.5, 10.0, 1.0, 0),
            ("c", "S1", 0.33, 0.33, 0.33, 0.5, 10.0, 1.0, 0),
        ]
        rule = screen_rule(_quality(rows), baseline="base")
        assert rule.loc[0, "needed"] == pytest.approx(0.05)
        assert not bool(rule.loc[0, "margin_ok"])

    def test_the_baseline_is_not_a_candidate(self) -> None:
        rule = screen_rule(_quality(self.ROWS), baseline="base")
        assert "base" not in set(rule["candidate"])

    def test_winner_passes_every_series_and_has_the_largest_mean_gain(self) -> None:
        rows = [
            ("base", "S1", 0.30, 0.28, 0.32, 0.5, 10.0, 1.0, 0),
            ("base", "S2", 0.30, 0.28, 0.32, 0.5, 10.0, 1.0, 0),
            ("a", "S1", 0.50, 0.48, 0.52, 0.6, 9.0, 1.0, 0),
            ("a", "S2", 0.50, 0.48, 0.52, 0.6, 9.0, 1.0, 0),
            ("b", "S1", 0.60, 0.58, 0.62, 0.6, 9.0, 1.0, 0),
            ("b", "S2", 0.31, 0.30, 0.32, 0.6, 9.0, 1.0, 0),
        ]
        rule = screen_rule(_quality(rows), baseline="base")
        assert screen_winner(rule) == "a"  # b fails S2

    def test_no_winner_when_nobody_passes(self) -> None:
        rule = screen_rule(_quality(self.ROWS[:1] + self.ROWS[2:3]), baseline="base")
        assert screen_winner(rule) is None


def test_the_rule_reproduces_the_stored_screen_of_notebook_15() -> None:
    import json

    from afg.shared.paths import EXPERIMENT_A_DIR

    path = EXPERIMENT_A_DIR / "model-screen-openkos" / "screen" / "scored.json"
    scored = json.loads(path.read_text(encoding="utf-8"))
    rule = screen_rule(screen_quality(scored, tau=0.60, phase="screen"), baseline="qwen3:8b")
    assert screen_winner(rule) == "qwen3.6:27b"
    row = rule[(rule["candidate"] == "qwen3:14b") & (rule["series"] == "ES2015")].iloc[0]
    assert not bool(row["margin_ok"])  # 0.097 gain against 0.099 needed
    assert row["d_f1"] == pytest.approx(0.097, abs=5e-4)
    assert row["needed"] == pytest.approx(0.099, abs=5e-4)


class TestCompareToBaseline:
    ROWS: ClassVar[list] = [
        ("base", "S1", 0.30, 0.25, 0.35, 0.50, 10.0, 100.0, 1),
        ("big", "S1", 0.50, 0.45, 0.55, 0.60, 8.0, 360.0, 0),
        ("base", "S2", 0.40, 0.35, 0.45, 0.70, 12.0, 200.0, 4),
        ("big", "S2", 0.45, 0.40, 0.50, 0.65, 9.0, 300.0, 2),
        ("other", "S1", 0.10, 0.05, 0.15, 0.20, 5.0, 50.0, 0),
    ]

    def test_one_row_per_series_with_the_candidate_against_the_baseline(self) -> None:
        out = compare_to_baseline(_quality(self.ROWS), baseline="base", candidate="big")
        assert list(out.index) == ["S1", "S2"]
        assert out.loc["S1", "f1_baseline"] == pytest.approx(0.30)
        assert out.loc["S1", "f1_candidate"] == pytest.approx(0.50)
        assert out.loc["S1", "d_f1"] == pytest.approx(0.20)
        assert out.loc["S2", "d_recall"] == pytest.approx(-0.05)
        assert out.loc["S1", "seconds_baseline"] == pytest.approx(100.0)
        assert out.loc["S1", "time_ratio"] == pytest.approx(3.6)
        assert out.loc["S2", "time_ratio"] == pytest.approx(1.5)
        assert out.loc["S2", "failed_baseline"] == 4
        assert out.loc["S2", "failed_candidate"] == 2
        assert out.loc["S2", "meeting_runs"] == 20

    def test_a_series_missing_for_one_model_is_left_out(self) -> None:
        rows = [r for r in self.ROWS if not (r[0] == "big" and r[1] == "S2")]
        out = compare_to_baseline(_quality(rows), baseline="base", candidate="big")
        assert list(out.index) == ["S1"]

    def test_an_absent_model_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="nope"):
            compare_to_baseline(_quality(self.ROWS), baseline="base", candidate="nope")
