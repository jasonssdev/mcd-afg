"""Tests for reading the OpenKOS decision-pass model screen with the thesis scorer."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from afg.domain.decision import EvidenceSpan
from afg.evaluation.reference import ReferenceDecision
from afg.experiments.model_screen import (
    CurvePoint,
    advances,
    ceiling_pairs,
    curve_summary,
    guardrails_frame,
    language_counts,
    language_of,
    load_openkos_scores,
    load_pass_runs,
    openkos_agreement,
    paired_similarity,
    relabel_series,
    score_curve,
    selection_rule,
)


def _partition(series: str) -> str:
    return "development" if series in {"ES2015", "TS3009"} else "evaluation"


def _item(subject: str, value: str) -> dict[str, Any]:
    return {
        "title": value,
        "evidence": ["A: q"],
        "matched_ids": [],
        "subject": subject,
        "value": value,
    }


def _record(
    run: int,
    meeting: str,
    items: list[dict[str, Any]],
    *,
    failure: str | None = None,
    wall_s: float = 10.0,
) -> dict[str, Any]:
    return {
        "arm": "pass",
        "run": run,
        "meeting": meeting,
        "series": meeting[:-1],
        "failure": failure,
        "wall_s": wall_s,
        "items": items,
    }


def _write_runs(path: Path, model: str, records: list[dict[str, Any]], arm: str = "pass") -> Path:
    path.write_text(json.dumps({"arm": arm, "model": model, "records": records}), "utf-8")
    return path


def _ref(i: int, meeting: str, text: str) -> ReferenceDecision:
    obj, content = text.split(": ", 1)
    return ReferenceDecision(
        decision_id=f"{meeting}.d{i}",
        series_id=meeting[:-1],
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"da.{i}",)),
        evidence_method="sentence_id",
        role="PM",
        roles=("PM",),
    )


def _exact(predicted: list[str], reference: list[str]) -> np.ndarray:
    """Similarity 0.9 between identical texts, 0.55 otherwise."""
    return np.array([[0.9 if p == r else 0.55 for r in reference] for p in predicted])


# --- loading -----------------------------------------------------------------------------


def test_load_pass_runs_groups_records_by_model_series_and_run(tmp_path: Path) -> None:
    path = _write_runs(
        tmp_path / "runs-pass-x.json",
        "m:8b",
        [
            _record(0, "ES2015a", [_item("price", "25 euros")], wall_s=4.0),
            _record(0, "ES2015b", [_item("case", "rubber"), _item("chip", "regular")]),
            _record(1, "ES2015a", [], failure="OllamaGenerationCapped", wall_s=7.5),
            _record(1, "ES2015b", [_item("case", "rubber")], wall_s=2.5),
        ],
    )

    runs = load_pass_runs([path], partition_of=_partition)

    assert [(r.model, r.series, r.run) for r in runs] == [
        ("m:8b", "ES2015", 0),
        ("m:8b", "ES2015", 1),
    ]
    first, second = runs
    assert [(d.meeting_id, d.decision_object, d.content) for d in first.decisions] == [
        ("ES2015a", "price", "25 euros"),
        ("ES2015b", "case", "rubber"),
        ("ES2015b", "chip", "regular"),
    ]
    assert all(d.is_decision for d in first.decisions)
    assert len({d.id for d in first.decisions}) == 3
    assert first.wall_s == pytest.approx(14.0)
    assert second.wall_s == pytest.approx(10.0)
    assert first.meetings == ("ES2015a", "ES2015b")
    assert second.failures == (("ES2015a", "OllamaGenerationCapped"),)
    assert second.failed_meeting_runs == 1
    assert first.decisions_per_meeting == pytest.approx(1.5)


def test_load_pass_runs_refuses_an_evaluation_series(tmp_path: Path) -> None:
    path = _write_runs(tmp_path / "r.json", "m", [_record(0, "ES2016a", [])])
    with pytest.raises(ValueError, match="ES2016"):
        load_pass_runs([path], partition_of=_partition)


def test_load_pass_runs_refuses_another_arm(tmp_path: Path) -> None:
    path = _write_runs(tmp_path / "r.json", "m", [_record(0, "ES2015a", [])], arm="baseline")
    with pytest.raises(ValueError, match="pass"):
        load_pass_runs([path], partition_of=_partition)


def test_load_pass_runs_refuses_a_repeated_key_across_files(tmp_path: Path) -> None:
    one = _write_runs(tmp_path / "one.json", "m", [_record(0, "ES2015a", [_item("a", "b")])])
    two = _write_runs(tmp_path / "two.json", "m", [_record(0, "ES2015a", [_item("c", "d")])])
    with pytest.raises(ValueError, match=r"two\.json.*ES2015a"):
        load_pass_runs([one, two], partition_of=_partition)


def test_load_pass_runs_refuses_a_repeated_key_within_a_file(tmp_path: Path) -> None:
    path = _write_runs(
        tmp_path / "dup.json",
        "m",
        [_record(0, "ES2015a", [_item("a", "b")]), _record(0, "ES2015a", [_item("c", "d")])],
    )
    with pytest.raises(ValueError, match=r"dup\.json.*repeated"):
        load_pass_runs([path], partition_of=_partition)


def test_load_pass_runs_names_the_file_when_a_record_has_no_items(tmp_path: Path) -> None:
    record = _record(0, "ES2015a", [])
    del record["items"]
    path = _write_runs(tmp_path / "noitems.json", "m", [record])
    with pytest.raises(ValueError, match=r"noitems\.json.*items"):
        load_pass_runs([path], partition_of=_partition)


def test_load_pass_runs_names_the_file_when_an_item_has_no_subject(tmp_path: Path) -> None:
    item = _item("a", "b")
    del item["subject"]
    path = _write_runs(tmp_path / "nosubject.json", "m", [_record(0, "ES2015a", [item])])
    with pytest.raises(ValueError, match=r"nosubject\.json.*subject"):
        load_pass_runs([path], partition_of=_partition)


def test_relabel_series_refuses_an_evaluation_series(tmp_path: Path) -> None:
    path = _write_runs(tmp_path / "r.json", "m", [_record(0, "ES2015a", [_item("a", "b")])])
    (run,) = load_pass_runs([path], partition_of=_partition)
    with pytest.raises(ValueError, match="ES2016"):
        relabel_series(run, "ES2016", partition_of=_partition)


def test_selection_rule_refuses_an_evaluation_series() -> None:
    with pytest.raises(ValueError, match="ES2016"):
        selection_rule(
            [], [], candidate="c", baseline="b", series=("ES2016",), partition_of=_partition
        )


def test_relabel_series_keeps_the_meeting_letter(tmp_path: Path) -> None:
    path = _write_runs(
        tmp_path / "r.json",
        "m",
        [_record(0, "ES2015a", [_item("a", "b")]), _record(0, "ES2015c", [_item("c", "d")])],
    )
    (run,) = load_pass_runs([path], partition_of=_partition)

    moved = relabel_series(run, "TS3009")

    assert moved.series == "TS3009"
    assert [d.meeting_id for d in moved.decisions] == ["TS3009a", "TS3009c"]
    assert all(d.series_id == "TS3009" for d in moved.decisions)
    assert [d.content for d in moved.decisions] == ["b", "d"]


# --- language ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("selling price: The product will be sold for twenty-five Euros", "en"),
        ("precio de venta: el producto se venderá en 25 euros para el mercado", "es"),
        ("kinetic", "unknown"),
    ],
)
def test_language_of(text: str, expected: str) -> None:
    assert language_of(text) == expected


def test_language_counts_reads_object_and_content(tmp_path: Path) -> None:
    path = _write_runs(
        tmp_path / "r.json",
        "m",
        [
            _record(
                0,
                "ES2015a",
                [_item("price", "it will be sold for 25 euros"), _item("precio", "será de la")],
            )
        ],
    )
    assert language_counts(load_pass_runs([path], partition_of=_partition)) == {
        "en": 1,
        "es": 1,
        "unknown": 0,
    }


# --- scoring -----------------------------------------------------------------------------


def _two_runs(tmp_path: Path) -> list[Any]:
    path = _write_runs(
        tmp_path / "r.json",
        "m",
        [
            _record(0, "ES2015a", [_item("price", "25"), _item("noise", "x")]),
            _record(0, "ES2015b", [_item("case", "rubber")]),
            _record(1, "ES2015a", [_item("price", "25")]),
            _record(1, "ES2015b", [_item("other", "y")]),
        ],
    )
    return load_pass_runs([path], partition_of=_partition)


def test_score_curve_counts_same_meeting_matches_per_run_and_tau(tmp_path: Path) -> None:
    runs = _two_runs(tmp_path)
    reference = {"ES2015": [_ref(1, "ES2015a", "price: 25"), _ref(2, "ES2015a", "case: rubber")]}

    points = score_curve(runs, reference, _exact, taus=(0.5, 0.6))

    by_key = {(p.run, p.tau): p for p in points}
    # tau 0.5: every same-meeting pair is a candidate; run 0 has 2 extracted in ES2015a.
    assert by_key[(0, 0.5)].tp == 2
    # tau 0.6: only identical texts; "case: rubber" was extracted in ES2015b, another meeting.
    assert by_key[(0, 0.6)].tp == 1
    assert by_key[(0, 0.6)].n_predicted == 3
    assert by_key[(0, 0.6)].n_reference == 2
    assert by_key[(0, 0.6)].recall == pytest.approx(0.5)
    assert by_key[(0, 0.6)].precision == pytest.approx(1 / 3)
    assert by_key[(1, 0.6)].tp == 1
    assert by_key[(1, 0.6)].f1 == pytest.approx(2 * 0.5 * 0.5 / 1.0)


def test_curve_summary_reports_mean_min_max_and_tp_per_run() -> None:
    points = [
        CurvePoint("m", "S", 0, 0.6, 1, 4, 2, 0.25, 0.5, 1 / 3),
        CurvePoint("m", "S", 1, 0.6, 2, 4, 2, 0.5, 1.0, 2 / 3),
    ]

    row = curve_summary(points).iloc[0]

    assert row["recall_mean"] == pytest.approx(0.75)
    assert row["recall_min"] == pytest.approx(0.5)
    assert row["f1_max"] == pytest.approx(2 / 3)
    assert row["tp"] == [1, 2]
    assert row["runs"] == 2


def test_paired_similarity_reads_the_diagonal() -> None:
    assert paired_similarity(_exact, ["a", "b"], ["a", "c"]) == pytest.approx([0.9, 0.55])


# --- selection rule ----------------------------------------------------------------------


def _points(model: str, series: str, f1s: list[float], recalls: list[float]) -> list[CurvePoint]:
    return [
        CurvePoint(model, series, k, 0.6, 0, 0, 0, 0.0, r, f)
        for k, (f, r) in enumerate(zip(f1s, recalls, strict=True))
    ]


def _guard_runs(
    tmp_path: Path, model: str, series: str, decisions: int, failed: int, n: int
) -> list[Any]:
    records = []
    for k in range(n):
        for letter in "ab":
            fail = "x" if (k * 2 + (letter == "b")) < failed else None
            records.append(
                _record(k, f"{series}{letter}", [_item("o", "c")] * decisions, failure=fail)
            )
    path = _write_runs(tmp_path / f"{model}-{series}.json", model, records)
    return load_pass_runs([path], partition_of=_partition)


def test_selection_rule_applies_the_four_preregistered_conditions(tmp_path: Path) -> None:
    points = (
        _points("base", "ES2015", [0.30, 0.32], [0.5, 0.5])
        + _points("cand", "ES2015", [0.50, 0.54], [0.6, 0.6])
        + _points("base", "TS3009", [0.30, 0.40], [0.6, 0.6])
        + _points("cand", "TS3009", [0.40, 0.42], [0.7, 0.7])
    )
    runs = (
        _guard_runs(tmp_path, "base", "ES2015", 10, 0, 2)
        + _guard_runs(tmp_path, "cand", "ES2015", 11, 2, 2)
        + _guard_runs(tmp_path, "base", "TS3009", 10, 0, 2)
        + _guard_runs(tmp_path, "cand", "TS3009", 12, 0, 2)
    )

    es, ts = selection_rule(points, runs, candidate="cand", baseline="base")

    assert es.series == "ES2015"
    assert es.d_f1 == pytest.approx(0.21)
    assert es.margin_needed == pytest.approx(0.05)
    assert es.margin_ok and es.recall_ok
    assert es.failures_ok  # 2 <= max(2, 0)
    assert es.volume_ok  # 11 <= 1.10 x 10
    assert es.passed
    # TS3009: dF1 0.06 against the baseline's own spread of 0.10; volume 12 > 11.
    assert ts.d_f1 == pytest.approx(0.06)
    assert ts.spread == pytest.approx(0.10)
    assert not ts.margin_ok
    assert not ts.volume_ok
    assert not ts.passed
    assert not advances([es, ts])
    assert advances([es])


def test_guardrails_frame_summarizes_each_model_and_series(tmp_path: Path) -> None:
    runs = _guard_runs(tmp_path, "m", "ES2015", 3, 1, 2)

    row = guardrails_frame(runs).iloc[0]

    assert row["runs"] == 2
    assert row["failed_meeting_runs"] == 1
    assert row["meeting_runs"] == 4
    assert row["decisions_per_meeting"] == pytest.approx(3.0)
    assert row["seconds_per_run"] == pytest.approx(20.0)


# --- openkos side ------------------------------------------------------------------------


def test_openkos_agreement_compares_true_positives_per_run(tmp_path: Path) -> None:
    scored = tmp_path / "scored.json"
    scored.write_text(
        json.dumps(
            {
                "m|ES2015": {
                    "model": "m",
                    "series": "ES2015",
                    "harness_recall": [0.3, 0.4],
                    "curve": [{"tau": 0.6, "tp": [1, 3]}],
                }
            }
        ),
        "utf-8",
    )
    points = [
        CurvePoint("m", "ES2015", 0, 0.6, 1, 4, 2, 0.25, 0.5, 0.3),
        CurvePoint("m", "ES2015", 1, 0.6, 2, 4, 2, 0.5, 1.0, 0.6),
    ]

    entries = load_openkos_scores(scored)
    table = openkos_agreement(points, entries)

    assert entries[("m", "ES2015")]["harness_recall"] == [0.3, 0.4]
    row = table.iloc[0]
    assert row["tp_thesis"] == [1, 2]
    assert row["tp_openkos"] == [1, 3]
    assert not row["equal"]
    assert row["tp_difference"] == -1


def test_ceiling_pairs_reads_decision_rows_with_a_sentence(tmp_path: Path) -> None:
    path = tmp_path / "ES2015.decisions.adjudicated.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "decision_id",
                "final_status",
                "sentence_text",
                "final_object",
                "final_content",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "decision_id": "a",
                "final_status": "decision",
                "sentence_text": "They chose rubber.",
                "final_object": "carcasa",
                "final_content": "de goma",
            }
        )
        writer.writerow(
            {
                "decision_id": "b",
                "final_status": "no_decision",
                "sentence_text": "x",
                "final_object": "o",
                "final_content": "c",
            }
        )
        writer.writerow(
            {
                "decision_id": "c",
                "final_status": "decision",
                "sentence_text": "",
                "final_object": "o",
                "final_content": "c",
            }
        )

    assert ceiling_pairs(path) == [("They chose rubber.", "carcasa: de goma")]


def test_ceiling_pairs_uses_the_shared_reader_and_refuses_a_non_utf8_file(tmp_path: Path) -> None:
    from afg.shared.csvio import CsvFormatError

    path = tmp_path / "latin1.csv"
    path.write_bytes("final_status,sentence_text\ndecision,canci\xf3n\n".encode("latin-1"))
    with pytest.raises(CsvFormatError, match=r"latin1\.csv"):
        ceiling_pairs(path)


def test_rule_check_volume_cap_is_the_preregistered_factor_of_the_baseline() -> None:
    from afg.experiments.model_screen import RuleCheck

    check = RuleCheck(
        "c", "b", "ES2015", 0.6, 0.5, 0.3, 0.2, 0.0, 0.05, True, 0.6, 0.5, True, 0, 0, True, 11.0,
        10.0, True,
    )  # fmt: skip
    assert check.volume_cap == pytest.approx(11.0)


def test_verdict_frame_orders_candidates_by_mean_df1(tmp_path: Path) -> None:
    from afg.experiments.model_screen import verdict_frame

    points = (
        _points("base", "ES2015", [0.30, 0.32], [0.5, 0.5])
        + _points("cand", "ES2015", [0.50, 0.54], [0.6, 0.6])
        + _points("weak", "ES2015", [0.31, 0.33], [0.4, 0.4])
        + _points("base", "TS3009", [0.30, 0.40], [0.6, 0.6])
        + _points("cand", "TS3009", [0.60, 0.62], [0.7, 0.7])
        + _points("weak", "TS3009", [0.31, 0.41], [0.5, 0.5])
    )
    runs = [
        r
        for m in ("base", "cand", "weak")
        for s in ("ES2015", "TS3009")
        for r in _guard_runs(tmp_path, m, s, 10, 0, 2)
    ]
    checks = {
        m: selection_rule(points, runs, candidate=m, baseline="base", partition_of=_partition)
        for m in ("cand", "weak")
    }

    frame = verdict_frame(checks)

    assert list(frame["candidate"]) == ["cand", "weak"]
    assert list(frame["advances"]) == [True, False]
    assert frame.loc[0, "d_f1_mean"] == pytest.approx((0.21 + 0.26) / 2)


def test_ceiling_summary_counts_and_quantiles_per_series() -> None:
    from afg.experiments.model_screen import ceiling_summary

    table = ceiling_summary({"A": [0.5, 0.7, 0.9], "B": [0.62]}, thresholds=(0.60, 0.80))

    a = table.loc["A"]
    assert (a["n"], a["median"], a["min"], a["max"]) == (3, 0.7, 0.5, 0.9)
    assert (a["count_ge_0.60"], a["count_ge_0.80"]) == (2, 1)
    assert table.loc["B", "count_ge_0.60"] == 1


def test_mean_min_max() -> None:
    from afg.experiments.model_screen import mean_min_max

    assert mean_min_max([0.2, 0.4, 0.3]) == pytest.approx((0.3, 0.2, 0.4))
    with pytest.raises(ValueError, match="empty"):
        mean_min_max([])


def test_reproduction_frame_pools_runs_next_to_the_openkos_copy() -> None:
    from afg.evaluation.scoring import IntervalSettings
    from afg.experiments.model_screen import reproduction_frame

    reference = [_ref(1, "ES2015a", "price: 25"), _ref(2, "ES2015a", "case: rubber")]
    runs = [
        [_decision("ES2015a", "price", "25")],
        [_decision("ES2015a", "price", "25"), _decision("ES2015a", "case", "rubber")],
    ]
    theirs = {0.6: {"tp": 3, "recall": 0.75}}

    frame = reproduction_frame(
        reference,
        runs,
        _exact,
        taus=(0.6,),
        openkos_pooled=theirs,
        settings=IntervalSettings(n_resamples=50, confidence_level=0.95, seed=1),
        partition_of=_partition,
    )

    row = frame.iloc[0]
    assert row["tp_per_run"] == [1, 2]
    assert (row["tp_pooled"], row["tp_pooled_openkos"]) == (3, 3)
    assert (row["n_extracted"], row["n_reference"]) == (3, 4)
    assert row["recall"] == pytest.approx(0.75)
    assert row["recall_openkos"] == pytest.approx(0.75)


def _decision(meeting: str, obj: str, content: str) -> Any:
    from afg.domain.decision import Decision, DecisionStatus

    return Decision(
        id=f"{meeting}/{obj}",
        series_id=meeting[:-1],
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"{meeting}#0",)),
    )


def test_curve_frame_has_one_row_per_point() -> None:
    from afg.experiments.model_screen import curve_frame

    frame = curve_frame([CurvePoint("m", "S", 0, 0.6, 1, 4, 2, 0.25, 0.5, 1 / 3)])

    assert frame.loc[0, "tp"] == 1
    assert list(frame.columns)[:4] == ["model", "series", "run", "tau"]
