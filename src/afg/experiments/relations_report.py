"""Relation report of Experiment A (``afg experiment a-relations``, ADR 0016).

For each ``(series, run)`` workspace of an extraction run (``data/interim/openkos/<run-name>/
<SERIES>/run-<r>``) this reads the decisions of the bundle, aligns them to the gold decisions
(ADR 0011, ADR 0012), reads the findings of ``openkos revisions`` and scores them against the gold
relations (:mod:`afg.evaluation.relations`). A workspace that cannot be read (no findings, schema
mismatch, unreadable bundle) becomes an entry with ``error`` and is left out of the pooled
figures, so one bad run does not hide the others.

Development series only (ADR 0005); the caller enforces it.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from afg.evaluation.alignment_analysis import scored_matches
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.relations import GoldPair, RelationCase, score_relations
from afg.evaluation.scoring import SimilarityFn
from afg.extraction.openkos.bundle_reader import read_decision_bundle
from afg.extraction.openkos.commands import CommandRunner, OpenKosError
from afg.extraction.openkos.event_dates import POSITION_LETTERS
from afg.extraction.openkos.revisions import read_revision_findings, run_revisions

__all__ = ["discover_runs", "score_workspaces"]

BUNDLE_DIRNAME = "bundle"
_RUN_DIR = re.compile(r"^run-(\d+)$")


def discover_runs(series_dir: Path) -> list[tuple[int, Path]]:
    """The ``run-<r>`` workspaces (folders with a ``bundle/``) of a series, by run number."""
    runs = [
        (int(match.group(1)), path)
        for path in series_dir.iterdir()
        if (match := _RUN_DIR.match(path.name)) and (path / BUNDLE_DIRNAME).is_dir()
    ]
    return sorted(runs)


def _entry(
    *,
    series_id: str,
    run: int,
    workspace: Path,
    reference: Sequence[ReferenceDecision],
    gold: tuple[GoldPair, ...],
    similarity: SimilarityFn,
    tau: float,
    transcripts_dir: Path,
) -> tuple[dict[str, Any], RelationCase]:
    decisions = read_decision_bundle(
        workspace / BUNDLE_DIRNAME,
        series_id=series_id,
        meeting_ids=[f"{series_id}{letter}" for letter in POSITION_LETTERS],
        transcripts_dir=transcripts_dir,
    ).decisions
    matches = scored_matches(reference, decisions, similarity, tau=tau)
    mapping = {m.predicted.id: m.reference.decision_id for m in matches}
    findings = read_revision_findings(workspace)
    case = RelationCase(f"{series_id}/run-{run}", gold, findings.relations, mapping)
    entry: dict[str, Any] = {
        "series": series_id,
        "run": run,
        "alignment": {
            "machine_decisions": len(decisions),
            "gold_decisions": len(reference),
            "aligned": len(matches),
        },
        "findings": {
            "n_relations": len(findings.relations),
            "by_verdict": dict(sorted(Counter(r.verdict for r in findings.relations).items())),
            "skipped_non_decision": findings.skipped_non_decision,
        },
        "score": score_relations([case]).to_dict(),
    }
    return entry, case


def score_workspaces(
    *,
    run_name: str,
    workspace_root: Path,
    series_ids: Sequence[str],
    reference_of: Callable[[str], Sequence[ReferenceDecision]],
    gold_of: Callable[[str], tuple[GoldPair, ...]],
    similarity: SimilarityFn,
    tau: float,
    transcripts_dir: Path,
    runner: CommandRunner | None = None,
    executable: str = "openkos",
    run_revisions_first: bool = False,
    report: Callable[[str], None] | None = None,
    partition: str = "development",
) -> dict[str, Any]:
    """Score every workspace of ``series_ids`` under ``workspace_root`` and pool the results.

    ``run_revisions_first`` runs ``openkos revisions --auto --all`` (needs ``runner``) in each
    workspace before reading it; otherwise the existing ``findings.db`` is read.
    """
    say = report or (lambda _line: None)
    entries: list[dict[str, Any]] = []
    cases: list[RelationCase] = []
    for series_id in series_ids:
        series_dir = workspace_root / series_id
        if not series_dir.is_dir():
            continue
        reference = reference_of(series_id)
        gold = gold_of(series_id)
        for run, workspace in discover_runs(series_dir):
            try:
                if run_revisions_first:
                    if runner is None:
                        raise OpenKosError("run_revisions_first needs a command runner.")
                    say(f"{series_id} run-{run}: openkos revisions --auto --all")
                    run_revisions(runner, executable, workspace)
                entry, case = _entry(
                    series_id=series_id,
                    run=run,
                    workspace=workspace,
                    reference=reference,
                    gold=gold,
                    similarity=similarity,
                    tau=tau,
                    transcripts_dir=transcripts_dir,
                )
            except (OpenKosError, FileNotFoundError) as exc:
                entries.append({"series": series_id, "run": run, "error": str(exc)})
                continue
            entries.append(entry)
            cases.append(case)
    pooled: Mapping[str, Any] = score_relations(cases).to_dict()
    return {
        "run_name": run_name,
        "partition": partition,
        "tau": tau,
        "alignment_scope": "origin_meetings",
        "series": list(series_ids),
        "n_errors": sum("error" in e for e in entries),
        "entries": entries,
        "pooled": dict(pooled),
    }
