"""The human reference for Experiment A (OE2), loaded as decisions.

Source: ``data/processed/decisions/<SERIES>.decisions.adjudicated.csv``, the file written by
``afg gold adjudicate`` once the adjudicator has filled the ``final_*`` columns. A series with
a single annotator (the development series IS1004 and the evaluation series, one annotator
each; issue #229) has no adjudication: its reference is its only
``<SERIES>.decisions.<ini>.csv`` (``<ini>`` = the annotator's initials). The adjudicated file
always wins; two or more single-annotator files without an adjudication are ambiguous and
:func:`resolve_reference` refuses them. The machine-generated base file
``<SERIES>.decisions.csv`` is never a reference.

A single-annotator row is read in the adjudicated shape (``status`` -> ``final_status``,
``decision_object`` -> ``final_object``, ``decision_content`` -> ``final_content``,
``annotator`` -> ``adjudicator``, the initials when blank), so every rule below applies to
both kinds unchanged. :attr:`ReferenceSet.source_kind` records which kind was used
(``"adjudicated"`` or ``"single:<ini>"``).

## What counts as a reference decision

Annotation manual, section 2 (``docs/anotacion/manual-anotacion-oe1.md``): a row is a
reference decision if and only if ``final_status == "decision"``.

- ``no_decision`` (open proposal, question, opinion) is not a decision. It stays in the
  annotation set to measure false positives of the annotation guide, but the scoring unit
  here is the decision, so it is counted in :attr:`ReferenceSet.excluded` and not scored.
- ``compuesta`` is an instruction, not a verdict: the parent row is excluded and its
  ``-1``, ``-2``, ... child rows (each with its own status) are the decisions. A child
  marked ``decision`` is one reference decision; a child marked ``descartar`` is excluded.
  A child whose ``meeting_id``, ``source_sentence_id`` or ``evidence_text`` is blank takes
  its parent's value (TS3009 leaves them blank, ES2015 repeats them).
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
from afg.shared.csvio import open_csv_reader
from afg.shared.paths import AMI_DIR, GOLD_DECISIONS_DIR, TRANSCRIPTS_DIR

__all__ = [
    "AmbiguousReferenceError",
    "Language",
    "NotAdjudicatedError",
    "ReferenceDecision",
    "ReferenceFigures",
    "ReferenceSet",
    "SeriesFile",
    "load_reference",
    "load_series_reference",
    "primary_role",
    "reference_figures",
    "reference_kind",
    "resolve_reference",
    "resolve_series_file",
    "roles_of",
]

EvidenceMethod = Literal["sentence_id", "quote", "none"]
Language = Literal["es", "en"]

_REQUIRED_COLUMNS = ("decision_id", "meeting_id", "source_sentence_id", "final_status")
_QUOTE_SEPARATOR = " | "
_TRUNCATION_SUFFIX = " […truncated]"
_SPEAKER_PREFIX = re.compile(r"^[A-Z]:\s*")
_DECISION = AnnotationStatus.DECISION.value


class NotAdjudicatedError(ValueError):
    """The file is not a complete adjudicated (or single-annotator) decisions CSV."""


class AmbiguousReferenceError(NotAdjudicatedError):
    """No adjudicated file and two or more single-annotator files: which one is the reference?"""


_ADJUDICATED = "adjudicated"
_INITIALS = r"[a-z]{2,4}"
_SINGLE_DECISIONS = re.compile(rf"^[^.]+\.decisions\.({_INITIALS})\.csv$")
_SINGLE_COLUMNS = {
    "status": "final_status",
    "decision_object": "final_object",
    "decision_content": "final_content",
}
_SINGLE_REQUIRED = ("decision_id", "meeting_id", "source_sentence_id", "status")


@dataclass(frozen=True, slots=True)
class SeriesFile:
    """The file that is a series' reference and which kind it is."""

    path: Path
    kind: str
    """``"adjudicated"`` or ``"single:<ini>"``."""


def reference_kind(path: Path) -> str:
    """``"single:<ini>"`` for a ``<SERIES>.<stem>.<ini>.csv`` file, else ``"adjudicated"``."""
    match = re.match(rf"^[^.]+\.[^.]+\.({_INITIALS})\.csv$", path.name)
    return f"single:{match.group(1)}" if match else _ADJUDICATED


def resolve_series_file(series_id: str, directory: Path, stem: str) -> SeriesFile:
    """``<series>.<stem>.adjudicated.csv`` or, without it, the only ``<series>.<stem>.<ini>.csv``.

    ``stem`` is ``"decisions"`` (this module) or ``"candidates"`` (relation gold). The adjudicated
    file wins. Files whose middle part is not 2-4 lowercase letters (the machine base, a
    ``recall-sample``, a translation) are not single-annotator files.

    Raises:
        FileNotFoundError: neither kind exists; the message names what was expected.
        AmbiguousReferenceError: two or more single-annotator files and no adjudication.
    """
    adjudicated = directory / f"{series_id}.{stem}.{_ADJUDICATED}.csv"
    if adjudicated.is_file():
        return SeriesFile(adjudicated, _ADJUDICATED)
    pattern = re.compile(rf"^{re.escape(series_id)}\.{stem}\.({_INITIALS})\.csv$")
    singles = sorted(
        p for p in directory.glob(f"{series_id}.{stem}.*.csv") if pattern.match(p.name)
    )
    if len(singles) == 1:
        return SeriesFile(singles[0], reference_kind(singles[0]))
    if singles:
        raise AmbiguousReferenceError(
            f"{series_id} has no {adjudicated.name} and more than one single-annotator file: "
            f"{', '.join(p.name for p in singles)}. Adjudicate them, or keep only the one that "
            "is the reference."
        )
    raise FileNotFoundError(
        f"Reference not found for {series_id}: expected {adjudicated.name} or one "
        f"{series_id}.{stem}.<ini>.csv (annotator initials) in {directory}."
    )


def resolve_reference(series_id: str, decisions_dir: Path = GOLD_DECISIONS_DIR) -> SeriesFile:
    """The decisions file that is the reference of ``series_id`` (:func:`resolve_series_file`)."""
    try:
        return resolve_series_file(series_id, decisions_dir, "decisions")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{exc} Run `afg gold adjudicate` and fill the final_* columns, or annotate the "
            "series with a single annotator; the machine base file is not a reference."
        ) from exc


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
    source_kind: str = _ADJUDICATED
    """``"adjudicated"`` or ``"single:<ini>"``: the kind of file the reference was read from."""


@dataclass(frozen=True, slots=True)
class ReferenceFigures:
    """The counts that describe one series' reference (and that documents quote)."""

    series_id: str
    n_decisions: int
    """Reference decisions, counting the children of a ``compuesta`` row, not the parent."""
    n_multi_role: int
    """Decisions whose evidence involves more than one speaker role."""
    role_counts: dict[int, int]
    """Decisions by number of roles involved (``{1: 21, 2: 5, 3: 1}``)."""
    excluded: dict[str, int]
    """Adjudicated rows left out, by final status."""

    @property
    def n_excluded(self) -> int:
        return sum(self.excluded.values())


def reference_figures(reference: ReferenceSet) -> ReferenceFigures:
    """Count the decisions, the multi-role ones and the exclusions of ``reference``."""
    roles = Counter(len(d.roles) for d in reference.decisions)
    return ReferenceFigures(
        series_id=reference.series_id,
        n_decisions=len(reference.decisions),
        n_multi_role=sum(n for count, n in roles.items() if count > 1),
        role_counts=dict(sorted(roles.items())),
        excluded=dict(reference.excluded),
    )


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
    """Rows of an adjudicated file, or of a single-annotator file mapped to that shape."""
    single = _SINGLE_DECISIONS.match(path.name)
    with open_csv_reader(path) as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        if single:
            missing = [c for c in _SINGLE_REQUIRED if c not in header]
            if missing:
                raise NotAdjudicatedError(
                    f"{path.name} is not a single-annotator decisions file: missing "
                    f"column(s) {', '.join(missing)}."
                )
        else:
            missing = [c for c in _REQUIRED_COLUMNS if c not in header]
            if missing:
                raise NotAdjudicatedError(
                    f"{path.name} is not an adjudicated decisions file: missing column(s) "
                    f"{', '.join(missing)}. Use <SERIES>.decisions.adjudicated.csv."
                )
        rows = [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]
    if single:
        return [_as_adjudicated(row, single.group(1)) for row in rows]
    return rows


def _as_adjudicated(row: dict[str, str], initials: str) -> dict[str, str]:
    """A single-annotator row in the adjudicated shape."""
    mapped = {_SINGLE_COLUMNS.get(k, k): v for k, v in row.items()}
    mapped["adjudicator"] = row.get("annotator", "") or initials
    return mapped


_INHERITED_FROM_PARENT = ("meeting_id", "source_sentence_id", "evidence_text")


def _inherit_from_compuesta_parent(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Fill a split child's blank meeting, sentence and evidence from its ``compuesta`` parent.

    The ``-1``, ``-2``, ... children of a ``compuesta`` row come from the parent's sentence.
    Some adjudicated files repeat the parent's ``meeting_id``, ``source_sentence_id`` and
    ``evidence_text`` on each child (ES2015) and others leave them blank (TS3009); a blank
    child field takes the parent's value, a filled one is kept.
    """
    parents = {r["decision_id"]: r for r in rows if r.get("final_status") == "compuesta"}
    filled: list[dict[str, str]] = []
    for row in rows:
        head, dash, suffix = row["decision_id"].rpartition("-")
        parent = parents.get(head) if dash and suffix.isdigit() else None
        if parent is not None:
            row = {
                **row,
                **{k: parent.get(k, "") for k in _INHERITED_FROM_PARENT if not row.get(k)},
            }
        filled.append(row)
    return filled


def load_reference(
    path: Path,
    *,
    sentence_acts: Mapping[str, Sequence[str]],
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    language: Language = "es",
    translation_path: Path | None = None,
) -> ReferenceSet:
    """Load an adjudicated (or single-annotator) decisions CSV as the reference set of its series.

    ``language="es"`` (default) uses the human labels as adjudicated. ``language="en"``
    substitutes ``decision_object``/``content`` with the automatic translation from
    ``translation_path`` (default: ``<SERIES>.reference-en.csv`` next to ``path``); nothing
    else changes. See :mod:`afg.evaluation.translation`.

    ``sentence_acts`` maps a decision sentence id (``source_sentence_id``) to the ids of its
    supporting dialogue acts (the ``summlink`` layer); see the module docstring for the
    inclusion rule and the evidence fallback.

    Raises:
        NotAdjudicatedError: the file lacks the adjudication columns, a row has no
            ``final_status``, or a ``decision`` row lacks ``final_object`` or ``final_content``.
        TranslationError: ``language="en"`` and the translation is missing, incomplete or stale.
        ValueError: ``language`` is neither ``"es"`` nor ``"en"``.
    """
    if language not in ("es", "en"):
        raise ValueError(f"language must be 'es' or 'en', got {language!r}.")
    rows = _inherit_from_compuesta_parent(
        [r for r in _read_adjudicated(path) if r.get("decision_id")]
    )
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
    translations: Mapping[str, tuple[str, str]] = {}
    if language == "en":
        from afg.evaluation.translation import load_translations

        translations = load_translations(
            path, translation_path or path.with_name(f"{series_id}.reference-en.csv")
        )
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
        object_text, content_text = translations.get(
            row["decision_id"], (row["final_object"], row["final_content"])
        )
        decisions.append(
            ReferenceDecision(
                decision_id=row["decision_id"],
                series_id=series_id,
                meeting_id=meeting_id,
                decision_object=object_text,
                content=content_text,
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
        source_kind=reference_kind(path),
    )


def load_series_reference(
    series_id: str,
    *,
    decisions_dir: Path = GOLD_DECISIONS_DIR,
    ami_root: Path = AMI_DIR,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    language: Language = "es",
) -> ReferenceSet:
    """Load the reference of ``series_id`` with evidence from the AMI ``summlink``.

    The reference is ``<series_id>.decisions.adjudicated.csv`` or, without it, the only
    ``<series_id>.decisions.<ini>.csv`` (:func:`resolve_reference`).
    ``language="en"`` reads the labels from ``<series_id>.reference-en.csv`` in ``decisions_dir``.
    """
    path = resolve_reference(series_id, decisions_dir).path
    meeting_ids = sorted({r["meeting_id"] for r in _read_adjudicated(path) if r.get("meeting_id")})
    sentence_acts: dict[str, list[str]] = {}
    for meeting_id in meeting_ids:
        sentence_acts.update(summlink_dialogue_act_ids(ami_root, meeting_id))
    return load_reference(
        path,
        sentence_acts=sentence_acts,
        transcripts_dir=transcripts_dir,
        language=language,
        translation_path=decisions_dir / f"{series_id}.reference-en.csv",
    )


class DecisionNotFoundError(ValueError):
    """The decision id is not in the adjudicated file; the message lists the valid ids."""


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    """Where one adjudicated decision is evidenced: its dialogue acts, in transcript order."""

    decision_id: str
    meeting_id: str
    final_status: str
    final_object: str
    final_content: str
    act_ids: tuple[str, ...]
    method: EvidenceMethod


def adjudicated_decision_evidence(
    path: Path,
    decision_id: str,
    *,
    sentence_acts: Mapping[str, Sequence[str]],
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> DecisionEvidence:
    """Dialogue acts of one decision of an adjudicated or single-annotator file.

    Same rule as :func:`load_reference`.

    Unlike :func:`load_reference`, a half-adjudicated file is fine: only the requested row
    is looked at, so an annotator can build a question from the decisions already closed.

    Raises:
        DecisionNotFoundError: ``decision_id`` is not in the file.
    """
    rows = {r["decision_id"]: r for r in _read_adjudicated(path) if r.get("decision_id")}
    row = rows.get(decision_id)
    if row is None:
        raise DecisionNotFoundError(
            f"{decision_id!r} no está en {path.name}. Decisiones disponibles: "
            f"{', '.join(sorted(rows)) or '(ninguna)'}."
        )
    meeting_id = row["meeting_id"]
    body, turns = load_meeting_text(meeting_id, transcripts_dir)
    method: EvidenceMethod = "sentence_id"
    acts = tuple(sentence_acts.get(row["source_sentence_id"], ()))
    if not acts:
        method = "quote"
        acts = _match_quotes(meeting_id, row.get("evidence_text", ""), body, turns)
    if not acts:
        method = "none"
    return DecisionEvidence(
        decision_id=decision_id,
        meeting_id=meeting_id,
        final_status=row.get("final_status", ""),
        final_object=row.get("final_object", ""),
        final_content=row.get("final_content", ""),
        act_ids=_transcript_order(acts, turns),
        method=method,
    )
