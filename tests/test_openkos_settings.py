"""Tests for deriving the OpenKOS run settings from the project configuration."""

from __future__ import annotations

import pytest

from afg.extraction.openkos.settings import openkos_run_settings
from afg.shared.config import Settings, load_experiments_config


def test_run_settings_come_from_the_shared_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AFG_GENERATIVE_MODEL", "AFG_EMBEDDING_MODEL", "AFG_OPENKOS_EXECUTABLE"):
        monkeypatch.delenv(name, raising=False)
    budget = load_experiments_config()["shared_budget"]
    run_settings = openkos_run_settings(Settings(_env_file=None))  # type: ignore[call-arg]
    assert run_settings.generative_model == budget["generative_model"]
    assert run_settings.embedding_model == budget["embedding_model"]
    assert run_settings.base_seed == budget["seed"]
    assert run_settings.temperature == budget["temperature"]
    assert run_settings.executable == "openkos"


def test_executable_override_is_carried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFG_OPENKOS_EXECUTABLE", "/x/openkos")
    run_settings = openkos_run_settings(Settings(_env_file=None))  # type: ignore[call-arg]
    assert run_settings.executable == "/x/openkos"
