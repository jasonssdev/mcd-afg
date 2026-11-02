"""Test doubles for the CLI guard ``afg.cli.require_pinned_environment``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
import typer

import afg.cli as afg_cli

OK_RECORD: dict[str, Any] = {
    "pinned_environment_ok": True,
    "pinned_environment": {"ollama_version": "0.0.0", "openkos_version": None, "model_digests": {}},
}


def passing_guard(models: Sequence[str], *, needs_openkos: bool) -> dict[str, Any]:
    return OK_RECORD


def tripwire(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], bool]]:
    """Replace the guard with one that records its arguments and refuses (exit code 1)."""
    calls: list[tuple[list[str], bool]] = []

    def refusing(models: Sequence[str], *, needs_openkos: bool) -> dict[str, Any]:
        calls.append((list(models), needs_openkos))
        raise typer.Exit(code=1)

    monkeypatch.setattr(afg_cli, "require_pinned_environment", refusing)
    return calls
