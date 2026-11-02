"""The pinned-environment guard: digests and versions fixed in the config (probes are faked)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from afg.experiments.pinned_environment import (
    PinnedEnvironment,
    PinnedEnvironmentError,
    check_pinned_environment,
    load_pinned_environment,
)
from afg.shared.config import load_experiments_config

PINS = PinnedEnvironment(
    model_digests={"qwen3:8b": "aaa", "gpt-oss:20b": "bbb", "bge-m3": "ccc"},
    ollama_version="0.32.9",
    openkos_version="0.7.0",
)


class Probe:
    def __init__(
        self,
        digests: Mapping[str, str] | None = None,
        ollama: str | None = "0.32.9",
        openkos: str | None = "0.7.0",
    ) -> None:
        self._digests = (
            {"qwen3:8b": "aaa", "gpt-oss:20b": "bbb", "bge-m3:latest": "ccc"}
            if digests is None
            else digests
        )
        self._ollama = ollama
        self._openkos = openkos

    def model_digests(self) -> Mapping[str, str] | None:
        return self._digests

    def ollama_version(self) -> str | None:
        return self._ollama

    def openkos_version(self) -> str | None:
        return self._openkos

    def git_dirty(self) -> bool | None:
        return False


def _check(probe: Probe, models: list[str], *, needs_openkos: bool = True) -> dict[str, Any]:
    return check_pinned_environment(probe, models=models, needs_openkos=needs_openkos, pins=PINS)


def test_matching_environment_returns_the_manifest_record() -> None:
    record = _check(Probe(), ["qwen3:8b", "bge-m3"])

    assert record["pinned_environment_ok"] is True
    assert record["pinned_environment"] == {
        "ollama_version": "0.32.9",
        "openkos_version": "0.7.0",
        "model_digests": {"qwen3:8b": "aaa", "bge-m3": "ccc"},
    }


def test_openkos_is_not_checked_nor_recorded_when_not_needed() -> None:
    record = _check(Probe(openkos="9.9.9"), ["bge-m3"], needs_openkos=False)

    assert record["pinned_environment"]["openkos_version"] is None


def test_every_mismatch_is_listed_in_one_error() -> None:
    probe = Probe(
        digests={"qwen3:8b": "zzz", "bge-m3:latest": "ccc"},
        ollama="0.40.0",
        openkos="0.8.0",
    )

    with pytest.raises(PinnedEnvironmentError) as caught:
        _check(probe, ["qwen3:8b", "gpt-oss:20b", "bge-m3"])

    message = str(caught.value)
    assert len(caught.value.mismatches) == 4
    assert "qwen3:8b" in message and "zzz" in message and "aaa" in message
    assert "gpt-oss:20b" in message and "no está instalado" in message
    assert "0.40.0" in message and "0.32.9" in message
    assert "0.8.0" in message and "0.7.0" in message


def test_a_model_without_a_pin_fails() -> None:
    with pytest.raises(PinnedEnvironmentError, match="sin huella fijada"):
        _check(Probe(), ["qwen3:32b"])


def test_unreachable_ollama_and_unreadable_versions_fail() -> None:
    probe = Probe(digests={}, ollama=None, openkos=None)
    probe._digests = None  # type: ignore[assignment]

    with pytest.raises(PinnedEnvironmentError) as caught:
        _check(probe, ["qwen3:8b"])

    assert len(caught.value.mismatches) == 3


def test_untagged_names_are_equivalent_to_latest() -> None:
    assert _check(Probe(), ["bge-m3:latest"])["pinned_environment_ok"] is True


def test_the_shipped_config_pins_every_model_it_names() -> None:
    config = load_experiments_config()
    named = {
        config["shared_budget"]["generative_model"],
        config["shared_budget"]["sufficiency_model"],
        config["shared_budget"]["embedding_model"],
        config["judge"]["model"],
    }
    pins = load_pinned_environment()

    assert named <= set(pins.model_digests)
    assert pins.ollama_version == "0.32.9"
    assert pins.openkos_version == "0.7.0"
    assert all(len(d) == 64 for d in pins.model_digests.values())


def test_a_malformed_section_is_rejected() -> None:
    with pytest.raises(ValueError, match="pinned_environment"):
        load_pinned_environment({"pinned_environment": {"ollama_version": "1"}})
