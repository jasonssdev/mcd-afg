"""The real CLI guard wrapper: probe and pins come from the machine, errors exit with code 1."""

from __future__ import annotations

import pytest
import typer

import afg.cli as afg_cli
from afg.experiments import pinned_environment as pinned
from tests.test_pinned_environment import PINS, Probe

# Captured at import time, before the autouse fixture replaces the attribute with a stub.
REAL_GUARD = afg_cli.require_pinned_environment


@pytest.fixture
def fixed_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pinned, "load_pinned_environment", lambda config=None: PINS)


def test_guard_passes_and_returns_the_record(
    monkeypatch: pytest.MonkeyPatch, fixed_pins: None
) -> None:
    monkeypatch.setattr(afg_cli, "make_provenance_probe", lambda: Probe())

    record = REAL_GUARD(["qwen3:8b"], needs_openkos=True)

    assert record["pinned_environment_ok"] is True


def test_guard_prints_every_mismatch_and_exits(
    monkeypatch: pytest.MonkeyPatch, fixed_pins: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        afg_cli, "make_provenance_probe", lambda: Probe(digests={"qwen3:8b": "zzz"}, ollama="1.0")
    )

    with pytest.raises(typer.Exit) as caught:
        REAL_GUARD(["qwen3:8b", "gpt-oss:20b"], needs_openkos=False)

    assert caught.value.exit_code == 1
    out = " ".join(capsys.readouterr().out.split())
    assert "qwen3:8b" in out and "zzz" in out and "gpt-oss:20b" in out and "1.0" in out
