"""``afg experiment b-hosted-compare``: reads stored runs, calls no model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from tests.test_hosted_answers import C1_NOW, FORMAL, _formal, _now, _records, answer_run_name


def _write_run(root: Path, name: str, records: list[dict[str, Any]]) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "respuestas.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path)
    monkeypatch.setattr(afg_cli, "configured_minimums", lambda base: 3)
    return tmp_path


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", "b-hosted-compare", *args])


def test_reports_pending_models_when_no_run_exists(root: Path) -> None:
    result = _invoke()
    assert result.exit_code == 0, result.output
    out = " ".join(result.output.split())
    assert "pendiente" in out and "openai-small" in out
    payload = json.loads(
        (root / "hosted-comparison" / "respuestas-comparacion.json").read_text(encoding="utf-8")
    )
    assert payload["family"]["n_models"] == 6
    assert (root / "hosted-comparison" / "respuestas-comparacion.csv").is_file()


def test_compares_a_finished_model_against_c1(root: Path) -> None:
    _write_run(root, FORMAL, _formal())
    _write_run(root, C1_NOW, _now())
    _write_run(root, answer_run_name("openai-small"), _records("C2", lambda i: i < 2))
    result = _invoke("--models", "openai-small")
    assert result.exit_code == 0, result.output
    assert "queda bajo C1 actual" in " ".join(result.output.split())
    payload = json.loads(
        (root / "hosted-comparison" / "respuestas-comparacion.json").read_text(encoding="utf-8")
    )
    assert list(payload["models"]) == ["openai-small"]
    assert payload["family"]["n_models"] == 6  # Bonferroni over the six, not over the subset


def test_unknown_label_is_refused(root: Path) -> None:
    result = _invoke("--models", "nope")
    assert result.exit_code == 2
    assert not (root / "hosted-comparison").exists()


def test_development_records_are_refused(root: Path) -> None:
    dev = [dict(r, partition="development") for r in _formal()]
    _write_run(root, FORMAL, dev)
    _write_run(root, C1_NOW, [dict(r, partition="development") for r in _now()])
    _write_run(
        root,
        answer_run_name("openai-small"),
        [dict(r, partition="development") for r in _records("C2", lambda i: True)],
    )
    result = _invoke("--models", "openai-small")
    assert result.exit_code == 1


def test_reports_the_infrastructure_effect_and_accepts_another_c1_run(root: Path) -> None:
    _write_run(root, FORMAL, _formal())
    _write_run(root, "mi-c1", _records("C1", lambda i: i < 4))
    _write_run(root, answer_run_name("openai-small"), _records("C2", lambda i: True))
    result = _invoke("--models", "openai-small", "--c1-run", "mi-c1")
    assert result.exit_code == 0, result.output
    assert "infraestructura" in " ".join(result.output.split()).lower()
    payload = json.loads(
        (root / "hosted-comparison" / "respuestas-comparacion.json").read_text(encoding="utf-8")
    )
    assert payload["runs"]["c1_actual"] == "mi-c1"
    assert payload["infrastructure_effect"]["comparison"]["difference"] == pytest.approx(-0.5)
