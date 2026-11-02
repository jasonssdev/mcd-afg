"""The freeze gate in the commands, and ``afg freeze write``. Records live under ``tmp_path``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.experiments.freeze import FreezeSources, write_freeze_record
from tests.freeze_fixtures import COMMIT, SERIES, make_sources


@pytest.fixture
def frozen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A matching record for ES2002 and ES2008, wired into the CLI module."""
    sources = make_sources(tmp_path)
    record = tmp_path / "config" / "freeze.json"
    write_freeze_record(record, sources, series=SERIES, adr="0017", commit=COMMIT)
    monkeypatch.setattr(afg_cli, "FREEZE_PATH", record)
    monkeypatch.setattr(afg_cli, "FreezeSources", lambda: sources)
    monkeypatch.setattr("afg.experiments.freeze.code_changes_since", lambda commit, root=None: [])
    return {"sources": sources, "record": record}


def test_development_series_pass_without_a_record() -> None:
    assert afg_cli._require_series_gate(["ES2015", "IS1004"]) == "development"


def test_evaluation_series_exit_without_a_record(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as raised:
        afg_cli._require_series_gate(["ES2002"])

    assert raised.value.exit_code == 1
    out = " ".join(capsys.readouterr().out.split())
    assert "ES2002" in out and "congelamiento" in out and "no se llamó a ningún modelo" in out


def test_evaluation_series_pass_with_a_matching_record(frozen: dict[str, Any]) -> None:
    assert afg_cli._require_series_gate(["ES2002", "ES2008"]) == "evaluation"


def test_a_mismatch_exits_naming_the_difference(
    frozen: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    sources: FreezeSources = frozen["sources"]
    (sources.decisions_dir / "ES2008.decisions.adjudicated.csv").write_text("changed\n")

    with pytest.raises(typer.Exit):
        afg_cli._require_series_gate(["ES2002"])

    out = " ".join(capsys.readouterr().out.split())
    assert "ES2008 decisions" in out and "huella actual" in out


# --- the commands refuse before any model call -------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["experiment", "a", "--series", "ES2002"],
        ["experiment", "a-batch", "--series", "ES2002", "--run-name", "x"],
        ["experiment", "a-batch", "--partition", "evaluation", "--run-name", "x"],
        ["experiment", "a-relations", "--c2-extraction", "x", "--series", "ES2002"],
        ["c3", "build", "--c2-extraction", "x", "--series", "ES2002"],
    ],
)
def test_a_a_batch_a_relations_and_c3_refuse_evaluation_without_a_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, argv: list[str]
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("a model or environment call happened before the gate")

    monkeypatch.setattr(afg_cli, "require_pinned_environment", boom)
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path)
    (tmp_path / "x").mkdir()

    result = CliRunner().invoke(afg_cli.app, argv)

    assert result.exit_code == 1, result.output
    assert "congelamiento" in " ".join(result.output.split())


# --- afg freeze write ----------------------------------------------------------------------------


def _write(tmp_path: Path, *extra: str) -> Any:
    return CliRunner().invoke(
        afg_cli.app,
        [
            "freeze",
            "write",
            "--adr",
            "0017",
            "--commit",
            COMMIT,
            "--series",
            ",".join(SERIES),
            "--output",
            str(tmp_path / "out.json"),
            *extra,
        ],
    )


@pytest.fixture
def wired_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FreezeSources:
    sources = make_sources(tmp_path)
    monkeypatch.setattr(afg_cli, "FreezeSources", lambda: sources)
    return sources


def test_freeze_write_writes_the_record(tmp_path: Path, wired_sources: FreezeSources) -> None:
    result = _write(tmp_path)

    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert data["adr"] == "0017" and sorted(data["reference"]) == list(SERIES)
    assert "out.json" in " ".join(result.output.split())


def test_freeze_write_refuses_to_overwrite(tmp_path: Path, wired_sources: FreezeSources) -> None:
    assert _write(tmp_path).exit_code == 0
    again = _write(tmp_path)

    assert again.exit_code == 1
    assert "ya existe" in " ".join(again.output.lower().split())


def test_freeze_write_names_a_missing_reference(
    tmp_path: Path, wired_sources: FreezeSources
) -> None:
    (wired_sources.decisions_dir / "ES2008.reference-en.csv").unlink()

    result = _write(tmp_path)

    assert result.exit_code == 1
    assert "ES2008" in result.output and not (tmp_path / "out.json").exists()


def test_freeze_write_defaults_to_the_oe1_series_and_head(
    tmp_path: Path, wired_sources: FreezeSources, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def fake_write(path: Path, sources: FreezeSources, **kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return {}

    monkeypatch.setattr(afg_cli, "write_freeze_record", fake_write)
    monkeypatch.setattr(afg_cli, "current_git_commit", lambda: COMMIT)

    result = CliRunner().invoke(
        afg_cli.app, ["freeze", "write", "--adr", "0017", "--output", str(tmp_path / "o.json")]
    )

    assert result.exit_code == 0, result.output
    assert seen["commit"] == COMMIT
    assert {"ES2015", "IS1004", "TS3009", "ES2002", "TS3011"} <= set(seen["series"])
    assert len(seen["series"]) == 14
