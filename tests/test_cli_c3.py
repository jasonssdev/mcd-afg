"""Tests for ``afg c3 build``. No OpenKOS: the runner is a fake."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.decision import EvidenceSpan
from afg.evaluation.reference import ReferenceDecision, ReferenceSet
from afg.extraction.openkos.gold_bundle import GoldRelation
from tests.openkos_bundle import decision_file, write_bundle_file, write_meeting
from tests.openkos_fake import FakeRunner

C2_RUN = "lote"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    transcripts = tmp_path / "transcripts"
    write_meeting(transcripts, "ES2015a", [("ME", "we use the kinetic battery", ("a.1",))])
    c2_base = tmp_path / "c2"
    for run in (0, 1):
        workspace = c2_base / C2_RUN / "ES2015" / f"run-{run}"
        (workspace / "bundle").mkdir(parents=True)
        (workspace / "openkos.yaml").write_text("seed: 42\n", encoding="utf-8")
        write_bundle_file(
            workspace / "bundle",
            "decisions",
            "old",
            decision_file(title="Old", subject="o", value="v", quotes=[("es2015a", "x")]),
        )
    reference = ReferenceSet(
        series_id="ES2015",
        decisions=(
            ReferenceDecision(
                decision_id="ES2015a.d01",
                series_id="ES2015",
                meeting_id="ES2015a",
                decision_object="battery",
                content="use the kinetic battery",
                evidence=EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.1",)),
                evidence_method="sentence_id",
                role=None,
            ),
        ),
    )
    runner = FakeRunner()
    c3_base = tmp_path / "c3"
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", c2_base)
    monkeypatch.setattr(afg_cli, "OPENKOS_C3_WORKSPACES_DIR", c3_base)
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", transcripts)
    monkeypatch.setattr(afg_cli, "SubprocessRunner", lambda: runner)
    monkeypatch.setattr(afg_cli, "load_series_reference", lambda series, language: reference)
    monkeypatch.setattr(
        afg_cli, "load_gold_relations", lambda series: (GoldRelation("a", "b", "refina"),)
    )
    return {"c3": c3_base, "runner": runner, "c2": c2_base}


def _run(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["c3", "build", *args])


def _out(result: Any) -> str:
    return " ".join(result.output.split())


def test_help_documents_the_options() -> None:
    out = _out(_run("--help"))
    for option in ("--c2-extraction", "--series", "--runs", "--overwrite"):
        assert option in out


def test_builds_one_workspace_per_series_and_run(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", C2_RUN, "--series", "ES2015", "--runs", "2")

    assert result.exit_code == 0, result.output
    for run in (0, 1):
        workspace = env["c3"] / C2_RUN / "ES2015" / f"run-{run}"
        assert (workspace / "bundle" / "decisions" / "es2015a-d01.md").is_file()
        assert not (workspace / "bundle" / "decisions" / "old.md").exists()
        manifest = json.loads((workspace / "c3-manifest.json").read_text(encoding="utf-8"))
        assert manifest["run"] == run and manifest["decisions_written"] == 1
    reindexed = [cwd for argv, cwd in env["runner"].calls if argv[1:2] == ("reindex",)]
    assert len(reindexed) == 2
    assert "ES2015 run-0: 1 decisión" in _out(result)


def test_runs_default_to_the_configured_budget(env: dict[str, Any]) -> None:
    (env["c2"] / C2_RUN / "ES2015" / "run-2" / "bundle").mkdir(parents=True)
    result = _run("--c2-extraction", C2_RUN, "--series", "ES2015")

    assert result.exit_code == 0, result.output  # runs_per_config = 3
    assert sorted(p.name for p in (env["c3"] / C2_RUN / "ES2015").iterdir()) == [
        "run-0",
        "run-1",
        "run-2",
    ]


def test_evaluation_series_are_refused_before_anything_happens(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", "tmp-gate", "--series", "ES2008")

    assert result.exit_code == 1
    assert "ES2008 no es una serie de desarrollo" in _out(result)
    assert not env["c3"].exists()
    assert env["runner"].calls == []


def test_missing_c2_workspace_stops_before_building_any(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", C2_RUN, "--series", "ES2015", "--runs", "3")

    assert result.exit_code == 1
    assert "run-2" in _out(result) and "afg experiment a" in _out(result)
    assert not env["c3"].exists()


def test_existing_c3_workspace_needs_overwrite(env: dict[str, Any]) -> None:
    args = ("--c2-extraction", C2_RUN, "--series", "ES2015", "--runs", "1")
    assert _run(*args).exit_code == 0
    marker = env["c3"] / C2_RUN / "ES2015" / "run-0" / "marker"
    marker.write_text("x", encoding="utf-8")

    refused = _run(*args)
    assert refused.exit_code == 1 and "--overwrite" in _out(refused)
    assert marker.exists()

    assert _run(*args, "--overwrite").exit_code == 0
    assert not marker.exists()


def test_a_series_without_gold_is_reported(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(series: str, language: str) -> ReferenceSet:
        raise FileNotFoundError(f"Adjudicated reference not found for {series}.")

    monkeypatch.setattr(afg_cli, "load_series_reference", missing)
    result = _run("--c2-extraction", C2_RUN, "--series", "ES2015", "--runs", "1")

    assert result.exit_code == 1 and "Adjudicated reference not found" in _out(result)
    assert not env["c3"].exists()


def test_dropped_decisions_are_listed_in_the_summary(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    bare = ReferenceSet(
        series_id="ES2015",
        decisions=(
            ReferenceDecision(
                decision_id="ES2015a.d09",
                series_id="ES2015",
                meeting_id="ES2015a",
                decision_object="o",
                content="c",
                evidence=None,
                evidence_method="none",
                role=None,
            ),
        ),
    )
    monkeypatch.setattr(afg_cli, "load_series_reference", lambda series, language: bare)
    result = _run("--c2-extraction", C2_RUN, "--series", "ES2015", "--runs", "1")

    assert result.exit_code == 0, result.output
    assert "descartada" in _out(result) and "ES2015a.d09" in _out(result)
