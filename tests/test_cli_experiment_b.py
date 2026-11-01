"""Tests for ``afg experiment b``. No Ollama: the condition and the judge backend are fakes."""

from __future__ import annotations

import hashlib
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


class _FakeProbe:
    def model_digests(self) -> dict[str, str]:
        return {"qwen3:8b": "d-gen", "gpt-oss:20b": "d-judge", "bge-m3:latest": "d-emb"}

    def ollama_version(self) -> str:
        return "0.9.9"

    def openkos_version(self) -> str | None:
        return None

    def git_dirty(self) -> bool:
        return True


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
    monkeypatch.setattr(afg_cli, "make_provenance_probe", lambda: _FakeProbe())
    monkeypatch.setattr(
        "afg.evaluation.judge_calibration_set.calibration_series",
        lambda: frozenset({"ES2015"}),
    )
    monkeypatch.setattr(afg_cli, "default_excerpt_for", lambda q: "passage")
    _strict_env(monkeypatch, tmp_path)
    return {
        "questions": questions,
        "out": tmp_path / "out",
        "condition": condition,
        "monkeypatch": monkeypatch,
    }


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


def test_manifest_records_the_reproducibility_fields(env: dict[str, Any]) -> None:
    result = _invoke(env, "--runs", "1", "--run-name", "repro")
    assert result.exit_code == 0, result.output
    manifest = json.loads((env["out"] / "repro" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generative_model_digest"] == "d-gen"
    assert manifest["judge_model_digest"] == "d-judge"
    assert manifest["embedding_model_digest"] == "d-emb"
    assert manifest["ollama_version"] == "0.9.9"
    assert manifest["openkos_version"] is None
    assert manifest["git_dirty"] is True
    assert manifest["c1_params"] == {"max_chars": 1200, "overlap_turns": 1, "k": 5}
    assert manifest["questions_sha256"] == hashlib.sha256(env["questions"].read_bytes()).hexdigest()


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


@pytest.mark.parametrize("condition", ["c3", "c1,c3"])
def test_c3_requires_the_extraction_run(env: dict[str, Any], condition: str) -> None:
    result = _invoke(env, "--conditions", condition)
    assert result.exit_code == 1
    assert "--c2-extraction" in _out(result)
    assert not env["out"].exists()


def test_c3_workspaces_must_have_been_built(env: dict[str, Any], tmp_path: Path) -> None:
    env["monkeypatch"].setattr(afg_cli, "OPENKOS_C3_WORKSPACES_DIR", tmp_path / "nowhere")
    result = _invoke(env, "--conditions", "c3", "--c2-extraction", "nope")
    assert result.exit_code == 1
    assert "nope" in _out(result) and "afg c3 build" in _out(result)
    assert not env["out"].exists()


def test_runs_c3_and_records_its_sources_in_the_manifest(
    env: dict[str, Any], tmp_path: Path
) -> None:
    class FakeC3(FakeC1):
        condition_id = "C3"

    env["monkeypatch"].setattr(afg_cli, "OPENKOS_C3_WORKSPACES_DIR", tmp_path / "c3-base")
    env["monkeypatch"].setattr(afg_cli, "make_c3_condition", lambda run: FakeC3())
    result = _invoke(
        env, "--conditions", "c3", "--c2-extraction", "es-run", "--runs", "1", "--run-name", "t"
    )
    assert result.exit_code == 0, result.output
    manifest = json.loads((env["out"] / "t" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["c2_extraction"] == "es-run"
    assert manifest["c3_workspaces"] == str(tmp_path / "c3-base")
    _invoke(env, "--runs", "1", "--run-name", "u")
    other = json.loads((env["out"] / "u" / "manifest.json").read_text(encoding="utf-8"))
    assert other["c3_workspaces"] is None


def test_make_experiment_b_condition_builds_c3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from afg.conditions.c3_compiled_gold import CompiledGoldCondition

    (tmp_path / "es-run").mkdir()
    monkeypatch.setattr(afg_cli, "OPENKOS_C3_WORKSPACES_DIR", tmp_path)
    condition = afg_cli.make_experiment_b_condition("c3", c2_extraction="es-run")
    assert isinstance(condition, CompiledGoldCondition)
    assert condition.extraction_run == "es-run" and condition.base_dir == tmp_path
    assert condition.condition_id == "C3"


@pytest.mark.parametrize("condition", ["c2", "c1,c2"])
def test_c2_requires_the_extraction_run(env: dict[str, Any], condition: str) -> None:
    result = _invoke(env, "--conditions", condition)
    assert result.exit_code == 1
    assert "--c2-extraction" in _out(result)
    assert not env["out"].exists()


def test_c2_extraction_without_c2_is_refused(env: dict[str, Any]) -> None:
    result = _invoke(env, "--conditions", "c1", "--c2-extraction", "es-run")
    assert result.exit_code == 1
    assert "--c2-extraction" in _out(result) and "c2" in _out(result)
    assert not env["out"].exists()


def test_manifest_records_the_c2_extraction_run(env: dict[str, Any]) -> None:
    class FakeC2(FakeC1):
        condition_id = "C2"

    env["monkeypatch"].setattr(afg_cli, "make_c2_condition", lambda run: FakeC2())
    _invoke(
        env, "--conditions", "c2", "--c2-extraction", "es-run", "--runs", "1", "--run-name", "m"
    )
    _invoke(env, "--runs", "1", "--run-name", "n")
    manifest = json.loads((env["out"] / "m" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["c2_extraction"] == "es-run"
    other = json.loads((env["out"] / "n" / "manifest.json").read_text(encoding="utf-8"))
    assert other["c2_extraction"] is None


def test_c2_extraction_run_must_exist(env: dict[str, Any], tmp_path: Path) -> None:
    env["monkeypatch"].setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "nowhere")
    result = _invoke(env, "--conditions", "c2", "--c2-extraction", "nope")
    assert result.exit_code == 1
    assert "nope" in _out(result) and "afg experiment a" in _out(result)
    assert not env["out"].exists()


def test_runs_c2_with_its_extraction_run(env: dict[str, Any], tmp_path: Path) -> None:
    class FakeC2(FakeC1):
        condition_id = "C2"

        def answer(self, question: Question) -> Answer:
            return Answer(question_id=question.id, condition="C2", text="b", abstained=True)

    built: list[str] = []

    def fake_make(extraction_run: str) -> FakeC2:
        built.append(extraction_run)
        return FakeC2()

    env["monkeypatch"].setattr(afg_cli, "make_c2_condition", fake_make)
    result = _invoke(
        env,
        "--conditions",
        "c1,c2",
        "--c2-extraction",
        "es-run",
        "--runs",
        "1",
        "--run-name",
        "two",
    )
    assert result.exit_code == 0, result.output
    assert built == ["es-run"]
    lines = (env["out"] / "two" / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    assert {json.loads(line)["condition"] for line in lines} == {"C1", "C2"}


def test_make_experiment_b_condition_builds_c2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from afg.conditions.c2_compiled_auto import CompiledAutoCondition

    (tmp_path / "es-run").mkdir()
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path)
    condition = afg_cli.make_experiment_b_condition("c2", c2_extraction="es-run")
    assert isinstance(condition, CompiledAutoCondition)
    assert condition.extraction_run == "es-run" and condition.limit == 5
    assert condition.base_dir == tmp_path


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
_BANK_OK = "q001,ES2016,E1_point_fact,How much?,Twelve,ES2016a:ES2016a.A.dialog-act.x.1,gm,gv,\n"
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
    _bank(env, _BANK_OK, "q002,ES2016,E1_point_fact,,A,ES2016a:ES2016a.A.dialog-act.x.1,gm,gv,\n")
    result = _invoke(env, "--run-name", "bad")
    assert result.exit_code == 1
    assert "q002" in _out(result)
    assert not env["out"].exists()


def test_bank_with_a_development_series_is_refused_before_running(env: dict[str, Any]) -> None:
    _bank(env, "q001,ES2015,E1_point_fact,Q?,A,ES2015a:x.1,gm,gv,\n")
    result = _invoke(env, "--run-name", "dev")
    assert result.exit_code == 1
    assert "desarrollo" in _out(result)
    assert not env["out"].exists()


def test_bank_with_unknown_dialogue_acts_is_refused_before_running(env: dict[str, Any]) -> None:
    _bank(env, "q001,ES2016,E1_point_fact,Q?,A,ES2016a:ES2016a.A.dialog-act.zzz.9,gm,gv,\n")
    result = _invoke(env, "--run-name", "acts")
    assert result.exit_code == 1
    assert "zzz" in _out(result)
    assert not env["out"].exists()


def test_bank_with_a_validator_that_is_not_an_annotator_is_refused(env: dict[str, Any]) -> None:
    _bank(env, "q001,ES2016,E1_point_fact,Q?,A,ES2016a:ES2016a.A.dialog-act.x.1,gm,jss,\n")
    result = _invoke(env, "--run-name", "who")
    assert result.exit_code == 1
    assert "jss" in _out(result)
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


def test_questions_check_reports_without_running(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a:ES2016a.A.dialog-act.x.1"), _BANK_PENDING)
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


# --- encoding and delimiter problems (Excel) --------------------------------------------------


def test_questions_check_explains_a_latin1_file(env: dict[str, Any]) -> None:
    env["questions"].write_bytes((_BANK_HEADER + "q001,decisión\n").encode("latin-1"))
    result = _check(env["questions"])
    assert result.exit_code == 1
    out = _out(result)
    assert env["questions"].name in out and "UTF-8" in out
    assert "codec" not in out and "Traceback" not in result.output


def test_questions_check_explains_a_utf16_file(env: dict[str, Any]) -> None:
    env["questions"].write_bytes((_BANK_HEADER + "q001,x\n").encode("utf-16"))
    result = _check(env["questions"])
    assert result.exit_code == 1
    assert "UTF-16" in _out(result) and "CSV UTF-8" in _out(result)


def test_questions_check_explains_a_semicolon_file(env: dict[str, Any]) -> None:
    env["questions"].write_text(_BANK_HEADER.replace(",", ";") + "q001;x\n", encoding="utf-8")
    result = _check(env["questions"])
    assert result.exit_code == 1
    assert "`;`" in _out(result) and "comas" in _out(result)


# --- questions-check: collapsed report and stricter evidence checks ----------------------------


def _strict_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir(exist_ok=True)
    turn = {
        "meeting_id": "ES2016a",
        "turn_index": 0,
        "speaker": "A",
        "role": "PM",
        "text": "hello",
        "start": 0.0,
        "end": 1.0,
        "char_start": 0,
        "char_end": 5,
        "dialogue_act_ids": ["ES2016a.A.dialog-act.x.1", "ES2016a.A.dialog-act.x.2"],
    }
    (transcripts / "ES2016a.jsonl").write_text(json.dumps(turn) + "\n", encoding="utf-8")
    monkeypatch.setattr("afg.experiments.question_bank.TRANSCRIPTS_DIR", transcripts)


def _row(evidence: str, *, series: str = "ES2016", validator: str = "gv") -> str:
    return f'q001,{series},E1_point_fact,Q?,A,"{evidence}",gm,{validator},\n'


def test_questions_check_complete_on_blank_bank_collapses_repeated_errors(
    env: dict[str, Any],
) -> None:
    rows = "".join(f"q{i:03d},,E1_point_fact,,,,gm,,\n" for i in range(1, 31))
    _bank(env, rows)
    result = _check(env["questions"], "--complete")
    out = _out(result)
    assert result.exit_code == 1
    assert "30 filas" in out and "sin escribir" in out and "q001" in out
    assert out.count("sin escribir") == 1, out
    assert "30 pendiente(s)" in out


def test_questions_check_rejects_comma_separated_acts(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a:ES2016a.A.dialog-act.x.1,ES2016a.A.dialog-act.x.2"))
    result = _check(env["questions"])
    out = _out(result)
    assert result.exit_code == 1
    assert "`;`" in out and "`|`" in out and "ES2016a:" in out


def test_questions_check_reports_unknown_act_ids(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a:ES2016a.A.dialog-act.x.1;ES2016a.A.dialog-act.zzz.9"))
    result = _check(env["questions"])
    out = _out(result)
    assert result.exit_code == 1
    assert "zzz.9" in out and "uv run afg gold evidencia" in out


def test_questions_check_accepts_known_act_ids(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a:ES2016a.A.dialog-act.x.1;ES2016a.A.dialog-act.x.2"))
    result = _check(env["questions"])
    assert result.exit_code == 0, result.output


def test_questions_check_warns_once_when_transcripts_are_missing(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("afg.experiments.question_bank.TRANSCRIPTS_DIR", tmp_path / "nada")
    _bank(env, _row("ES2016a:a.1"), "q002,ES2016,E1_point_fact,Q?,A,ES2016b:b.1,gm,gv,\n")
    result = _check(env["questions"])
    out = _out(result)
    assert result.exit_code == 0, result.output
    assert out.count("uv run afg gold setup") == 1


def test_questions_check_reports_evidence_without_meeting_in_spanish(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a.A.dialog-act.x.1"))
    out = _out(_check(env["questions"]))
    assert "malformed" not in out and "reunión" in out and "ES2016a:" in out


def test_questions_check_rejects_development_series(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2015a:x.1", series="ES2015"))
    result = _check(env["questions"])
    out = _out(result)
    assert result.exit_code == 1
    assert "desarrollo" in out and "ADR 0005" in out


def test_questions_check_rejects_validators_that_are_not_annotators(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _strict_env(monkeypatch, tmp_path)
    _bank(env, _row("ES2016a:ES2016a.A.dialog-act.x.1", validator="jss"))
    result = _check(env["questions"])
    out = _out(result)
    assert result.exit_code == 1
    assert "jss" in out and "gm, gv" in out
