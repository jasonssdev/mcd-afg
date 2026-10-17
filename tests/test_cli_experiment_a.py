"""Tests for ``afg experiment a``. No OpenKOS: the adapter is a fake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.extraction.openkos.bundle_reader import QuoteCounts, UnmappedDecision
from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.extraction.openkos_adapter import SeriesExtraction
from afg.extraction.protocol import ExtractionResult

SETTINGS = OpenKosRunSettings("openkos", "qwen3:8b", "bge-m3", 42, 0.1)


class FakeProbe:
    def __init__(self, digests: dict[str, str] | None) -> None:
        self._digests = digests

    def model_digests(self) -> dict[str, str] | None:
        return self._digests

    def ollama_version(self) -> str | None:
        return "0.9.9"

    def openkos_version(self) -> str | None:
        return None

    def git_dirty(self) -> bool | None:
        return True


class FakeAdapter:
    def __init__(self, base_dir: Path, fail_on_run: int | None = None) -> None:
        self.base_dir = base_dir
        self.fail_on_run = fail_on_run
        self.calls: list[tuple[str, int]] = []

    def extract_series(self, series_id: str, run: int) -> SeriesExtraction:
        self.calls.append((series_id, run))
        if run == self.fail_on_run:
            raise OpenKosError("ingest de ES2015b salió con 1")
        decision = Decision(
            id="decisions/kinetic",
            series_id=series_id,
            meeting_id=f"{series_id}a",
            decision_object="battery",
            content="Use a kinetic battery.",
            status=DecisionStatus.ACCEPTED,
            evidence=EvidenceSpan(meeting_id=f"{series_id}a", dialogue_act_ids=("a1",)),
        )
        workspace = self.base_dir / series_id / f"run-{run}"
        return SeriesExtraction(
            series_id=series_id,
            run=run,
            result=ExtractionResult(decisions=(decision,)),
            openkos_version="0.5.5",
            workspace=workspace,
            manifest_path=self.base_dir / series_id / f"run-{run}.manifest.json",
            quotes=QuoteCounts(total=3, found=2, not_found=1),
            unmapped=(UnmappedDecision("decisions/ghost", (f"{series_id}b",), ("not_found",)),),
        )


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeAdapter:
    adapter = FakeAdapter(tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "make_openkos_adapter", lambda base_dir: adapter)
    monkeypatch.setattr(afg_cli, "openkos_run_settings", lambda: SETTINGS)
    monkeypatch.setattr(afg_cli, "current_git_commit", lambda: "abc123")
    monkeypatch.setattr(
        afg_cli,
        "make_provenance_probe",
        lambda: FakeProbe({"qwen3:8b": "d-gen", "bge-m3:latest": "d-emb", "other:1b": "d-x"}),
    )
    return adapter


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a", *args])


def test_help_is_no_longer_a_stub() -> None:
    out = " ".join(_run("--help").output.split())
    assert "Sin implementar" not in out
    assert "--series" in out
    assert "desarrollo" in out


def test_runs_a_development_series_and_persists_each_run(tmp_path: Path, fake: FakeAdapter) -> None:
    result = _run("--series", "ES2015", "--runs", "2", "--run-name", "humo")

    assert result.exit_code == 0, result.output
    assert fake.calls == [("ES2015", 0), ("ES2015", 1)]
    run_dir = tmp_path / "out" / "humo"
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["series"] == "ES2015"
    assert manifest["partition"] == "development"
    assert manifest["runs"] == 2
    assert manifest["git_commit"] == "abc123"
    assert manifest["openkos"]["seed"] == 42
    assert manifest["openkos"]["temperature"] == 0.1
    lines = [json.loads(x) for x in (run_dir / "extracciones.jsonl").read_text().splitlines()]
    assert [line["run"] for line in lines] == [0, 1]
    first = lines[0]
    assert first["openkos_version"] == "0.5.5"
    assert first["n_decisions"] == 1
    assert first["quotes"] == {
        "total": 3,
        "found": 2,
        "not_found": 1,
        "no_dialogue_acts": 0,
        "empty": 0,
    }
    assert first["unmapped"] == [
        {"concept_id": "decisions/ghost", "meeting_ids": ["ES2015b"], "reasons": ["not_found"]}
    ]
    assert first["decisions"][0]["decision_object"] == "battery"
    assert first["decisions"][0]["evidence"]["dialogue_act_ids"] == ["a1"]
    assert "2 corridas" in result.output or "corrida" in result.output


def test_manifest_records_model_digests_and_machine_provenance(
    tmp_path: Path, fake: FakeAdapter
) -> None:
    assert _run("--series", "ES2015", "--runs", "1", "--run-name", "prov").exit_code == 0

    manifest = json.loads((tmp_path / "out" / "prov" / "manifest.json").read_text())
    openkos = manifest["openkos"]
    assert openkos["generative_model_digest"] == "d-gen"
    assert openkos["embedding_model_digest"] == "d-emb"
    assert openkos["model_digest_source"] == "ollama /api/tags"
    assert openkos["ollama_version"] == "0.9.9"
    assert manifest["git_dirty"] is True
    assert "judge_model_digest" not in openkos
    assert "questions_sha256" not in manifest


def test_unreachable_ollama_records_null_digests_without_failing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake: FakeAdapter
) -> None:
    monkeypatch.setattr(afg_cli, "make_provenance_probe", lambda: FakeProbe(None))
    result = _run("--series", "ES2015", "--runs", "1", "--run-name", "sin-ollama")

    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "out" / "sin-ollama" / "manifest.json").read_text())
    assert manifest["openkos"]["generative_model_digest"] is None
    assert manifest["openkos"]["embedding_model_digest"] is None
    assert manifest["openkos"]["model_digest_source"].startswith("unavailable")


def test_default_runs_come_from_the_shared_budget(tmp_path: Path, fake: FakeAdapter) -> None:
    result = _run("--series", "ES2015", "--run-name", "defecto")
    assert result.exit_code == 0, result.output
    assert len(fake.calls) == 3  # runs_per_config of config/experiments.toml


@pytest.mark.parametrize("series", ["ES2002", "TS3011", "XX9999"])
def test_evaluation_and_unknown_series_are_refused_before_any_work(
    tmp_path: Path, fake: FakeAdapter, series: str
) -> None:
    result = _run("--series", series, "--run-name", "no")

    assert result.exit_code == 1
    assert "desarrollo" in result.output
    assert fake.calls == []
    assert not (tmp_path / "out").exists()


def test_a_repeated_run_name_is_refused_instead_of_overwritten(
    tmp_path: Path, fake: FakeAdapter
) -> None:
    assert _run("--series", "ES2015", "--runs", "1", "--run-name", "dup").exit_code == 0
    again = _run("--series", "ES2015", "--runs", "1", "--run-name", "dup")
    assert again.exit_code == 1
    assert "dup" in again.output
    assert len(fake.calls) == 1


def test_a_failed_run_keeps_the_earlier_ones_and_exits_with_an_error(
    tmp_path: Path, fake: FakeAdapter
) -> None:
    fake.fail_on_run = 1
    result = _run("--series", "ES2015", "--runs", "3", "--run-name", "falla")

    assert result.exit_code == 1
    assert "ingest de ES2015b" in result.output
    lines = (tmp_path / "out" / "falla" / "extracciones.jsonl").read_text().splitlines()
    assert [json.loads(x)["run"] for x in lines] == [0]
    manifest = json.loads((tmp_path / "out" / "falla" / "manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["completed_runs"] == [0]


def test_missing_frozen_transcripts_are_reported_in_spanish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake: FakeAdapter
) -> None:
    def boom(series_id: str, run: int) -> SeriesExtraction:
        raise FileNotFoundError("Frozen transcripts of ES2015a not found")

    monkeypatch.setattr(fake, "extract_series", boom)
    result = _run("--series", "ES2015", "--run-name", "sin-transcripciones")
    assert result.exit_code == 1
    assert "ES2015a" in result.output
