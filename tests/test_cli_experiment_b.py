"""Tests for ``afg experiment b``. No Ollama: the condition and the judge backend are fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question

_HEADER = "id,series_id,stratum,question,reference_answer,reference_evidence\n"
_ROWS = "".join(
    f"ES2015.q{i:03d},ES2015,E1_point_fact,Question {i}?,Answer {i},ES2015a:d{i}\n"
    for i in range(1, 4)
)
GOOD = json.dumps({"correct": True, "evidence_supported": True, "rationale": "ok"})


class FakeC1:
    condition_id = "C1"

    def __init__(self) -> None:
        self.seeds: list[int] = []

    def with_seed(self, seed: int) -> FakeC1:
        self.seeds.append(seed)
        return self

    def answer(self, question: Question) -> Answer:
        span = EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("d1",))
        return Answer(question_id=question.id, condition="C1", text="a", cited_evidence=(span,))


class FakeBackend:
    def complete(self, system: str, user: str, **kwargs: Any) -> str:
        return GOOD


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    questions = tmp_path / "q.csv"
    questions.write_text(_HEADER + _ROWS, encoding="utf-8")
    condition = FakeC1()
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "make_c1_condition", lambda: condition)
    monkeypatch.setattr(afg_cli, "make_judge_backend", lambda: FakeBackend())
    monkeypatch.setattr(
        afg_cli, "list_installed_models", lambda: ["qwen3:8b", "gpt-oss:20b", "bge-m3:latest"]
    )
    monkeypatch.setattr(afg_cli, "configured_embedding_model", lambda: "bge-m3")
    monkeypatch.setattr(
        "afg.evaluation.judge_calibration_set.calibration_series",
        lambda: frozenset({"ES2015"}),
    )
    monkeypatch.setattr(afg_cli, "default_excerpt_for", lambda q: "passage")
    return {"questions": questions, "out": tmp_path / "out", "condition": condition}


def _invoke(env: dict[str, Any], *args: str) -> Any:
    argv = ["experiment", "b", "--questions", str(env["questions"]), *args]
    return CliRunner().invoke(afg_cli.app, argv)


def _out(result: Any) -> str:
    return " ".join(result.output.split())


def test_runs_c1_and_writes_records_and_manifest(env: dict[str, Any]) -> None:
    result = _invoke(env, "--conditions", "c1", "--runs", "2", "--run-name", "smoke")
    assert result.exit_code == 0, result.output
    run_dir = env["out"] / "smoke"
    lines = (run_dir / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 * 1 * 2
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["partition"] == "development" and manifest["development_only"] is True
    assert manifest["settings"]["base_seed"] == 42
    assert "6" in _out(result)


def test_limit_questions_and_default_runs_from_config(env: dict[str, Any]) -> None:
    result = _invoke(env, "--run-name", "lim", "--limit-questions", "1")
    assert result.exit_code == 0, result.output
    lines = (env["out"] / "lim" / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # runs_per_config = 3


def test_second_invocation_resumes(env: dict[str, Any]) -> None:
    _invoke(env, "--runs", "1", "--run-name", "again")
    result = _invoke(env, "--runs", "1", "--run-name", "again")
    assert result.exit_code == 0, result.output
    lines = (env["out"] / "again" / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3


@pytest.mark.parametrize("condition", ["c2", "c3", "c1,c2"])
def test_other_conditions_are_refused_clearly(env: dict[str, Any], condition: str) -> None:
    result = _invoke(env, "--conditions", condition)
    assert result.exit_code == 1
    assert "no está disponible" in _out(result)
    assert not env["out"].exists()


def test_unknown_condition_is_refused(env: dict[str, Any]) -> None:
    result = _invoke(env, "--conditions", "c9")
    assert result.exit_code == 1
    assert "c9" in _out(result)


def test_missing_model_stops_before_running(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "list_installed_models", lambda: ["qwen3:8b", "bge-m3:latest"])
    result = _invoke(env)
    assert result.exit_code == 1
    assert "ollama pull" in _out(result)
    assert not env["out"].exists()


def test_missing_questions_file_is_reported(env: dict[str, Any]) -> None:
    env["questions"].unlink()
    result = _invoke(env)
    assert result.exit_code == 1
    assert not env["out"].exists()


# --- question bank source --------------------------------------------------------------------

_BANK_HEADER = (
    "id,series_id,stratum,text,reference_answer,reference_evidence,author,validated_by,"
    "validation_notes\n"
)
_BANK_OK = "q001,ES2015,E1_point_fact,How much?,Twelve,ES2015a:d1,gm,gv,\n"
_BANK_PENDING = "q002,,E2_current_state,,,,gm,,\n"


def _bank(env: dict[str, Any], *rows: str) -> None:
    env["questions"].write_text(_BANK_HEADER + "".join(rows), encoding="utf-8")


def test_bank_runs_only_validated_rows_and_reports_pending(env: dict[str, Any]) -> None:
    _bank(env, _BANK_OK, _BANK_PENDING)
    result = _invoke(env, "--runs", "1", "--run-name", "bank")
    assert result.exit_code == 0, result.output
    lines = (env["out"] / "bank" / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["question_id"] for line in lines] == ["q001"]
    assert "1 pendiente" in _out(result)


def test_bank_with_blocking_errors_is_refused_before_running(env: dict[str, Any]) -> None:
    _bank(env, _BANK_OK, "q002,ES2015,E1_point_fact,,A,ES2015a:d1,gm,gv,\n")
    result = _invoke(env, "--run-name", "bad")
    assert result.exit_code == 1
    assert "q002" in _out(result)
    assert not env["out"].exists()


def test_bank_with_nothing_validated_is_refused(env: dict[str, Any]) -> None:
    _bank(env, _BANK_PENDING)
    result = _invoke(env, "--run-name", "none")
    assert result.exit_code == 1
    assert "pendiente" in _out(result)
    assert not env["out"].exists()


# --- afg gold questions-check ----------------------------------------------------------------


def _check(path: Path, *args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["gold", "questions-check", "--path", str(path), *args])


def test_questions_check_reports_without_running(env: dict[str, Any]) -> None:
    _bank(env, _BANK_OK, _BANK_PENDING)
    result = _check(env["questions"])
    assert result.exit_code == 0, result.output
    assert "1 validada" in _out(result) and "1 pendiente" in _out(result)


def test_questions_check_exits_1_on_blocking_errors(env: dict[str, Any]) -> None:
    _bank(env, "q001,ES9999,E1_point_fact,Q?,A,ES9999a:d1,gm,gv,\n")
    result = _check(env["questions"])
    assert result.exit_code == 1
    assert "q001" in _out(result)


def test_questions_check_complete_requires_every_row_validated(env: dict[str, Any]) -> None:
    _bank(env, _BANK_OK, _BANK_PENDING)
    assert _check(env["questions"], "--complete").exit_code == 1


def test_questions_check_rejects_a_file_that_is_not_a_bank(env: dict[str, Any]) -> None:
    env["questions"].write_text(_HEADER + _ROWS, encoding="utf-8")
    result = _check(env["questions"])
    assert result.exit_code == 1
