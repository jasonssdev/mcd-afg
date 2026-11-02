"""Tests for ``afg experiment a-relations``. No OpenKOS: the runner and the embedder are fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.relation import RelationType
from afg.evaluation.reference import ReferenceSet, SeriesFile
from afg.evaluation.relations import GoldPair
from afg.extraction.openkos.commands import CommandResult
from tests.openkos_findings import Row
from tests.relations_workspace import (
    ALPHA,
    BETA,
    reference_decision,
    text_similarity,
    write_transcripts,
    write_workspace,
)

A, B = "decisions/alpha", "decisions/beta"
RUN = "lote"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    write_transcripts(tmp_path / "transcripts")
    workspace = write_workspace(tmp_path / "ws" / RUN, findings=[Row((A, B), "refines")])
    reference = ReferenceSet(
        series_id="ES2015",
        decisions=(
            reference_decision("ES2015a.d01", "ES2015a", *ALPHA),
            reference_decision("ES2015b.d01", "ES2015b", *BETA),
        ),
    )
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    class Runner:
        def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
            calls.append((tuple(args), cwd))
            return CommandResult(0, "", "", 0.1)

    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", tmp_path / "transcripts")
    monkeypatch.setattr(afg_cli, "load_series_reference", lambda series, language="es": reference)
    monkeypatch.setattr(
        afg_cli,
        "load_gold_pairs",
        lambda series: (GoldPair("ES2015a.d01", "ES2015b.d01", RelationType.REFINA, True),),
    )
    monkeypatch.setattr(afg_cli, "gold_source", lambda series: SeriesFile(Path("x"), "single:gv"))
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: text_similarity)
    monkeypatch.setattr(afg_cli, "SubprocessRunner", Runner)
    return {"tmp": tmp_path, "workspace": workspace, "calls": calls}


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a-relations", *args])


def test_help_documents_the_options_in_spanish() -> None:
    out = " ".join(_run("--help").output.split())
    for option in ("--c2-extraction", "--series", "--run-revisions", "--tau"):
        assert option in out


def test_writes_the_report_under_the_run_folder(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN)

    assert result.exit_code == 0, result.output
    report = json.loads((env["tmp"] / "out" / RUN / "relaciones.json").read_text())
    assert report["run_name"] == RUN
    assert report["series"] == ["ES2015"]
    assert report["tau"] == 0.70
    assert report["pooled"]["existence_end_to_end"]["tp"] == 1
    assert [(e["series"], e["run"]) for e in report["entries"]] == [("ES2015", 0)]
    assert env["calls"] == []  # OpenKOS is not run without the flag
    assert report["reference_kinds"] == {
        "ES2015": {"decisions": "adjudicated", "relations": "single:gv"}
    }
    assert "relaciones.json" in result.output


def test_run_revisions_flag_runs_openkos_in_the_workspace(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN, "--run-revisions")

    assert result.exit_code == 0, result.output
    assert env["calls"] == [(("openkos", "revisions", "--auto", "--all"), env["workspace"])]


def test_series_option_filters_and_other_series_are_ignored(env: dict[str, Any]) -> None:
    write_workspace(env["tmp"] / "ws" / RUN, series="TS3009", findings=None)

    result = _run("--c2-extraction", RUN, "--series", "ES2015")

    assert result.exit_code == 0, result.output
    report = json.loads((env["tmp"] / "out" / RUN / "relaciones.json").read_text())
    assert report["series"] == ["ES2015"]


def test_evaluation_series_are_refused(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN, "--series", "ES2002")

    assert result.exit_code == 1
    assert "no es una serie de desarrollo" in result.output


def test_missing_workspace_run_is_reported(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", "no-such-run")

    assert result.exit_code == 1
    assert "no-such-run" in result.output


def test_unreadable_workspace_exits_with_one_but_still_writes_the_report(
    env: dict[str, Any],
) -> None:
    write_workspace(env["tmp"] / "ws" / RUN, run=1, findings=None)

    result = _run("--c2-extraction", RUN)

    assert result.exit_code == 1
    report = json.loads((env["tmp"] / "out" / RUN / "relaciones.json").read_text())
    assert report["n_errors"] == 1
    assert "run-1" in result.output


def test_prints_a_spanish_summary_without_markup_errors(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN)

    assert "recall" in result.output.lower()
    assert "ES2015" in result.output
