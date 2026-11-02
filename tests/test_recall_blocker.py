"""Tests for the Task B blocker recall estimate (``afg.annotation.recall``).

Fixtures are synthetic under ``tmp_path``; no real series and no AMI corpus are needed.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from afg.annotation.recall import (
    SeriesRecallCounts,
    estimate_recall,
    read_recall_counts,
    recall_report,
    rejected_population,
)
from afg.annotation.workspace import WorkspacePaths
from afg.evaluation.metrics import wilson_interval

NO_REL = "no_relacionada"


def _write(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


@pytest.fixture
def paths(tmp_path: Path) -> WorkspacePaths:
    return WorkspacePaths(
        decisions_dir=tmp_path / "decisions",
        relations_dir=tmp_path / "relations",
        questions_dir=tmp_path / "questions",
    )


def _make_series(
    paths: WorkspacePaths,
    series: str,
    *,
    meetings: dict[str, int],
    n_candidates: int,
    sample: list[str],
    kept: list[str],
    annotator: str = "gv",
    adjudicated: bool = True,
) -> None:
    """Write decisions (per-meeting counts), base candidates, the sample and the Task B labels."""
    _write(
        paths.decisions_dir / f"{series}.decisions.csv",
        ("decision_id", "meeting_id"),
        [
            {"decision_id": f"{m}.d{i:02d}", "meeting_id": m}
            for m, count in meetings.items()
            for i in range(1, count + 1)
        ],
    )
    _write(
        paths.relations_dir / f"{series}.candidates.csv",
        ("pair_id",),
        [{"pair_id": f"{series}.p{i:03d}"} for i in range(1, n_candidates + 1)],
    )
    _write(
        paths.relations_dir / f"{series}.recall-sample.{annotator}.csv",
        ("pair_id", "earlier_text", "relation"),
        [
            {"pair_id": f"{series}.r{i:03d}", "earlier_text": "x", "relation": rel}
            for i, rel in enumerate(sample, start=1)
        ],
    )
    if adjudicated:
        _write(
            paths.relations_dir / f"{series}.candidates.adjudicated.csv",
            ("pair_id", "final_relation"),
            [{"pair_id": f"{series}.p{i:03d}", "final_relation": r} for i, r in enumerate(kept)],
        )
    else:
        _write(
            paths.relations_dir / f"{series}.candidates.{annotator}.csv",
            ("pair_id", "relation"),
            [{"pair_id": f"{series}.p{i:03d}", "relation": r} for i, r in enumerate(kept)],
        )


def test_rejected_population_is_cross_meeting_pairs_minus_candidates(
    paths: WorkspacePaths,
) -> None:
    # meetings of 3, 2 and 1 decisions: 3*2 + 3*1 + 2*1 = 11 cross-meeting pairs.
    _make_series(
        paths, "ES9001", meetings={"a": 3, "b": 2, "c": 1}, n_candidates=4, sample=[], kept=[]
    )
    assert rejected_population("ES9001", paths=paths) == 7


def test_counts_sample_false_negatives_and_kept_relations(paths: WorkspacePaths) -> None:
    _make_series(
        paths,
        "ES9001",
        meetings={"a": 10, "b": 10},
        n_candidates=3,
        sample=[NO_REL, NO_REL, "refina", NO_REL, "reafirma"],
        kept=["refina", NO_REL, "revierte"],
    )
    counts = read_recall_counts("ES9001", "gv", paths=paths)
    assert counts == SeriesRecallCounts(
        series_id="ES9001",
        n_sampled=5,
        n_false_negative=2,
        rejected_population=97,
        kept_relations=2,
    )


def test_individually_annotated_series_use_the_annotator_labels_for_kept_relations(
    paths: WorkspacePaths,
) -> None:
    _make_series(
        paths,
        "IS9004",
        meetings={"a": 4, "b": 4},
        n_candidates=2,
        sample=[NO_REL],
        kept=["introduce", NO_REL],
        adjudicated=False,
    )
    counts = read_recall_counts("IS9004", "gv", paths=paths)
    assert counts is not None and counts.kept_relations == 1


def test_missing_sample_file_returns_none(paths: WorkspacePaths) -> None:
    assert read_recall_counts("IS9004", "gv", paths=paths) is None


def test_unlabeled_row_is_an_error(paths: WorkspacePaths) -> None:
    _make_series(
        paths,
        "ES9001",
        meetings={"a": 5, "b": 5},
        n_candidates=1,
        sample=[NO_REL, "", NO_REL, ""],
        kept=[NO_REL],
    )
    with pytest.raises(ValueError, match=r"ES9001.*2 .*sin etiqueta"):
        read_recall_counts("ES9001", "gv", paths=paths)


def test_unknown_label_is_an_error(paths: WorkspacePaths) -> None:
    _make_series(
        paths, "ES9001", meetings={"a": 5, "b": 5}, n_candidates=1, sample=["foo"], kept=[NO_REL]
    )
    with pytest.raises(ValueError, match="foo"):
        read_recall_counts("ES9001", "gv", paths=paths)


def test_sample_larger_than_population_is_an_error(paths: WorkspacePaths) -> None:
    _make_series(
        paths, "ES9001", meetings={"a": 1, "b": 2}, n_candidates=0, sample=[NO_REL] * 3, kept=[]
    )
    with pytest.raises(ValueError, match="población"):
        read_recall_counts("ES9001", "gv", paths=paths)


def _counts(series: str, n: int, fn: int, population: int, kept: int) -> SeriesRecallCounts:
    return SeriesRecallCounts(series, n, fn, population, kept)


def test_single_series_matches_the_wilson_interval_helper() -> None:
    est = estimate_recall([_counts("ES9001", 50, 3, 200, 8)])
    ref = wilson_interval(3, 50)
    assert est.false_negative_rate == pytest.approx(0.06)
    assert est.rate_lower == pytest.approx(ref.lower)
    assert est.rate_upper == pytest.approx(ref.upper)
    assert est.missed == pytest.approx(12.0)
    assert est.missed_lower == pytest.approx(ref.lower * 200)
    assert est.missed_upper == pytest.approx(ref.upper * 200)


def test_recall_formula_and_interval_propagation() -> None:
    est = estimate_recall([_counts("ES9001", 50, 3, 200, 8)])
    assert est.recall == pytest.approx(8 / (8 + 12))
    # More missed relations means lower recall, so the bounds swap.
    assert est.recall_lower == pytest.approx(8 / (8 + est.missed_upper))
    assert est.recall_upper == pytest.approx(8 / (8 + est.missed_lower))
    assert est.recall_lower < est.recall < est.recall_upper


def test_zero_false_negatives_keeps_a_non_degenerate_interval() -> None:
    est = estimate_recall([_counts("ES9001", 50, 0, 200, 8)])
    assert est.false_negative_rate == 0.0
    assert est.rate_lower == 0.0
    assert est.rate_upper > 0.0
    assert est.missed == 0.0
    assert est.recall == 1.0
    assert est.recall_upper == 1.0
    assert est.recall_lower < 1.0


def test_all_false_negatives() -> None:
    est = estimate_recall([_counts("ES9001", 50, 50, 200, 8)])
    assert est.false_negative_rate == 1.0
    assert est.rate_upper == 1.0
    assert est.rate_lower < 1.0
    assert est.missed == 200.0
    assert est.recall == pytest.approx(8 / 208)
    assert est.recall_lower > 0.0


def test_no_kept_relations_gives_zero_recall_when_something_is_missed() -> None:
    est = estimate_recall([_counts("ES9001", 50, 5, 200, 0)])
    assert est.recall == 0.0
    assert est.recall_upper == 0.0


def test_stratified_pooling_weights_by_rejected_population_not_sample_counts() -> None:
    small = _counts("ES9001", 50, 25, 100, 3)  # rate 0.5, population 100
    large = _counts("ES9002", 50, 0, 900, 5)  # rate 0.0, population 900
    est = estimate_recall([small, large])
    # Naive pooling of sample counts would give 25/100 = 0.25.
    assert est.false_negative_rate == pytest.approx(0.05)
    assert est.missed == pytest.approx(50.0)
    assert est.rejected_population == 1000
    assert est.kept_relations == 8
    assert est.recall == pytest.approx(8 / 58)
    assert est.n_sampled == 100
    assert est.n_false_negative == 25


def test_pooled_interval_uses_the_effective_sample_size() -> None:
    a = _counts("ES9001", 50, 5, 200, 4)
    b = _counts("ES9002", 50, 10, 200, 4)
    est = estimate_recall([a, b])
    # Equal weights and equal samples: effective n is the total sample (100), p = 0.15.
    ref = wilson_interval(15, 100)
    assert est.false_negative_rate == pytest.approx(0.15)
    assert est.rate_lower == pytest.approx(ref.lower)
    assert est.rate_upper == pytest.approx(ref.upper)


def test_unequal_weights_widen_the_interval() -> None:
    equal = estimate_recall([_counts("A", 50, 5, 500, 4), _counts("B", 50, 5, 500, 4)])
    skewed = estimate_recall([_counts("A", 50, 5, 900, 4), _counts("B", 50, 5, 100, 4)])
    assert (skewed.rate_upper - skewed.rate_lower) > (equal.rate_upper - equal.rate_lower)


def test_estimate_recall_requires_at_least_one_series() -> None:
    with pytest.raises(ValueError):
        estimate_recall([])


def test_report_groups_by_site_and_total_and_lists_missing_series(
    paths: WorkspacePaths,
) -> None:
    common = {"meetings": {"a": 10, "b": 10}, "n_candidates": 2}
    _make_series(
        paths, "ES9001", sample=[NO_REL] * 9 + ["refina"], kept=["refina", "introduce"], **common
    )
    _make_series(paths, "ES9002", sample=[NO_REL] * 10, kept=["refina", NO_REL], **common)
    _make_series(paths, "TS9005", sample=[NO_REL] * 10, kept=["refina", "refina"], **common)
    # IS9004 has no sample file at all.
    report = recall_report(["ES9001", "ES9002", "IS9004", "TS9005"], "gv", paths=paths)

    assert report.n_planned == 4
    assert report.n_used == 3
    assert report.missing == ("IS9004",)
    assert [e.label for e in report.series] == ["ES9001", "ES9002", "TS9005"]
    assert [e.label for e in report.sites] == ["ES", "TS"]
    es = report.sites[0]
    assert es.n_sampled == 20 and es.n_false_negative == 1
    assert es.kept_relations == 3
    assert report.total.label == "Total"
    assert report.total.n_sampled == 30
    assert report.total.kept_relations == 5
    assert report.total.rejected_population == 3 * 98


def test_report_with_no_samples_raises(paths: WorkspacePaths) -> None:
    with pytest.raises(ValueError, match="ninguna muestra"):
        recall_report(["IS9004"], "gv", paths=paths)


def test_normal_quantile_is_not_hard_coded() -> None:
    est = estimate_recall([_counts("A", 50, 5, 200, 4)], confidence_level=0.90)
    ref = wilson_interval(5, 50, 0.90)
    assert math.isclose(est.rate_lower, ref.lower)
