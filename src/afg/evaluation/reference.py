"""The adjudicated human reference for Experiment A (OE2), loaded as decisions.

Source: ``data/processed/decisions/<SERIES>.decisions.adjudicated.csv``, the file written by
``afg gold adjudicate`` once the adjudicator has filled the ``final_*`` columns. The
per-annotator and the machine-generated base files are NOT references: they carry no
adjudicated verdict, so this loader refuses them.

## What counts as a reference decision

Annotation manual, section 2 (``docs/anotacion/manual-anotacion-oe1.md``): a row is a
reference decision if and only if ``final_status == "decision"``.

- ``no_decision`` (open proposal, question, opinion) is not a decision. It stays in the
  annotation set to measure false positives of the annotation guide, but the scoring unit
  here is the decision, so it is counted in :attr:`ReferenceSet.excluded` and not scored.
- ``compuesta`` is an instruction, not a verdict: the parent row is excluded and its
  ``-1``, ``-2``, ... child rows (each with its own status) are the decisions. A child
  marked ``decision`` is one reference decision; a child marked ``descartar`` is excluded.
- ``sin_soporte`` and ``descartar`` are excluded.

## Evidence

``source_sentence_id`` is the ``nite:id`` of the abstractive decision sentence, and the AMI
``summlink`` layer links it to the dialogue acts that support it
(:func:`afg.annotation.goldset.summlink_dialogue_act_ids`). Those ids are exact and are the
same ids the frozen transcripts carry, so they are preferred. When a sentence has no
``summlink`` entry the ``evidence_text`` quote is matched against the frozen transcript
(:func:`afg.extraction.openkos.evidence.locate_quote`); a decision that neither route maps
is kept (dropping it would silently shrink the reference) and listed in
:attr:`ReferenceSet.evidence_misses`.

## Speaker role

The role of a decision is the role (PM, ME, UI, ID) that spoke most of its evidence
dialogue acts; ties go to the earliest turn. ``roles`` keeps every role involved, because
some decisions are ratified across speakers.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from afg.annotation.goldset import summlink_dialogue_act_ids
from afg.conditions.c1_chunking import FrozenTurn
from afg.domain.decision import AnnotationStatus, Decision, DecisionStatus, EvidenceSpan
from afg.extraction.openkos.evidence import EvidenceMatch, load_meeting_text, locate_quote
from afg.shared.paths import AMI_DIR, GOLD_DECISIONS_DIR, TRANSCRIPTS_DIR

__all__ = [
    "NotAdjudicatedError",
    "ReferenceDecision",
    "ReferenceSet",
    "load_reference",
    "load_series_reference",
    "primary_role",
    "roles_of",
]

EvidenceMethod = Literal["sentence_id", "quote", "none"]

_REQUIRED_COLUMNS = ("decision_id", "meeting_id", "source_sentence_id", "final_status")
_QUOTE_SEPARATOR = " | "
_TRUNCATION_SUFFIX = " […truncated]"
_SPEAKER_PREFIX = re.compile(r"^[A-Z]:\s*")
_DECISION = AnnotationStatus.DECISION.value


class NotAdjudicatedError(ValueError):
    """The file is not a complete adjudicated decisions CSV."""


@dataclass(frozen=True, slots=True)
class ReferenceDecision:
    """One reference decision with the evidence and speaker role needed to score it."""

    decision_id: str
    series_id: str
    meeting_id: str
    decision_object: str
    content: str
    evidence: EvidenceSpan | None
    evidence_method: EvidenceMethod
    role: str | None
    roles: tuple[str, ...] = ()
    adjudicator: str | None = None

    def as_decision(self) -> Decision | None:
        """The domain :class:`Decision`, or ``None`` when no evidence could be mapped."""
        if self.evidence is None:
            return None
        return Decision(
            id=self.decision_id,
            series_id=self.series_id,
            meeting_id=self.meeting_id,
            decision_object=self.decision_object,
            content=self.content,
            status=DecisionStatus.ACCEPTED,
            evidence=self.evidence,
            annotator=self.adjudicator,
        )


@dataclass(frozen=True, slots=True)
class ReferenceSet:
    """The reference decisions of one series and what was left out of it."""

    series_id: str
    decisions: tuple[ReferenceDecision, ...]
    excluded: Mapping[str, int] = field(default_factory=dict)
    evidence_misses: tuple[str, ...] = ()


def _turn_positions(turns: Sequence[FrozenTurn]) -> dict[str, tuple[int, int]]:
    """Dialogue act id -> (turn index, position inside the turn)."""
    positions: dict[str, tuple[int, int]] = {}
    for turn in sorted(turns, key=lambda t: t.turn_index):
        for offset, act in enumerate(turn.dialogue_act_ids):
            positions.setdefault(act, (turn.turn_index, offset))
    return positions


def _act_roles(turns: Sequence[FrozenTurn]) -> dict[str, str]:
    return {act: turn.role for turn in turns for act in turn.dialogue_act_ids}


def primary_role(act_ids: Sequence[str], turns: Sequence[FrozenTurn]) -> str | None:
    """Role that spoke most of ``act_ids``; ties go to the role of the earliest act.

    Acts that the transcript does not carry are ignored; ``None`` when none is found.
    """
    positions = _turn_positions(turns)
    roles = _act_roles(turns)
    known = sorted((a for a in dict.fromkeys(act_ids) if a in positions), key=positions.__getitem__)
    if not known:
        return None
    counts = Counter(roles[a] for a in known)
    best = max(counts.values())
    return next(roles[a] for a in known if counts[roles[a]] == best)


def roles_of(act_ids: Sequence[str], turns: Sequence[FrozenTurn]) -> tuple[str, ...]:
    """Distinct roles of ``act_ids`` in transcript order."""
    positions = _turn_positions(turns)
    roles = _act_roles(turns)
    known = sorted((a for a in dict.fromkeys(act_ids) if a in positions), key=positions.__getitem__)
    return tuple(dict.fromkeys(roles[a] for a in known))


def _transcript_order(act_ids: Sequence[str], turns: Sequence[FrozenTurn]) -> tuple[str, ...]:
    positions = _turn_positions(turns)
    unique = list(dict.fromkeys(act_ids))
    known = sorted((a for a in unique if a in positions), key=positions.__getitem__)
    return tuple(known + [a for a in unique if a not in positions])


def _quote_parts(evidence_text: str) -> list[str]:
    parts = []
    for raw in evidence_text.split(_QUOTE_SEPARATOR):
        text = raw.removesuffix(_TRUNCATION_SUFFIX)
        text = _SPEAKER_PREFIX.sub("", text.strip()).strip()
        if text:
            parts.append(text)
    return parts


def _match_quotes(
    meeting_id: str, evidence_text: str, body: str, turns: Sequence[FrozenTurn]
) -> tuple[str, ...]:
    acts: list[str] = []
    for quote in _quote_parts(evidence_text):
        match = locate_quote(meeting_id, body, turns, quote)
        if isinstance(match, EvidenceMatch):
            acts.extend(match.span.dialogue_act_ids)
    return tuple(dict.fromkeys(acts))


def _read_adjudicated(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [c for c in _REQUIRED_COLUMNS if c not in header]
        if missing:
            raise NotAdjudicatedError(
                f"{path.name} is not an adjudicated decisions file: missing column(s) "
                f"{', '.join(missing)}. Use <SERIES>.decisions.adjudicated.csv."
            )
        return [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]


def load_reference(
    path: Path,
    *,
    sentence_acts: Mapping[str, Sequence[str]],
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> ReferenceSet:
    """Load an adjudicated decisions CSV as the reference set of its series.

    ``sentence_acts`` maps a decision sentence id (``source_sentence_id``) to the ids of its
    supporting dialogue acts (the ``summlink`` layer); see the module docstring for the
    inclusion rule and the evidence fallback.

    Raises:
        NotAdjudicatedError: the file lacks the adjudication columns, a row has no
            ``final_status``, or a ``decision`` row lacks ``final_object`` or ``final_content``.
    """
    rows = [r for r in _read_adjudicated(path) if r.get("decision_id")]
    legal = {status.value for status in AnnotationStatus}
    for row in rows:
        status = row["final_status"]
        if not status:
            raise NotAdjudicatedError(
                f"{path.name}: {row['decision_id']} has no final_status; "
                "adjudication is incomplete."
            )
        if status not in legal:
            raise NotAdjudicatedError(
                f"{path.name}: {row['decision_id']} has unknown final_status {status!r}."
            )
        if status == _DECISION and not (
            row.get("final_object", "") and row.get("final_content", "")
        ):
            raise NotAdjudicatedError(
                f"{path.name}: {row['decision_id']} is a decision without "
                "final_object/final_content."
            )

    series_id = path.name.split(".")[0]
    excluded: Counter[str] = Counter()
    decisions: list[ReferenceDecision] = []
    misses: list[str] = []
    meetings: dict[str, tuple[str, list[FrozenTurn]]] = {}

    for row in rows:
        if row["final_status"] != _DECISION:
            excluded[row["final_status"]] += 1
            continue
        meeting_id = row["meeting_id"]
        if meeting_id not in meetings:
            meetings[meeting_id] = load_meeting_text(meeting_id, transcripts_dir)
        body, turns = meetings[meeting_id]

        method: EvidenceMethod = "sentence_id"
        acts = tuple(sentence_acts.get(row["source_sentence_id"], ()))
        if not acts:
            method = "quote"
            acts = _match_quotes(meeting_id, row.get("evidence_text", ""), body, turns)
        if not acts:
            method = "none"
            misses.append(row["decision_id"])
        ordered = _transcript_order(acts, turns)
        decisions.append(
            ReferenceDecision(
                decision_id=row["decision_id"],
                series_id=series_id,
                meeting_id=meeting_id,
                decision_object=row["final_object"],
                content=row["final_content"],
                evidence=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=ordered)
                if ordered
                else None,
                evidence_method=method,
                role=primary_role(ordered, turns),
                roles=roles_of(ordered, turns),
                adjudicator=row.get("adjudicator") or None,
            )
        )

    return ReferenceSet(
        series_id=series_id,
        decisions=tuple(decisions),
        excluded=dict(excluded),
        evidence_misses=tuple(misses),
    )


def load_series_reference(
    series_id: str,
    *,
    decisions_dir: Path = GOLD_DECISIONS_DIR,
    ami_root: Path = AMI_DIR,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> ReferenceSet:
    """Load ``<series_id>.decisions.adjudicated.csv`` with evidence from the AMI ``summlink``."""
    path = decisions_dir / f"{series_id}.decisions.adjudicated.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"Adjudicated reference not found: {path}. Run `afg gold adjudicate` and fill "
            "the final_* columns first; the annotator and base files are not references."
        )
    meeting_ids = sorted({r["meeting_id"] for r in _read_adjudicated(path) if r.get("meeting_id")})
    sentence_acts: dict[str, list[str]] = {}
    for meeting_id in meeting_ids:
        sentence_acts.update(summlink_dialogue_act_ids(ami_root, meeting_id))
    return load_reference(path, sentence_acts=sentence_acts, transcripts_dir=transcripts_dir)
