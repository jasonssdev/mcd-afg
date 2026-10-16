"""Read the ``Decision`` concepts of an OpenKOS bundle into :class:`~afg.domain.decision.Decision`.

On-disk format (OpenKOS v0.5.5, ``bundle/decisions/<slug>.md``), written by the transcript
decision pass (``extraction/decision_pass.py:184`` ``to_result``) and ``model/okf.py:1554``
``build_concept``:

* YAML frontmatter with ``type: Decision``, ``description: "<subject>: <value>"`` and
  ``provenance: [sources/<slug>, ...]``. The source slug is the lowercased stem of the ingested
  file (``application/ingest.py:375``), so ``ES2015a.md`` is ``sources/es2015a``.
* Body: ``# <title>``, the description, then ``<value>`` and ``> <evidence quote>`` (one line,
  ``decision_pass.py:160`` ``compose_body``), then ``## Related``.
* A decision restated in a later meeting is attached to the existing concept
  (``model/okf.py:3270`` ``build_attached_document``): its ``provenance`` gains the later source
  and the body gains ``## Update from <title> (sources/<slug>)`` followed by the later value and
  quote.

``bundle/.state/decisions/*.decisions.okf`` (``bundle/decisions.py``) holds the operator's
contradiction and identity rulings, not decisions, and is never read here.

Mapping:

* ``decision_object`` / ``content``: the description split at the ``<subject>: `` prefix. When
  the body repeats the value (it does in every file the decision pass writes) the split is exact
  even if the subject contains ``": "``; otherwise the first ``": "`` splits it.
* ``meeting_id``: the earliest meeting of ``provenance``; ``origin_meeting_ids`` lists all of
  them when there is more than one.
* ``evidence``: the quotes are tried in body order, each against the meeting that supports it,
  with :func:`~afg.extraction.openkos.evidence.locate_quote`; the first one that maps to
  dialogue acts is the evidence. A decision whose quotes all fail cannot be built (an
  :class:`~afg.domain.decision.EvidenceSpan` needs at least one dialogue act), so it is reported
  in :attr:`BundleDecisions.unmapped` instead of being dropped silently.
* ``status`` is always ``ACCEPTED``: the decision pass only keeps decisions it considers made.

Every other concept that is not a ``Source`` (``concepts/``, ``events/``, ``projects/``,
``people/``; :func:`read_concept_bundle`) has the same frontmatter and, after ``# <title>`` and
the description, a verbatim excerpt of the transcript: ``ROLE: text`` turns separated by blank
lines (``people/`` files put the turns on one line). Its meetings are those of ``provenance``.
The excerpt is a window of consecutive turns, so it is located as ONE quote first (joined with
spaces, which is what the blank lines normalise to); if that fails, each turn is located on its
own. A turn that occurs more than once in the meeting is not assigned to the first occurrence
(``Mm-hmm.`` would point at an arbitrary turn): it counts as ``ambiguous``. The span of a
concept is one :class:`~afg.domain.decision.EvidenceSpan` per meeting, with the union of the
dialogue acts of its located excerpts. ``sources/`` files embed a whole transcript and are never
read here (their treatment as citations is a research decision, issue #97).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from afg.conditions.c1_chunking import FrozenTurn
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos.evidence import (
    EvidenceMatch,
    MissReason,
    load_meeting_text,
    locate_quote,
)
from afg.shared.paths import TRANSCRIPTS_DIR

DECISIONS_DIRNAME = "decisions"
DECISION_TYPE = "Decision"
_SOURCE_PREFIX = "sources/"
_RELATED_HEADING = "## Related"
_UPDATE_HEADING = re.compile(r"^## Update from .*\((sources/[^()\s]+)\)\s*$")
_QUOTE_LINE = re.compile(r"^>\s?(.*)$")
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_SUBJECT_SEPARATOR = ": "
NO_QUOTE = "no_quote"
NO_EXCERPT = "no_excerpt"
AMBIGUOUS = "ambiguous"
SOURCE_TYPE = "Source"
SOURCES_DIRNAME = "sources"
_CONCEPT_SKIPPED_DIRNAMES = frozenset({DECISIONS_DIRNAME, SOURCES_DIRNAME})


class BundleFormatError(OpenKosError):
    """A file of the bundle does not have the layout OpenKOS v0.5.5 writes."""


@dataclass(frozen=True, slots=True)
class QuoteCounts:
    """What happened to the evidence quotes of the bundle (one count per quote)."""

    total: int = 0
    found: int = 0
    not_found: int = 0
    no_dialogue_acts: int = 0
    empty: int = 0


@dataclass(frozen=True, slots=True)
class UnmappedDecision:
    """A decision of the bundle that could not become a :class:`Decision`."""

    concept_id: str
    meeting_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BundleDecisions:
    """The decisions read from one bundle, with what could not be mapped."""

    decisions: tuple[Decision, ...]
    unmapped: tuple[UnmappedDecision, ...]
    quotes: QuoteCounts


@dataclass(frozen=True, slots=True)
class _Quote:
    source: str
    text: str


def _split_front_matter(text: str, path: Path) -> tuple[dict[str, object], str]:
    match = _FRONT_MATTER.match(text)
    if match is None:
        raise BundleFormatError(f"{path}: no front matter block.")
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise BundleFormatError(f"{path}: front matter is not valid YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise BundleFormatError(f"{path}: front matter is not a mapping.")
    return {str(key): value for key, value in loaded.items()}, match.group(2)


def _required_text(metadata: dict[str, object], key: str, path: Path) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BundleFormatError(f"{path}: missing or empty `{key}`.")
    return value.strip()


def _provenance(metadata: dict[str, object], path: Path) -> list[str]:
    value = metadata.get("provenance")
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(entry, str) and entry for entry in value)
    ):
        raise BundleFormatError(f"{path}: `provenance` must be a non-empty list of source ids.")
    return [str(entry) for entry in value]


def _meeting_of(source_id: str, by_slug: dict[str, str], path: Path) -> str:
    slug = source_id.removeprefix(_SOURCE_PREFIX)
    if not source_id.startswith(_SOURCE_PREFIX) or slug not in by_slug:
        raise BundleFormatError(f"{path}: provenance {source_id!r} is not a meeting of the series.")
    return by_slug[slug]


def _paragraphs(body: str) -> list[str]:
    head = body.split(f"\n{_RELATED_HEADING}", 1)[0]
    return [block.strip() for block in head.strip().split("\n\n") if block.strip()]


def _split_description(description: str, body: str, path: Path) -> tuple[str, str]:
    """``(decision_object, content)`` from ``<subject>: <value>``."""
    blocks = _paragraphs(body)
    if len(blocks) >= 3 and blocks[1] == description:
        value = blocks[2]
        suffix = f"{_SUBJECT_SEPARATOR}{value}"
        if description.endswith(suffix) and len(description) > len(suffix):
            return description[: -len(suffix)], value
    subject, separator, value = description.partition(_SUBJECT_SEPARATOR)
    if not separator or not subject.strip() or not value.strip():
        raise BundleFormatError(f"{path}: description is not `<subject>: <value>`.")
    return subject.strip(), value.strip()


def _quotes(body: str, first_source: str) -> list[_Quote]:
    """The ``> `` quote lines of the body, each with the source that supports it."""
    quotes: list[_Quote] = []
    source = first_source
    for line in body.split("\n"):
        if line.strip() == _RELATED_HEADING:
            break
        heading = _UPDATE_HEADING.match(line)
        if heading is not None:
            source = heading.group(1)
            continue
        quote = _QUOTE_LINE.match(line)
        if quote is not None and quote.group(1).strip():
            quotes.append(_Quote(source, quote.group(1)))
    return quotes


class _MeetingCache:
    def __init__(self, transcripts_dir: Path) -> None:
        self._dir = transcripts_dir
        self._cache: dict[str, tuple[str, list[FrozenTurn]]] = {}

    def get(self, meeting_id: str) -> tuple[str, list[FrozenTurn]]:
        if meeting_id not in self._cache:
            self._cache[meeting_id] = load_meeting_text(meeting_id, self._dir)
        return self._cache[meeting_id]


def read_decision_bundle(
    bundle_dir: Path,
    *,
    series_id: str,
    meeting_ids: Sequence[str],
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> BundleDecisions:
    """Read ``bundle_dir/decisions/*.md`` (file name order) into decisions of ``series_id``.

    Raises:
        BundleFormatError: a file is not a ``Decision`` concept of the v0.5.5 layout or cites a
            source that is not one of ``meeting_ids``.
        FileNotFoundError: the frozen transcript of a cited meeting is missing.
    """
    by_slug = {meeting.casefold(): meeting for meeting in meeting_ids}
    order = {meeting: index for index, meeting in enumerate(meeting_ids)}
    meetings = _MeetingCache(transcripts_dir)
    folder = bundle_dir / DECISIONS_DIRNAME
    paths = sorted(folder.glob("*.md")) if folder.is_dir() else []

    decisions: list[Decision] = []
    unmapped: list[UnmappedDecision] = []
    counts = {"total": 0, "found": 0, "not_found": 0, "no_dialogue_acts": 0, "empty": 0}

    for path in paths:
        metadata, body = _split_front_matter(path.read_text(encoding="utf-8"), path)
        if metadata.get("type") != DECISION_TYPE:
            raise BundleFormatError(f"{path}: `type` is {metadata.get('type')!r}, not Decision.")
        description = _required_text(metadata, "description", path)
        provenance = _provenance(metadata, path)
        origin = tuple(
            sorted(
                dict.fromkeys(_meeting_of(source, by_slug, path) for source in provenance),
                key=order.__getitem__,
            )
        )
        decision_object, content = _split_description(description, body, path)

        evidence: EvidenceMatch | None = None
        reasons: list[str] = []
        quotes = _quotes(body, provenance[0])
        for quote in quotes:
            meeting_id = _meeting_of(quote.source, by_slug, path)
            text, turns = meetings.get(meeting_id)
            counts["total"] += 1
            outcome = locate_quote(meeting_id, text, turns, quote.text)
            if isinstance(outcome, EvidenceMatch):
                counts["found"] += 1
                if evidence is None:
                    evidence = outcome
                continue
            reasons.append(outcome.reason.value)
            if outcome.reason is MissReason.NOT_FOUND:
                counts["not_found"] += 1
            elif outcome.reason is MissReason.NO_DIALOGUE_ACTS:
                counts["no_dialogue_acts"] += 1
            else:
                counts["empty"] += 1
        concept_id = f"{DECISIONS_DIRNAME}/{path.stem}"
        if evidence is None:
            unmapped.append(UnmappedDecision(concept_id, origin, tuple(reasons) or (NO_QUOTE,)))
            continue
        decisions.append(
            Decision(
                id=concept_id,
                series_id=series_id,
                meeting_id=origin[0],
                decision_object=decision_object,
                content=content,
                status=DecisionStatus.ACCEPTED,
                evidence=evidence.span,
                origin_meeting_ids=origin if len(origin) > 1 else (),
            )
        )
    return BundleDecisions(tuple(decisions), tuple(unmapped), QuoteCounts(**counts))


@dataclass(frozen=True, slots=True)
class ExcerptCounts:
    """What happened to the transcript excerpts of the non-decision concepts.

    One count per located unit: the whole excerpt when it matched as one window, otherwise each
    of its turns.
    """

    total: int = 0
    found: int = 0
    not_found: int = 0
    ambiguous: int = 0
    no_dialogue_acts: int = 0
    empty: int = 0


@dataclass(frozen=True, slots=True)
class UnmappedConcept:
    """A non-decision concept none of whose excerpts could be located."""

    concept_id: str
    meeting_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BundleConcepts:
    """The evidence of the non-decision, non-source concepts of one bundle."""

    spans: dict[str, tuple[EvidenceSpan, ...]]
    unmapped: tuple[UnmappedConcept, ...]
    excerpts: ExcerptCounts


def _excerpt_turns(body: str, title: str, description: str) -> list[str]:
    """The transcript turns of a concept body, without the title, description and headings."""
    blocks = _paragraphs(body)
    if blocks and blocks[0] == f"# {title}":
        blocks = blocks[1:]
    if blocks and blocks[0] == description:
        blocks = blocks[1:]
    return [block for block in blocks if not block.startswith("#")]


def _locate_unit(
    text: str, meeting_ids: Sequence[str], meetings: _MeetingCache
) -> tuple[EvidenceMatch | None, str]:
    """First unique match of ``text`` in ``meeting_ids``, or ``(None, reason)``."""
    reason = MissReason.NOT_FOUND.value
    for meeting_id in meeting_ids:
        body, turns = meetings.get(meeting_id)
        outcome = locate_quote(meeting_id, body, turns, text)
        if isinstance(outcome, EvidenceMatch):
            if outcome.occurrences == 1:
                return outcome, ""
            reason = AMBIGUOUS
        elif reason == MissReason.NOT_FOUND.value:
            reason = outcome.reason.value
    return None, reason


def read_concept_bundle(
    bundle_dir: Path,
    *,
    meeting_ids: Sequence[str],
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> BundleConcepts:
    """Locate the transcript excerpts of every concept of ``bundle_dir`` that is not a decision.

    Reads ``bundle_dir/<folder>/*.md`` (folder and file name order) for every folder except
    ``decisions/`` and ``sources/``, skipping files whose ``type`` is ``Decision`` or ``Source``.

    Raises:
        BundleFormatError: a file has no valid front matter or cites a source that is not one
            of ``meeting_ids``.
        FileNotFoundError: the frozen transcript of a cited meeting is missing.
    """
    by_slug = {meeting.casefold(): meeting for meeting in meeting_ids}
    order = {meeting: index for index, meeting in enumerate(meeting_ids)}
    meetings = _MeetingCache(transcripts_dir)
    folders = (
        sorted(
            f
            for f in bundle_dir.iterdir()
            if f.is_dir() and not f.name.startswith(".") and f.name not in _CONCEPT_SKIPPED_DIRNAMES
        )
        if bundle_dir.is_dir()
        else []
    )

    spans: dict[str, tuple[EvidenceSpan, ...]] = {}
    unmapped: list[UnmappedConcept] = []
    counts = dict.fromkeys(
        ("total", "found", "not_found", "ambiguous", "no_dialogue_acts", "empty"), 0
    )
    by_reason = {
        MissReason.NOT_FOUND.value: "not_found",
        AMBIGUOUS: "ambiguous",
        MissReason.NO_DIALOGUE_ACTS.value: "no_dialogue_acts",
        MissReason.EMPTY_QUOTE.value: "empty",
    }

    for folder in folders:
        for path in sorted(folder.glob("*.md")):
            metadata, body = _split_front_matter(path.read_text(encoding="utf-8"), path)
            if metadata.get("type") in (DECISION_TYPE, SOURCE_TYPE):
                continue
            provenance = _provenance(metadata, path)
            origin = tuple(
                sorted(
                    dict.fromkeys(_meeting_of(source, by_slug, path) for source in provenance),
                    key=order.__getitem__,
                )
            )
            turns = _excerpt_turns(
                body, str(metadata.get("title", "")).strip(), str(metadata.get("description", ""))
            )
            concept_id = f"{folder.name}/{path.stem}"
            if not turns:
                unmapped.append(UnmappedConcept(concept_id, origin, (NO_EXCERPT,)))
                continue

            acts: dict[str, dict[str, None]] = {}
            reasons: list[str] = []
            window, _ = _locate_unit(" ".join(turns), origin, meetings)
            if window is not None:
                matches = [window]
                counts["total"] += 1
            else:
                matches = []
                for turn in turns:
                    match, reason = _locate_unit(turn, origin, meetings)
                    if match is not None:
                        matches.append(match)
                    else:
                        reasons.append(reason)
                        counts[by_reason[reason]] += 1
                counts["total"] += len(turns)
            counts["found"] += len(matches)
            for match in matches:
                found = acts.setdefault(match.span.meeting_id, {})
                found.update(dict.fromkeys(match.span.dialogue_act_ids))
            if not acts:
                unmapped.append(
                    UnmappedConcept(concept_id, origin, tuple(reasons) or (NO_EXCERPT,))
                )
                continue
            spans[concept_id] = tuple(
                EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=tuple(ids))
                for meeting_id, ids in sorted(acts.items(), key=lambda item: order[item[0]])
            )
    return BundleConcepts(spans, tuple(unmapped), ExcerptCounts(**counts))
