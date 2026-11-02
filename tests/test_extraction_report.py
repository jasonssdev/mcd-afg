"""Tests for the Experiment A report of a stored extraction run (``extraction_report``)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from afg.evaluation.scoring import (
    DevelopmentResultError,
    IntervalSettings,
    pool_scores,
    score_series,
)
from afg.experiments.extraction_report import build_extraction_report
from afg.experiments.extraction_runs import ExtractionRun
from tests.relations_workspace import ALPHA, BETA, reference_decision, text_similarity

SETTINGS = IntervalSettings(n_resamples=200, confidence_level=0.95, seed=42)
GAMMA = ("remote colour", "The remote is yellow.")
GRID = [0.50, 0.70, 0.75, 0.80]


def _decision(meeting: str, text: tuple[str, str], index: int) -> dict[str, Any]:
    return {
        "id": f"decisions/{meeting}-{index}",
        "series_id": meeting[:-1],
        "meeting_id": meeting,
        "decision_object": text[0],
        "content": text[1],
        "status": "accepted",
        "evidence": {"meeting_id": meeting, "dialogue_act_ids": [f"{meeting}.a1"]},
        "annotator": None,
        "origin_meeting_ids": [],
    }


def _run(series: str, number: int, found: list[tuple[str, tuple[str, str]]]) -> ExtractionRun:
    decisions = [_decision(f"{series}{m}", text, i) for i, (m, text) in enumerate(found)]
    record = {"series_id": series, "run": number, "decisions": decisions}
    return ExtractionRun("lote", number, 42 + number, record, {"git_commit": "abc"})


def _references(series: str = "ES2015") -> dict[str, Any]:
    alpha = dataclasses.replace(
        reference_decision(f"{series}a.d01", f"{series}a", *ALPHA), role="ID"
    )
    beta = dataclasses.replace(reference_decision(f"{series}b.d01", f"{series}b", *BETA), role="PM")
    return {series: (alpha, beta)}


RUNS = [
    _run("ES2015", 0, [("a", ALPHA), ("b", BETA), ("c", GAMMA)]),
    _run("ES2015", 1, [("a", ALPHA)]),
    _run("ES2015", 2, [("a", ALPHA), ("b", BETA)]),
]


def _build(runs: list[ExtractionRun] = RUNS, **overrides: Any) -> dict[str, Any]:
    refs = overrides.pop("references", _references())
    options: dict[str, Any] = {
        "run_name": "lote",
        "runs": runs,
        "reference_of": lambda series: refs[series],
        "similarity": text_similarity,
        "settings": SETTINGS,
        "tau_grid": GRID,
        "tau_principal": 0.70,
        "tau_sensitivity": (0.75, 0.80),
        "partition_of": lambda series: "development",
        "descriptive": True,
    }
    options.update(overrides)
    return build_extraction_report(**options)


def _entry(report: dict[str, Any], tau: float) -> dict[str, Any]:
    return next(e for e in report["curve"] if e["tau"] == tau)


def test_pooled_principal_matches_the_scoring_functions() -> None:
    report = _build()

    scores = [
        score_series("ES2015", _references()["ES2015"], _decisions(run), text_similarity, tau=0.70)
        for run in RUNS
    ]
    expected = pool_scores(scores, settings=SETTINGS, partition_of=lambda s: "development")
    pooled = _entry(report, 0.70)["origin_meetings"]["pooled"]
    assert (pooled["tp"], pooled["fp"], pooled["fn"]) == (5, 1, 1)
    assert pooled["precision"] == pytest.approx(expected.precision)
    assert pooled["f1"] == pytest.approx(expected.f1)
    assert pooled["intervals"]["f1"] == list(expected.f1_interval)
    assert pooled["reference_intervals"]["recall"] == list(expected.recall_interval_reference)
    assert pooled["n_clusters"] == expected.n_clusters
    assert pooled["interval_methods"]["f1"] == "meeting-cluster bootstrap"


def _decisions(run: ExtractionRun) -> list[Any]:
    from afg.domain.decision import Decision

    return [Decision(**d) for d in run.decisions]


def test_curve_covers_the_grid_and_flags_principal_and_sensitivities() -> None:
    report = _build()

    assert [e["tau"] for e in report["curve"]] == GRID
    assert [e["role"] for e in report["curve"]] == [None, "principal", "sensitivity", "sensitivity"]
    assert report["tau_principal"] == 0.70
    assert report["tau_sensitivity"] == [0.75, 0.80]
    assert report["tau_grid"] == GRID
    assert report["alignment_scope_principal"] == "origin_meetings"


def test_series_wide_sensitivity_sits_beside_the_primary_scope() -> None:
    entry = _entry(_build(), 0.70)

    assert set(entry) >= {"origin_meetings", "series"}
    assert entry["series"]["pooled"]["tp"] == 5


def test_null_coverage_floor_is_reported_for_adr_0012_taus() -> None:
    report = _build()

    assert _entry(report, 0.70)["null_coverage"] == 0.138
    assert _entry(report, 0.75)["null_coverage"] == 0.053
    assert _entry(report, 0.80)["null_coverage"] == 0.015
    assert _entry(report, 0.50)["null_coverage"] is None


def test_per_run_scores_and_dispersion_across_runs() -> None:
    cell = _entry(_build(), 0.70)["origin_meetings"]

    assert [r["run"] for r in cell["per_run"]] == [0, 1, 2]
    assert cell["per_run"][1]["tp"] == 1
    assert cell["across_runs"]["n_runs"] == 3
    assert cell["across_runs"]["recall_mean"] == pytest.approx((1.0 + 0.5 + 1.0) / 3)
    assert cell["across_runs"]["recall_stdev"] is not None


def test_single_run_has_no_dispersion_and_a_warning() -> None:
    report = _build([RUNS[0]])

    assert _entry(report, 0.70)["origin_meetings"]["across_runs"]["f1_stdev"] is None
    assert any("3 corridas" in w for w in report["warnings"])


def test_breakdown_by_series_for_each_series_of_the_run() -> None:
    refs = {**_references("ES2015"), **_references("TS3009")}
    runs = [*RUNS, _run("TS3009", 0, [("a", ALPHA)])]

    report = _build(runs, references=refs)

    cell = _entry(report, 0.70)["origin_meetings"]
    assert sorted(cell["by_series"]) == ["ES2015", "TS3009"]
    assert cell["by_series"]["TS3009"]["tp"] == 1
    assert cell["by_series"]["ES2015"]["tp"] == 5
    assert report["series"] == ["ES2015", "TS3009"]
    assert report["runs_per_series"] == {"ES2015": 3, "TS3009": 1}


def test_breakdown_by_role_counts_the_reference_side_in_both_views() -> None:
    pooled = _entry(_build(), 0.70)["origin_meetings"]["pooled"]

    assert pooled["by_role"]["ID"] == {
        "n_reference": 3, "n_covered": 3, "recall": 1.0,
        "n_predicted": 0, "n_correct": 0, "precision": None,
    }  # fmt: skip
    assert pooled["by_role"]["PM"]["n_covered"] == 2
    assert pooled["by_role_every_role"]["PM"]["n_reference"] == 3


def test_development_series_are_refused_unless_descriptive() -> None:
    with pytest.raises(DevelopmentResultError):
        _build(descriptive=False)


def test_descriptive_report_is_flagged_not_reportable() -> None:
    report = _build()

    assert report["partition"] == "development"
    assert report["descriptive"] is True
    assert report["reportable"] is False


def test_evaluation_series_give_a_reportable_report_without_the_flag() -> None:
    report = _build(partition_of=lambda series: "evaluation", descriptive=False)

    assert report["reportable"] is True
    assert report["partition"] == "evaluation"


def test_tau_principal_must_belong_to_the_grid() -> None:
    with pytest.raises(ValueError, match="grid"):
        _build(tau_grid=[0.5, 0.6])


def test_relations_result_is_embedded_when_given_and_marked_missing_otherwise() -> None:
    relations = {"run_name": "lote", "tau": 0.70, "n_errors": 0, "pooled": {"n_gold_links": 4}}

    with_relations = _build(relations=relations)
    without = _build()

    assert with_relations["relations"]["pooled"] == {"n_gold_links": 4}
    assert with_relations["relations"]["source"] == "relaciones.json"
    assert without["relations"] is None


def test_reference_kinds_and_provenance_are_recorded(tmp_path: Path) -> None:
    report = _build(reference_kinds={"ES2015": "adjudicated"})

    assert report["reference_kinds"] == {"ES2015": "adjudicated"}
    assert report["language"] == "en"
    assert report["interval"]["resamples"] == 200
    assert report["interval"]["confidence_level"] == 0.95
    assert report["provenance"]["git_commit"] == "abc"


def test_hypotheses_use_the_principal_decision_figures_and_the_run_model() -> None:
    runs = [
        ExtractionRun(
            r.run_name,
            r.run,
            r.seed,
            r.record,
            {**r.manifest, "openkos": {"generative_model": "qwen3:8b"}},
        )
        for r in RUNS
    ]
    report = _build(runs=runs, relations={"tau": 0.70, "pooled": {"n_gold_links": 4}})

    principal = _entry(report, 0.70)["origin_meetings"]["pooled"]
    h2 = report["hypotheses"]["extraction_gap_relations_vs_decisions"]
    assert h2["tau"] == 0.70
    assert h2["decisions"]["gap"] == pytest.approx(1 - principal["recall"])
    assert h2["verdict"] == "not_computable"
    assert report["hypotheses"]["h3"]["scale"]["measured_models"] == ["qwen3:8b"]


def test_hypotheses_are_absent_without_relations() -> None:
    assert _build()["hypotheses"] is None
