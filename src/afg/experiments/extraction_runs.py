"""Analysis of exploratory OpenKOS extraction runs (``reports/experiment-a/<run-name>/``).

Pure functions over the files written by ``afg experiment a`` (``manifest.json`` and
``extracciones.jsonl``). They describe the runs themselves: how many decisions each one
extracted per meeting, how much two runs agree with each other, whether a repeated seed
reproduces the same output, and the provenance of the run. Nothing here calls a model, and
nothing here matches extracted decisions against the adjudicated reference: precision and
recall are the Experiment A evaluation, which waits for the pinned OpenKOS version (ADR 0005,
ADR 0006).

The overlap between two runs is measured on the pair ``(meeting_id, content)``: two
extractions are the same decision when they come from the same meeting and carry the same
content text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from afg.evaluation.reference import ReferenceSet

__all__ = [
    "ExtractionRun",
    "ReproducibilityResult",
    "decisions_matching",
    "decisions_per_meeting",
    "load_extraction_runs",
    "pairwise_overlap",
    "provenance_table",
    "reference_counts_per_meeting",
    "reproducibility_check",
]

MANIFEST_FILENAME = "manifest.json"
RECORDS_FILENAME = "extracciones.jsonl"
_DIGEST_PREFIX = 12


@dataclass(frozen=True, slots=True)
class ExtractionRun:
    """One run (one line of ``extracciones.jsonl``) with the manifest of its directory."""

    run_name: str
    run: int
    seed: int | None
    record: dict[str, Any]
    manifest: dict[str, Any]

    @property
    def label(self) -> str:
        return f"{self.run_name} / corrida {self.run}"

    @property
    def decisions(self) -> list[dict[str, Any]]:
        return list(self.record.get("decisions", []))

    def keys(self) -> set[tuple[str, str]]:
        """The ``(meeting_id, content)`` pairs of the run."""
        return {(d["meeting_id"], d["content"]) for d in self.decisions}


def load_extraction_runs(run_dirs: Iterable[Path]) -> list[ExtractionRun]:
    """Read every run of the given ``reports/experiment-a/<run-name>/`` directories.

    The seed of a run is the base seed of the manifest plus the run number, as the workspace
    orchestrator derives it. Runs keep the order of the directories and of the file.
    """
    runs: list[ExtractionRun] = []
    for directory in run_dirs:
        manifest = json.loads((directory / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        base_seed = manifest.get("openkos", {}).get("seed")
        lines = (directory / RECORDS_FILENAME).read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            record = json.loads(line)
            seed = None if base_seed is None else int(base_seed) + int(record["run"])
            runs.append(
                ExtractionRun(
                    run_name=directory.name,
                    run=int(record["run"]),
                    seed=seed,
                    record=record,
                    manifest=manifest,
                )
            )
    return runs


def decisions_per_meeting(
    runs: Sequence[ExtractionRun], meeting_ids: Sequence[str]
) -> pd.DataFrame:
    """Tidy table: decisions extracted per run and meeting (zero when a meeting has none)."""
    rows = []
    for item in runs:
        counts = pd.Series([d["meeting_id"] for d in item.decisions], dtype=str).value_counts()
        for meeting_id in meeting_ids:
            rows.append(
                {
                    "run_name": item.run_name,
                    "run": item.run,
                    "seed": item.seed,
                    "meeting_id": meeting_id,
                    "n_decisions": int(counts.get(meeting_id, 0)),
                }
            )
    return pd.DataFrame(rows, columns=["run_name", "run", "seed", "meeting_id", "n_decisions"])


def pairwise_overlap(runs: Sequence[ExtractionRun]) -> pd.DataFrame:
    """Overlap of every pair of runs by ``(meeting_id, content)``: common count and Jaccard."""
    rows = []
    for first, second in combinations(runs, 2):
        keys_a, keys_b = first.keys(), second.keys()
        common = len(keys_a & keys_b)
        union = len(keys_a | keys_b)
        rows.append(
            {
                "run_a": first.label,
                "run_b": second.label,
                "n_a": len(keys_a),
                "n_b": len(keys_b),
                "common": common,
                "union": union,
                "jaccard": common / union if union else 1.0,
            }
        )
    return pd.DataFrame(
        rows, columns=["run_a", "run_b", "n_a", "n_b", "common", "union", "jaccard"]
    )


@dataclass(frozen=True, slots=True)
class ReproducibilityResult:
    """Whether two runs that used the same seed produced the same decisions."""

    seed: int | None
    identical: bool
    n_decisions: tuple[int, int]


def reproducibility_check(first: ExtractionRun, second: ExtractionRun) -> ReproducibilityResult:
    """Compare two runs of the same seed; ``identical`` is equality of every decision field.

    Raises:
        ValueError: the runs did not use the same seed, so they are not expected to match.
    """
    if first.seed != second.seed:
        raise ValueError(
            f"Las corridas no usaron la misma semilla ({first.seed} y {second.seed}); "
            "no se espera que coincidan."
        )
    return ReproducibilityResult(
        seed=first.seed,
        identical=first.decisions == second.decisions,
        n_decisions=(len(first.decisions), len(second.decisions)),
    )


def reference_counts_per_meeting(reference: ReferenceSet, meeting_ids: Sequence[str]) -> pd.Series:
    """Adjudicated reference decisions per meeting (``ReferenceSet`` already applies the rule)."""
    counts = pd.Series([d.meeting_id for d in reference.decisions], dtype=str).value_counts()
    return pd.Series(
        {m: int(counts.get(m, 0)) for m in meeting_ids}, name="decisiones de referencia"
    )


def decisions_matching(item: ExtractionRun, pattern: str) -> pd.DataFrame:
    """Extracted decisions of a run whose content matches ``pattern`` (case-insensitive)."""
    regex = re.compile(pattern, re.IGNORECASE)
    rows = [
        {
            "meeting_id": d["meeting_id"],
            "decision_object": d["decision_object"],
            "content": d["content"],
        }
        for d in item.decisions
        if regex.search(d["content"])
    ]
    return pd.DataFrame(rows, columns=["meeting_id", "decision_object", "content"])


def _minutes(manifest: dict[str, Any]) -> float | None:
    start, end = manifest.get("created_at"), manifest.get("updated_at")
    if not start or not end:
        return None
    delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    return round(delta.total_seconds() / 60, 1)


def provenance_table(runs: Sequence[ExtractionRun]) -> pd.DataFrame:
    """One row per run directory: version, models, seed, commit and duration from the manifest.

    The duration is ``updated_at - created_at`` of the manifest, i.e. the whole directory
    (all of its runs), in minutes.
    """
    rows: dict[str, dict[str, Any]] = {}
    for item in runs:
        if item.run_name in rows:
            continue
        manifest = item.manifest
        openkos = manifest.get("openkos", {})
        rows[item.run_name] = {
            "versión de OpenKOS": ", ".join(openkos.get("versions", [])),
            "modelo generativo": openkos.get("generative_model"),
            "digest del modelo generativo": str(openkos.get("generative_model_digest", ""))[
                :_DIGEST_PREFIX
            ],
            "modelo de embeddings": openkos.get("embedding_model"),
            "digest del modelo de embeddings": str(openkos.get("embedding_model_digest", ""))[
                :_DIGEST_PREFIX
            ],
            "temperatura": openkos.get("temperature"),
            "semilla base": openkos.get("seed"),
            "corridas": manifest.get("runs"),
            "commit": manifest.get("git_commit"),
            "duración (min)": _minutes(manifest),
        }
    return pd.DataFrame.from_dict(rows, orient="index")
