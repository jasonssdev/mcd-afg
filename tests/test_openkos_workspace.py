"""Tests for the series-level OpenKOS workspace orchestrator (no real OpenKOS)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.extraction.openkos.capabilities import MissingCapabilitiesError
from afg.extraction.openkos.commands import CommandResult
from afg.extraction.openkos.workspace import (
    IngestDriftError,
    IngestRefusedError,
    MeetingSource,
    OpenKosCommandError,
    OpenKosRunSettings,
    WorkspaceNotEmptyError,
    drop_config_keys,
    ensure_config_keys,
    read_config_value,
    redact_secrets,
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


def test_drop_config_keys_removes_active_lines_only() -> None:
    text = "model: a\nbase_url: http://x  # note\n# base_url: http://y\nseed: 1\n"
    out = drop_config_keys(text, ("base_url", "missing"))
    assert out.splitlines() == ["model: a", "# base_url: http://y", "seed: 1"]


def test_read_config_value_reads_the_active_value_without_comment() -> None:
    text = "backend: ollama  # default\n# seed: 9\ncontext_window: 12288\n"
    assert read_config_value(text, "backend") == "ollama"
    assert read_config_value(text, "context_window") == "12288"
    assert read_config_value(text, "seed") is None  # commented lines are not active


def test_stage_meeting_body_writes_the_body_without_front_matter(tmp_path: Path) -> None:
    src = tmp_path / "t"
    src.mkdir()
    (src / "ES2015a.md").write_text("---\nmeeting_id: ES2015a\n---\n\nPM: hi\n\nME: yo\n")
    staged = stage_meeting_body("ES2015a", src, tmp_path / "out")
    assert staged.read_text() == "PM: hi\n\nME: yo\n"
    assert staged.name == "ES2015a.md"


HOSTED_TEMPLATE = (
    CONFIG_TEMPLATE
    + "# backend: openai-compatible\n"
    + "# base_url: http://127.0.0.1:8080\n"
    + "# embedding_base_url: http://127.0.0.1:8081\n"
    + "# reasoning_effort: low\n"
    + "max_generation_tokens: 4096\n"
    + "# evidence_quote: true\n"
)

HOSTED = OpenKosRunSettings(
    executable="openkos",
    generative_model="gpt-5-mini",
    embedding_model="bge-m3",
    base_seed=None,
    temperature=None,
    backend="openai-compatible",
    base_url="https://api.example.test",
    embedding_base_url="http://127.0.0.1:11434",
    reasoning_effort="low",
    max_generation_tokens=8192,
    evidence_quote=False,
)


def test_hosted_settings_write_provider_keys_and_leave_seed_and_temperature_unset(
    tmp_path: Path,
) -> None:
    runner = FakeRunner(config_template=HOSTED_TEMPLATE)
    result = run_series_workspace(
        runner,
        series_id="ES2015",
        run=1,
        base_dir=tmp_path / "ws",
        settings=HOSTED,
        sources=_sources(tmp_path),
    )
    text = (tmp_path / "ws" / "ES2015" / "run-1" / "openkos.yaml").read_text()
    assert "backend: openai-compatible" in text
    assert "base_url: https://api.example.test" in text
    assert "embedding_base_url: http://127.0.0.1:11434" in text
    assert "reasoning_effort: low" in text
    assert "max_generation_tokens: 8192" in text
    assert "evidence_quote: false" in text
    assert "transcript_decisions: true" in text
    assert "# seed: 42" in text and "# temperature: 0.1" in text  # still commented: unset
    manifest = json.loads(result.manifest_path.read_text())
    settings = manifest["settings"]
    assert settings["backend"] == "openai-compatible"
    assert settings["base_url"] == "https://api.example.test"
    assert settings["reasoning_effort"] == "low"
    assert settings["seed"] is None and settings["temperature"] is None
    assert manifest["openkos_version"] == "0.6.0"


def test_hosted_settings_never_write_an_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENKOS_OPENAI_API_KEY", "sk-secret-value")
    runner = FakeRunner(config_template=HOSTED_TEMPLATE)
    result = run_series_workspace(
        runner,
        series_id="ES2015",
        run=0,
        base_dir=tmp_path / "ws",
        settings=HOSTED,
        sources=_sources(tmp_path),
    )
    written = (tmp_path / "ws" / "ES2015" / "run-0" / "openkos.yaml").read_text()
    assert "sk-secret-value" not in written
    assert "sk-secret-value" not in result.manifest_path.read_text()


def test_hosted_backend_requires_a_version_that_knows_the_key(tmp_path: Path) -> None:
    with pytest.raises(MissingCapabilitiesError):
        run_series_workspace(
            FakeRunner(),  # template without a backend key
            series_id="ES2015",
            run=0,
            base_dir=tmp_path / "ws",
            settings=HOSTED,
            sources=_sources(tmp_path),
        )


def test_baseline_settings_keep_the_manifest_block_without_provider_keys(tmp_path: Path) -> None:
    result = _run(tmp_path, FakeRunner())
    settings = json.loads(result.manifest_path.read_text())["settings"]
    assert set(settings) == {
        "generative_model",
        "embedding_model",
        "seed",
        "temperature",
        "transcript_decisions",
    }


def test_the_api_key_is_redacted_from_stderr_tails_and_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENKOS_OPENAI_API_KEY", "sk-secret-123")
    monkeypatch.setenv("OPENKOS_OPENAI_EMBEDDING_API_KEY", "sk-embed-456")

    class Echo(FakeRunner):
        def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
            result = super().run(args, cwd=cwd)
            if result.returncode:
                return CommandResult(
                    returncode=result.returncode,
                    stdout="",
                    stderr="bad key sk-secret-123 / sk-embed-456 end",
                    duration_s=0.01,
                )
            return result

    runner = Echo(ingest_codes={"ES2015b.md": [1]})
    with pytest.raises(IngestRefusedError) as caught:
        _run(tmp_path, runner)

    assert "sk-secret-123" not in str(caught.value)
    assert "sk-embed-456" not in str(caught.value)
    assert "***" in str(caught.value)
    text = (tmp_path / "ws" / "ES2015" / "run-0.manifest.json").read_text()
    assert "sk-secret-123" not in text and "sk-embed-456" not in text
    assert "***" in text


def test_redaction_ignores_an_empty_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENKOS_OPENAI_API_KEY", "")
    assert redact_secrets("plain text") == "plain text"


# --- token capture (OpenKOS 0.7.3) ----------------------------------------------------------


def _ingest_entries(manifest: dict) -> list[dict]:  # type: ignore[type-arg]
    return [
        c
        for c in manifest["commands"]
        if c["argv"][1] == "ingest" and not c["argv"][2].startswith("-")
    ]


def test_ingest_commands_store_the_parsed_token_record(tmp_path: Path) -> None:
    runner = FakeRunner(
        ingest_stdout={
            "ES2015a.md": "  tokens: 14 calls, prompt 52310, completion 9120, total 61430\n",
            "ES2015b.md": "  tokens: 12 of 14 calls reported, prompt 1, completion 2, total 3\n",
            "ES2015c.md": "  tokens: not reported by the backend (5 calls)\n",
        }
    )
    manifest = json.loads(_run(tmp_path, runner).manifest_path.read_text())
    entries = _ingest_entries(manifest)
    assert entries[0]["tokens"] == {
        "calls": 14,
        "reported_calls": 14,
        "prompt": 52310,
        "completion": 9120,
        "total": 61430,
    }
    assert entries[1]["tokens"]["reported_calls"] == 12
    assert entries[2]["tokens"] == {
        "calls": 5,
        "reported_calls": 0,
        "prompt": None,
        "completion": None,
        "total": None,
    }
    assert "tokens" not in entries[3]  # no line: no chat call, no key


def test_non_ingest_commands_and_full_stdout_are_never_stored(tmp_path: Path) -> None:
    runner = FakeRunner(
        ingest_stdout={
            "ES2015a.md": "secret body\n  tokens: 1 call, prompt 1, completion 1, total 2\n"
        }
    )
    text = _run(tmp_path, runner).manifest_path.read_text()
    assert "secret body" not in text
    manifest = json.loads(text)
    assert all(
        "tokens" not in c for c in manifest["commands"] if c not in _ingest_entries(manifest)
    )


def test_a_drift_retry_logs_one_token_record_per_ingest_command(tmp_path: Path) -> None:
    runner = FakeRunner(
        ingest_codes={"ES2015b.md": [3, 0]},
        ingest_stdout={"ES2015b.md": "  tokens: 2 calls, prompt 4, completion 2, total 6\n"},
    )
    manifest = json.loads(_run(tmp_path, runner).manifest_path.read_text())
    b_entries = [c for c in _ingest_entries(manifest) if c["argv"][2].endswith("ES2015b.md")]
    assert [e["returncode"] for e in b_entries] == [3, 0]
    assert all(e["tokens"]["total"] == 6 for e in b_entries)
