"""Tests for the hosted-extractor configuration and preflight (ADR 0026); no model calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.experiments.hosted_extraction import (
    API_KEY_ENV,
    EXECUTABLE_ENV,
    HOSTED_CONFIG_PATH,
    HostedConfigError,
    HostedPreflightError,
    bridge_run_settings,
    hosted_run_name,
    hosted_run_settings,
    load_hosted_config,
    preflight,
    resolve_executable,
)
from afg.extraction.openkos.workspace import OpenKosRunSettings
from tests.openkos_fake import FakeRunner

CONFIG = load_hosted_config()
BASE = OpenKosRunSettings("openkos", "qwen3:8b", "bge-m3", base_seed=42, temperature=0.1)
OLLAMA_OK = {"bge-m3:latest": "d1", "qwen3:8b": "d2"}


def test_the_shipped_config_lists_six_models_and_the_adr_comparison_settings() -> None:
    assert HOSTED_CONFIG_PATH.name == "hosted_extraction.toml"
    assert list(CONFIG.models) == [
        "openai-small",
        "openai-large",
        "anthropic-small",
        "anthropic-large",
        "google-small",
        "google-large",
    ]
    assert CONFIG.required_version == "0.7.2"
    assert CONFIG.runs_per_model == 3
    assert CONFIG.comparison.bootstrap_resamples == 10000
    assert CONFIG.comparison.bootstrap_seed == 42
    assert CONFIG.comparison.family_alpha == 0.05
    assert CONFIG.comparison.precision_margin == -0.05
    assert CONFIG.bridge.series == ("ES2002",)
    assert CONFIG.baseline_run_name == "experimento-a-formal"
    assert CONFIG.models["google-large"].base_url.startswith("https://generativelanguage")


def test_run_names_for_full_runs_and_pilots() -> None:
    assert hosted_run_name("openai-small") == "experimento-a-hosted-openai-small"
    assert hosted_run_name("openai-small", pilot=True) == "experimento-a-piloto-openai-small"


def test_hosted_settings_send_no_seed_or_temperature_and_pin_the_shared_keys() -> None:
    settings = hosted_run_settings(CONFIG, "anthropic-large", executable="/x/openkos")
    assert settings.executable == "/x/openkos"
    assert settings.generative_model == "claude-sonnet-5-5"
    assert settings.embedding_model == "bge-m3"
    assert settings.base_seed is None and settings.temperature is None
    assert settings.backend == "openai-compatible"
    assert settings.base_url == "https://api.anthropic.com"
    assert settings.embedding_base_url == "http://127.0.0.1:11434"
    assert settings.reasoning_effort == "low"
    assert settings.max_generation_tokens == 8192
    assert settings.evidence_quote is False


def test_an_unknown_label_is_refused_naming_the_valid_ones() -> None:
    with pytest.raises(HostedConfigError, match="openai-small"):
        hosted_run_settings(CONFIG, "nope", executable="x")


def test_bridge_keeps_the_baseline_settings_on_the_ollama_backend() -> None:
    settings = bridge_run_settings(BASE, executable="/x/openkos")
    assert settings.executable == "/x/openkos"
    assert settings.generative_model == "qwen3:8b"
    assert settings.base_seed == 42 and settings.temperature == 0.1
    assert settings.backend == "ollama"
    assert settings.reasoning_effort is None and settings.base_url is None


def test_executable_override_wins_and_relative_paths_resolve_from_the_project_root() -> None:
    assert resolve_executable(CONFIG, {EXECUTABLE_ENV: "/o/openkos"}) == "/o/openkos"
    default = Path(resolve_executable(CONFIG, {}))
    assert default.is_absolute() and default.parts[-4:] == (
        "interim",
        "openkos-0.7.2",
        "bin",
        "openkos",
    )


def _runner(version: str = "openkos 0.7.2\n") -> FakeRunner:
    return FakeRunner(version_output=version)


def test_preflight_passes_for_a_hosted_label_with_key_version_and_embeddings() -> None:
    preflight(
        CONFIG,
        label="openai-small",
        executable="openkos",
        runner=_runner(),
        env={API_KEY_ENV: "sk-x"},
        ollama_models=lambda: OLLAMA_OK,
        executable_exists=lambda _path: True,
    )


def test_preflight_names_the_missing_key_without_any_value() -> None:
    with pytest.raises(HostedPreflightError) as error:
        preflight(
            CONFIG,
            label="openai-small",
            executable="openkos",
            runner=_runner(),
            env={},
            ollama_models=lambda: OLLAMA_OK,
            executable_exists=lambda _path: True,
        )
    assert API_KEY_ENV in str(error.value)


def test_preflight_rejects_a_wrong_openkos_version() -> None:
    with pytest.raises(HostedPreflightError, match=r"0\.7\.0.*0\.7\.2|0\.7\.2.*0\.7\.0"):
        preflight(
            CONFIG,
            label="openai-small",
            executable="openkos",
            runner=_runner("openkos 0.7.0\n"),
            env={API_KEY_ENV: "k"},
            ollama_models=lambda: OLLAMA_OK,
            executable_exists=lambda _path: True,
        )


def test_preflight_rejects_a_missing_executable() -> None:
    with pytest.raises(HostedPreflightError, match=r"openkos-0\.7\.2"):
        preflight(
            CONFIG,
            label="openai-small",
            executable="/nope/openkos-0.7.2/bin/openkos",
            runner=_runner(),
            env={API_KEY_ENV: "k"},
            ollama_models=lambda: OLLAMA_OK,
            executable_exists=lambda _path: False,
        )


def test_preflight_requires_the_embedding_model_in_local_ollama() -> None:
    with pytest.raises(HostedPreflightError, match="bge-m3"):
        preflight(
            CONFIG,
            label="openai-small",
            executable="openkos",
            runner=_runner(),
            env={API_KEY_ENV: "k"},
            ollama_models=lambda: {"qwen3:8b": "d"},
            executable_exists=lambda _path: True,
        )


def test_bridge_preflight_needs_no_key_but_needs_the_local_generative_model() -> None:
    preflight(
        CONFIG,
        label=None,
        executable="openkos",
        runner=_runner(),
        env={},
        ollama_models=lambda: OLLAMA_OK,
        executable_exists=lambda _path: True,
        bridge_model="qwen3:8b",
    )
    with pytest.raises(HostedPreflightError, match="qwen3:8b"):
        preflight(
            CONFIG,
            label=None,
            executable="openkos",
            runner=_runner(),
            env={},
            ollama_models=lambda: {"bge-m3:latest": "d"},
            executable_exists=lambda _path: True,
            bridge_model="qwen3:8b",
        )


def test_preflight_fails_when_ollama_is_unreachable() -> None:
    with pytest.raises(HostedPreflightError, match="Ollama"):
        preflight(
            CONFIG,
            label="openai-small",
            executable="openkos",
            runner=_runner(),
            env={API_KEY_ENV: "k"},
            ollama_models=lambda: None,
            executable_exists=lambda _path: True,
        )
