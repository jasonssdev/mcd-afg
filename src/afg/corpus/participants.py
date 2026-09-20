"""Native-language derivation for AMI participants (thesis section 5.1).

Thesis section 5.1: the native/non-native English composition of the corpus is not
published anywhere; computing and reporting it is a minor original contribution of this
project.

AUTHORITATIVE SOURCE (VERIFIED 2026-09-20 against the real download at ``data/raw/ami/``):
``corpusResources/participants.xml`` carries an explicit ``native_language`` attribute
per participant (189 participants corpus-wide). This is the primary and only trusted
source of native-language data. The participant id's third character ("E"/"D"/"O"
encoding) is NOT used by the main resolution path any more -- see
:func:`native_language_from_participant_id` below, which is kept only as an explicitly
opt-in, clearly-demoted fallback, because it was measured to *fabricate* a language for
participant ids that do not appear in ``participants.xml`` at all (see its docstring).

The raw attribute is dirty and is normalized before use (case folding + an explicit,
commented alias map for known spelling variants -- see ``_NATIVE_LANGUAGE_ALIASES``).
Two participants (out of 189) have an empty ``native_language`` attribute; those resolve
to :attr:`NativeSpeakerStatus.UNKNOWN`, never to ``NON_NATIVE``.

MEASURED LIMITATION (thesis section 2 OE2 / section 6.3): within the six configured
target series (thesis section 5.0), the native/non-native English axis is almost
perfectly confounded with series identity -- most series are heavily skewed toward one
class, and the entire TS3005 series is UNKNOWN (its four participant ids use a different,
role-suffixed format that appears in no corpus resource file at all, so nothing about
their native language is knowable from this corpus). With this sample, a language effect
and a series effect are NOT separable, and any stratified analysis on this axis (as OE2
and section 6.3 require) must report that as a measured limitation rather than treating
the axis as independent of series. The role axis (PM/ME/UI/ID), by contrast, is balanced
across the six series and does not have this problem.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rich.console import Console
from rich.table import Table

from afg.corpus.nxt import (
    NxtParseError,
    find_by_local_name,
    get_attr,
    get_attr_by_local_name,
    iter_elements,
    parse_xml,
)
from afg.domain.participant import NativeLanguage, NativeSpeakerStatus, Participant, SpeakerRole
from afg.shared.config import load_corpus_config
from afg.shared.logging import get_logger
from afg.shared.paths import TABLES_DIR

logger = get_logger(__name__)

PARTICIPANTS_CSV_NAME = "participants.csv"

# Thesis section 2 OE2 / section 6.3: stated plainly, independent of the exact measured
# counts (which are printed alongside it, never hard-coded here) -- with only 24
# participants across the six configured target series, the native/non-native English
# axis and the series axis cannot be assumed independent, and any stratified analysis on
# this axis must report that as a measured limitation.
CONFOUND_WARNING = (
    "In the six target series, the native/non-native English axis is nearly "
    "confounded with series identity: most series lean heavily toward one class, and "
    "TS3005 is entirely UNKNOWN (its ids appear in no corpus resource file). A language "
    "effect is NOT separable from a series effect in this sample (thesis section 2 OE2, "
    "section 6.3). The role axis (PM/ME/UI/ID), by contrast, is balanced across series."
)

# --- role mapping -------------------------------------------------------------------

# VERIFIED (2026-09-20) against corpusResources/meetings.xml: every <speaker> element's
# `role` attribute is one of exactly these four codes, corpus-wide.
_ROLE_CODE_TO_ROLE = {
    "PM": SpeakerRole.PROJECT_MANAGER,
    "ME": SpeakerRole.MARKETING_EXPERT,
    "UI": SpeakerRole.USER_INTERFACE_DESIGNER,
    "ID": SpeakerRole.INDUSTRIAL_DESIGNER,
}


def role_from_code(code: str) -> SpeakerRole | None:
    """Map a role code (e.g. 'PM') to :class:`SpeakerRole`, or None if unrecognized."""
    return _ROLE_CODE_TO_ROLE.get(code.upper())


# --- authoritative native-language normalization (participants.xml) -----------------

# Explicit, hand-verified alias map for known dirty spellings in the real
# corpusResources/participants.xml (measured 2026-09-20). Deliberately NOT fuzzy-matched
# -- only these exact case-folded variants are folded into their canonical form, so a
# genuinely different (but similarly-spelled) language is never silently merged.
_NATIVE_LANGUAGE_ALIASES: dict[str, str] = {
    "chines": "Chinese",  # 1 occurrence: missing trailing "e"
    "mandarin chinese": "Chinese",  # 1 occurrence: more specific spelling of the same language
    "czeque": "Czech",  # 2 occurrences: alternate spelling
}

_ENGLISH_CASEFOLD = "english"


def normalize_native_language(raw: str | None) -> str | None:
    """Normalize a raw ``native_language`` attribute value.

    Returns None for a missing or empty (whitespace-only) value -- callers must map that
    to :attr:`NativeSpeakerStatus.UNKNOWN`, never guess a language for it. Known dirty
    spellings (see ``_NATIVE_LANGUAGE_ALIASES``) are folded to their canonical form;
    anything else is returned with its first letter upper-cased (fixing entries like the
    corpus's lowercase ``"romanian"``) but is NOT fuzzy-matched against other entries.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    canonical = _NATIVE_LANGUAGE_ALIASES.get(stripped.casefold())
    if canonical is not None:
        return canonical
    return stripped[0].upper() + stripped[1:]


def classify_native_speaker_status(normalized_language: str | None) -> NativeSpeakerStatus:
    """Classify a normalized native-language name as native/non-native/unknown.

    ``None`` (missing or empty attribute, or participant absent from
    ``participants.xml`` altogether) always maps to
    :attr:`NativeSpeakerStatus.UNKNOWN` -- it is never guessed into ``NON_NATIVE``.
    """
    if normalized_language is None:
        return NativeSpeakerStatus.UNKNOWN
    if normalized_language.casefold() == _ENGLISH_CASEFOLD:
        return NativeSpeakerStatus.NATIVE
    return NativeSpeakerStatus.NON_NATIVE


# --- legacy id-character heuristic (kept for reference; NOT used by the main path) --

_ID_CHAR_INDEX = 2
_ID_CHAR_TO_LANGUAGE = {
    "E": NativeLanguage.ENGLISH,
    "D": NativeLanguage.DUTCH,
    "O": NativeLanguage.OTHER,
}


def native_language_from_participant_id(pid: str) -> NativeLanguage:
    """LEGACY FALLBACK ONLY -- derive a native-language guess from the third character
    of a participant id. Kept for reference and explicit comparison; nothing in this
    module's main resolution path (:func:`load_native_language_records`,
    :func:`load_participants`) calls this function, and callers must opt into it
    explicitly and knowingly.

    MEASURED (2026-09-20) against the 189 participants that have an authoritative
    ``native_language`` attribute in ``corpusResources/participants.xml``: this heuristic
    (3rd character 'E'->English, 'D'->Dutch, else Other) agrees with the authoritative
    attribute for 187/189 (98.9%). The two disagreements: ``MEO022`` (3rd char 'O' ->
    predicted Other; actually English) and ``MIO082`` (3rd char 'O' -> predicted Other;
    actually Dutch).

    It also FABRICATES a confident answer for ids that are not in ``participants.xml`` at
    all: every participant of the TS3005 series (``MTD017PM``, ``MTD018ID``,
    ``FTD019UID``, ``MTD020ME``) uses a different, role-suffixed id format that appears in
    NO corpus resource file, so their native language is genuinely unknown -- yet this
    heuristic's third character happens to be 'D' for all four, so it confidently (and
    wrongly) returns :attr:`NativeLanguage.DUTCH` for the entire series. This is the
    reason this function was demoted out of the main resolution path.

    Returns :attr:`NativeLanguage.UNKNOWN` for ids too short to contain the expected
    character, or containing a character outside ``{E, D, O}`` -- this function never
    guesses past what the assumed encoding actually supports.
    """
    if len(pid) <= _ID_CHAR_INDEX:
        return NativeLanguage.UNKNOWN
    code = pid[_ID_CHAR_INDEX].upper()
    return _ID_CHAR_TO_LANGUAGE.get(code, NativeLanguage.UNKNOWN)


# --- corpus-wide native-language records (participants.xml only, no meetings join) --


@dataclass(frozen=True, slots=True)
class NativeLanguageRecord:
    """One corpus-wide participant's native-language condition (thesis 5.1).

    Sourced ONLY from ``corpusResources/participants.xml`` -- not joined to
    ``meetings.xml``, so it carries no role or series association. This is the
    authoritative, corpus-wide (all AMI series, not just the six configured target
    series) distribution.
    """

    participant_id: str
    native_language: str | None  # normalized; None means UNKNOWN (absent/empty attribute)
    native_speaker_status: NativeSpeakerStatus


def load_native_language_records(ami_root: Path) -> list[NativeLanguageRecord]:
    """Load every participant's native-language condition from ``corpusResources/participants.xml``.

    Returns an empty list if the file is missing or fails to parse (never raises) --
    callers should treat an empty result the same way the rest of this module treats a
    corpus that has not been downloaded yet.
    """
    resources_path = ami_root / "corpusResources" / "participants.xml"
    if not resources_path.exists():
        return []
    try:
        root = parse_xml(resources_path)
    except NxtParseError:
        logger.warning(
            "Corpus resources file at %s failed to parse; returning no native-language "
            "records.",
            resources_path,
        )
        return []

    records: list[NativeLanguageRecord] = []
    for el in find_by_local_name(root, "participant"):
        pid = get_attr_by_local_name(el, "id")
        if not pid:
            continue
        normalized = normalize_native_language(get_attr(el, "native_language"))
        records.append(
            NativeLanguageRecord(
                participant_id=pid,
                native_language=normalized,
                native_speaker_status=classify_native_speaker_status(normalized),
            )
        )
    return records


# --- six-target-series roster (meetings.xml -> participants.xml join) ---------------


def load_participants(ami_root: Path) -> list[Participant]:
    """Load the participant roster for the six configured target series (thesis 6.3),
    joining ``corpusResources/meetings.xml`` (role, series membership -- the meeting id
    is the ``observation`` attribute, and speakers are ``global_name``-keyed) to
    ``corpusResources/participants.xml`` (authoritative native language, via
    :func:`load_native_language_records`).

    AMI's scenario design reuses the same four people, in the same roles, with the same
    native-language condition, across all four meetings of a series -- so each of the six
    configured series (``config/corpus.toml`` ``corpus.series.ids``) contributes exactly
    four participants, deduplicated by id, for 24 total against the real corpus.

    A participant whose id does not appear in ``participants.xml`` at all resolves to
    :attr:`NativeSpeakerStatus.UNKNOWN` -- this NEVER falls back to
    :func:`native_language_from_participant_id`, which is known to fabricate ``Dutch``
    for exactly this situation (see its docstring). This is expected for every member of
    TS3005.

    Returns an empty list if ``meetings.xml`` is missing or fails to parse.
    """
    meetings_path = ami_root / "corpusResources" / "meetings.xml"
    if not meetings_path.exists():
        return []
    try:
        meetings_root = parse_xml(meetings_path)
    except NxtParseError:
        logger.warning(
            "Corpus resources file at %s failed to parse; returning no participants.",
            meetings_path,
        )
        return []

    language_by_id = {
        record.participant_id: record.native_language
        for record in load_native_language_records(ami_root)
    }

    cfg = load_corpus_config()
    series_ids: list[str] = cfg["corpus"]["series"]["ids"]

    seen: dict[str, Participant] = {}
    for meeting_el in find_by_local_name(meetings_root, "meeting"):
        observation = get_attr(meeting_el, "observation")
        if not observation:
            continue
        # The meeting id is the series id plus one letter (e.g. "ES2015a" -> "ES2015");
        # only meetings belonging to a configured target series are relevant here.
        series_id = observation[:-1]
        if series_id not in series_ids:
            continue

        for speaker_el in iter_elements(meeting_el, "speaker"):
            pid = get_attr(speaker_el, "global_name")
            if not pid or pid in seen:
                continue
            role_code = get_attr(speaker_el, "role") or ""
            role = role_from_code(role_code)
            if role is None:
                logger.warning(
                    "Unrecognized role code %r for participant %r in meeting %r; skipping.",
                    role_code,
                    pid,
                    observation,
                )
                continue
            normalized_language = language_by_id.get(pid)  # None -> UNKNOWN, never guessed
            seen[pid] = Participant(
                id=pid,
                role=role,
                series_id=series_id,
                native_language=normalized_language or "Unknown",
                native_speaker_status=classify_native_speaker_status(normalized_language),
            )

    return list(seen.values())


# --- native speaker ratio (thesis 5.1 -- an original derivation) --------------------


class _HasNativeSpeakerStatus(Protocol):
    @property
    def native_speaker_status(self) -> NativeSpeakerStatus: ...


@dataclass(frozen=True, slots=True)
class NativeSpeakerCounts:
    """Native/non-native/unknown participant counts (thesis 5.1).

    This figure is unpublished in the AMI literature; computing it is a minor original
    contribution. ``unknown`` is always reported separately and is never folded into
    ``native``, ``non_native``, or a denominator that would imply it is known.
    """

    native: int
    non_native: int
    unknown: int

    @property
    def total(self) -> int:
        return self.native + self.non_native + self.unknown

    @property
    def known(self) -> int:
        """Participants with a known native-language condition (excludes ``unknown``)."""
        return self.native + self.non_native

    @property
    def ratio_of_known(self) -> float | None:
        """Native fraction of participants with a KNOWN condition.

        Returns None when there are zero participants with a known condition (undefined
        ratio) rather than dividing by zero or silently treating ``unknown`` as
        non-native.
        """
        if self.known == 0:
            return None
        return self.native / self.known


def native_speaker_ratio(participants: Sequence[_HasNativeSpeakerStatus]) -> NativeSpeakerCounts:
    """Count native/non-native/unknown participants (thesis 5.1).

    Accepts any sequence of objects exposing ``native_speaker_status`` -- both
    :class:`~afg.domain.participant.Participant` (from :func:`load_participants`) and
    :class:`NativeLanguageRecord` (from :func:`load_native_language_records`) qualify.
    """
    counts = Counter(p.native_speaker_status for p in participants)
    return NativeSpeakerCounts(
        native=counts.get(NativeSpeakerStatus.NATIVE, 0),
        non_native=counts.get(NativeSpeakerStatus.NON_NATIVE, 0),
        unknown=counts.get(NativeSpeakerStatus.UNKNOWN, 0),
    )


def _print_counts(console: Console, label: str, counts: NativeSpeakerCounts) -> None:
    ratio = counts.ratio_of_known
    ratio_text = f"{ratio:.2%} of known" if ratio is not None else "N/A (no known cases)"
    console.print(
        f"{label}: {counts.total} total -- "
        f"native={counts.native}, non_native={counts.non_native}, unknown={counts.unknown} "
        f"(native ratio: {ratio_text})"
    )


# --- reporting ------------------------------------------------------------------------


def render_table(
    corpus_wide: Sequence[NativeLanguageRecord],
    series_participants: Sequence[Participant],
    console: Console | None = None,
) -> None:
    """Render the corpus-wide distribution, six-series breakdown, per-series split, and
    role distribution to the console (``afg corpus participants``)."""
    console = console or Console()

    console.print("[bold]Corpus-wide native-language distribution[/bold] (participants.xml)")
    _print_counts(console, "All AMI series", native_speaker_ratio(corpus_wide))

    console.print()
    console.print("[bold]Six target series (thesis 6.3)[/bold]")
    _print_counts(console, "All six series combined", native_speaker_ratio(series_participants))

    per_series: dict[str, list[Participant]] = {}
    for participant in series_participants:
        per_series.setdefault(participant.series_id or "?", []).append(participant)

    series_table = Table(title="Per-series native/non-native/unknown split")
    series_table.add_column("Series")
    series_table.add_column("Native", justify="right")
    series_table.add_column("Non-native", justify="right")
    series_table.add_column("Unknown", justify="right")
    for series_id in sorted(per_series):
        counts = native_speaker_ratio(per_series[series_id])
        series_table.add_row(
            series_id, str(counts.native), str(counts.non_native), str(counts.unknown)
        )
    console.print(series_table)

    role_counts = Counter(p.role for p in series_participants)
    role_table = Table(title="Role distribution (six target series)")
    role_table.add_column("Role")
    role_table.add_column("Count", justify="right")
    for role in SpeakerRole:
        role_table.add_row(role.value, str(role_counts.get(role, 0)))
    console.print(role_table)

    console.print()
    console.print(f"[bold yellow]Warning:[/bold yellow] {CONFOUND_WARNING}")


def write_csv(participants: Sequence[Participant], out_dir: Path = TABLES_DIR) -> Path:
    """Write the six-target-series participant roster to ``reports/tables/participants.csv``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / PARTICIPANTS_CSV_NAME
    with out_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["series_id", "participant_id", "role", "native_language", "native_speaker_status"]
        )
        for participant in participants:
            writer.writerow(
                [
                    participant.series_id or "",
                    participant.id,
                    participant.role.value,
                    participant.native_language,
                    participant.native_speaker_status.value,
                ]
            )
    logger.info("Wrote participants table to %s", out_path)
    return out_path
