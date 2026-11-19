"""Tests for ``afg.experiments.video_results`` (values behind the video result figures)."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from afg.experiments.video_results import (
    CONDITION_LABELS,
    answer_latency,
    correctness_by_type,
    failure_causes,
    headline_point,
    phase2_kappas,
    total_correctness,
)


def _cells() -> pd.DataFrame:
    rows = []
    for condition, values in {
        "C0": [0.1, 0.0, 0.0, 0.4, 0.16],
        "C1": [0.72, 0.64, 0.54, 0.96, 0.72],
        "C2": [0.43, 0.35, 0.17, 1.0, 0.49],
    }.items():
        for stratum, value in zip(["E1", "E2", "E3", "E4", "ALL"], values, strict=True):
            rows.append({"run": "r1", "condition": condition, "stratum": stratum, "correct": value})
    # A second run of the same cell must not count twice.
    rows.append({"run": "r2", "condition": "C1", "stratum": "ALL", "correct": 0.01})
    return pd.DataFrame(rows)


def test_labels_name_the_conditions_in_words() -> None:
    assert CONDITION_LABELS["C0"] == "Sin ayuda (C0)"
    assert CONDITION_LABELS["C3"] == "Base con decisiones humanas (C3)"


def test_total_correctness_reads_the_all_stratum_of_the_first_run() -> None:
    assert total_correctness(_cells()) == {"C0": 0.16, "C1": 0.72, "C2": 0.49}


def test_correctness_by_type_excludes_abstention_stratum() -> None:
    result = correctness_by_type(_cells(), conditions=("C1", "C2"))
    assert result == {"C1": [0.72, 0.64, 0.54], "C2": [0.43, 0.35, 0.17]}


def test_headline_point_selects_tau_and_scope() -> None:
    table = pd.DataFrame(
        {
            "tau": [0.7, 0.7, 0.75],
            "scope": ["origin_meetings", "series", "origin_meetings"],
            "precision": [0.1, 0.2, 0.3],
            "recall": [0.4, 0.5, 0.6],
            "f1": [0.5, 0.6, 0.7],
        }
    )
    assert headline_point(table, tau=0.7) == {"precision": 0.1, "recall": 0.4, "f1": 0.5}


def test_failure_causes_use_all_failures_of_the_structured_condition() -> None:
    table = pd.DataFrame(
        {
            "condition": ["C2"] * 6,
            "stage": ["extraccion", "recuperacion", "sintesis"] * 2,
            "cases": [21, 11, 11, 21, 11, 8],
            "n_failures": [43, 43, 43, 40, 40, 40],
            "basis": ["todas"] * 3 + ["etiquetadas"] * 3,
        }
    )
    causes, total = failure_causes(table)
    assert causes == {"extraccion": 21, "recuperacion": 11, "sintesis": 11}
    assert total == 43


def test_answer_latency_is_the_mean_per_condition_of_the_answer_role() -> None:
    table = pd.DataFrame(
        {
            "role": ["answer", "answer", "judge"],
            "activity": ["experimento-b-formal / C1", "experimento-b-formal / C2", "x"],
            "mean_seconds": [5.7, 15.3, 6.3],
        }
    )
    assert answer_latency(table) == {"C1": 5.7, "C2": 15.3}


def test_phase2_kappas_picks_the_phase_two_group() -> None:
    def group(scope: str, existence: float, kind: float) -> SimpleNamespace:
        axes = [
            SimpleNamespace(axis="existence", kappa=existence),
            SimpleNamespace(axis="type", kappa=kind),
        ]
        return SimpleNamespace(scope=scope, axes=axes)

    report = [group("phase 1 + 2", 0.1, 0.2), group("phase 2", 0.783, 0.554)]
    assert phase2_kappas(report) == {"existence": 0.783, "type": 0.554}
    with pytest.raises(ValueError, match="phase 2"):
        phase2_kappas([group("other", 0.1, 0.2)])
