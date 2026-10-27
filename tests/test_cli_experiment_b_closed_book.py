"""Tests for ``afg experiment b-closed-book``. No Ollama: condition and judge are fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.question import Answer, Question
from tests.test_cli_experiment_b import _HEADER, _ROWS, FakeBackend, _FakeProbe


class FakeC0:
    condition_id = "C0"

    def __init__(self) -> None:
        self.seeds: list[int] = []

    def with_seed(self, seed: int) -> FakeC0:
        self.seeds.append(seed)
        return self

    def answer(self, question: Question) -> Answer:
        return Answer(question_id=question.id, condition="C0", text="a")


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    questions = tmp_path / "q.csv"
    questions.write_text(_HEADER + _ROWS, encoding="utf-8")
    condition = FakeC0()
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "make_closed_book_condition", lambda: condition)
    monkeypatch.setattr(afg_cli, "make_judge_backend", lambda: FakeBackend())
    monkeypatch.setattr(afg_cli, "list_installed_models", lambda: ["qwen3:8b", "gpt-oss:20b"])
    monkeypatch.setattr(afg_cli, "configured_embedding_model", lambda: "bge-m3")
    monkeypatch.setattr(afg_cli, "make_provenance_probe", lambda: _FakeProbe())
    monkeypatch.setattr(afg_cli, "default_excerpt_for", lambda q: "passage")
    monkeypatch.setattr(
        "afg.evaluation.judge_calibration_set.calibration_series",
        lambda: frozenset({"ES2015"}),
    )
    return {"questions": questions, "out": tmp_path / "out", "condition": condition}


def _invoke(env: dict[str, Any], *args: str) -> Any:
    argv = ["experiment", "b-closed-book", "--questions", str(env["questions"]), *args]
    return CliRunner().invoke(afg_cli.app, argv)


def test_default_run_is_three_seeded_runs_in_the_diagnostic_folder(env: dict[str, Any]) -> None:
    result = _invoke(env)
    assert result.exit_code == 0, result.output
    run_dir = env["out"] / "diagnostico-sin-contexto-es2015"
    records = [
        json.loads(line)
        for line in (run_dir / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 3 * 3  # questions x runs_per_config
    assert {r["condition"] for r in records} == {"C0"}
    assert {r["seed"] for r in records} == {42, 43, 44}
    assert env["condition"].seeds == [42, 43, 44]
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["conditions"] == ["C0"]
    assert manifest["development_only"] is True
    assert manifest["settings"]["judge_model"] == "gpt-oss:20b"


def test_second_invocation_resumes(env: dict[str, Any]) -> None:
    _invoke(env, "--runs", "1", "--run-name", "again")
    result = _invoke(env, "--runs", "1", "--run-name", "again")
    assert result.exit_code == 0, result.output
    lines = (env["out"] / "again" / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


def test_evaluation_series_are_refused_before_writing(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "development_series", lambda: frozenset({"ES2016"}))
    result = _invoke(env)
    assert result.exit_code == 1
    assert "ES2015" in " ".join(result.output.split())
    assert not env["out"].exists()


def test_the_thesis_command_still_refuses_c0(env: dict[str, Any]) -> None:
    argv = ["experiment", "b", "--questions", str(env["questions"]), "--conditions", "c0"]
    result = CliRunner().invoke(afg_cli.app, argv)
    assert result.exit_code == 1
    assert not env["out"].exists()


def test_factory_wires_the_shared_generation_settings() -> None:
    from afg.conditions.c1_document_rag import GenerationSettings

    condition = afg_cli.make_closed_book_condition()
    assert condition.settings == GenerationSettings.from_config()
    assert condition.condition_id == "C0"
