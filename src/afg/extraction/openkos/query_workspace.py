"""Derive query workspaces from the workspaces of an extraction run (ADR 0026, amendment 3).

The third amendment measures the answers (C2) over the objects a paid model extracted, with
everything else as in the formal run: the generator (``qwen3:8b``), the sufficiency model, the
seeds and the judge are local. A hosted workspace was compiled with ``backend: openai-compatible``
and no seed, so querying it as it is would call the paid model and would fail
:func:`~afg.extraction.openkos.query.require_reproducible`. This module copies the workspaces of
an extraction run into a NEW directory, never touching the source, and rewrites only the
query-side keys of each ``openkos.yaml``:

* ``backend`` back to ``ollama`` and ``base_url``, ``embedding_base_url`` and ``reasoning_effort``
  dropped (the last one is refused by the ``ollama`` backend), so no API is called;
* ``model``, ``temperature`` and ``seed`` (``base_seed + run``, the Experiment B convention) set
  to the formal values, so ``require_reproducible`` validates;
* ``context_window`` when given (the formal run queries with 12288; the packaged default of
  later OpenKOS versions is larger, so leaving it would change the retrieval budget);
* ``sufficiency_check`` only to make it explicit: ``false`` for the relaxed variant (issue #337),
  ``true`` (the default) turns a relaxed source back on.

The objects (``bundle/``, ``raw/``) and the search indexes (``.openkos/``) are copied byte for
byte; nothing is re-extracted and no OpenKOS command other than ``--version`` runs. The workspaces
of an extraction run must be queried with the executable of the version that compiled them, so the
derivation records that executable and its version in ``derived-manifest.json`` and
``afg experiment b`` reads them from there.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from afg.extraction.openkos.capabilities import parse_version
from afg.extraction.openkos.commands import CommandRunner, OpenKosError
from afg.extraction.openkos.workspace import (
    drop_config_keys,
    ensure_config_keys,
    read_config_value,
    require_config_key,
)
from afg.extraction.openkos_adapter import project_relative

__all__ = [
    "DERIVED_GENERATOR",
    "DERIVED_MANIFEST_NAME",
    "DerivationResult",
    "DerivedManifest",
    "DerivedWorkspaceExistsError",
    "ExecutableVersionError",
    "QuerySideSettings",
    "derive_query_workspaces",
    "executable_for_version",
    "load_derived_manifest",
    "source_openkos_version",
]

DERIVED_GENERATOR = "afg/query-derive"
DERIVED_MANIFEST_NAME = "derived-manifest.json"
SCHEMA_VERSION = 1
QUERY_BACKEND = "ollama"
DROPPED_KEYS: tuple[str, ...] = ("base_url", "embedding_base_url", "reasoning_effort")
"""Provider keys a hosted workspace carries and the ``ollama`` backend must not (the last one is
refused outright)."""
_PACKAGED_DEFAULTS = {"backend": QUERY_BACKEND, "sufficiency_check": "true"}
_RUN_DIR = re.compile(r"^run-(\d+)$")


class DerivedWorkspaceExistsError(OpenKosError):
    """The derived directory already exists and overwriting was not requested."""


class ExecutableVersionError(OpenKosError):
    """The executable is not the version that compiled the source workspaces."""


@dataclass(frozen=True, slots=True)
class QuerySideSettings:
    """The query-side configuration written into every derived ``openkos.yaml``."""

    generative_model: str
    base_seed: int
    temperature: float
    context_window: int | None = None
    sufficiency_check: bool = True
    backend: str = QUERY_BACKEND


@dataclass(frozen=True, slots=True)
class DerivationResult:
    """What :func:`derive_query_workspaces` wrote."""

    target_root: Path
    manifest_path: Path
    pairs: tuple[tuple[str, int], ...]
    skipped: tuple[str, ...]
    openkos_version: str
    executable: str


@dataclass(frozen=True, slots=True)
class DerivedManifest:
    """``derived-manifest.json`` as typed values (what ``afg experiment b`` needs)."""

    source_run: str
    executable: str
    openkos_version: str
    sufficiency_check: bool
    settings: dict[str, Any]
    pairs: tuple[dict[str, Any], ...]
    skipped: tuple[str, ...]


def executable_for_version(
    version: str,
    *,
    pinned_version: str,
    pinned_executable: str,
    hosted_version: str,
    hosted_executable: str,
) -> str:
    """The executable of the OpenKOS ``version`` that compiled a run (formal or hosted install).

    Raises:
        ExecutableVersionError: the version is neither of the two installs; pass the executable
            explicitly.
    """
    if version == pinned_version:
        return pinned_executable
    if version == hosted_version:
        return hosted_executable
    raise ExecutableVersionError(
        f"The source run was compiled with OpenKOS {version}, which is neither the pinned "
        f"{pinned_version} nor the hosted {hosted_version}; pass the executable explicitly "
        "(--openkos-executable)."
    )


def _source_pairs(
    source_root: Path, series: Sequence[str] | None
) -> tuple[list[tuple[str, int, str]], list[str]]:
    """``(series, run, openkos_version)`` of every finished pair, and the skipped ones.

    A pair is finished when its ``run-<r>.manifest.json`` (written last by the extraction) says
    ``status: ok`` and its bundle exists.
    """
    pairs: list[tuple[str, int, str]] = []
    skipped: list[str] = []
    for series_dir in sorted(p for p in source_root.iterdir() if p.is_dir()):
        if series is not None and series_dir.name not in series:
            continue
        for workspace in sorted(series_dir.iterdir()):
            match = _RUN_DIR.match(workspace.name)
            if match is None or not workspace.is_dir():
                continue
            run = int(match.group(1))
            manifest = series_dir / f"{workspace.name}.manifest.json"
            version: str | None = None
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if data.get("status") == "ok":
                    version = data.get("openkos_version")
            if version is None or not (workspace / "bundle").is_dir():
                skipped.append(f"{series_dir.name}/{workspace.name}")
                continue
            pairs.append((series_dir.name, run, str(version)))
    return pairs, skipped


def _inspect_source(
    source_root: Path, series: Sequence[str] | None
) -> tuple[list[tuple[str, int, str]], list[str], str]:
    if not source_root.is_dir():
        raise FileNotFoundError(f"No source run at {source_root}.")
    pairs, skipped = _source_pairs(source_root, series)
    if not pairs:
        raise FileNotFoundError(f"No finished workspace in {source_root}.")
    versions = {version for _, _, version in pairs}
    if len(versions) > 1:
        raise ExecutableVersionError(
            f"The source run was compiled with more than one OpenKOS version "
            f"({', '.join(sorted(versions))}); derive one version at a time with --series."
        )
    return pairs, skipped, next(iter(versions))


def source_openkos_version(source_root: Path, series: Sequence[str] | None = None) -> str:
    """The single OpenKOS version that compiled the finished workspaces of ``source_root``.

    Raises:
        FileNotFoundError: no source run or no finished workspace.
        ExecutableVersionError: the source mixes versions.
    """
    return _inspect_source(source_root, series)[2]


def _set_key(text: str, key: str, value: str, *, executable: str, version: str) -> str:
    current = read_config_value(text, key)
    if current == value or (current is None and _PACKAGED_DEFAULTS.get(key) == value):
        return text
    require_config_key(text, key, executable=executable, version=version)
    return ensure_config_keys(text, {key: value})


def _derived_config(
    text: str, settings: QuerySideSettings, run: int, *, executable: str, version: str
) -> str:
    out = drop_config_keys(text, DROPPED_KEYS)
    wanted = {
        "backend": settings.backend,
        "model": settings.generative_model,
        "temperature": str(settings.temperature),
        "seed": str(settings.base_seed + run),
        "sufficiency_check": "true" if settings.sufficiency_check else "false",
    }
    if settings.context_window is not None:
        wanted["context_window"] = str(settings.context_window)
    for key, value in wanted.items():
        out = _set_key(out, key, value, executable=executable, version=version)
    return out


def derive_query_workspaces(
    *,
    source_root: Path,
    target_root: Path,
    settings: QuerySideSettings,
    executable: str,
    runner: CommandRunner,
    series: Sequence[str] | None = None,
    overwrite: bool = False,
    generated_at: str | None = None,
) -> DerivationResult:
    """Copy the finished workspaces of ``source_root`` to ``target_root`` with query-side config.

    ``executable`` is the OpenKOS that compiled the source; its ``--version`` must equal the one
    the source manifests record. The copy is staged next to ``target_root`` and renamed when
    complete, so a failure leaves no partial directory.

    Raises:
        FileNotFoundError: ``source_root`` has no finished workspace.
        DerivedWorkspaceExistsError: ``target_root`` exists and ``overwrite`` is false.
        ExecutableVersionError: the source mixes versions or ``executable`` is another one.
        MissingCapabilitiesError: a key to write is unknown to the source's OpenKOS version.
    """
    pairs, skipped, version = _inspect_source(source_root, series)
    reported = runner.run([executable, "--version"])
    actual = parse_version(reported.stdout) if reported.returncode == 0 else None
    if actual != version:
        raise ExecutableVersionError(
            f"{executable} reports OpenKOS {actual or 'an unreadable version'}, but the source "
            f"run was compiled with {version}; query it with the version that compiled it."
        )
    if target_root.exists() and not overwrite:
        raise DerivedWorkspaceExistsError(f"The derived directory {target_root} already exists.")

    stage = target_root.parent / f".{target_root.name}.partial"
    shutil.rmtree(stage, ignore_errors=True)
    try:
        for series_id, run, _ in pairs:
            destination = stage / series_id / f"run-{run}"
            shutil.copytree(source_root / series_id / f"run-{run}", destination)
            config = destination / "openkos.yaml"
            config.write_text(
                _derived_config(
                    config.read_text(encoding="utf-8"),
                    settings,
                    run,
                    executable=executable,
                    version=version,
                ),
                encoding="utf-8",
            )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "generated_by": DERIVED_GENERATOR,
            "generated_at": generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_run": source_root.name,
            "source_root": project_relative(source_root),
            "workspace": project_relative(target_root),
            "executable": executable,
            "openkos_version": version,
            "sufficiency_check": settings.sufficiency_check,
            "settings": {
                "backend": settings.backend,
                "generative_model": settings.generative_model,
                "base_seed": settings.base_seed,
                "temperature": settings.temperature,
                "context_window": settings.context_window,
                "sufficiency_check": settings.sufficiency_check,
                "dropped_keys": list(DROPPED_KEYS),
            },
            "pairs": [{"series": s, "run": r, "seed": settings.base_seed + r} for s, r, _ in pairs],
            "skipped": skipped,
        }
        (stage / DERIVED_MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        if target_root.exists():
            shutil.rmtree(target_root)
        stage.rename(target_root)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return DerivationResult(
        target_root=target_root,
        manifest_path=target_root / DERIVED_MANIFEST_NAME,
        pairs=tuple((s, r) for s, r, _ in pairs),
        skipped=tuple(skipped),
        openkos_version=version,
        executable=executable,
    )


def load_derived_manifest(target_root: Path) -> DerivedManifest:
    """Read ``derived-manifest.json`` of a derived directory.

    Raises:
        FileNotFoundError: the directory is not a finished derivation.
    """
    path = target_root / DERIVED_MANIFEST_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"{target_root} has no {DERIVED_MANIFEST_NAME}: it is not a finished derivation."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return DerivedManifest(
        source_run=str(data["source_run"]),
        executable=str(data["executable"]),
        openkos_version=str(data["openkos_version"]),
        sufficiency_check=bool(data["sufficiency_check"]),
        settings=dict(data["settings"]),
        pairs=tuple(data["pairs"]),
        skipped=tuple(data["skipped"]),
    )
