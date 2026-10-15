"""Tests for the series-level OpenKOS workspace orchestrator (no real OpenKOS)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.extraction.openkos.capabilities import MissingCapabilitiesError
from afg.extraction.openkos.workspace import (
    IngestDriftError,
    IngestRefusedError,
    MeetingSource,
    OpenKosCommandError,
    OpenKosRunSettings,
    WorkspaceNotEmptyError,
    ensure_config_keys,
    run_series_workspace,
    stage_meeting_body,
)
from tests.openkos_fake import CONFIG_TEMPLATE, FakeRunner

SETTINGS = OpenKosRunSettings(
    executable="openkos",
    generative_model="qwen3:8b",
    embedding_model="bge-m3",
    base_seed=42,
    temperature=0.1,
)


def _sources(tmp_path: Path, dates: bool = False) -> list[MeetingSource]:
    out: list[MeetingSource] = []
    for letter, day in zip(
        "abcd", ("2004-11-23", "2004-11-24", "2004-11-25", "2004-11-26"), strict=True
    ):
        path = tmp_path / "sources" / f"ES2015{letter}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(f"PM: hello {letter}\n", encoding="utf-8")
        out.append(MeetingSource(f"ES2015{letter}", path, day if dates else None))
    return out


def _run(tmp_path: Path, runner: FakeRunner, run: int = 0, **kw):  # type: ignore[no-untyped-def]
    return run_series_workspace(
        runner,
        series_id="ES2015",
        run=run,
        base_dir=tmp_path / "ws",
        settings=SETTINGS,
        sources=kw.pop("sources", _sources(tmp_path)),
        **kw,
    )


def test_happy_path_creates_workspace_and_ingests_in_order(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = _run(tmp_path, runner)
    workspace = tmp_path / "ws" / "ES2015" / "run-0"
    assert result.workspace == workspace
    subs = runner.subcommands()
    assert subs[0:3] == [("--version",), ("ingest", "--help"), ("query", "--help")]
    assert subs[3] == ("init", "--model", "qwen3:8b", "--embedding-model", "bge-m3")
    ingested = [Path(s[1]).name for s in subs if s[0] == "ingest" and s[1] != "--help"]
    assert ingested == ["ES2015a.md", "ES2015b.md", "ES2015c.md", "ES2015d.md"]
    assert all("--auto" in s for s in subs if s[0] == "ingest" and s[1] != "--help")
    assert all(
        cwd == workspace
        for argv, cwd in runner.calls
        if argv[1] in ("init", "ingest") and argv[2:3] != ("--help",)
    )


def test_config_receives_decision_pass_seed_temperature_and_no_review(tmp_path: Path) -> None:
    _run(tmp_path, FakeRunner(), run=2)
    text = (tmp_path / "ws" / "ES2015" / "run-2" / "openkos.yaml").read_text()
    assert "transcript_decisions: true" in text
    assert "seed: 44" in text  # base seed + run, as in the Experiment B runner
    assert "temperature: 0.1" in text
    assert "review: false" in text
    assert "review: true" not in text
    assert "# seed" not in text and "# temperature" not in text


def test_event_date_is_passed_only_when_known(tmp_path: Path) -> None:
    runner = FakeRunner()
    _run(tmp_path, runner)
    assert not any("--event-date" in s for s in runner.subcommands())
    runner2 = FakeRunner()
    _run(tmp_path, runner2, run=1, sources=_sources(tmp_path, dates=True))
    first = next(s for s in runner2.subcommands() if s[0] == "ingest" and "--auto" in s)
    assert first[-2:] == ("--event-date", "2004-11-23")


def test_event_date_without_support_fails_before_creating_anything(tmp_path: Path) -> None:
    runner = FakeRunner(ingest_help="--auto only\n")
    with pytest.raises(MissingCapabilitiesError):
        _run(tmp_path, runner, sources=_sources(tmp_path, dates=True))
    assert not (tmp_path / "ws" / "ES2015" / "run-0").exists()


def test_drift_is_retried_once(tmp_path: Path) -> None:
    runner = FakeRunner(ingest_codes={"ES2015b.md": [3, 0]})
    result = _run(tmp_path, runner)
    attempts = [s for s in runner.subcommands() if s[:1] == ("ingest",) and s[1].endswith("b.md")]
    assert len(attempts) == 2
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["status"] == "ok"
    assert [
        c["returncode"] for c in manifest["commands"] if "ES2015b.md" in " ".join(c["argv"])
    ] == [3, 0]


def test_second_drift_fails(tmp_path: Path) -> None:
    runner = FakeRunner(ingest_codes={"ES2015b.md": [3, 3]})
    with pytest.raises(IngestDriftError):
        _run(tmp_path, runner)
    manifest = json.loads((tmp_path / "ws" / "ES2015" / "run-0.manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failed_meeting"] == "ES2015b"


def test_refusal_is_not_retried_and_names_the_meeting(tmp_path: Path) -> None:
    runner = FakeRunner(ingest_codes={"ES2015c.md": [1]})
    with pytest.raises(IngestRefusedError, match="ES2015c"):
        _run(tmp_path, runner)
    assert (
        len([s for s in runner.subcommands() if s[:1] == ("ingest",) and s[1].endswith("c.md")])
        == 1
    )
    assert not any(s[:1] == ("ingest",) and s[1].endswith("d.md") for s in runner.subcommands())


def test_init_failure_is_a_command_error(tmp_path: Path) -> None:
    with pytest.raises(OpenKosCommandError, match="init"):
        _run(tmp_path, FakeRunner(init_code=2))


def test_refuses_a_non_empty_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws" / "ES2015" / "run-0"
    workspace.mkdir(parents=True)
    (workspace / "leftover.txt").write_text("x")
    runner = FakeRunner()
    with pytest.raises(WorkspaceNotEmptyError):
        _run(tmp_path, runner)
    assert not any(s[:1] == ("init",) for s in runner.subcommands())


def test_an_empty_existing_workspace_dir_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "ws" / "ES2015" / "run-0").mkdir(parents=True)
    _run(tmp_path, FakeRunner())


def test_missing_decision_pass_key_in_the_generated_config_fails_before_ingest(
    tmp_path: Path,
) -> None:
    runner = FakeRunner(config_template="model: qwen3:8b\nreview: true\n")
    with pytest.raises(MissingCapabilitiesError) as excinfo:
        _run(tmp_path, runner)
    assert "transcript_decisions" in excinfo.value.missing
    assert not any(s[:1] == ("ingest",) and s[1] != "--help" for s in runner.subcommands())


def test_manifest_records_version_settings_commands_and_durations(tmp_path: Path) -> None:
    result = _run(tmp_path, FakeRunner(), run=1)
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["openkos_version"] == "0.6.0"
    assert manifest["executable"] == "openkos"
    assert manifest["series_id"] == "ES2015" and manifest["run"] == 1
    assert manifest["settings"] == {
        "generative_model": "qwen3:8b",
        "embedding_model": "bge-m3",
        "seed": 43,
        "temperature": 0.1,
        "transcript_decisions": True,
    }
    assert manifest["meetings"] == ["ES2015a", "ES2015b", "ES2015c", "ES2015d"]
    assert manifest["event_dates_passed"] is False
    assert manifest["commands"][0]["argv"] == ["openkos", "--version"]
    assert all({"argv", "returncode", "duration_s"} <= set(c) for c in manifest["commands"])
    assert result.manifest_path == tmp_path / "ws" / "ES2015" / "run-1.manifest.json"


def test_ensure_config_keys_replaces_uncomments_and_appends() -> None:
    text = ensure_config_keys(CONFIG_TEMPLATE, {"seed": "7", "review": "false", "extra_key": "1"})
    lines = text.splitlines()
    assert "seed: 7" in lines
    assert "review: false" in lines and "review: true" not in lines
    assert "# seed: 42" not in lines
    assert lines[-1] == "extra_key: 1"
    assert "# temperature: 0.1" in lines  # untouched


def test_stage_meeting_body_writes_the_body_without_front_matter(tmp_path: Path) -> None:
    src = tmp_path / "t"
    src.mkdir()
    (src / "ES2015a.md").write_text("---\nmeeting_id: ES2015a\n---\n\nPM: hi\n\nME: yo\n")
    staged = stage_meeting_body("ES2015a", src, tmp_path / "out")
    assert staged.read_text() == "PM: hi\n\nME: yo\n"
    assert staged.name == "ES2015a.md"
