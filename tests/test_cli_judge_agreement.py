"""Tests for ``afg judge calibration-second-sheet`` and ``calibration-agreement``."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.judge_calibration_agreement import SECOND_SHEET_COLUMNS, read_label_rows


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["judge", *args])


def _out(result: Any) -> str:
    return " ".join(result.output.split())


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    calibration = tmp_path / "calibracion-juez.csv"
    second = tmp_path / "segunda.csv"
    agreement = tmp_path / "out" / "acuerdo-humano.json"
    rows = []
    for n in range(20):
        rows.append(
            {
                "id": f"ES2015.q{n:03d}.grounded",
                "series_id": "ES2015",
                "stratum": "E1_point_fact",
                "question": "q",
                "reference_answer": "r",
                "answer_text": "a",
                "pasaje_transcripcion": "p",
                "archivos_transcripcion": "f",
                "correct": "si" if n % 2 else "no",
                "evidence_supported": "si" if n % 3 else "no",
            }
        )
    _write(calibration, rows)
    monkeypatch.setattr(afg_cli, "CALIBRATION_PATH", calibration)
    monkeypatch.setattr(afg_cli, "SECOND_SHEET_PATH", second)
    monkeypatch.setattr(afg_cli, "AGREEMENT_PATH", agreement)
    return {"calibration": calibration, "second": second, "agreement": agreement}


def test_second_sheet_is_created_blank(paths: dict[str, Path]) -> None:
    result = _invoke("calibration-second-sheet", "--n", "5")
    assert result.exit_code == 0, result.output
    rows = read_label_rows(paths["second"])
    assert len(rows) == 5
    assert tuple(rows[0]) == SECOND_SHEET_COLUMNS
    assert all(r["correct"] == "" and r["evidence_supported"] == "" for r in rows)


def test_second_sheet_refuses_to_overwrite_labels(paths: dict[str, Path]) -> None:
    _invoke("calibration-second-sheet", "--n", "5")
    rows = read_label_rows(paths["second"])
    rows[0]["correct"] = "si"
    _write(paths["second"], rows)
    result = _invoke("calibration-second-sheet", "--n", "5")
    assert result.exit_code == 1
    assert "etiquetas" in _out(result)
    assert read_label_rows(paths["second"])[0]["correct"] == "si"


def test_agreement_prints_table_and_saves_json(paths: dict[str, Path]) -> None:
    _invoke("calibration-second-sheet", "--n", "6")
    primary = {r["id"]: r for r in read_label_rows(paths["calibration"])}
    rows = read_label_rows(paths["second"])
    for row in rows:
        row["correct"] = primary[row["id"]]["correct"]
        row["evidence_supported"] = primary[row["id"]]["evidence_supported"]
    _write(paths["second"], rows)
    result = _invoke("calibration-agreement")
    assert result.exit_code == 0, result.output
    text = _out(result)
    assert "correct" in text and "evidence_supported" in text
    payload = json.loads(paths["agreement"].read_text(encoding="utf-8"))
    assert payload["min_kappa"] == 0.70
    assert [c["n_agree"] for c in payload["columns"]] == [6, 6]


def test_agreement_requires_labels(paths: dict[str, Path]) -> None:
    _invoke("calibration-second-sheet", "--n", "4")
    result = _invoke("calibration-agreement")
    assert result.exit_code == 1
    assert "correct" in _out(result)
    assert not paths["agreement"].exists()


def test_agreement_without_second_sheet(paths: dict[str, Path]) -> None:
    result = _invoke("calibration-agreement")
    assert result.exit_code == 1
    assert "calibration-second-sheet" in _out(result)
