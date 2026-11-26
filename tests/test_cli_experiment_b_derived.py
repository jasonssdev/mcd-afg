"""``afg experiment b-derive`` and ``afg experiment b --c2-derived`` (ADR 0026, amendment 3).

No OpenKOS and no Ollama: the runner, the condition and the judge are fakes.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.question import Answer, Question
from afg.extraction.openkos.query_workspace import (
    DERIVED_MANIFEST_NAME,
    QuerySideSettings,
    derive_query_workspaces,
)
from afg.extraction.openkos.workspace import read_config_value
from tests.openkos_fake import FakeRunner
from tests.test_cli_experiment_b import FakeC1, _FakeProbe, _invoke, _out
from tests.test_cli_experiment_b import env as env_fixture  # noqa: F401

HOSTED_YAML = (
    "model: synthetic\nembedding_model: bge-m3\nbackend: openai-compatible\n"
    "base_url: https://api.example.test\nreasoning_effort: low\n"
    "# seed: 42\n# temperature: 0.1\n# context_window: 24576\n# sufficiency_check: true\n"
)


def _source(root: Path, version: str = "0.7.3") -> None:
    for run in (0, 1):
        ws = root / "ES2015" / f"run-{run}"
        (ws / "bundle").mkdir(parents=True)
        (ws / "openkos.yaml").write_text(HOSTED_YAML, encoding="utf-8")
        (root / "ES2015" / f"run-{run}.manifest.json").write_text(
            json.dumps({"status": "ok", "openkos_version": version}), encoding="utf-8"
        )


@pytest.fixture
def dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    workspaces, query = tmp_path / "openkos", tmp_path / "openkos-query"
    _source(workspaces / "experimento-a-hosted-x")
    monkeypatch.setattr(afg_cli, "OPENKOS_WORKSPACES_DIR", workspaces)
    monkeypatch.setattr(afg_cli, "OPENKOS_QUERY_WORKSPACES_DIR", query)
    monkeypatch.setattr(
        afg_cli, "SubprocessRunner", lambda: FakeRunner(version_output="openkos 0.7.3\n")
    )
    monkeypatch.setenv("AFG_HOSTED_OPENKOS_EXECUTABLE", "/opt/openkos-0.7.3/bin/openkos")
    return {"workspaces": workspaces, "query": query}


def _derive(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", "b-derive", *args])


# --- b-derive ---------------------------------------------------------------------------------


def test_derive_writes_a_default_named_directory_with_the_formal_settings(
    dirs: dict[str, Path],
) -> None:
    result = _derive("--source", "experimento-a-hosted-x")
    assert result.exit_code == 0, result.output
    target = dirs["query"] / "experimento-a-hosted-x-consulta"
    text = (target / "ES2015" / "run-1" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "backend") == "ollama"
    assert read_config_value(text, "model") == "qwen3:8b"
    assert read_config_value(text, "seed") == "43"
    assert (
        read_config_value(text, "context_window") == "12288"
    )  # [shared_budget], as the formal run
    manifest = json.loads((target / DERIVED_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["executable"] == "/opt/openkos-0.7.3/bin/openkos"  # hosted install, by version
    assert manifest["sufficiency_check"] is True
    assert "experimento-a-hosted-x-consulta" in _out(result)


def test_derive_without_sufficiency_gets_its_own_default_name(dirs: dict[str, Path]) -> None:
    result = _derive("--source", "experimento-a-hosted-x", "--no-sufficiency-check")
    assert result.exit_code == 0, result.output
    target = dirs["query"] / "experimento-a-hosted-x-consulta-sin-suficiencia"
    text = (target / "ES2015" / "run-0" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "sufficiency_check") == "false"


def test_derive_honours_name_executable_context_and_overwrite(dirs: dict[str, Path]) -> None:
    args = ("--source", "experimento-a-hosted-x", "--name", "mine", "--context-window", "999")
    assert _derive(*args, "--openkos-executable", "/other/openkos").exit_code == 0
    manifest = json.loads(
        (dirs["query"] / "mine" / DERIVED_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["executable"] == "/other/openkos"
    assert manifest["settings"]["context_window"] == 999
    again = _derive(*args)
    assert again.exit_code == 1 and "mine" in _out(again)  # exists
    assert _derive(*args, "--overwrite").exit_code == 0


def test_derive_formal_run_resolves_the_pinned_executable(
    dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _source(dirs["workspaces"] / "experimento-a-formal", version="0.7.0")
    monkeypatch.setattr(
        afg_cli, "SubprocessRunner", lambda: FakeRunner(version_output="openkos 0.7.0\n")
    )
    result = _derive("--source", "experimento-a-formal", "--no-sufficiency-check")
    assert result.exit_code == 0, result.output
    manifest = json.loads(
        (
            dirs["query"] / "experimento-a-formal-consulta-sin-suficiencia" / DERIVED_MANIFEST_NAME
        ).read_text(encoding="utf-8")
    )
    assert manifest["openkos_version"] == "0.7.0"
    assert manifest["executable"] == afg_cli.get_settings().openkos_executable


def test_derive_unknown_source_or_version_is_refused(dirs: dict[str, Path]) -> None:
    assert _derive("--source", "nope").exit_code == 1
    _source(dirs["workspaces"] / "old", version="0.7.2")
    old = _derive("--source", "old")
    assert old.exit_code == 1 and "0.7.2" in _out(old) and "--openkos-executable" in _out(old)
    assert not dirs["query"].exists()


# --- b --c2-derived ---------------------------------------------------------------------------


class FakeC2(FakeC1):
    condition_id = "C2"

    def answer(self, question: Question) -> Answer:
        return Answer(question_id=question.id, condition="C2", text="b", abstained=True)


def _make_derived(dirs: dict[str, Path], *, sufficiency: bool = True, name: str = "d") -> Path:
    return derive_query_workspaces(
        source_root=dirs["workspaces"] / "experimento-a-hosted-x",
        target_root=dirs["query"] / name,
        settings=QuerySideSettings("qwen3:8b", 42, 0.1, 12288, sufficiency),
        executable="/opt/openkos-0.7.3/bin/openkos",
        runner=FakeRunner(version_output="openkos 0.7.3\n"),
    ).target_root


class _VersionProbe(_FakeProbe):
    def openkos_version(self) -> str | None:
        return "0.7.3"


@pytest.fixture
def derived_env(request: pytest.FixtureRequest, dirs: dict[str, Path]) -> dict[str, Any]:
    base: dict[str, Any] = request.getfixturevalue("env_fixture")
    mp = base["monkeypatch"]
    seen: list[str | None] = []

    def probe(executable: str | None = None) -> _FakeProbe:
        seen.append(executable)
        return _VersionProbe() if executable else _FakeProbe()

    mp.setattr(afg_cli, "make_provenance_probe", probe)
    mp.setattr(afg_cli, "make_c2_derived_condition", lambda name: FakeC2())
    return {**base, "dirs": dirs, "probe_calls": seen}


def _run(env: dict[str, Any], *args: str) -> Any:
    return _invoke(env, "--conditions", "c2", "--runs", "1", "--run-name", "m", *args)


def _manifest(env: dict[str, Any], name: str = "m") -> dict[str, Any]:
    return json.loads((env["out"] / name / "manifest.json").read_text(encoding="utf-8"))


def test_runs_c2_on_derived_workspaces_and_records_them(derived_env: dict[str, Any]) -> None:
    _make_derived(derived_env["dirs"])
    result = _run(derived_env, "--c2-derived", "d")
    assert result.exit_code == 0, result.output
    manifest = _manifest(derived_env)
    assert manifest["c2_extraction"] == "d"
    assert manifest["c2_derived_from"] == "experimento-a-hosted-x"
    assert manifest["c2_openkos_executable"] == "/opt/openkos-0.7.3/bin/openkos"
    assert manifest["sufficiency_check"] is True
    assert manifest["c2_workspaces_dir"].endswith("openkos-query")
    assert manifest["openkos_version"] == "0.7.3"  # read from the derived executable
    assert "/opt/openkos-0.7.3/bin/openkos" in derived_env["probe_calls"]


def test_resuming_with_other_derived_workspaces_is_refused(derived_env: dict[str, Any]) -> None:
    _make_derived(derived_env["dirs"], name="d")
    _make_derived(derived_env["dirs"], name="e")
    assert _run(derived_env, "--c2-derived", "d").exit_code == 0
    again = _run(derived_env, "--c2-derived", "e")
    assert again.exit_code == 1 and "c2_extraction" in _out(again)


def test_relaxed_derivation_needs_the_matching_flag(derived_env: dict[str, Any]) -> None:
    _make_derived(derived_env["dirs"], sufficiency=False)
    refused = _run(derived_env, "--c2-derived", "d")
    assert refused.exit_code == 1 and "sufficiency" in _out(refused)
    assert not derived_env["out"].exists()
    ok = _run(derived_env, "--c2-derived", "d", "--no-sufficiency-check")
    assert ok.exit_code == 0, ok.output
    assert _manifest(derived_env)["sufficiency_check"] is False


def test_sufficiency_model_is_not_required_when_the_check_is_off(
    derived_env: dict[str, Any],
) -> None:
    _make_derived(derived_env["dirs"], sufficiency=False)
    models: list[list[str]] = []

    def guard(names: Sequence[str], *, needs_openkos: bool) -> dict[str, Any]:
        models.append(list(names))
        return {"pinned_environment_ok": True, "pinned_environment": {"openkos_version": None}}

    derived_env["monkeypatch"].setattr(afg_cli, "require_pinned_environment", guard)
    derived_env["monkeypatch"].setattr(
        afg_cli, "list_installed_models", lambda: ["qwen3:8b", "gpt-oss:20b", "bge-m3:latest"]
    )
    result = _run(derived_env, "--c2-derived", "d", "--no-sufficiency-check")
    assert result.exit_code == 0, result.output
    assert all("gemma4:26b-a4b" not in names for names in models)


def test_sufficiency_model_is_still_required_when_the_check_is_on(
    derived_env: dict[str, Any],
) -> None:
    _make_derived(derived_env["dirs"])
    derived_env["monkeypatch"].setattr(
        afg_cli, "list_installed_models", lambda: ["qwen3:8b", "gpt-oss:20b", "bge-m3:latest"]
    )
    result = _run(derived_env, "--c2-derived", "d")
    assert result.exit_code == 1 and "gemma4:26b-a4b" in _out(result)


def test_pin_check_skips_the_path_openkos_for_derived_runs(derived_env: dict[str, Any]) -> None:
    _make_derived(derived_env["dirs"])
    calls: list[tuple[list[str], bool]] = []

    def guard(names: Sequence[str], *, needs_openkos: bool) -> dict[str, Any]:
        calls.append((list(names), needs_openkos))
        return {"pinned_environment_ok": True, "pinned_environment": {"openkos_version": None}}

    derived_env["monkeypatch"].setattr(afg_cli, "require_pinned_environment", guard)
    assert _run(derived_env, "--c2-derived", "d").exit_code == 0
    assert [needs for _, needs in calls] == [False]


def test_a_derived_executable_of_another_version_stops_the_run(
    derived_env: dict[str, Any],
) -> None:
    _make_derived(derived_env["dirs"])

    class Other(_FakeProbe):
        def openkos_version(self) -> str | None:
            return "0.7.0"

    derived_env["monkeypatch"].setattr(
        afg_cli, "make_provenance_probe", lambda executable=None: Other()
    )
    result = _run(derived_env, "--c2-derived", "d")
    assert result.exit_code == 1 and "0.7.3" in _out(result) and "0.7.0" in _out(result)
    assert not derived_env["out"].exists()


@pytest.mark.parametrize(
    ("args", "needle"),
    [
        (["--conditions", "c1,c2", "--c2-derived", "d"], "--c2-derived"),
        (["--conditions", "c3", "--c2-derived", "d"], "--c2-derived"),
        (["--conditions", "c2", "--c2-derived", "d", "--c2-extraction", "a"], "--c2-extraction"),
        (["--conditions", "c2", "--c2-extraction", "a", "--no-sufficiency-check"], "sufficiency"),
        (["--conditions", "c1", "--no-sufficiency-check"], "sufficiency"),
    ],
)
def test_incompatible_options_are_refused_before_any_work(
    derived_env: dict[str, Any], args: list[str], needle: str
) -> None:
    _make_derived(derived_env["dirs"])
    result = CliRunner().invoke(
        afg_cli.app, ["experiment", "b", "--questions", str(derived_env["questions"]), *args]
    )
    assert result.exit_code == 1 and needle in _out(result)
    assert not derived_env["out"].exists()


def test_missing_derivation_is_refused_with_the_command_to_make_it(
    derived_env: dict[str, Any],
) -> None:
    result = _run(derived_env, "--c2-derived", "nope")
    assert result.exit_code == 1 and "b-derive" in _out(result)


def test_formal_manifests_keep_their_shape(derived_env: dict[str, Any]) -> None:
    derived_env["monkeypatch"].setattr(afg_cli, "make_c2_condition", lambda run: FakeC2())
    assert _run(derived_env, "--c2-extraction", "es-run").exit_code == 0
    manifest = _manifest(derived_env)
    for key in (
        "c2_derived_from",
        "c2_openkos_executable",
        "c2_workspaces_dir",
        "sufficiency_check",
    ):
        assert key not in manifest


def test_make_c2_derived_condition_uses_the_recorded_executable(
    dirs: dict[str, Path],
) -> None:
    from afg.conditions.c2_compiled_auto import CompiledAutoCondition

    _make_derived(dirs)
    condition = afg_cli.make_c2_derived_condition("d")
    assert isinstance(condition, CompiledAutoCondition)
    assert condition.extraction_run == "d" and condition.base_dir == dirs["query"]
    assert condition.settings.executable == "/opt/openkos-0.7.3/bin/openkos"
    assert condition.settings.base_seed == 42 and condition.settings.backend is None


def test_a_derivation_with_another_base_seed_is_refused(dirs: dict[str, Path]) -> None:
    derive_query_workspaces(
        source_root=dirs["workspaces"] / "experimento-a-hosted-x",
        target_root=dirs["query"] / "d",
        settings=QuerySideSettings("qwen3:8b", 7, 0.1, 12288),
        executable="/opt/openkos-0.7.3/bin/openkos",
        runner=FakeRunner(version_output="openkos 0.7.3\n"),
    )
    with pytest.raises(ValueError, match="seed"):
        afg_cli.make_c2_derived_condition("d")
