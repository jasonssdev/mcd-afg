"""Tests for ``afg experiment b-oe4-sheet``: the question file must be the one of the run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli


@pytest.fixture
def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from afg.experiments.provenance import file_sha256

    questions = tmp_path / "q.csv"
    questions.write_text("id\nES2015.q001\n", encoding="utf-8")
    run_dir = tmp_path / "out" / "c2"
    run_dir.mkdir(parents=True)
    record = {"question_id": "ES2015.q001", "condition": "C2", "run": 0, "stratum": "E1_point"}
    (run_dir / "respuestas.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    manifest = {"conditions": ["C2"], "c2_extraction": "lote", "series": ["ES2015"]}
    manifest["questions_sha256"] = file_sha256(questions)
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path / "out")
    return {"questions": questions, "run_dir": run_dir, "manifest": manifest}


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", "b-oe4-sheet", *args])


def test_questions_option_is_required(run: dict[str, Any]) -> None:
    result = _invoke("--run-name", "c2")
    assert result.exit_code == 2
    assert "--questions" in result.output


def test_a_question_file_other_than_the_runs_is_refused(run: dict[str, Any]) -> None:
    run["questions"].write_text("id\nES2015.q002\n", encoding="utf-8")
    result = _invoke("--run-name", "c2", "--questions", str(run["questions"]))
    assert result.exit_code == 1
    text = " ".join(result.output.split())
    assert "questions_sha256" in text and "huella" in text
    assert not (run["run_dir"] / afg_cli.OE4_SHEET_FILE).exists()
