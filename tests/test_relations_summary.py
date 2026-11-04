"""Tests for the notebook-facing summary of a relation report (``relaciones.json``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from afg.experiments.relations_summary import (
    accuracy_frame,
    existence_frame,
    format_proportion,
    load_relation_report,
    run_frame,
)


def _prop(successes: int, trials: int) -> dict[str, Any]:
    if trials == 0:
        return {"successes": 0, "trials": 0, "rate": None, "lower": None, "upper": None}
    return {
        "successes": successes,
        "trials": trials,
        "rate": successes / trials,
        "lower": 0.1,
        "upper": 0.9,
    }


def _views(s: int, t: int) -> dict[str, Any]:
    return {"end_to_end": _prop(s, t), "conditional": _prop(s, 1), "among_detected": _prop(s, 1)}


def _existence(tp: int, fp: int, fn: int, **breakdown: int) -> dict[str, Any]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": _prop(tp, tp + fp),
        "recall": _prop(tp, tp + fn),
        "f1": 0.5,
        "fp_breakdown": {"gold_no_link": 0, "not_candidate": 0, "unaligned": 0, **breakdown},
    }


def _score() -> dict[str, Any]:
    return {
        "n_gold_pairs": 4,
        "n_gold_links": 3,
        "n_gold_links_aligned": 1,
        "n_machine_relations": 10,
        "n_machine_links": 6,
        "n_machine_links_aligned": 2,
        "existence_end_to_end": _existence(1, 5, 2, unaligned=4, not_candidate=1),
        "existence_conditional": _existence(1, 1, 0, not_candidate=1),
        "type_principal": _views(1, 3),
        "type_strict": _views(1, 3),
        "direction_principal": _views(1, 3),
        "direction_unknown_excluded": _views(1, 3),
        "unknown_direction": _prop(0, 1),
    }


def _report() -> dict[str, Any]:
    return {
        "run_name": "x",
        "partition": "development",
        "tau": 0.7,
        "entries": [
            {
                "series": "ES2015",
                "run": 0,
                "alignment": {"machine_decisions": 20, "gold_decisions": 10, "aligned": 4},
                "findings": {
                    "n_relations": 10,
                    "by_verdict": {"refines": 4, "reverses": 2, "unrelated": 4},
                },
                "score": _score(),
            },
            {"series": "ES2015", "run": 1, "error": "no findings"},
        ],
        "pooled": _score(),
    }


def test_format_proportion() -> None:
    assert format_proportion(_prop(1, 4)) == "1/4 (25,0 %) [10,0; 90,0]"
    assert format_proportion(_prop(0, 0)) == "sin casos"


def test_load_rejects_non_development(tmp_path: Path) -> None:
    path = tmp_path / "relaciones.json"
    report = _report() | {"partition": "evaluation"}
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="development"):
        load_relation_report(path)


def test_load_reads_report(tmp_path: Path) -> None:
    path = tmp_path / "relaciones.json"
    path.write_text(json.dumps(_report()))
    assert load_relation_report(path)["run_name"] == "x"


def test_run_frame_counts_links_by_verdict_and_skips_errors() -> None:
    frame = run_frame(_report())
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["Decisiones alineadas"] == 4
    assert row["Decisiones de oro"] == 10
    assert row["Enlaces de oro alineados"] == 1
    assert row["Enlaces de la máquina"] == 6
    assert row["refina"] == 4
    assert row["revierte o reemplaza"] == 2
    assert row["Enlaces con ambas decisiones alineadas"] == 2


def test_existence_frame_has_both_scopes_and_pooled_row() -> None:
    frame = existence_frame(_report())
    assert list(frame["Ámbito"].unique()) == ["extremo a extremo", "condicionada"]
    assert list(frame["Corrida"].unique()) == ["run-0", "conjunto"]
    row = frame[(frame["Ámbito"] == "extremo a extremo") & (frame["Corrida"] == "run-0")].iloc[0]
    assert (row["TP"], row["FP"], row["FN"]) == (1, 5, 2)
    assert row["FP sin par candidato"] == 1


def test_existence_frame_precision_excluding_not_candidate_false_positives() -> None:
    frame = existence_frame(_report())
    row = frame[(frame["Ámbito"] == "extremo a extremo") & (frame["Corrida"] == "run-0")].iloc[0]
    # tp = 1, fp = 5 of which 1 has no candidate pair: 1 / (1 + 5 - 1) = 1/5.
    assert row["Precisión sin FP fuera de candidatos"] == "1/5 (20,0 %) [3,6; 62,4]"
    assert row["Precisión"] == "1/6 (16,7 %) [10,0; 90,0]"


def test_precision_excluding_not_candidate_is_undefined_without_remaining_trials() -> None:
    score = _score()
    score["existence_end_to_end"] = _existence(0, 2, 1, not_candidate=2)
    report = _report() | {"pooled": score}
    frame = existence_frame(report)
    row = frame[(frame["Ámbito"] == "extremo a extremo") & (frame["Corrida"] == "conjunto")].iloc[0]
    assert row["Precisión sin FP fuera de candidatos"] == "sin casos"


def test_accuracy_frame_rows_cover_four_views() -> None:
    frame = accuracy_frame(_report()["pooled"])
    assert list(frame.index) == [
        "Tipo (principal)",
        "Tipo (estricta)",
        "Dirección (principal)",
        "Dirección (desconocida excluida)",
    ]
    assert list(frame.columns) == ["Extremo a extremo", "Condicionada", "Entre detectados"]
    assert frame.loc["Tipo (principal)", "Extremo a extremo"] == "1/3 (33,3 %) [10,0; 90,0]"
