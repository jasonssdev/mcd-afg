"""``--help`` for annotators: Spanish, with their commands apart from the maintainer's."""

from __future__ import annotations

import re

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
