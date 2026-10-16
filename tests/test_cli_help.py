"""``--help`` for annotators: Spanish, with their commands apart from the maintainer's."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli

_ANNOTATOR_COMMANDS = ("setup", "status", "validate", "evidencia", "questions-check", "prepare")
_MAINTAINER_COMMANDS = (
    "build",
    "link",
    "candidates",
    "recall-sample",
    "agreement",
    "adjudicate",
    "validate-adjudication",
    "questions-init",
)
_ENGLISH_WORDS = re.compile(
    r"\b(Build|Generate|Compute|Sample|Writes|Reads|Refuses|series id|Overlap|Number of)\b"
)


def _help(*args: str) -> str:
    result = CliRunner().invoke(afg_cli.app, [*args, "--help"], terminal_width=100)
    assert result.exit_code == 0, result.output
    return result.output


def test_gold_help_separates_annotator_and_maintainer_commands() -> None:
    out = _help("gold")
    annotators, maintenance = out.index("Para anotadores"), out.index("Para mantenimiento")
    assert annotators < maintenance
    for name in _ANNOTATOR_COMMANDS:
        assert annotators < out.index(f"│ {name} ") < maintenance
    for name in _MAINTAINER_COMMANDS:
        assert out.index(f"│ {name} ") > maintenance


def test_maintainer_commands_are_marked_in_their_own_help() -> None:
    out = _help("gold")
    for name in _MAINTAINER_COMMANDS:
        line = next(line for line in out.splitlines() if line.startswith(f"│ {name} "))
        assert "(Mantenedor)" in line


@pytest.mark.parametrize("name", [*_ANNOTATOR_COMMANDS, *_MAINTAINER_COMMANDS])
def test_gold_subcommand_help_is_in_spanish(name: str) -> None:
    assert not _ENGLISH_WORDS.search(_help("gold", name))


def test_root_help_is_in_spanish_and_points_annotators_to_gold() -> None:
    out = _help()
    assert "Comandos" in out and "Para mantenimiento" in out
    assert "afg gold" in out
    assert not _ENGLISH_WORDS.search(out)


_ENGLISH_HELP = re.compile(
    r"\b(Fetch|Download|Copy|Check|Symlink|Freeze|Coverage|Counts|Synced|Skill name|"
    r"Directory|Output directory|Overwrite|Skip the|Native|Defaults to|series id|Repeatable|"
    r"Regenerates|Experiment A|Requires)\b"
)


@pytest.mark.parametrize(
    "args",
    [
        ("corpus",),
        ("corpus", "download"),
        ("corpus", "inventory"),
        ("corpus", "participants"),
        ("corpus", "transcripts"),
        ("biblio",),
        ("biblio", "audit"),
        ("biblio", "stats"),
        ("skills",),
        ("skills", "sync-assets"),
        ("skills", "verify"),
        ("skills", "link"),
        ("experiment",),
        ("experiment", "a"),
        ("report",),
    ],
)
def test_maintenance_group_help_is_in_spanish(args: tuple[str, ...]) -> None:
    assert not _ENGLISH_HELP.search(_help(*args))


@pytest.mark.parametrize("args", [("gold", "link")])
def test_stubs_state_they_are_unimplemented_and_wait_for_openkos(args: tuple[str, ...]) -> None:
    out = " ".join(_help(*args).split())
    assert "Sin implementar" in out
    assert "OpenKOS ~0.6.0" in out
    assert "código 2" in out


@pytest.mark.parametrize("args", [["gold", "link"]])
def test_stub_output_is_spanish_and_exits_with_code_2(args: list[str]) -> None:
    result = CliRunner().invoke(afg_cli.app, args)
    assert result.exit_code == 2
    assert "Sin implementar" in result.output
    assert "Not yet implemented" not in result.output
    assert "Requires" not in result.output


def test_report_help_names_only_what_it_regenerates() -> None:
    out = " ".join(_help("report").split())
    assert "bibliography_audit.csv" in out
    assert "reports/tables/*.csv" not in out


def test_report_output_is_spanish(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(afg_cli, "biblio_audit", lambda: None)
    result = CliRunner().invoke(afg_cli.app, ["report"])
    assert result.exit_code == 0, result.output
    assert "Regenerating" not in result.output
    assert "afg corpus inventory" in result.output


def test_biblio_audit_reports_the_written_path_in_spanish(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "bibliography_audit.csv"
    monkeypatch.setattr(afg_cli, "run_audit", lambda: object())
    monkeypatch.setattr(afg_cli, "render_biblio_table", lambda audit, console: None)
    monkeypatch.setattr(afg_cli, "write_biblio_csv", lambda audit: target)
    result = CliRunner().invoke(afg_cli.app, ["biblio", "audit"])
    assert result.exit_code == 0, result.output
    assert "Escrito:" in result.output
    assert "Wrote" not in result.output
