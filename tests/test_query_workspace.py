"""Tests for the derived query workspaces (ADR 0026, third amendment). No real OpenKOS."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from afg.extraction.openkos.capabilities import MissingCapabilitiesError
from afg.extraction.openkos.query_workspace import (
    DERIVED_MANIFEST_NAME,
    DerivedWorkspaceExistsError,
    ExecutableVersionError,
    QuerySideSettings,
    derive_query_workspaces,
    executable_for_version,
    load_derived_manifest,
)
from afg.extraction.openkos.workspace import read_config_value
from tests.openkos_fake import FakeRunner

HOSTED_YAML = (
    "model: synthetic-hosted-model\n"
    "embedding_model: bge-m3\n"
    "backend: openai-compatible\n"
    "base_url: https://api.example.test\n"
    "embedding_base_url: http://127.0.0.1:11434\n"
    "reasoning_effort: low\n"
    "max_generation_tokens: 8192\n"
    "evidence_quote: false\n"
    "transcript_decisions: true\n"
    "# seed: 42\n"
    "# temperature: 0.1\n"
    "# context_window: 24576\n"
    "# sufficiency_check: true\n"
)
SETTINGS = QuerySideSettings(
    generative_model="qwen3:8b", base_seed=42, temperature=0.1, context_window=12288
)


def _pair(
    root: Path,
    series: str,
    run: int,
    *,
    yaml: str = HOSTED_YAML,
    status: str = "ok",
    version: str = "0.7.3",
) -> None:
    workspace = root / series / f"run-{run}"
    (workspace / "bundle" / "decisions").mkdir(parents=True)
    (workspace / ".openkos").mkdir()
    (workspace / "openkos.yaml").write_text(yaml, encoding="utf-8")
    (workspace / "bundle" / "decisions" / "d.md").write_text("synthetic\n", encoding="utf-8")
    (workspace / ".openkos" / "vectors.db").write_bytes(b"\x00\x01")
    (root / series / f"run-{run}.manifest.json").write_text(
        json.dumps({"status": status, "openkos_version": version}), encoding="utf-8"
    )


def _fingerprint(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    for series in ("AA0001", "BB0002"):
        for run in (0, 1):
            _pair(root, series, run)
    return root


def _derive(source: Path, tmp_path: Path, **kw):  # type: ignore[no-untyped-def]
    return derive_query_workspaces(
        source_root=source,
        target_root=tmp_path / "derived",
        settings=kw.pop("settings", SETTINGS),
        executable="/opt/openkos-0.7.3/bin/openkos",
        runner=kw.pop("runner", FakeRunner(version_output="openkos 0.7.3\n")),
        **kw,
    )


def test_rewrites_only_the_query_side_keys(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path)
    text = (result.target_root / "AA0001" / "run-1" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "backend") == "ollama"
    assert read_config_value(text, "model") == "qwen3:8b"
    assert read_config_value(text, "seed") == "43"  # base_seed + run
    assert read_config_value(text, "temperature") == "0.1"
    assert read_config_value(text, "context_window") == "12288"
    for gone in ("base_url", "embedding_base_url", "reasoning_effort"):
        assert read_config_value(text, gone) is None
    # extraction-side keys and the sufficiency default are untouched
    assert read_config_value(text, "embedding_model") == "bge-m3"
    assert read_config_value(text, "max_generation_tokens") == "8192"
    assert read_config_value(text, "evidence_quote") == "false"
    assert read_config_value(text, "sufficiency_check") is None
    assert "# sufficiency_check: true" in text


def test_the_seed_follows_the_run_number(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path)
    seeds = {
        (s, r): read_config_value(
            (result.target_root / s / f"run-{r}" / "openkos.yaml").read_text(encoding="utf-8"),
            "seed",
        )
        for s in ("AA0001", "BB0002")
        for r in (0, 1)
    }
    assert seeds == {
        ("AA0001", 0): "42",
        ("AA0001", 1): "43",
        ("BB0002", 0): "42",
        ("BB0002", 1): "43",
    }


def test_the_source_is_never_touched(source: Path, tmp_path: Path) -> None:
    before = _fingerprint(source)
    _derive(source, tmp_path)
    assert _fingerprint(source) == before


def test_objects_and_indexes_are_copied_unchanged(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path)
    workspace = result.target_root / "BB0002" / "run-0"
    assert (workspace / "bundle" / "decisions" / "d.md").read_text(encoding="utf-8") == (
        "synthetic\n"
    )
    assert (workspace / ".openkos" / "vectors.db").read_bytes() == b"\x00\x01"


def test_sufficiency_off_is_written_and_recorded(source: Path, tmp_path: Path) -> None:
    from dataclasses import replace

    result = _derive(source, tmp_path, settings=replace(SETTINGS, sufficiency_check=False))
    text = (result.target_root / "AA0001" / "run-0" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "sufficiency_check") == "false"
    assert load_derived_manifest(result.target_root).sufficiency_check is False


def test_sufficiency_on_is_the_default_and_is_recorded(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path)
    assert load_derived_manifest(result.target_root).sufficiency_check is True


def test_a_relaxed_source_is_turned_back_on_by_the_default(tmp_path: Path) -> None:
    root = tmp_path / "relaxed"
    _pair(
        root,
        "AA0001",
        0,
        yaml=HOSTED_YAML.replace("# sufficiency_check: true", "sufficiency_check: false"),
    )
    result = _derive(root, tmp_path)
    text = (result.target_root / "AA0001" / "run-0" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "sufficiency_check") == "true"


def test_a_workspace_of_an_ollama_source_keeps_the_default_backend(tmp_path: Path) -> None:
    root = tmp_path / "formal"
    formal = (
        "model: qwen3:8b\nembedding_model: bge-m3\ncontext_window: 12288\n"
        "temperature: 0.1\nseed: 42\n# sufficiency_check: true\n"
    )
    _pair(root, "AA0001", 0, yaml=formal, version="0.7.0")
    result = derive_query_workspaces(
        source_root=root,
        target_root=tmp_path / "d",
        settings=SETTINGS,
        executable="/x/openkos",
        runner=FakeRunner(version_output="openkos 0.7.0\n"),
    )
    text = (result.target_root / "AA0001" / "run-0" / "openkos.yaml").read_text(encoding="utf-8")
    assert read_config_value(text, "backend") is None  # not written: already the default
    assert read_config_value(text, "seed") == "42"


def test_manifest_records_the_executable_version_and_pairs(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path)
    manifest = json.loads((result.target_root / DERIVED_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["executable"] == "/opt/openkos-0.7.3/bin/openkos"
    assert manifest["openkos_version"] == "0.7.3"
    assert manifest["source_run"] == "source"
    assert manifest["settings"]["generative_model"] == "qwen3:8b"
    assert manifest["settings"]["context_window"] == 12288
    assert manifest["pairs"] == [
        {"series": "AA0001", "run": 0, "seed": 42},
        {"series": "AA0001", "run": 1, "seed": 43},
        {"series": "BB0002", "run": 0, "seed": 42},
        {"series": "BB0002", "run": 1, "seed": 43},
    ]
    loaded = load_derived_manifest(result.target_root)
    assert (loaded.executable, loaded.openkos_version) == (
        "/opt/openkos-0.7.3/bin/openkos",
        "0.7.3",
    )


def test_executable_of_another_version_is_refused_and_leaves_nothing(
    source: Path, tmp_path: Path
) -> None:
    with pytest.raises(ExecutableVersionError, match=r"0\.7\.0"):
        _derive(source, tmp_path, runner=FakeRunner(version_output="openkos 0.7.0\n"))
    assert not (tmp_path / "derived").exists()
    assert not list(tmp_path.glob(".derived*"))


def test_a_key_the_version_does_not_know_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "old"
    _pair(root, "AA0001", 0, yaml="model: x\nembedding_model: bge-m3\n")
    with pytest.raises(MissingCapabilitiesError):
        _derive(root, tmp_path)
    assert not (tmp_path / "derived").exists()


def test_an_existing_target_is_refused_unless_overwrite(source: Path, tmp_path: Path) -> None:
    _derive(source, tmp_path)
    with pytest.raises(DerivedWorkspaceExistsError):
        _derive(source, tmp_path)
    again = _derive(source, tmp_path, overwrite=True)
    assert (again.target_root / DERIVED_MANIFEST_NAME).is_file()


def test_pairs_without_a_finished_manifest_are_skipped_and_listed(
    source: Path, tmp_path: Path
) -> None:
    _pair(source, "CC0003", 0, status="error")
    (source / "BB0002" / "run-1.manifest.json").unlink()
    result = _derive(source, tmp_path)
    manifest = load_derived_manifest(result.target_root)
    assert [(p["series"], p["run"]) for p in manifest.pairs] == [
        ("AA0001", 0),
        ("AA0001", 1),
        ("BB0002", 0),
    ]
    assert manifest.skipped == ("BB0002/run-1", "CC0003/run-0")
    assert not (result.target_root / "CC0003").exists()


def test_series_filter_limits_the_pairs(source: Path, tmp_path: Path) -> None:
    result = _derive(source, tmp_path, series=("BB0002",))
    assert [(p["series"], p["run"]) for p in load_derived_manifest(result.target_root).pairs] == [
        ("BB0002", 0),
        ("BB0002", 1),
    ]


def test_mixed_source_versions_are_refused(source: Path, tmp_path: Path) -> None:
    _pair(source, "CC0003", 0, version="0.7.2")
    with pytest.raises(ExecutableVersionError, match="more than one"):
        _derive(source, tmp_path)


def test_an_empty_source_is_refused(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        _derive(tmp_path / "empty", tmp_path)


def test_executable_for_version_maps_each_known_version() -> None:
    kwargs = {
        "pinned_version": "0.7.0",
        "pinned_executable": "openkos",
        "hosted_version": "0.7.3",
        "hosted_executable": "/h/openkos",
    }
    assert executable_for_version("0.7.0", **kwargs) == "openkos"
    assert executable_for_version("0.7.3", **kwargs) == "/h/openkos"
    with pytest.raises(ExecutableVersionError, match=r"0\.7\.2"):
        executable_for_version("0.7.2", **kwargs)
