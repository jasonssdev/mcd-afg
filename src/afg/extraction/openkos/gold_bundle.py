"""Build the C3 workspace of one C2 run: the same bundle with its decisions from the gold.

C3 (thesis section 5.3) queries a base compiled from the adjudicated human annotation. To make
C3 -> C2 isolate the error of the decision extraction (ADR 0013), the C3 workspace of run ``r``
is the C2 workspace of run ``r`` with ONE difference: ``bundle/decisions/`` holds the gold
reference decisions instead of the extracted ones. Concepts, events, people, projects, sources
and ``raw/`` are copied untouched, ``openkos.yaml`` too (the seed and the temperature are what
``require_reproducible`` checks), and the search indexes are rebuilt with ``openkos reindex``.

A gold decision is written in the layout :mod:`~afg.extraction.openkos.bundle_reader` reads
(``# title``, description, value, ``> quote``, ``## Related``), so the C2 evidence code maps a C3
citation exactly as it maps a C2 one:

* the quote is the transcript text of the turns that carry the gold dialogue acts (the
  reader maps a quote back to the acts of every turn it overlaps, so evidence always comes back as
  whole turns); the reader keeps only the first quote that maps, so evidence made of
  non-consecutive turns keeps its first run and is reported in ``evidence_partial``, as is a
  quote that maps to another occurrence of the same text. Gold acts are finer than turns, so
  the evidence of a C3 citation is the whole turn, exactly the granularity C2 has;
* a gold decision without evidence that can be located in the transcript cannot be a citable
  concept: it is dropped and listed with the reason in the manifest, never silently;
* the adjudicated cross-meeting relations are links under ``## Related`` on both decisions,
  with the relation type as the link description;
* ``generated.by`` is :data:`GOLD_GENERATOR`, so a file can never pass for an OpenKOS one.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from afg.conditions.c1_chunking import FrozenTurn
from afg.evaluation.reference import ReferenceDecision, ReferenceSet
from afg.extraction.openkos.bundle_reader import DECISIONS_DIRNAME
from afg.extraction.openkos.capabilities import parse_version
from afg.extraction.openkos.commands import CommandRunner, OpenKosError
from afg.extraction.openkos.evidence import EvidenceMatch, load_meeting_text, locate_quote
from afg.extraction.openkos.workspace import OpenKosCommandError
from afg.extraction.openkos_adapter import BUNDLE_DIRNAME, project_relative
from afg.shared.csvio import open_csv_reader
from afg.shared.paths import GOLD_RELATIONS_DIR, TRANSCRIPTS_DIR

GOLD_GENERATOR = "afg/c3-gold"
MANIFEST_NAME = "c3-manifest.json"
INDEX_NAME = "index.md"
_INDEX_DECISIONS_HEADING = "# Decisions"
_INDEX_HEADING = "# "
_OPENKOS_INDEX_DIRNAME = ".openkos"
_NO_RELATION = "no_relacionada"
_DIRECTION_OK = "si"
_SOURCE_NOTE = "source this was extracted from"
NO_EVIDENCE = "no_evidence"
EVIDENCE_NOT_IN_TRANSCRIPT = "evidence_not_in_transcript"
QUOTE_NOT_LOCATED = "quote_not_located"

# Relation label (Spanish, as annotated) -> how the later decision relates to the earlier one,
# and the reverse reading written on the earlier decision.
_RELATION_VERBS: dict[str, tuple[str, str]] = {
    "reafirma": ("reaffirms", "reaffirmed by"),
    "refina": ("refines", "refined by"),
    "reemplaza": ("replaces", "replaced by"),
    "revierte": ("reverts", "reverted by"),
}


class GoldWorkspaceExistsError(OpenKosError):
    """The C3 workspace already exists and overwriting was not requested."""


@dataclass(frozen=True, slots=True)
class GoldRelation:
    """An accepted cross-meeting relation: ``later`` acts on ``earlier``."""

    earlier_id: str
    later_id: str
    relation: str


@dataclass(frozen=True, slots=True)
class DroppedDecision:
    """A gold decision that could not become a bundle file, and why."""

    decision_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class GoldBuildResult:
    """What :func:`build_gold_workspace` produced."""

    workspace: Path
    manifest_path: Path
    decisions_written: int
    dropped: tuple[DroppedDecision, ...]
    evidence_partial: tuple[str, ...]
    relations_written: int
    relations_dropped: tuple[str, ...]
    openkos_version: str | None


@dataclass(frozen=True, slots=True)
class _GoldFile:
    reference: ReferenceDecision
    slug: str
    description: str
    quotes: tuple[str, ...]


def load_gold_relations(
    series_id: str, *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> tuple[GoldRelation, ...]:
    """The accepted pairs of ``<series_id>.candidates.adjudicated.csv`` (none if no file).

    Accepted means a final relation other than ``no_relacionada`` whose direction was confirmed
    (``final_direction_ok == si``); anything unadjudicated is left out.
    """
    path = relations_dir / f"{series_id}.candidates.adjudicated.csv"
    if not path.is_file():
        return ()
    accepted: list[GoldRelation] = []
    with open_csv_reader(path) as handle:
        for row in csv.DictReader(handle):
            relation = (row.get("final_relation") or "").strip()
            direction = (row.get("final_direction_ok") or "").strip()
            earlier = (row.get("earlier_decision_id") or "").strip()
            later = (row.get("later_decision_id") or "").strip()
            if not (relation and earlier and later) or relation == _NO_RELATION:
                continue
            if direction != _DIRECTION_OK:
                continue
            accepted.append(GoldRelation(earlier, later, relation))
    return tuple(accepted)


def _slug(decision_id: str) -> str:
    return decision_id.lower().replace(".", "-")


def _runs(turns: Sequence[FrozenTurn]) -> list[list[FrozenTurn]]:
    """Group ``turns`` (in transcript order) into runs of consecutive turn indices."""
    runs: list[list[FrozenTurn]] = []
    for turn in turns:
        if runs and turn.turn_index == runs[-1][-1].turn_index + 1:
            runs[-1].append(turn)
        else:
            runs.append([turn])
    return runs


def _quote_of(run: Sequence[FrozenTurn]) -> str:
    """One line with the text of ``run``; later turns keep their ``ROLE: `` prefix."""
    parts = [" ".join(run[0].text.split())]
    parts += [f"{turn.role}: {' '.join(turn.text.split())}" for turn in run[1:]]
    return " ".join(parts)


def _plan_file(
    reference: ReferenceDecision,
    meetings: dict[str, tuple[str, list[FrozenTurn]]],
    transcripts_dir: Path,
) -> tuple[_GoldFile | None, DroppedDecision | None, bool]:
    """The file to write for ``reference``, or why not; the flag marks partial evidence."""
    decision_id = reference.decision_id
    if reference.evidence is None:
        return None, DroppedDecision(decision_id, NO_EVIDENCE), False
    meeting_id = reference.meeting_id
    if meeting_id not in meetings:
        meetings[meeting_id] = load_meeting_text(meeting_id, transcripts_dir)
    body, turns = meetings[meeting_id]
    acts = set(reference.evidence.dialogue_act_ids)
    hit = sorted(
        (turn for turn in turns if acts & set(turn.dialogue_act_ids)),
        key=lambda turn: turn.turn_index,
    )
    if not hit:
        return None, DroppedDecision(decision_id, EVIDENCE_NOT_IN_TRANSCRIPT), False
    runs = _runs(hit)
    quotes = tuple(_quote_of(run) for run in runs)
    located = locate_quote(meeting_id, body, turns, quotes[0])
    if not isinstance(located, EvidenceMatch):
        return None, DroppedDecision(decision_id, QUOTE_NOT_LOCATED), False
    # The reader widens gold acts to whole turns (as it does for C2); what matters is that no
    # turn is lost or replaced by another occurrence of the same text.
    expected = {act for turn in hit for act in turn.dialogue_act_ids}
    exact = set(located.span.dialogue_act_ids) == expected
    description = f"{reference.decision_object}: {reference.content}"
    return _GoldFile(reference, _slug(decision_id), description, quotes), None, not exact


def _relation_links(
    gold: _GoldFile,
    relations: Iterable[GoldRelation],
    written: dict[str, _GoldFile],
) -> list[str]:
    links: list[str] = []
    decision_id = gold.reference.decision_id
    for relation in relations:
        verbs = _RELATION_VERBS.get(relation.relation, (relation.relation, relation.relation))
        if relation.later_id == decision_id and relation.earlier_id in written:
            other, verb = written[relation.earlier_id], verbs[0]
        elif relation.earlier_id == decision_id and relation.later_id in written:
            other, verb = written[relation.later_id], verbs[1]
        else:
            continue
        links.append(f"- [{other.description}](/{DECISIONS_DIRNAME}/{other.slug}.md) — {verb}")
    return links


def _render(gold: _GoldFile, related: list[str], generated_at: str) -> str:
    reference = gold.reference
    source = f"sources/{reference.meeting_id.lower()}"
    metadata: dict[str, object] = {
        "type": "Decision",
        "title": reference.content,
        "description": gold.description,
        "tags": [],
        "generated": {"by": GOLD_GENERATOR, "at": generated_at},
        "status": "stable",
        "version": 1,
        "freshness": "snapshot",
        "sensitivity": "private",
        "provenance": [source],
        "sources": [{"id": source, "resource": f"/{source}.md"}],
    }
    frontmatter = yaml.safe_dump(
        metadata, default_flow_style=False, allow_unicode=True, sort_keys=True
    )
    quotes = "\n".join(f"> {quote}" for quote in gold.quotes)
    head = f"# {reference.content}\n\n{gold.description}\n\n{reference.content}\n\n{quotes}"
    links = [f"- [{source}](/{source}.md) — {_SOURCE_NOTE}", *related]
    return f"---\n{frontmatter}---\n\n{head}\n\n## Related\n\n" + "\n".join(links) + "\n"


def _rewrite_index(index_path: Path, written: Iterable[_GoldFile]) -> None:
    """Replace the ``# Decisions`` section of ``bundle/index.md`` with the gold decisions."""
    if not index_path.is_file():
        return
    entries = [
        f"* [{gold.reference.content}](/{DECISIONS_DIRNAME}/{gold.slug}.md) - {gold.description}"
        for gold in written
    ]
    lines = index_path.read_text(encoding="utf-8").split("\n")
    section = ["", _INDEX_DECISIONS_HEADING, "", *entries, ""]
    if _INDEX_DECISIONS_HEADING in lines:
        start = lines.index(_INDEX_DECISIONS_HEADING)
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith(_INDEX_HEADING)),
            len(lines),
        )
        lines[start:end] = section[1:]
    else:
        lines.extend(section)
    index_path.write_text("\n".join(lines), encoding="utf-8")


def _ignore_for(c2_workspace: Path) -> Callable[[str, list[str]], set[str]]:
    bundle = c2_workspace / BUNDLE_DIRNAME

    def ignore(directory: str, names: list[str]) -> set[str]:
        here = Path(directory)
        if here == c2_workspace:
            return {_OPENKOS_INDEX_DIRNAME} & set(names)
        if here == bundle:
            return {DECISIONS_DIRNAME} & set(names)
        return set()

    return ignore


def build_gold_workspace(
    *,
    series_id: str,
    c2_run: str,
    run: int,
    c2_workspace: Path,
    target: Path,
    reference: ReferenceSet,
    relations: Sequence[GoldRelation],
    runner: CommandRunner,
    executable: str,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    overwrite: bool = False,
    generated_at: str | None = None,
) -> GoldBuildResult:
    """Write the C3 workspace ``target`` from ``c2_workspace`` and the gold ``reference``.

    Raises:
        FileNotFoundError: ``c2_workspace`` has no bundle.
        GoldWorkspaceExistsError: ``target`` exists and ``overwrite`` is false.
        OpenKosCommandError: ``openkos reindex`` failed.
    """
    if not (c2_workspace / BUNDLE_DIRNAME).is_dir():
        raise FileNotFoundError(f"No bundle in the C2 workspace {c2_workspace}.")
    if target.exists():
        if not overwrite:
            raise GoldWorkspaceExistsError(f"The C3 workspace {target} already exists.")
        shutil.rmtree(target)
    stamp = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    meetings: dict[str, tuple[str, list[FrozenTurn]]] = {}
    planned: list[_GoldFile] = []
    dropped: list[DroppedDecision] = []
    inexact: list[str] = []
    for decision in reference.decisions:
        gold, miss, not_exact = _plan_file(decision, meetings, transcripts_dir)
        if gold is not None:
            planned.append(gold)
        if miss is not None:
            dropped.append(miss)
        if not_exact:
            inexact.append(decision.decision_id)
    written = {gold.reference.decision_id: gold for gold in planned}
    linked = {
        (r.earlier_id, r.later_id)
        for r in relations
        if r.earlier_id in written and r.later_id in written
    }
    relations_dropped = tuple(
        f"{r.earlier_id}>{r.later_id}"
        for r in relations
        if (r.earlier_id, r.later_id) not in linked
    )

    shutil.copytree(c2_workspace, target, ignore=_ignore_for(c2_workspace))
    decisions_dir = target / BUNDLE_DIRNAME / DECISIONS_DIRNAME
    decisions_dir.mkdir(parents=True, exist_ok=True)
    for gold in sorted(planned, key=lambda g: g.slug):
        related = _relation_links(gold, relations, written)
        (decisions_dir / f"{gold.slug}.md").write_text(
            _render(gold, related, stamp), encoding="utf-8"
        )
    _rewrite_index(target / BUNDLE_DIRNAME / INDEX_NAME, sorted(planned, key=lambda g: g.slug))

    reindex = runner.run([executable, "reindex", "--force"], cwd=target)
    if reindex.returncode != 0:
        raise OpenKosCommandError(f"reindex exited {reindex.returncode}: {reindex.stderr[-500:]}")
    version_run = runner.run([executable, "--version"])
    version = parse_version(version_run.stdout) if version_run.returncode == 0 else None

    manifest_path = target / MANIFEST_NAME
    manifest = {
        "schema_version": 1,
        "series_id": series_id,
        "c2_run": c2_run,
        "run": run,
        "c2_workspace": project_relative(c2_workspace),
        "workspace": project_relative(target),
        "generated_by": GOLD_GENERATOR,
        "generated_at": stamp,
        "openkos_version": version,
        "reference_decisions": len(reference.decisions),
        "decisions_written": len(planned),
        "dropped": [{"id": d.decision_id, "reason": d.reason} for d in dropped],
        "evidence_partial": inexact,
        "relations_written": len(linked),
        "relations_dropped": list(relations_dropped),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return GoldBuildResult(
        workspace=target,
        manifest_path=manifest_path,
        decisions_written=len(planned),
        dropped=tuple(dropped),
        evidence_partial=tuple(inexact),
        relations_written=len(linked),
        relations_dropped=relations_dropped,
        openkos_version=version,
    )
