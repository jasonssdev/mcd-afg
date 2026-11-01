"""Tests for ``afg experiment a-batch``. No OpenKOS: the adapter is a fake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from tests.test_cli_experiment_a import SETTINGS, FakeAdapter, FakeProbe

DEVELOPMENT = ["ES2015", "IS1004", "TS3009"]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeAdapter:
    adapter = FakeAdapter(tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "make_openkos_adapter", lambda base_dir: adapter)
    monkeypatch.setattr(afg_cli, "openkos_run_settings", lambda: SETTINGS)
    monkeypatch.setattr(afg_cli, "current_git_commit", lambda: "abc123")
    monkeypatch.setattr(afg_cli, "make_provenance_probe", lambda: FakeProbe({"qwen3:8b": "d"}))
    return adapter


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a-batch", *args])


def test_help_documents_the_options() -> None:
    out = " ".join(_run("--help").output.split())
    for option in ("--series", "--partition", "--runs", "--run-name"):
        assert option in out


def test_series_list_runs_every_pair_under_one_run_name(tmp_path: Path, fake: FakeAdapter) -> None:
    result = _run("--series", "ES2015,IS1004", "--runs", "2", "--run-name", "lote")

    assert result.exit_code == 0, result.output
    assert fake.calls == [("ES2015", 0), ("ES2015", 1), ("IS1004", 0), ("IS1004", 1)]
    run_dir = tmp_path / "out" / "lote"
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["series"] == "ES2015,IS1004"
    assert manifest["partition"] == "development"
    assert manifest["git_commit"] == "abc123"
    assert manifest["openkos"]["seed"] == 42
    assert manifest["openkos"]["generative_model_digest"] == "d"
    assert len((run_dir / "extracciones.jsonl").read_text().splitlines()) == 4
    assert "Resumen de integridad" in result.output
    assert "ES2015: 2 de 2 corridas completas" in result.output


def test_partition_development_selects_its_series_and_default_runs(
    fake: FakeAdapter,
) -> None:
    result = _run("--partition", "development", "--run-name", "dev")

    assert result.exit_code == 0, result.output
    assert {s for s, _ in fake.calls} == set(DEVELOPMENT)
    assert len(fake.calls) == 9  # runs_per_config = 3


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--series", "ES2015", "--partition", "development"],
        ["--partition", "unassigned"],
    ],
)
def test_series_xor_partition_is_required(
    tmp_path: Path, fake: FakeAdapter, args: list[str]
) -> None:
    result = _run(*args, "--run-name", "x")

    assert result.exit_code != 0
    assert fake.calls == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--partition", "evaluation"],
        ["--series", "ES2015,ES2002"],
        ["--series", "XX9999"],
    ],
)
def test_non_development_series_are_refused_before_any_work(
    tmp_path: Path, fake: FakeAdapter, args: list[str]
) -> None:
    result = _run(*args, "--run-name", "no")

    assert result.exit_code == 1
    assert "desarrollo" in result.output
    assert fake.calls == []
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "ws").exists()


def test_a_and_a_batch_share_the_partition_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake: FakeAdapter
) -> None:
    monkeypatch.setattr(afg_cli, "configured_partition_of", lambda: lambda series: "development")

    single = CliRunner().invoke(
        afg_cli.app, ["experiment", "a", "--series", "ES2002", "--runs", "1", "--run-name", "u"]
    )
    batch = _run("--series", "ES2002", "--runs", "1", "--run-name", "v")

    assert single.exit_code == 0, single.output
    assert batch.exit_code == 0, batch.output


def test_a_failed_pair_gives_a_non_zero_exit_after_finishing_the_rest(
    tmp_path: Path, fake: FakeAdapter
) -> None:
    fake.fail_on_run = 1
    result = _run("--series", "ES2015,IS1004", "--runs", "2", "--run-name", "falla")

    assert result.exit_code == 1
    assert len(fake.calls) == 4
    assert "1 fallida" in result.output
    manifest = json.loads((tmp_path / "out" / "falla" / "manifest.json").read_text())
    assert manifest["status"] == "failed"


def test_repeating_the_run_name_resumes_without_redoing_ok_pairs(
    tmp_path: Path, fake: FakeAdapter
) -> None:
    fake.fail_on_run = 1
    assert _run("--series", "ES2015", "--runs", "2", "--run-name", "r").exit_code == 1
    fake.fail_on_run = None
    fake.calls.clear()

    result = _run("--series", "ES2015", "--runs", "2", "--run-name", "r")

    assert result.exit_code == 0, result.output
    assert fake.calls == [("ES2015", 1)]
    lines = (tmp_path / "out" / "r" / "extracciones.jsonl").read_text().splitlines()
    assert sorted(json.loads(x)["run"] for x in lines) == [0, 1]


def test_an_existing_single_series_run_is_refused(tmp_path: Path, fake: FakeAdapter) -> None:
    single = CliRunner().invoke(
        afg_cli.app, ["experiment", "a", "--series", "ES2015", "--runs", "1", "--run-name", "uno"]
    )
    assert single.exit_code == 0
    fake.calls.clear()

    result = _run("--series", "ES2015", "--runs", "1", "--run-name", "uno")

    assert result.exit_code == 1
    assert "uno" in result.output
    assert fake.calls == []
