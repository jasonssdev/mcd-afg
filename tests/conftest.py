"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator

import numpy as np
import pytest

# Rich wraps CLI output at the console width it detects (``COLUMNS`` wins over the terminal).
# GitHub Actions runners report about 100 columns, which splits long file paths in the middle
# of their name and broke tests that look for ``ES2015.candidates.gv.csv`` in the output;
# locally, with no terminal, Rich falls back to 80 and the breaks happen to land elsewhere.
# A fixed, wide console makes the tests assert on content, never on where a line wrapped.
os.environ["COLUMNS"] = "200"

# Typer forces a colour terminal for ``--help`` when it sees GITHUB_ACTIONS, FORCE_COLOR or
# PY_COLORS (read once, at import), and the ANSI codes then sit between the box border and the
# command name, so ``"│ setup "`` is no longer a substring of the output. Tests must see the
# same plain help everywhere; conftest runs before any module imports typer.
for _flag in ("GITHUB_ACTIONS", "FORCE_COLOR", "PY_COLORS"):
    os.environ.pop(_flag, None)


@pytest.fixture
def rng() -> Iterator[np.random.Generator]:
    yield np.random.default_rng(seed=42)


@pytest.fixture(autouse=True)
def _pinned_environment_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI tests run with fake probes whose digests are not the pinned ones: the guard passes.

    The guard itself is tested in ``test_pinned_environment.py`` and ``test_cli_pinned_guard.py``,
    and each wired command has a test that replaces this stub with a refusing guard.
    """
    import afg.cli as afg_cli
    from tests.pinned_guard import passing_guard

    monkeypatch.setattr(afg_cli, "require_pinned_environment", passing_guard, raising=False)


@pytest.fixture(autouse=True)
def _no_freeze_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No test sees the real ``config/freeze.json`` (it exists once the freeze ADR is merged).

    The freeze gate is tested in ``test_freeze.py`` and ``test_cli_freeze_gate.py`` with records
    written under ``tmp_path``; the other CLI tests run as if nothing were frozen.
    """
    import afg.cli as afg_cli

    absent = tmp_path_factory.mktemp("freeze") / "freeze.json"
    monkeypatch.setattr(afg_cli, "FREEZE_PATH", absent, raising=False)


@pytest.fixture(autouse=True)
def _no_result_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The developer's own ``AFG_*`` overrides and ``.env`` must not reach the freeze gate."""
    from afg.experiments.freeze import RESULT_AFFECTING_ENV

    for name in RESULT_AFFECTING_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        "afg.experiments.freeze.ENV_PATH", tmp_path_factory.getbasetemp() / "no-such.env"
    )
