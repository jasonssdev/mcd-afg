"""Tests for the runtime settings defaults (``afg.shared.config.Settings``)."""

from __future__ import annotations

import pytest

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
