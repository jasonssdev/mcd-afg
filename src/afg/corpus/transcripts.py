"""Render plain-text and dialogue-act-anchored transcripts from AMI word/segment/
dialogue-act layers.

Two render levels, both required, and BOTH built from the exact same word-level
resolution below so they are identical across all three experimental conditions
(thesis section 5.3):

* :func:`render_meeting_transcript` / :func:`render_meeting_plain_text` -- segment-level
  plain text. This is what OpenKOS and the C1 document-RAG baseline ingest.
* :func:`render_meeting_dialogue_acts` -- dialogue-act-level text that keeps each act's
  ``nite:id``. The OE1 gold set anchors abstractive summary sentences to dialogue acts via
  ``extractive/<meeting>.summlink.xml``; losing that id would break the thesis section 5.4
  alignment protocol and OE4 error attribution.

VERIFIED (2026-09-21) against the real download at ``data/raw/ami/`` (meeting IS1004d, and
corpus-wide file counts recorded in ``afg.corpus.layers``):

1. Word text lives in ``words/<meeting>.<spk>.words.xml``, one element per token, in
   document order. Non-lexical siblings -- ``vocalsound``, ``disfmarker``, ``gap``,
   ``pause``, ``nonvocalsound`` -- still carry their own ``nite:id`` and therefore their
   own document-order slot. They contribute no text but MUST be kept in the parsed token
   list (see :func:`load_word_tokens`), or every ``id(a)..id(b)`` range that spans one
   would resolve against the wrong index.
2. Turn boundaries with wall-clock timing live in ``segments/<meeting>.<spk>.segments.xml``.
3. Dialogue acts live in ``dialogueActs/<meeting>.<spk>.dialog-act.xml``. Each ``<dact>``
   carries TWO hrefs -- one to ``da-types.xml#id(ami_da_N)`` (the act type, irrelevant
   here) and one to ``<meeting>.<spk>.words.xml#id(a)..id(b)`` (the text span). Only the
   latter is resolved (see :func:`href_filename` filtering in
   :func:`_render_speaker_dialogue_acts`); the former is deliberately never touched.
4. ``id(a)..id(b)`` is an INCLUSIVE range over document order in the target words file,
   not a two-element set naming just the endpoints -- see
   ``afg.corpus.nxt.resolve_id_range``.
5. Speaker roles come from ``corpusResources/meetings.xml`` (``<speaker nxt_agent="A"
   role="PM" .../>``), reusing ``afg.corpus.participants.role_from_code`` so the role
   taxonomy is defined in exactly one place.

Design decisions (fixed, identical across all three experimental conditions):

* Chronological interleaving across all speakers, sorted by ``transcriber_start``
  (segments) or earliest constituent word's ``starttime`` (dialogue acts); ties break on
  speaker id for reproducibility. This is the defect that mattered most: rendering
  grouped by speaker file (the pre-fix behaviour) produced a transcript where one speaker
  talks start to finish before the next begins, which is not what C1 (thesis section 5.3)
  should index.
* Speaker label is the short AMI role code (``PM``/``ME``/``UI``/``ID``), because thesis
  section 6.3 stratifies by role. Falls back to the ``nxt_agent`` letter when a role
  cannot be resolved; this module never raises over a missing/unrecognized role.
* Filler words ("uh", "um", ...) are genuine ``<w>`` elements and are KEPT, not stripped.
  The ``disfluency/`` layer that would allow principled cleaning covers only 5 of the 14
  OE1 series (ES2002, ES2008, IS1003, IS1009, TS3005); cleaning on top of it would bias
  part of the configured set and not the rest, so nothing is cleaned here.
* Non-lexical elements (``vocalsound``, ``disfmarker``, ``gap``, ``pause``,
  ``nonvocalsound``) are dropped from the rendered TEXT -- but still occupy an id slot
  while resolving ranges (point 1 above).
* Punctuation: a token with ``punc="true"`` attaches to the previous token with no space.
* Timestamps stay out of the rendered text; they are available on the returned dataclasses
  (``TranscriptTurn.start_time``/``end_time``, ``DialogueActTurn.start_time``/``end_time``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.nxt import (
    NxtParseError,
    find_by_local_name,
    get_attr,
    get_attr_by_local_name,
    get_href_targets,
    href_filename,
    iter_elements,
    local_name,
    parse_href_ids,
    parse_xml,
    resolve_id_range,
)
from afg.corpus.participants import role_from_code
from afg.shared.logging import get_logger

logger = get_logger(__name__)

# Non-lexical elements verified (2026-09-21) to occupy a nite:id document-order slot in
# words.xml files without contributing any transcript text.
_NON_LEXICAL_TAGS = frozenset({"vocalsound", "disfmarker", "gap", "pause", "nonvocalsound"})


def _parse_time(value: str | None) -> float | None:
    """Parse a NITE ``starttime``/``endtime``/``transcriber_start``/``transcriber_end``
    attribute. Returns None (never raises) for a missing or malformed value."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _speaker_id_from_path(path: Path) -> str:
    """Extract the speaker letter from a layer filename, e.g. ``IS1004d.A.words.xml`` ->
    ``"A"``. VERIFIED (2026-09-21): the speaker id is always the second '.'-delimited
    component of words/segments/dialogueActs filenames."""
    parts = path.stem.split(".")
    return parts[1] if len(parts) > 1 else "unknown"


# --- word-level parsing --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WordToken:
    """One document-order slot in a words-layer file.

    ``text`` is empty for non-lexical elements (see module docstring point 1) -- they are
    still represented here, at their own document-order position, precisely so that
    :func:`afg.corpus.nxt.resolve_id_range` resolves later ids against the correct index.
    """

    id: str
    text: str
    is_punc: bool
    start_time: float | None
    end_time: float | None


@dataclass(frozen=True, slots=True)
class WordIndex:
    """A words-layer file's tokens plus its id -> document-order-index mapping, ready for
    repeated ``id(a)..id(b)`` resolution via :func:`resolve_href_tokens`."""

    tokens: list[WordToken]
    index_by_id: dict[str, int]


def load_word_tokens(words_file: Path) -> list[WordToken]:
    """Parse one words-layer file into an ordered list of tokens, in document order.

    Iterates the direct children of ``<nite:root>`` (VERIFIED 2026-09-21: every token,
    lexical or not, is a direct child, never nested) so document order is preserved
    exactly regardless of element type. Filler words ("uh", "um", ...) are genuine ``<w>``
    elements and are kept as-is -- see the module docstring for why they are never
    stripped here.

    Returns an empty list (never raises) when the file is missing or fails to parse, so a
    single unreadable meeting/speaker does not abort a larger corpus-wide run.
    """
    try:
        root = parse_xml(words_file)
    except NxtParseError as exc:
        logger.warning("Could not parse words file %s: %s", words_file, exc)
        return []

    tokens: list[WordToken] = []
    for el in root:
        tag = local_name(el)
        if tag is None:
            continue
        word_id = get_attr_by_local_name(el, "id")
        if not word_id:
            continue
        if tag == "w":
            text = (el.text or "").strip()
            is_punc = get_attr(el, "punc") == "true"
        else:
            # Either a known non-lexical tag or an element type this module does not
            # special-case; either way it still occupies a document-order id slot (see
            # module docstring point 1) and contributes no text.
            text = ""
            is_punc = False
        tokens.append(
            WordToken(
                id=word_id,
                text=text,
                is_punc=is_punc,
                start_time=_parse_time(get_attr(el, "starttime")),
                end_time=_parse_time(get_attr(el, "endtime")),
            )
        )
    return tokens


def load_word_index(words_file: Path) -> WordIndex:
    """Load a words-layer file and build its id -> document-order-index mapping, for
    repeated range resolution against it (many segments/dialogue acts share one words
    file)."""
    tokens = load_word_tokens(words_file)
    return WordIndex(tokens=tokens, index_by_id={tok.id: i for i, tok in enumerate(tokens)})


def resolve_href_tokens(href: str, index: WordIndex) -> list[WordToken]:
    """Resolve one NITE href (a single id or an inclusive ``id(a)..id(b)`` range) against
    a words file's document-order index.

    Returns an empty list (never raises) for a dangling reference, an unparsable href, or
    an empty index -- callers should treat that the same as "no text for this span".
    """
    ids = parse_href_ids(href)
    span = resolve_id_range(ids, index.index_by_id)
    if span is None:
        return []
    start, end = span
    return index.tokens[start : end + 1]


def resolve_href_range(href: str, index: WordIndex) -> tuple[int, int] | None:
    """Resolve one NITE href to an inclusive ``(start, end)`` document-order index pair,
    without materializing the token slice.

    Needed by :mod:`afg.corpus.render` to compute overlap between two different
    segmentations of the same word stream (segments vs. dialogue acts) purely from their
    index ranges -- see :attr:`TranscriptTurn.word_start_index` /
    :attr:`DialogueActTurn.word_start_index`. Returns ``None`` under the same conditions
    as :func:`resolve_href_tokens`.
    """
    ids = parse_href_ids(href)
    return resolve_id_range(ids, index.index_by_id)


def join_word_tokens(tokens: Sequence[WordToken]) -> str:
    """Join a slice of word tokens into text, honoring AMI's punctuation-attachment
    convention: a token with ``punc="true"`` attaches to the previous token with no space
    (VERIFIED 2026-09-21, e.g. "Okay" + "." -> "Okay."). Non-lexical tokens (empty
    ``text``) contribute nothing."""
    parts: list[str] = []
    for tok in tokens:
        if not tok.text:
            continue
        if tok.is_punc and parts:
            parts[-1] += tok.text
        else:
            parts.append(tok.text)
    return " ".join(parts)


# --- speaker role labels ---------------------------------------------------------------


def speaker_role_labels(ami_root: Path, meeting_id: str) -> dict[str, str]:
    """Map each speaker's ``nxt_agent`` letter (e.g. ``"A"``) to a short role label (e.g.
    ``"PM"``), for one meeting, from ``corpusResources/meetings.xml``.

    VERIFIED (2026-09-21): every ``<meeting observation="...">`` element's ``<speaker>``
    children carry both ``nxt_agent`` (the letter used in words/segments/dialogueActs
    filenames) and ``role``. Reuses :func:`afg.corpus.participants.role_from_code` so the
    role taxonomy is defined in exactly one place, per project convention -- this module
    never reimplements it. A speaker whose role code does not validate against that
    taxonomy, or a meeting missing from ``meetings.xml`` entirely, falls back to the
    ``nxt_agent`` letter as its own label; this function never raises.
    """
    labels: dict[str, str] = {}
    meetings_path = ami_root / "corpusResources" / "meetings.xml"
    try:
        root = parse_xml(meetings_path)
    except NxtParseError as exc:
        logger.warning("Could not parse meetings file %s: %s", meetings_path, exc)
        return labels

    for meeting_el in find_by_local_name(root, "meeting"):
        if get_attr(meeting_el, "observation") != meeting_id:
            continue
        for speaker_el in iter_elements(meeting_el, "speaker"):
            agent = get_attr(speaker_el, "nxt_agent")
            if not agent:
                continue
            role_code = get_attr(speaker_el, "role") or ""
            role = role_from_code(role_code)
            labels[agent] = role_code.upper() if role is not None else agent
        break
    return labels


# --- segment-level rendering (C1 plain text) ------------------------------------------


@dataclass(frozen=True, slots=True)
class TranscriptTurn:
    """One segment-level turn, chronologically ordered across all speakers of a meeting
    (thesis section 5.3, the C1 document-RAG baseline's input).

    ``word_start_index``/``word_end_index`` are the inclusive document-order index range
    (into this speaker's own words file) this turn's text was resolved from -- needed by
    :mod:`afg.corpus.render` to compute overlap against :class:`DialogueActTurn` ranges,
    since segments and dialogue acts are two different segmentations of the same word
    stream. They are meaningless compared across different speakers (each speaker's words
    file has its own independent index).
    """

    meeting_id: str
    speaker_id: str
    role_label: str
    start_time: float
    end_time: float
    text: str
    word_start_index: int
    word_end_index: int


def _render_speaker_segments(
    meeting_id: str,
    speaker_id: str,
    role_label: str,
    segments_path: Path,
    word_index: WordIndex,
) -> list[TranscriptTurn]:
    try:
        root = parse_xml(segments_path)
    except NxtParseError as exc:
        logger.warning("Could not parse segments file %s: %s", segments_path, exc)
        return []

    turns: list[TranscriptTurn] = []
    for seg_el in find_by_local_name(root, "segment"):
        start = _parse_time(get_attr(seg_el, "transcriber_start"))
        end = _parse_time(get_attr(seg_el, "transcriber_end"))
        tokens: list[WordToken] = []
        word_start: int | None = None
        word_end: int | None = None
        for href in get_href_targets(seg_el):
            tokens.extend(resolve_href_tokens(href, word_index))
            span = resolve_href_range(href, word_index)
            if span is not None:
                span_start, span_end = span
                word_start = span_start if word_start is None else min(word_start, span_start)
                word_end = span_end if word_end is None else max(word_end, span_end)
        text = join_word_tokens(tokens)
        if not text:
            continue
        turns.append(
            TranscriptTurn(
                meeting_id=meeting_id,
                speaker_id=speaker_id,
                role_label=role_label,
                start_time=start if start is not None else 0.0,
                end_time=end if end is not None else (start or 0.0),
                text=text,
                word_start_index=word_start if word_start is not None else 0,
                word_end_index=word_end if word_end is not None else 0,
            )
        )
    return turns


def render_meeting_transcript(ami_root: Path, meeting_id: str) -> list[TranscriptTurn]:
    """Render one meeting's segment-level transcript, chronologically interleaved across
    all speakers (thesis section 5.3).

    Returns an empty list when the meeting has no discoverable words/segments files
    rather than raising -- callers building a corpus-wide index should simply skip
    meetings that render empty and log accordingly.
    """
    words_by_speaker = {
        _speaker_id_from_path(f.path): f.path
        for f in discover_layer_files(ami_root, AnnotationLayer.WORDS)
        if f.meeting_id == meeting_id
    }
    segments_by_speaker = {
        _speaker_id_from_path(f.path): f.path
        for f in discover_layer_files(ami_root, AnnotationLayer.SEGMENTS)
        if f.meeting_id == meeting_id
    }

    if not words_by_speaker or not segments_by_speaker:
        logger.info(
            "No words/segments files found for meeting %s; cannot render transcript.",
            meeting_id,
        )
        return []

    role_labels = speaker_role_labels(ami_root, meeting_id)

    turns: list[TranscriptTurn] = []
    for speaker_id, segments_path in segments_by_speaker.items():
        words_path = words_by_speaker.get(speaker_id)
        if words_path is None:
            continue
        word_index = load_word_index(words_path)
        role_label = role_labels.get(speaker_id, speaker_id)
        turns.extend(
            _render_speaker_segments(meeting_id, speaker_id, role_label, segments_path, word_index)
        )

    turns.sort(key=lambda t: (t.start_time, t.speaker_id))
    return turns


def render_meeting_plain_text(ami_root: Path, meeting_id: str) -> str:
    """Render one meeting as flat, chronologically interleaved plain text, for the C1
    document-RAG baseline (thesis section 5.3) to chunk and index.

    Built from :func:`render_meeting_transcript` (the segment level -- the coarser,
    naturally chunkable unit). Identical across all three experimental conditions: this is
    the single rendering C1 ever consumes, un-cleaned of disfluencies (see module
    docstring).
    """
    turns = render_meeting_transcript(ami_root, meeting_id)
    return "\n".join(f"{turn.role_label}: {turn.text}" for turn in turns)


# --- dialogue-act-level rendering (OE1 alignment) ---------------------------------------


@dataclass(frozen=True, slots=True)
class DialogueActTurn:
    """One dialogue act's rendered text, keeping its ``nite:id`` (thesis section 5.4
    alignment protocol / OE4 error attribution) and chronologically ordered across all
    speakers of a meeting.

    ``word_start_index``/``word_end_index`` are the inclusive document-order index range
    (into this speaker's own words file) this act's text was resolved from -- see
    :attr:`TranscriptTurn.word_start_index` for why this exists.
    """

    meeting_id: str
    speaker_id: str
    role_label: str
    dialogue_act_id: str
    start_time: float
    end_time: float
    text: str
    word_start_index: int
    word_end_index: int


def _render_speaker_dialogue_acts(
    meeting_id: str,
    speaker_id: str,
    role_label: str,
    dialogue_acts_path: Path,
    word_index: WordIndex,
) -> list[DialogueActTurn]:
    try:
        root = parse_xml(dialogue_acts_path)
    except NxtParseError as exc:
        logger.warning("Could not parse dialogue-act file %s: %s", dialogue_acts_path, exc)
        return []

    turns: list[DialogueActTurn] = []
    for dact_el in find_by_local_name(root, "dact"):
        act_id = get_attr_by_local_name(dact_el, "id") or ""
        tokens: list[WordToken] = []
        word_start: int | None = None
        word_end: int | None = None
        for href in get_href_targets(dact_el):
            # A dact carries two hrefs; only the one pointing at this speaker's words
            # file names a text span. The da-types.xml href is deliberately never
            # resolved (module docstring point 3).
            if not href_filename(href).endswith(".words.xml"):
                continue
            tokens.extend(resolve_href_tokens(href, word_index))
            span = resolve_href_range(href, word_index)
            if span is not None:
                span_start, span_end = span
                word_start = span_start if word_start is None else min(word_start, span_start)
                word_end = span_end if word_end is None else max(word_end, span_end)
        text = join_word_tokens(tokens)
        if not text:
            continue
        start_time = next((t.start_time for t in tokens if t.start_time is not None), None)
        end_time = next((t.end_time for t in reversed(tokens) if t.end_time is not None), None)
        turns.append(
            DialogueActTurn(
                meeting_id=meeting_id,
                speaker_id=speaker_id,
                role_label=role_label,
                dialogue_act_id=act_id,
                start_time=start_time if start_time is not None else 0.0,
                end_time=end_time if end_time is not None else (start_time or 0.0),
                text=text,
                word_start_index=word_start if word_start is not None else 0,
                word_end_index=word_end if word_end is not None else 0,
            )
        )
    return turns


def render_meeting_dialogue_acts(ami_root: Path, meeting_id: str) -> list[DialogueActTurn]:
    """Render one meeting's dialogue-act-level transcript, chronologically interleaved
    across all speakers and anchored to each act's ``nite:id`` (thesis section 5.4).

    Returns an empty list when the meeting has no discoverable words/dialogue-act files,
    never raising.
    """
    words_by_speaker = {
        _speaker_id_from_path(f.path): f.path
        for f in discover_layer_files(ami_root, AnnotationLayer.WORDS)
        if f.meeting_id == meeting_id
    }
    dialogue_acts_by_speaker = {
        _speaker_id_from_path(f.path): f.path
        for f in discover_layer_files(ami_root, AnnotationLayer.DIALOGUE_ACTS)
        if f.meeting_id == meeting_id
    }

    if not words_by_speaker or not dialogue_acts_by_speaker:
        logger.info(
            "No words/dialogue-act files found for meeting %s; cannot render dialogue acts.",
            meeting_id,
        )
        return []

    role_labels = speaker_role_labels(ami_root, meeting_id)

    turns: list[DialogueActTurn] = []
    for speaker_id, dialogue_acts_path in dialogue_acts_by_speaker.items():
        words_path = words_by_speaker.get(speaker_id)
        if words_path is None:
            continue
        word_index = load_word_index(words_path)
        role_label = role_labels.get(speaker_id, speaker_id)
        turns.extend(
            _render_speaker_dialogue_acts(
                meeting_id, speaker_id, role_label, dialogue_acts_path, word_index
            )
        )

    turns.sort(key=lambda t: (t.start_time, t.speaker_id))
    return turns
