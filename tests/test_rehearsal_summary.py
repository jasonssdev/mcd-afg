"""Tests for the notebook-facing summary of the full-chain rehearsal (#255)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from afg.experiments.rehearsal_summary import (
    correctness_frame,
    load_development_json,
    load_rehearsal_table,
    steps_frame,
    verdict_frame,
)

MARK = "desarrollo — no reportable"


def test_steps_cover_the_whole_chain_in_order() -> None:
    frame = steps_frame()
    assert list(frame.columns) == ["Paso", "Comando", "Duración", "Resultado"]
    assert frame["Comando"].iloc[0].startswith("afg experiment a ")
    assert frame["Comando"].iloc[-1].startswith("afg experiment final-tables")
    assert len(frame) >= 9


def test_json_of_another_partition_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"partition": "evaluation"}), encoding="utf-8")
    with pytest.raises(ValueError, match="development"):
        load_development_json(path)


def test_table_without_the_development_mark_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "t.csv"
    pd.DataFrame({"a": [1], "status": ["reportable"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="desarrollo"):
        load_rehearsal_table(path)


def test_correctness_frame_pivots_condition_by_stratum() -> None:
    cells = pd.DataFrame(
        {
            "condition": ["C0", "C0", "C1"],
            "stratum": ["E1", "ALL", "E1"],
            "questions": [14, 21, 14],
            "correct": [0.14, 0.19, 0.79],
            "status": [MARK] * 3,
        }
    )
    frame = correctness_frame(cells)
    assert frame.loc["C0", "E1"] == "0,14 (14)"
    assert frame.loc["C1", "E1"] == "0,79 (14)"
    assert "ALL" in frame.columns


def test_verdict_frame_lists_primary_h2_and_h4_with_their_sample() -> None:
    analysis: dict[str, Any] = {
        "partition": "development",
        "comparisons": [
            {
                "primary": True,
                "descriptive": False,
                "condition_a": "C2",
                "condition_b": "C1",
                "stratum": "E3",
                "metric": "correct",
                "n_pairs": 1,
                "difference": 1.0,
                "difference_lower": 1.0,
                "difference_upper": 1.0,
                "criterion": "insufficient_sample",
            },
            {
                "primary": False,
                "descriptive": True,
                "condition_a": "C1",
                "condition_b": "C0",
                "stratum": "E3",
                "metric": "correct",
                "n_pairs": 1,
                "difference": 0.0,
                "difference_lower": 0.0,
                "difference_upper": 0.0,
                "criterion": "inconclusive",
            },
        ],
        "h2": {
            "verdict": "insufficient_sample",
            "difference": -1.2,
            "difference_lower": -1.5,
            "difference_upper": -0.9,
            "n_e1": 14,
            "n_e3": 1,
        },
    }
    frame = verdict_frame(analysis)
    assert list(frame["Hipótesis"]) == ["D16 (C2 - C1, E3)", "H2 (brecha E3 - E1)"]
    assert set(frame["Veredicto"]) == {"muestra insuficiente"}
