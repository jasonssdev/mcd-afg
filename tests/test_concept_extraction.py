"""Tests for reading the OpenKOS concept-extraction screens from their aggregated files."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from afg.experiments.concept_extraction import (
    STAGES,
    WINDOW_ARMS,
    ask_halving,
    ask_penalty_frame,
    ask_role_frame,
    ask_select,
    ask_vetoes,
    drop_class_counts,
    drop_rule_frame,
    exploratory_forecast,
    g1_frame,
    judge_labels,
    judge_study_frame,
    judge_verdict,
    l7_attribution,
    load_concept_screens,
    per_meeting_deltas,
    round_frame,
    round_one_vetoes,
    round_two_selection,
    stage_frame,
    trace_frame,
    window_arm_frame,
    window_selection,
)


def _partition(series: str) -> str:
    return "development" if series in {"ES2015", "IS1004", "TS3009"} else "evaluation"


def _frac(num: int, den: int) -> dict[str, int]:
    return {"num": num, "den": den}


def _ci(point: float, low: float, high: float) -> dict[str, float]:
    return {"point": point, "low": low, "high": high}


def _model(
    *,
    dlift: dict[str, float] | None = None,
    failures: tuple[int, int] = (0, 40),
    objects: float = 5.0,
    wrong_language: tuple[int, int] = (0, 10),
    verbatim: tuple[int, int] = (0, 25),
    stage_lifts: tuple[float, ...] = (0.05, 0.05, 0.04, 0.04, 0.04, 0.03, 0.03),
) -> dict[str, Any]:
    m: dict[str, Any] = {
        "window_lift_mean": stage_lifts[-1],
        "meeting_lift_mean": 0.01,
        "failures": _frac(*failures),
        "objects_total": int(objects * 5),
        "meeting_runs": 5,
        "objects_per_meeting": objects,
        "verbatim": _frac(*verbatim),
        "prose": {"wrong_language": _frac(*wrong_language)},
        "median_window_s": 30.0,
        "mean_s_per_meeting_run": 250.0,
        "counters": {"judged_out": 4, "participant_added": 9},
        "stage_window_lift": dict(zip(STAGES, stage_lifts, strict=True)),
        "stage_table": {s: {"units": 10 - i, "lift": 0.01} for i, s in enumerate(STAGES)},
    }
    if dlift is not None:
        m["dlift"] = dlift
        m["dlift_meeting"] = _ci(0.01, 0.0, 0.02)
    return m


def _round(models: dict[str, dict[str, Any]], meetings: tuple[str, ...]) -> dict[str, Any]:
    return {
        "models": models,
        "per_window": {name: {m: {"0": [0.0]} for m in meetings} for name in models},
        "g1": {},
    }


def _arm(
    *,
    windows: int,
    dlift: dict[str, float] | None,
    failed_chars: tuple[int, int] = (0, 1000),
    objects: float = 4.0,
    redundant: tuple[int, int] = (1, 20),
    per_meeting: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    arm: dict[str, Any] = {
        "failures": _frac(0, windows * 2),
        "meeting_lift_mean": 0.01,
        "failed_chars": _frac(*failed_chars),
        "objects_total": int(objects * 10),
        "objects_per_meeting": objects,
        "verbatim": _frac(0, 20),
        "prose": {"wrong_language": _frac(0, 10), "subject_recall_exact": _frac(20, 33)},
        "redundant_final": _frac(*redundant),
        "judged": {"coverage_mean": 0.25, "precision": _frac(9, 10)},
        "medium10_699": [{"windows": 4}],
        "median_window_s": 30.0,
        "mean_s_per_meeting_run": 300.0,
        "per_meeting": per_meeting or {"ES2015a": [0.01, 0.03]},
        "stage_table": {s: {"units": 5, "lift": 0.01} for s in STAGES},
    }
    if dlift is not None:
        arm["dlift_meeting"] = dlift
    return arm


def _window_score(**overrides: dict[str, Any]) -> dict[str, Any]:
    arms = {
        "c4000": _arm(windows=41, dlift=None, failed_chars=(20, 1000), objects=4.0),
        "c6000": _arm(windows=27, dlift=_ci(0.01, 0.002, 0.02), objects=3.0),
        "c8000": _arm(windows=22, dlift=_ci(-0.01, -0.02, -0.001), objects=2.4),
        "c12000": _arm(windows=15, dlift=_ci(0.02, 0.01, 0.03), objects=1.9),
    }
    arms.update(overrides)
    return {"runs": [1, 2], "arms": arms}


def _write(root: Path, *, classes: list[dict[str, Any]], meetings: tuple[str, ...]) -> None:
    files: dict[str, Any] = {
        "model-screen/r1.json": _round({"qwen3:8b": _model()}, meetings),
        "model-screen/r2.json": _round({"qwen3:8b": _model()}, meetings),
        "model-screen/validity.json": _round({"qwen3:8b": _model()}, meetings),
        "model-screen/stage0.json": {"models": {}},
        "model-screen/decisions/r1-1.json": {"trace": []},
        "drop-ablation/drop_ablation.json": {"primary": {}},
        "drop-ablation/drop_ablation_classes.json": classes,
        "window-screen/w8b.json": _window_score(),
        "window-screen/stage0.json": {"models": {}},
        "window-screen/decisions/w8b.json": {"trace": []},
        "judge-study/judge_study.json": {"primary": {}},
        "ask-screen/round1.json": {},
        "ask-screen/round2.json": {},
        "ask-screen/confirmation.json": {},
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content), encoding="utf-8")


_CLASS_ROW = {"rule": "framing", "meeting": "IS1004b", "type": "Event", "class": "target"}


def test_loader_reads_every_file(tmp_path: Path) -> None:
    _write(tmp_path, classes=[_CLASS_ROW], meetings=("ES2015a", "TS3009c"))
    screens = load_concept_screens(tmp_path, partition_of=_partition)
    assert set(screens.round1["models"]) == {"qwen3:8b"}
    assert set(screens.model_decisions) == {"r1-1"}
    assert screens.ablation_classes == [_CLASS_ROW]


def test_loader_refuses_an_evaluation_meeting(tmp_path: Path) -> None:
    _write(tmp_path, classes=[_CLASS_ROW], meetings=("ES2015a", "ES2002a"))
    with pytest.raises(ValueError, match="ES2002a is not in a development series"):
        load_concept_screens(tmp_path, partition_of=_partition)


def test_loader_refuses_an_evaluation_meeting_in_the_audit(tmp_path: Path) -> None:
    _write(tmp_path, classes=[{**_CLASS_ROW, "meeting": "TS3003c"}], meetings=("ES2015a",))
    with pytest.raises(ValueError, match="TS3003c"):
        load_concept_screens(tmp_path, partition_of=_partition)


def test_loader_refuses_model_written_text(tmp_path: Path) -> None:
    _write(tmp_path, classes=[{**_CLASS_ROW, "title": "x"}], meetings=("ES2015a",))
    with pytest.raises(ValueError, match="titles or descriptions"):
        load_concept_screens(tmp_path, partition_of=_partition)


def _round_one() -> dict[str, Any]:
    return {
        "models": {
            "qwen3:8b": _model(failures=(1, 40), objects=5.0),
            # V3: 2 of 10 wrong-language titles > 0 + 0.02.
            "qwen3.6:35b-a3b": _model(dlift=_ci(0.03, -0.01, 0.05), wrong_language=(2, 10)),
            # V4: 8.0 objects is outside [2.5, 7.5].
            "gemma4:26b-a4b": _model(dlift=_ci(0.04, -0.01, 0.06), objects=8.0),
            # V1: 3 of 40 = 0.075 > 0.025 + 0.02.
            "qwen3:14b": _model(dlift=_ci(0.05, -0.01, 0.07), failures=(3, 40)),
            # Passes every veto.
            "qwen3.6:27b": _model(dlift=_ci(-0.01, -0.03, 0.01), objects=7.5),
        }
    }


def test_round_frame_orders_models_and_leaves_baseline_delta_empty() -> None:
    frame = round_frame(_round_one())
    assert frame.model.tolist()[0] == "qwen3:8b"
    assert math.isnan(frame.dlift.iloc[0])
    assert frame.set_index("model").loc["qwen3:14b"].failure_rate == pytest.approx(0.075)


def test_round_one_vetoes_name_the_failing_veto_and_keep_survivors() -> None:
    vetoes = round_one_vetoes(round_frame(_round_one())).set_index("model")
    assert not vetoes.loc["qwen3.6:35b-a3b", "V3"]
    assert not vetoes.loc["gemma4:26b-a4b", "V4"]
    assert not vetoes.loc["qwen3:14b", "V1"]
    # 7.5 sits on the inclusive upper volume bound.
    assert vetoes.loc["qwen3.6:27b", "V4"]
    assert vetoes.kept.tolist() == [False, False, False, True]


def test_round_one_drops_a_candidate_whose_interval_lies_below_zero() -> None:
    score = _round_one()
    score["models"]["qwen3.6:27b"]["dlift"] = _ci(-0.03, -0.05, -0.001)
    vetoes = round_one_vetoes(round_frame(score)).set_index("model")
    assert not vetoes.loc["qwen3.6:27b", "passes"]


def test_round_one_keeps_at_most_half_of_the_candidates_by_point_delta() -> None:
    score = {
        "models": {
            "qwen3:8b": _model(),
            "a": _model(dlift=_ci(0.01, -0.01, 0.02)),
            "b": _model(dlift=_ci(0.03, -0.01, 0.04)),
            "c": _model(dlift=_ci(0.02, -0.01, 0.03)),
            "d": _model(dlift=_ci(0.00, -0.01, 0.01)),
        }
    }
    kept = round_one_vetoes(round_frame(score)).set_index("model").kept
    assert set(kept[kept].index) == {"b", "c"}


def _round_two(*, g1_low: float, lift_low: float) -> dict[str, Any]:
    return {
        "models": {
            "qwen3:8b": _model(),
            "qwen3.6:27b": _model(dlift=_ci(0.01, lift_low, 0.02)),
        },
        "g1": {
            "qwen3:8b": {
                "precision": _frac(38, 41),
                "partial": 1,
                "unsupported": 2,
                "judge_coverage_mean": 0.27,
            },
            "qwen3.6:27b": {
                "precision": _frac(28, 31),
                "partial": 2,
                "unsupported": 1,
                "dprecision": _ci(-0.02, g1_low, 0.1),
                "judge_coverage_mean": 0.23,
            },
        },
    }


@pytest.mark.parametrize(
    ("g1_low", "lift_low", "selected"),
    [(-0.04, 0.001, True), (-0.06, 0.001, False), (-0.04, 0.0, False)],
)
def test_round_two_selection_needs_both_lower_bounds(
    g1_low: float, lift_low: float, selected: bool
) -> None:
    score = _round_two(g1_low=g1_low, lift_low=lift_low)
    result = round_two_selection(round_frame(score), g1_frame(score))
    assert result.selected.tolist() == [selected]


def test_g1_frame_reads_precision_as_a_fraction() -> None:
    g1 = g1_frame(_round_two(g1_low=-0.1, lift_low=0.0)).set_index("model")
    assert g1.loc["qwen3:8b", "precision"] == pytest.approx(38 / 41)
    assert math.isnan(g1.loc["qwen3:8b", "dprecision"])


def test_stage_frame_reports_each_stage_change() -> None:
    frame = stage_frame({"models": {"qwen3:8b": _model()}})
    assert frame.stage.tolist() == list(STAGES)
    assert math.isnan(frame.change.iloc[0])
    assert frame.change.iloc[2] == pytest.approx(-0.01)
    assert frame.objects.iloc[0] == 10


def test_trace_frame_joins_reasons() -> None:
    decision = {"trace": [{"model": "m", "passed": False, "reasons": ["V1 x", "V4 y"]}]}
    assert trace_frame(decision).reasons.tolist() == ["V1 x; V4 y"]


def _rule(delta: float, dropped: int, emptied: int, fp: int = 0) -> dict[str, Any]:
    return {
        "delta": _ci(delta, delta - 0.01, delta + 0.01),
        "dropped": dropped,
        "windows_emptied": emptied,
        "false_positives": fp,
        "false_positive_delta": 0.0005 if fp else 0.0,
    }


def _ablation_model(l7: float, framing: float) -> dict[str, Any]:
    return {
        "rules": {"framing": _rule(framing, 9, 9), "dedup": _rule(0.0, 0, 0)},
        "l7_loss": l7,
        "l6_loss": 0.0,
        "caps": {"ceiling": {"objects_cut": 0}, "backstop": {"objects_cut": 0}},
        "invalid": [],
    }


def test_l7_attribution_gives_the_framing_share_only_for_a_loss() -> None:
    ablation = {
        "primary": {
            "loses": _ablation_model(0.008, 0.006),
            "gains": _ablation_model(-0.002, -0.002),
        }
    }
    frame = l7_attribution(ablation).set_index("model")
    assert frame.loc["loses", "l7_change"] == pytest.approx(-0.008)
    assert frame.loc["loses", "framing_share"] == pytest.approx(0.75)
    assert math.isnan(frame.loc["gains", "framing_share"])


def test_drop_rule_frame_has_one_row_per_model_and_rule() -> None:
    frame = drop_rule_frame({"primary": {"m": _ablation_model(0.008, 0.006)}})
    assert sorted(frame.rule) == ["dedup", "framing"]
    assert frame.set_index("rule").loc["framing", "windows_emptied"] == 9


def test_drop_class_counts_counts_by_rule_class_and_type() -> None:
    rows = [_CLASS_ROW, _CLASS_ROW, {**_CLASS_ROW, "type": "Decision", "class": "false_positive"}]
    counts = drop_class_counts(rows).set_index(["class", "type"]).objects
    assert counts.loc[("target", "Event")] == 2
    assert counts.loc[("false_positive", "Decision")] == 1


def test_window_arm_frame_derives_windows_per_run() -> None:
    frame = window_arm_frame(_window_score()).set_index("arm")
    assert frame.index.tolist() == list(WINDOW_ARMS)
    assert frame.loc[6000, "da_windows"] == 27
    assert math.isnan(frame.loc[4000, "dlift"])


def test_window_selection_applies_every_bar() -> None:
    # 6,000 passes everything; 8,000's interval excludes 0 from below;
    # 12,000: V1 (0.08 > 0.02 + 0.02), V4 (1.9 < 2.0) and F (0.2 > 0.05 + 0.10) fail.
    score = _window_score(
        c12000=_arm(
            windows=15,
            dlift=_ci(0.02, 0.01, 0.03),
            failed_chars=(80, 1000),
            objects=1.9,
            redundant=(4, 20),
        )
    )
    result = window_selection(window_arm_frame(score)).set_index("arm")
    assert result.loc[6000, "selected"]
    assert not result.loc[8000, "lift lower > 0"]
    assert not result.loc[12000, ["V1", "V4", "F"]].any()
    assert result.loc[12000, "lift lower > 0"]


def test_per_meeting_deltas_average_runs_before_subtracting() -> None:
    score = _window_score(
        c6000=_arm(windows=27, dlift=_ci(0, 0, 0), per_meeting={"ES2015a": [0.0, 0.01]})
    )
    deltas = per_meeting_deltas(score)
    assert deltas.loc[6000, "ES2015a"] == pytest.approx(0.005 - 0.02)


def test_exploratory_forecast_follows_the_registered_formula() -> None:
    stage0 = {
        "models": {
            "big": {
                "c6000": {"median_window_s": 20.0, "load_s": 5.0, "window_s": [10.0, 20.0]},
                "c8000": {"median_window_s": 40.0, "load_s": 5.0, "window_s": [30.0]},
            }
        }
    }
    forecast = exploratory_forecast(
        stage0,
        model="big",
        da_seconds=100.0,
        medium10_seconds=10.0,
        median_4000_s=10.0,
        da_windows={4000: 40, 6000: 20, 8000: 10},
        medium10_windows={4000: 4, 6000: 2, 8000: 2},
        budget_h=1.0,
    )
    # 6,000: 2 x (100 x 20 x 20 / 400 + 10 x 2 x 20 / 40) = 2 x (100 + 10) = 220.
    # 8,000: 2 x (100 x 10 x 40 / 400 + 10 x 2 x 40 / 40) = 2 x (100 + 20) = 240.
    assert forecast.per_arm_s == {6000: pytest.approx(220.0), 8000: pytest.approx(240.0)}
    # The shared load counts once: 5 + 10 + 20 + 30.
    assert forecast.stage0_s == pytest.approx(65.0)
    assert forecast.total_s == pytest.approx(220 + 240 + 10 + 65)
    assert forecast.runs


def _judge_arm(lift: float, loss: tuple[float, float, float] | None) -> dict[str, Any]:
    arm: dict[str, Any] = {"lift": lift, "kept": 10.0}
    if loss is not None:
        arm |= {
            "loss": _ci(*loss),
            "judged_out": 5.0,
            "seeds": [0, 1, 2],
            "seed_lifts": {"0": lift, "1": lift, "2": lift},
            "judge_failed": 0,
        }
    return arm


def _extractor(
    *, fixed_loss: tuple[float, float, float], coupling: tuple[float, float, float]
) -> dict[str, Any]:
    return {
        "meeting_runs": 5,
        "arms": {
            "none": _judge_arm(0.05, None),
            "self": _judge_arm(0.03, (-0.02, -0.04, -0.001)),
            "fixed": _judge_arm(0.04, fixed_loss),
        },
        "deltas": {"coupling": _ci(*coupling)},
    }


def _judge_study() -> dict[str, Any]:
    return {
        "primary": {
            # Coupling lower bound above 0, even though the fixed loss also excludes 0.
            "qwen3.6:27b": _extractor(
                fixed_loss=(-0.02, -0.04, -0.01), coupling=(0.01, 0.001, 0.03)
            ),
            # No coupling; the fixed loss excludes 0.
            "qwen3:8b": _extractor(
                fixed_loss=(-0.02, -0.04, -0.003), coupling=(-0.01, -0.02, -0.0)
            ),
            # Both intervals hold 0.
            "qwen3.6:35b-a3b": _extractor(
                fixed_loss=(-0.01, -0.02, 0.004), coupling=(0.006, -0.004, 0.02)
            ),
            # The fixed judge's own model: never labelled.
            "gemma4:26b-a4b": _extractor(
                fixed_loss=(-0.01, -0.03, -0.001), coupling=(0.0, 0.0, 0.0)
            ),
        }
    }


def test_judge_study_frame_reads_arms_losses_and_seeds() -> None:
    frame = judge_study_frame(_judge_study()).set_index("model")
    assert frame.index.tolist()[0] == "qwen3:8b"
    assert frame.loc["qwen3:8b", "none_lift"] == pytest.approx(0.05)
    assert frame.loc["qwen3:8b", "fixed_loss_high"] == pytest.approx(-0.003)
    assert frame.loc["qwen3:8b", "self_seed_lifts"] == (0.03, 0.03, 0.03)


def test_judge_labels_apply_the_registered_order() -> None:
    labels = judge_labels(judge_study_frame(_judge_study()))
    assert labels == {
        "qwen3:8b": "judge",
        "qwen3.6:35b-a3b": "unresolved",
        "qwen3.6:27b": "coupling",
    }


@pytest.mark.parametrize(
    ("labels", "verdict", "follow_up"),
    [
        ({"a": "coupling", "b": "judge", "c": "judge"}, "not_resolved", True),
        ({"a": "coupling", "b": "coupling", "c": "judge"}, "coupling", True),
        ({"a": "judge", "b": "judge", "c": "unresolved"}, "judge", True),
        ({"a": "judge", "b": "unresolved"}, "not_resolved", True),
        ({"a": "unresolved", "b": "unresolved"}, "not_resolved", False),
    ],
)
def test_judge_verdict_needs_two_of_a_kind_and_no_conflict(
    labels: dict[str, str], verdict: str, follow_up: bool
) -> None:
    assert judge_verdict(labels) == (verdict, follow_up)


def _guard(**overrides: float | None) -> dict[str, float | None]:
    g: dict[str, float | None] = {
        "suff_failure": 0.0,
        "ans_failure": 0.0,
        "suff_median_s": 2.0,
        "ans_median_s": 4.0,
        "grounded_refused": 0.2,
        "adjacent_missed": 0.0,
        "spanish_answers": 0.9,
        "compliance": 1.0,
    }
    g.update(overrides)
    return g


def _candidate(point: float, low: float, high: float, es_en_high: float = 0.1) -> dict[str, Any]:
    per_set = {
        name: {"n": 32, "mean": point, "lo": low, "hi": high} for name in ("es-es", "es-built")
    }
    per_set["es-en"] = {"n": 32, "mean": point, "lo": low, "hi": es_en_high}
    return {
        "delta": {"n": 96, "mean": point, "lo": low, "hi": high},
        "per_set": per_set,
        "vetoes": [],
    }


def _ask_report(
    guards: dict[str, dict[str, float | None]], role: str, cands: dict[str, Any]
) -> dict[str, Any]:
    return {
        "baseline": "base",
        "guardrails": {"base": _guard(), **guards},
        "roles": {role: {"baseline_mean": 0.8, "candidates": cands}},
        "penalty": {"base": {"sufficiency": {"n": 32, "mean": 0.01, "lo": -0.05, "hi": 0.07}}},
    }


@pytest.mark.parametrize(
    ("role", "guard", "es_en_high", "expected"),
    [
        ("sufficiency", {}, 0.1, []),
        ("sufficiency", {"suff_failure": 0.03}, 0.1, ["V1"]),
        ("sufficiency", {"suff_median_s": 4.1}, 0.1, ["V2"]),
        # 4.0 s is exactly 2.0x the baseline: allowed.
        ("sufficiency", {"suff_median_s": 4.0}, 0.1, []),
        ("sufficiency", {"grounded_refused": 0.21}, 0.1, ["S1"]),
        ("sufficiency", {"adjacent_missed": 0.03}, 0.1, ["S2"]),
        ("sufficiency", {}, -0.01, ["X1"]),
        ("answer", {"spanish_answers": 0.84}, 0.1, ["V3"]),
        ("answer", {"spanish_answers": 0.85}, 0.1, []),
        ("citation", {"compliance": 0.94}, 0.1, ["V4"]),
        # A veto of another role never applies.
        ("citation", {"spanish_answers": 0.1, "grounded_refused": 0.9}, 0.1, []),
        # No answer call (confirmation): no latency veto on that call.
        ("answer", {"ans_median_s": None}, 0.1, []),
    ],
)
def test_ask_vetoes_apply_each_registered_bar(
    role: str, guard: dict[str, float | None], es_en_high: float, expected: list[str]
) -> None:
    report = _ask_report(
        {"m": _guard(**guard)}, role, {"m": _candidate(0.05, 0.01, 0.1, es_en_high)}
    )
    assert ask_vetoes(report, role, "m") == expected


def test_ask_halving_keeps_the_top_half_of_the_eligible() -> None:
    report = _ask_report(
        {"a": _guard(), "b": _guard(), "c": _guard(), "d": _guard(adjacent_missed=0.1)},
        "sufficiency",
        {
            "a": _candidate(0.05, -0.01, 0.1),
            "b": _candidate(0.07, 0.01, 0.1),
            "c": _candidate(0.03, -0.02, 0.08),
            "d": _candidate(0.09, 0.02, 0.15),
        },
    )
    frame = ask_role_frame(report, "sufficiency")
    assert frame.set_index("model").loc["d", "vetoes"] == ("S2",)
    assert ask_halving(frame) == {"a", "b"}


def test_ask_select_needs_a_positive_lower_bound_and_breaks_ties_by_name() -> None:
    report = _ask_report(
        {"z": _guard(), "g": _guard(), "q": _guard()},
        "sufficiency",
        {
            "z": _candidate(0.08, 0.02, 0.14),
            "g": _candidate(0.08, 0.03, 0.13),
            "q": _candidate(0.12, 0.0, 0.2),
        },
    )
    assert ask_select(ask_role_frame(report, "sufficiency")) == "g"


def test_ask_select_returns_none_when_every_candidate_is_vetoed() -> None:
    report = _ask_report(
        {"m": _guard(spanish_answers=0.5)}, "answer", {"m": _candidate(0.1, 0.05, 0.2)}
    )
    assert ask_select(ask_role_frame(report, "answer")) is None


def test_ask_penalty_frame_reads_each_model_and_role() -> None:
    report = _ask_report({}, "sufficiency", {})
    frame = ask_penalty_frame(report)
    assert frame.to_dict("records") == [
        {
            "model": "base",
            "role": "sufficiency",
            "n": 32,
            "penalty": 0.01,
            "low": -0.05,
            "high": 0.07,
        }
    ]
