"""Reproducibility fields recorded in the manifest of an Experiment B run.

A run is only reproducible if the exact model files, runtime versions, retrieval parameters
and question set are known. Ollama tags (``qwen3:8b``) can be re-pointed to other weights,
so the manifest records the content digest of each model, plus the Ollama and OpenKOS
versions, the effective C1 parameters, the SHA-256 of the question file and whether the
working tree had uncommitted changes.

The probes are behind the :class:`ProvenanceProbe` protocol so tests inject fakes and need
no network. Every probe degrades to ``None`` (recorded as ``null``) instead of failing: a
run must not be blocked because a version could not be read. The fields are forward-only:
manifests written before this module existed simply lack them.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from afg.conditions.c1_retrieval import resolve_ollama_host
from afg.extraction.openkos.capabilities import parse_version
from afg.extraction.openkos.commands import SubprocessRunner
from afg.shared.paths import EXPERIMENT_A_DIR, EXPERIMENT_B_DIR, PROJECT_ROOT

DIGEST_SOURCE = "ollama /api/tags"
C1_PARAM_KEYS = ("max_chars", "overlap_turns", "k")
_TIMEOUT_S = 5.0


class ProvenanceProbe(Protocol):
    """What the runner needs to know about the machine; every answer may be ``None``."""

    def model_digests(self) -> Mapping[str, str] | None:
        """Installed model name -> content digest, or ``None`` when Ollama is unreachable."""
        ...

    def ollama_version(self) -> str | None: ...

    def openkos_version(self) -> str | None: ...

    def git_dirty(self) -> bool | None: ...


class LiveProbe:
    """:class:`ProvenanceProbe` backed by the local Ollama, ``openkos`` and ``git``."""

    def __init__(self, host: str | None = None, openkos_executable: str = "openkos") -> None:
        self._host = host or resolve_ollama_host()
        self._openkos = openkos_executable

    def _get_json(self, path: str) -> Any:
        try:
            with urllib.request.urlopen(f"{self._host}{path}", timeout=_TIMEOUT_S) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def model_digests(self) -> Mapping[str, str] | None:
        payload = self._get_json("/api/tags")
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            return None
        return {
            str(model["name"]): str(model["digest"])
            for model in payload["models"]
            if isinstance(model, dict) and model.get("name") and model.get("digest")
        }

    def ollama_version(self) -> str | None:
        payload = self._get_json("/api/version")
        version = payload.get("version") if isinstance(payload, dict) else None
        return str(version) if version else None

    def openkos_version(self) -> str | None:
        try:
            done = SubprocessRunner().run([self._openkos, "--version"])
        except OSError:
            return None
        return parse_version(done.stdout) if done.returncode == 0 else None

    def git_dirty(self) -> bool | None:
        """Uncommitted changes outside the experiment report folders (runs write there)."""
        excluded = [
            f":(exclude){d.relative_to(PROJECT_ROOT).as_posix()}"
            for d in (EXPERIMENT_A_DIR, EXPERIMENT_B_DIR)
        ]
        try:
            done = subprocess.run(
                ["git", "status", "--porcelain", "--", ".", *excluded],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return bool(done.stdout.strip())


def _with_tag(name: str) -> str:
    last = name.rsplit("/", 1)[-1]
    return name if ":" in last else f"{name}:latest"


def _digest_of(model: str, digests: Mapping[str, str] | None) -> str | None:
    if digests is None:
        return None
    by_tag = {_with_tag(name): digest for name, digest in digests.items()}
    return by_tag.get(_with_tag(model))


def file_sha256(path: Path | None) -> str | None:
    """SHA-256 of the file bytes, or ``None`` when there is no such file."""
    if path is None or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_provenance(
    probe: ProvenanceProbe,
    *,
    generative_model: str,
    judge_model: str | None = None,
    embedding_model: str,
    c1_params: Mapping[str, Any] | None = None,
    questions_path: Path | None = None,
    c2_extraction: str | None = None,
    c3_workspaces: str | None = None,
) -> dict[str, Any]:
    """The reproducibility fields to merge into the run manifest (all JSON-ready)."""
    digests = probe.model_digests()
    return {
        "generative_model_digest": _digest_of(generative_model, digests),
        "judge_model_digest": _digest_of(judge_model, digests) if judge_model else None,
        "embedding_model_digest": _digest_of(embedding_model, digests),
        "model_digest_source": (
            DIGEST_SOURCE if digests is not None else "unavailable: Ollama not reachable"
        ),
        "ollama_version": probe.ollama_version(),
        "openkos_version": probe.openkos_version(),
        "c1_params": {
            key: c1_params[key] for key in C1_PARAM_KEYS if c1_params and key in c1_params
        },
        "c2_extraction": c2_extraction,
        "c3_workspaces": c3_workspaces,
        "questions_sha256": file_sha256(questions_path),
        "git_dirty": probe.git_dirty(),
    }


_MISSING = "—"
_DIGEST_SHOWN = 12
_COMMIT_SHOWN = 8


def _short(value: Any, length: int) -> str:
    return str(value)[:length] if value else _MISSING


def manifest_provenance_table(manifests: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    """One row per run manifest with the fields that make a run reproducible.

    Digests are shortened to 12 characters and commits to 8. A field the manifest lacks
    (manifests written before provenance was recorded) reads ``—`` instead of failing.
    """
    rows = []
    for name, manifest in manifests.items():
        settings = manifest.get("settings") or {}
        rows.append(
            {
                "run": name,
                "conditions": ", ".join(manifest.get("conditions") or []),
                "runs": settings.get("runs"),
                "generative_model": settings.get("generative_model") or _MISSING,
                "generative_digest": _short(manifest.get("generative_model_digest"), _DIGEST_SHOWN),
                "judge_model": settings.get("judge_model") or _MISSING,
                "judge_digest": _short(manifest.get("judge_model_digest"), _DIGEST_SHOWN),
                "embedding_digest": _short(manifest.get("embedding_model_digest"), _DIGEST_SHOWN),
                "ollama": manifest.get("ollama_version") or _MISSING,
                "openkos": manifest.get("openkos_version") or _MISSING,
                "commit": _short(manifest.get("git_commit"), _COMMIT_SHOWN),
                "git_dirty": manifest.get("git_dirty"),
            }
        )
    return pd.DataFrame(rows)
