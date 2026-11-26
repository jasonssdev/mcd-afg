"""Tests for ``afg experiment a-hosted`` and the descriptive report of its runs (ADR 0026).

No OpenKOS and no API: the adapter, the runner and the Ollama probe are fakes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.experiments.hosted_extraction import API_KEY_ENV
from afg.extraction.openkos.workspace import OpenKosRunSettings
from tests.openkos_fake import FakeRunner
from tests.test_cli_experiment_a import SETTINGS, FakeAdapter, FakeProbe


class RecordingFactory:
    """Stands in for ``make_hosted_adapter``: keeps the settings it was asked to wire."""

    def __init__(self, tmp_path: Path) -> None:
        self.adapter = FakeAdapter(tmp_path / "ws")
        self.settings: list[OpenKosRunSettings] = []

    def __call__(self, base_dir: Path, settings: OpenKosRunSettings) -> FakeAdapter:
        self.settings.append(settings)
        return self.adapter


class ExtensionProbe(FakeProbe):
    """The local server of the extension: Ollama 0.40.16 (ADR 0026, fourth amendment)."""

    def ollama_version(self) -> str | None:
        return "0.40.16"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> RecordingFactory:
    factory = RecordingFactory(tmp_path)
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "make_hosted_adapter", factory)
    monkeypatch.setattr(afg_cli, "openkos_run_settings", lambda: SETTINGS)
    monkeypatch.setattr(afg_cli, "current_git_commit", lambda: "abc123")
    monkeypatch.setattr(
        afg_cli,
        "make_provenance_probe",
        lambda: ExtensionProbe({"qwen3:8b": "d-gen", "bge-m3:latest": "d-emb"}),
    )
    monkeypatch.setattr(
        afg_cli, "make_hosted_runner", lambda: FakeRunner(version_output="openkos 0.7.3\n")
    )
    monkeypatch.setattr(afg_cli, "_executable_exists", lambda _path: True)
    monkeypatch.setenv(API_KEY_ENV, "sk-test-never-printed")
    return factory


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a-hosted", *args])


def test_pilot_runs_one_series_and_one_repetition_under_the_pilot_name(
    tmp_path: Path, fake: RecordingFactory
) -> None:
    result = _run("--model", "openai-small", "--pilot")

    assert result.exit_code == 0, result.output
    assert fake.adapter.calls == [("ES2002", 0)]
    run_dir = tmp_path / "out" / "experimento-a-piloto-openai-small"
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["kind"] == "batch"
    assert manifest["adr"] == "0026"
    assert manifest["extension"] == "hosted"
    assert manifest["pilot"] is True
    assert manifest["model_label"] == "openai-small"
    assert manifest["provider"] == "openai"
    assert manifest["partition"] == "evaluation"
    assert manifest["freeze"] is None
    assert manifest["git_commit"] == "abc123"
    assert manifest["openkos"]["generative_model"] == "gpt-5-mini"
    assert manifest["openkos"]["backend"] == "openai-compatible"
    assert manifest["openkos"]["base_url"] == "https://api.openai.com"
    assert manifest["openkos"]["reasoning_effort"] == "low"
    assert manifest["openkos"]["seed"] is None
    assert manifest["openkos"]["temperature"] is None
    assert manifest["openkos"]["required_version"] == "0.7.3"
    assert all("seconds" in pair for pair in manifest["pairs"].values())


def test_the_api_key_never_reaches_the_output_or_the_manifest(
    tmp_path: Path, fake: RecordingFactory
) -> None:
    result = _run("--model", "openai-small", "--pilot")

    assert "sk-test-never-printed" not in result.output
    run_dir = tmp_path / "out" / "experimento-a-piloto-openai-small"
    assert "sk-test-never-printed" not in (run_dir / "manifest.json").read_text()


def test_full_run_covers_the_eleven_evaluation_series_three_runs_each(
    fake: RecordingFactory,
) -> None:
    result = _run("--model", "google-large")

    assert result.exit_code == 0, result.output
    assert len(fake.adapter.calls) == 33
    assert {s for s, _ in fake.adapter.calls} >= {"ES2002", "ES2008"}
    assert fake.settings[0].generative_model == "gemini-4-argon"
    assert fake.settings[0].base_seed is None


def test_series_and_runs_can_be_narrowed(tmp_path: Path, fake: RecordingFactory) -> None:
    result = _run(
        "--model", "openai-large", "--series", "ES2008", "--series", "ES2002", "--runs", "2"
    )

    assert result.exit_code == 0, result.output
    assert fake.adapter.calls == [("ES2008", 0), ("ES2008", 1), ("ES2002", 0), ("ES2002", 1)]
    assert (tmp_path / "out" / "experimento-a-hosted-openai-large").is_dir()


def test_repeating_the_command_resumes_the_batch(tmp_path: Path, fake: RecordingFactory) -> None:
    assert _run("--model", "openai-small", "--series", "ES2002", "--runs", "2").exit_code == 0
    first = list(fake.adapter.calls)

    again = _run("--model", "openai-small", "--series", "ES2002", "--runs", "2")

    assert again.exit_code == 0, again.output
    assert fake.adapter.calls == first  # every pair was already complete


def test_development_series_are_refused_before_any_work(
    tmp_path: Path, fake: RecordingFactory
) -> None:
    result = _run("--model", "openai-small", "--series", "ES2015")

    assert result.exit_code == 1
    assert fake.adapter.calls == []
    assert not (tmp_path / "out").exists()


def test_a_missing_key_stops_before_creating_anything(
    tmp_path: Path, fake: RecordingFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(API_KEY_ENV)

    result = _run("--model", "openai-small", "--pilot")

    assert result.exit_code == 1
    assert API_KEY_ENV in " ".join(result.output.split())
    assert fake.adapter.calls == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("flag", [["--model", "openai-small", "--pilot"], ["--local-baseline"]])
def test_another_ollama_version_stops_every_mode_before_any_call(
    tmp_path: Path, fake: RecordingFactory, monkeypatch: pytest.MonkeyPatch, flag: list[str]
) -> None:
    monkeypatch.setattr(
        afg_cli, "make_provenance_probe", lambda: FakeProbe({"qwen3:8b": "d", "bge-m3:latest": "e"})
    )  # reports Ollama 0.9.9

    result = _run(*flag)

    assert result.exit_code == 1
    assert "0.40.16" in " ".join(result.output.split())
    assert fake.adapter.calls == []
    assert not (tmp_path / "out").exists()


def test_the_manifest_records_the_ollama_version(tmp_path: Path, fake: RecordingFactory) -> None:
    assert _run("--model", "openai-small", "--pilot").exit_code == 0
    manifest = json.loads(
        (tmp_path / "out" / "experimento-a-piloto-openai-small" / "manifest.json").read_text()
    )
    assert manifest["ollama_version"] == "0.40.16"


def test_model_xor_bridge_is_required(fake: RecordingFactory) -> None:
    assert _run().exit_code == 2
    assert _run("--model", "openai-small", "--bridge").exit_code == 2
    assert _run("--model", "no-such-label").exit_code == 2
    assert fake.adapter.calls == []


def test_the_bridge_is_historical_and_is_not_rerun_on_the_current_version(
    fake: RecordingFactory,
) -> None:
    result = _run("--bridge")

    assert result.exit_code == 2
    assert "0.7.2" in result.output
    assert fake.adapter.calls == []


def test_bridge_refuses_series_and_runs_overrides(fake: RecordingFactory) -> None:
    assert _run("--bridge", "--series", "ES2008").exit_code == 2
    assert _run("--bridge", "--runs", "3").exit_code == 2
    assert _run("--bridge", "--pilot").exit_code == 2


def test_local_baseline_runs_the_bridge_settings_on_every_evaluation_series(
    tmp_path: Path, fake: RecordingFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(API_KEY_ENV)

    result = _run("--local-baseline")

    assert result.exit_code == 0, result.output
    assert len(fake.adapter.calls) == 33
    used = fake.settings[0]
    assert used.generative_model == "qwen3:8b"
    assert (used.base_seed, used.temperature, used.backend) == (42, 0.1, "ollama")
    manifest = json.loads(
        (tmp_path / "out" / "experimento-a-base-0-7-3" / "manifest.json").read_text()
    )
    assert manifest["extension"] == "hosted"
    assert manifest["local_baseline"] is True
    assert manifest["bridge"] is False
    assert manifest["partition"] == "evaluation"
    assert manifest["runs"] == 3


def test_local_baseline_resumes_and_refuses_overrides_and_other_modes(
    fake: RecordingFactory,
) -> None:
    assert _run("--local-baseline").exit_code == 0
    first = list(fake.adapter.calls)
    assert _run("--local-baseline").exit_code == 0
    assert fake.adapter.calls == first  # resumed: nothing re-run

    assert _run("--local-baseline", "--series", "ES2008").exit_code == 2
    assert _run("--local-baseline", "--runs", "2").exit_code == 2
    assert _run("--local-baseline", "--pilot").exit_code == 2
    assert _run("--local-baseline", "--bridge").exit_code == 2
    assert _run("--local-baseline", "--model", "openai-small").exit_code == 2


def test_it_never_touches_the_frozen_configuration(fake: RecordingFactory) -> None:
    before = (Path("config/experiments.toml").read_bytes(), Path("config/freeze.json").read_bytes())
    _run("--model", "openai-small", "--pilot")
    after = (Path("config/experiments.toml").read_bytes(), Path("config/freeze.json").read_bytes())
    assert before == after


# --- the descriptive report of a hosted run ---------------------------------------------------


def _hosted_report_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from afg.evaluation.reference import ReferenceSet
    from tests.relations_workspace import (
        ALPHA,
        reference_decision,
        text_similarity,
        write_transcripts,
    )
    from tests.test_cli_experiment_a_report import RUN, _record  # reuse the record builder

    run_dir = tmp_path / "out" / RUN
    run_dir.mkdir(parents=True)
    manifest = {
        "extension": "hosted",
        "adr": "0026",
        "freeze": None,
        "openkos": {"seed": None, "generative_model": "gpt-5-mini"},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest))
    (run_dir / "extracciones.jsonl").write_text(_record(0, [("a", ALPHA)]) + "\n")
    write_transcripts(tmp_path / "transcripts")
    reference = ReferenceSet(
        series_id="ES2015",
        decisions=(reference_decision("ES2015a.d01", "ES2015a", *ALPHA),),
        source_kind="adjudicated",
    )
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", tmp_path / "transcripts")
    monkeypatch.setattr(afg_cli, "load_series_reference", lambda s, language="es": reference)
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: text_similarity)
    monkeypatch.setattr(afg_cli, "configured_partition_of", lambda: lambda series: "evaluation")
    return run_dir


def _report(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a-report", *args])


def test_descriptive_report_of_a_hosted_run_never_writes_informe_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _hosted_report_env(tmp_path, monkeypatch)

    result = _report("--c2-extraction", "lote", "--descriptive")

    assert result.exit_code == 0, result.output
    assert not (run_dir / "informe.json").exists()
    report: dict[str, Any] = json.loads((run_dir / "informe-descriptivo.json").read_text())
    assert report["reportable"] is False
    assert report["partition"] == "evaluation"


def test_a_hosted_run_is_refused_without_the_descriptive_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _hosted_report_env(tmp_path, monkeypatch)

    result = _report("--c2-extraction", "lote")

    assert result.exit_code == 1
    assert "--descriptive" in result.output
    assert not (run_dir / "informe.json").exists()


# --- a-hosted-compare ---------------------------------------------------------------------------


def test_compare_writes_json_and_csv_and_reports_missing_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.relations_workspace import reference_decision, text_similarity
    from tests.test_hosted_comparison import _all, _meetings, _reference_of, _write_run

    _write_run(tmp_path, "experimento-a-formal", _all({"ES2015": _meetings("ES2015", "a")}))
    _write_run(
        tmp_path, "experimento-a-hosted-openai-small", _all({"ES2015": _meetings("ES2015", "abcd")})
    )
    del reference_decision
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: text_similarity)
    monkeypatch.setattr(
        afg_cli,
        "load_series_reference",
        lambda series, language="es": type("R", (), {"decisions": _reference_of(series)})(),
    )

    result = CliRunner().invoke(
        afg_cli.app,
        ["experiment", "a-hosted-compare", "--models", "openai-small", "--models", "google-large"],
    )

    assert result.exit_code == 0, result.output
    out = tmp_path / "out" / "hosted-comparison"
    payload = json.loads((out / "comparacion.json").read_text())
    assert {c["label"]: c["status"] for c in payload["candidates"]} == {
        "openai-small": "ok",
        "google-large": "sin corrida",
    }
    assert (out / "comparacion.csv").is_file()
    assert "sin corrida" in result.output
    assert "openai-small" in result.output


def test_compare_with_an_unknown_label_exits_with_a_message(tmp_path: Path) -> None:
    result = CliRunner().invoke(afg_cli.app, ["experiment", "a-hosted-compare", "--models", "nope"])
    assert result.exit_code == 2


def _compare_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.relations_workspace import text_similarity
    from tests.test_hosted_comparison import _all, _meetings, _reference_of, _write_run

    _write_run(tmp_path, "experimento-a-formal", _all({"ES2015": _meetings("ES2015", "a")}))
    _write_run(
        tmp_path, "experimento-a-hosted-openai-small", _all({"ES2015": _meetings("ES2015", "abcd")})
    )
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", tmp_path / "ws")
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: text_similarity)
    monkeypatch.setattr(
        afg_cli,
        "load_series_reference",
        lambda series, language="es": type("R", (), {"decisions": _reference_of(series)})(),
    )


def test_compare_reports_both_baselines_by_default_and_the_missing_local_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compare_env(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        afg_cli.app, ["experiment", "a-hosted-compare", "--models", "openai-small"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads((tmp_path / "out" / "hosted-comparison" / "comparacion.json").read_text())
    assert payload["baseline"] == "both"
    assert payload["candidates"][0]["vs_local"]["status"] == "sin corrida"
    assert "formal" in result.output
    assert "local" in result.output


def test_compare_baseline_option_selects_one_baseline_and_rejects_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compare_env(tmp_path, monkeypatch)

    ok = CliRunner().invoke(
        afg_cli.app,
        ["experiment", "a-hosted-compare", "--models", "openai-small", "--baseline", "formal"],
    )
    bad = CliRunner().invoke(afg_cli.app, ["experiment", "a-hosted-compare", "--baseline", "x"])

    assert ok.exit_code == 0, ok.output
    payload = json.loads((tmp_path / "out" / "hosted-comparison" / "comparacion.json").read_text())
    assert "vs_local" not in payload["candidates"][0]
    assert bad.exit_code == 2
