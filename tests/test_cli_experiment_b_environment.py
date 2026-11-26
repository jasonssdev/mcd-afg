"""``afg experiment b --environment hosted`` (ADR 0026, fourth amendment): the extension pin.

No Ollama, no OpenKOS: the guard, the probe, the condition and the judge are fakes.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import afg.cli as afg_cli
from tests.test_cli_experiment_b import _invoke, _out
from tests.test_cli_experiment_b import env as env_fixture  # noqa: F401
from tests.test_cli_experiment_b_derived import _make_derived, dirs  # noqa: F401
from tests.test_cli_experiment_b_derived import derived_env as derived_fixture  # noqa: F401

C1_CONTROL = "experimento-b-c1-ollama-0-40-16"


class Guard:
    """A pin guard that records how it was called and echoes the Ollama pin it was given."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, models: Sequence[str], **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return {
            "pinned_environment_ok": True,
            "pinned_environment": {"ollama_version": kwargs.get("ollama_version", "0.32.9")},
        }


@pytest.fixture
def base_env(request: pytest.FixtureRequest) -> dict[str, Any]:
    fixture: dict[str, Any] = request.getfixturevalue("env_fixture")
    return fixture


@pytest.fixture
def guard(base_env: dict[str, Any]) -> Guard:
    recorder = Guard()
    base_env["monkeypatch"].setattr(afg_cli, "require_pinned_environment", recorder)
    return recorder


def _manifest(env: dict[str, Any], name: str) -> dict[str, Any]:
    return json.loads((env["out"] / name / "manifest.json").read_text(encoding="utf-8"))


def _c1(env: dict[str, Any], name: str, *extra: str) -> Any:
    return _invoke(env, "--conditions", "c1", "--runs", "1", "--run-name", name, *extra)


def test_hosted_environment_checks_ollama_against_the_extension_pin(
    base_env: dict[str, Any],
    guard: Guard,
) -> None:
    result = _c1(base_env, C1_CONTROL, "--environment", "hosted")
    assert result.exit_code == 0, result.output
    assert guard.calls == [{"needs_openkos": True, "ollama_version": "0.40.16"}]
    manifest = _manifest(base_env, C1_CONTROL)
    assert manifest["environment"] == "hosted"
    assert manifest["ollama_version"] == "0.9.9"  # what the probe read from the server
    assert manifest["pinned_environment"]["ollama_version"] == "0.40.16"


def test_the_formal_default_is_untouched(base_env: dict[str, Any], guard: Guard) -> None:
    result = _c1(base_env, "plain")
    assert result.exit_code == 0, result.output
    assert guard.calls == [{"needs_openkos": True}]  # same call as before: no new argument
    assert "environment" not in _manifest(base_env, "plain")


def test_an_explicit_formal_environment_is_the_default(
    base_env: dict[str, Any],
    guard: Guard,
) -> None:
    assert _c1(base_env, "plain", "--environment", "formal").exit_code == 0
    assert guard.calls == [{"needs_openkos": True}]
    assert "environment" not in _manifest(base_env, "plain")


def test_an_unknown_environment_is_refused(base_env: dict[str, Any], guard: Guard) -> None:
    result = _c1(base_env, "x", "--environment", "cloud")
    assert result.exit_code == 1 and "hosted" in _out(result)
    assert guard.calls == [] and not base_env["out"].exists()


@pytest.mark.parametrize("name", ["experimento-b-formal", "experimento-b-formal-copia"])
def test_the_formal_run_names_are_never_mixed_with_the_extension(
    base_env: dict[str, Any],
    guard: Guard,
    name: str,
) -> None:
    result = _c1(base_env, name, "--environment", "hosted")
    assert result.exit_code == 1 and name in _out(result)
    assert guard.calls == [] and not base_env["out"].exists()


def test_resuming_in_another_environment_is_refused(
    base_env: dict[str, Any],
    guard: Guard,
) -> None:
    assert _c1(base_env, C1_CONTROL, "--environment", "hosted").exit_code == 0
    again = _c1(base_env, C1_CONTROL)
    assert again.exit_code == 1 and "environment" in _out(again)
    other = _c1(base_env, "plain")
    assert other.exit_code == 0
    back = _c1(base_env, "plain", "--environment", "hosted")
    assert back.exit_code == 1 and "environment" in _out(back)


def test_resuming_in_the_same_environment_continues(
    base_env: dict[str, Any],
    guard: Guard,
) -> None:
    assert _c1(base_env, C1_CONTROL, "--environment", "hosted").exit_code == 0
    assert _c1(base_env, C1_CONTROL, "--environment", "hosted").exit_code == 0


@pytest.fixture
def derived_env(request: pytest.FixtureRequest) -> dict[str, Any]:
    fixture: dict[str, Any] = request.getfixturevalue("derived_fixture")
    return fixture


def test_derived_runs_imply_the_hosted_environment(derived_env: dict[str, Any]) -> None:
    guard = Guard()
    derived_env["monkeypatch"].setattr(afg_cli, "require_pinned_environment", guard)
    _make_derived(derived_env["dirs"])
    result = _invoke(
        derived_env, "--conditions", "c2", "--runs", "1", "--run-name", "m", "--c2-derived", "d"
    )
    assert result.exit_code == 0, result.output
    assert guard.calls == [{"needs_openkos": False, "ollama_version": "0.40.16"}]
    assert _manifest(derived_env, "m")["environment"] == "hosted"


def test_derived_runs_cannot_ask_for_the_formal_environment(
    derived_env: dict[str, Any],
) -> None:
    _make_derived(derived_env["dirs"])
    result = _invoke(
        derived_env,
        "--conditions",
        "c2",
        "--runs",
        "1",
        "--run-name",
        "m",
        "--c2-derived",
        "d",
        "--environment",
        "formal",
    )
    assert result.exit_code == 1 and "--c2-derived" in _out(result)
    assert not derived_env["out"].exists()


def test_a_mismatching_server_stops_the_hosted_run_through_the_real_guard(
    base_env: dict[str, Any],
    tmp_path: Path,
) -> None:
    from afg.experiments import pinned_environment as pinned
    from tests.test_pinned_environment import PINS, Probe

    mp = base_env["monkeypatch"]
    mp.setattr(afg_cli, "require_pinned_environment", REAL_GUARD)
    mp.setattr(pinned, "load_pinned_environment", lambda config=None: PINS)
    mp.setattr(afg_cli, "make_provenance_probe", lambda *a: Probe(ollama="0.32.9"))
    result = _c1(base_env, C1_CONTROL, "--environment", "hosted")
    assert result.exit_code == 1 and "0.40.16" in _out(result)
    assert not base_env["out"].exists()


# Captured at import time, before the autouse fixture replaces the attribute with a stub.
REAL_GUARD = afg_cli.require_pinned_environment
