"""Tests for the runtime settings defaults (``afg.shared.config.Settings``)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.shared.config import Settings, load_experiments_config


def test_judge_model_defaults_to_the_configured_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AFG_JUDGE_MODEL", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.judge_model == load_experiments_config()["judge"]["model"]


def test_blank_judge_model_falls_back_to_the_configured_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ``AFG_JUDGE_MODEL=`` line left blank in ``.env`` must not unset the judge."""
    monkeypatch.setenv("AFG_JUDGE_MODEL", "")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.judge_model == load_experiments_config()["judge"]["model"]


def test_judge_model_can_still_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFG_JUDGE_MODEL", "mistral-small3.2:24b")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.judge_model == "mistral-small3.2:24b"


def test_openkos_executable_defaults_to_the_path_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AFG_OPENKOS_EXECUTABLE", raising=False)
    assert Settings(_env_file=None).openkos_executable == "openkos"  # type: ignore[call-arg]


def test_openkos_executable_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFG_OPENKOS_EXECUTABLE", "/opt/openkos-0.6/bin/openkos")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.openkos_executable == "/opt/openkos-0.6/bin/openkos"


def test_generative_and_embedding_models_default_to_the_shared_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AFG_GENERATIVE_MODEL", raising=False)
    monkeypatch.delenv("AFG_EMBEDDING_MODEL", raising=False)
    monkeypatch.setattr(
        "afg.shared.config.load_experiments_config",
        lambda: {
            "judge": {"model": "j"},
            "shared_budget": {"generative_model": "gen-from-toml", "embedding_model": "emb-toml"},
        },
    )
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.generative_model == "gen-from-toml"
    assert settings.embedding_model == "emb-toml"


def test_real_config_models_match_the_shared_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AFG_GENERATIVE_MODEL", raising=False)
    monkeypatch.delenv("AFG_EMBEDDING_MODEL", raising=False)
    budget = load_experiments_config()["shared_budget"]
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.generative_model == budget["generative_model"]
    assert settings.embedding_model == budget["embedding_model"]


def test_generative_and_embedding_models_can_still_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AFG_GENERATIVE_MODEL", "other-gen")
    monkeypatch.setenv("AFG_EMBEDDING_MODEL", "other-emb")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (settings.generative_model, settings.embedding_model) == ("other-gen", "other-emb")


def test_ollama_host_reads_the_afg_variable_before_the_ollama_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "plain-ollama:1")
    monkeypatch.setenv("AFG_OLLAMA_HOST", "afg-host:2")
    assert Settings(_env_file=None).ollama_host == "afg-host:2"  # type: ignore[call-arg]


def test_ollama_host_falls_back_to_the_ollama_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AFG_OLLAMA_HOST", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "plain-ollama:1")
    assert Settings(_env_file=None).ollama_host == "plain-ollama:1"  # type: ignore[call-arg]


def test_settings_have_no_dead_fields() -> None:
    assert "openkos_workspace" not in Settings.model_fields


def test_log_level_setting_drives_the_cli_when_no_flag_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []
    monkeypatch.setattr(afg_cli, "configure_logging", seen.append)
    monkeypatch.setattr(afg_cli, "ensure_dirs", lambda: None)
    monkeypatch.setenv("AFG_LOG_LEVEL", "DEBUG")
    result = CliRunner().invoke(afg_cli.app, ["skills", "--help"])
    assert result.exit_code == 0, result.output
    result = CliRunner().invoke(afg_cli.app, ["--log-level", "ERROR", "skills", "--help"])
    assert seen == ["DEBUG", "ERROR"]
