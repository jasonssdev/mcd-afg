"""Map the evidence quote of an OpenKOS decision to AMI dialogue act ids.

The OpenKOS decision pass keeps, per decision, ONE evidence quote, and only when the quote
is a verbatim substring of the transcript window after casefolding and whitespace
collapsing (``openkos.extraction.decision_pass.quoted_verbatim``). It returns no offsets
and no turn ids, so the link back to the reference set (dialogue acts) is rebuilt here by
repeating that match on the frozen transcript and reading the turns it overlaps.

Frozen transcript layout (``afg.corpus.render``): the body is ``ROLE: text`` turns
separated by a blank line; each turn in ``<meeting>.jsonl`` carries ``char_start`` /
``char_end`` over the TEXT of the turn (the ``ROLE: `` prefix sits just before
``char_start``) and its ``dialogue_act_ids``.

Rules (all deterministic; a quote that cannot be mapped is a typed miss, never an error):

1. Matching mirrors OpenKOS: casefold, collapse whitespace, then strip the trailing
   ``.,;:!?`` of the quote. Offsets are carried through the normalization.
2. The quote is searched in the body INCLUDING the ``ROLE: `` prefixes, because that is
   what OpenKOS saw. A quote that crosses turns therefore matches only if it contains the
   prefix of the later turn(s), exactly as it would for OpenKOS.
3. A turn is overlapped when the matched range touches its ``ROLE: text`` extent.
4. Several occurrences: the FIRST one is used and the count is reported.
5. The span is the union of the overlapped turns' dialogue act ids, in turn order, without
   repeats. Overlapped turns with no act at all give a miss (``NO_DIALOGUE_ACTS``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from afg.conditions.c1_chunking import FrozenTurn, load_frozen_turns
from afg.corpus.render import parse_front_matter
from afg.domain.decision import EvidenceSpan
from afg.shared.paths import TRANSCRIPTS_DIR

# openkos.extraction.decision_pass._NEEDLE_TRAILING_PUNCTUATION
_NEEDLE_TRAILING_PUNCTUATION = ".,;:!?"
_ROLE_SEPARATOR = ": "


class MissReason(StrEnum):
    """Why a quote could not be mapped."""

    EMPTY_QUOTE = "empty_quote"
    NOT_FOUND = "not_found"
    NO_DIALOGUE_ACTS = "no_dialogue_acts"


@dataclass(frozen=True, slots=True)
class EvidenceMatch:
    """A quote mapped to dialogue acts."""

    span: EvidenceSpan
    turn_indices: tuple[int, ...]
    occurrences: int
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class EvidenceMiss:
    """A quote that could not be mapped; countable by the caller."""

    reason: MissReason
    quote: str
    turn_indices: tuple[int, ...] = ()


def normalize_with_offsets(value: str) -> tuple[str, list[int]]:
    """Casefold and collapse whitespace like ``decision_pass._normalize``.

    Returns the normalized text and, for each of its characters, the index of the original
    character it came from (a collapsed whitespace run maps to the start of the run).
    """
    chars: list[str] = []
    offsets: list[int] = []
    pending_space: int | None = None
    for index, char in enumerate(value):
        if char.isspace():
            if pending_space is None:
                pending_space = index
            continue
        if pending_space is not None and chars:
            chars.append(" ")
            offsets.append(pending_space)
        pending_space = None
        for folded in char.casefold():
            chars.append(folded)
            offsets.append(index)
    return "".join(chars), offsets


def _normalized_needle(quote: str) -> str:
    text, _ = normalize_with_offsets(quote)
    return text.rstrip(_NEEDLE_TRAILING_PUNCTUATION)


def _turn_extent(turn: FrozenTurn) -> tuple[int, int]:
    prefix = len(turn.role) + len(_ROLE_SEPARATOR)
    return turn.char_start - prefix, turn.char_end


def locate_quote(
    meeting_id: str, body: str, turns: Sequence[FrozenTurn], quote: str
) -> EvidenceMatch | EvidenceMiss:
    """Map ``quote`` to the dialogue acts of the turns it overlaps in ``body``."""
    needle = _normalized_needle(quote)
    if not needle:
        return EvidenceMiss(MissReason.EMPTY_QUOTE, quote)

    haystack, offsets = normalize_with_offsets(body)
    first = haystack.find(needle)
    if first < 0:
        return EvidenceMiss(MissReason.NOT_FOUND, quote)
    occurrences = 0
    position = first
    while position >= 0:
        occurrences += 1
        position = haystack.find(needle, position + len(needle))

    start = offsets[first]
    end = offsets[first + len(needle) - 1] + 1
    hit = [
        turn
        for turn in sorted(turns, key=lambda t: t.turn_index)
        if start < _turn_extent(turn)[1] and end > _turn_extent(turn)[0]
    ]
    turn_indices = tuple(turn.turn_index for turn in hit)
    acts = tuple(dict.fromkeys(act for turn in hit for act in turn.dialogue_act_ids))
    if not acts:
        return EvidenceMiss(MissReason.NO_DIALOGUE_ACTS, quote, turn_indices)
    return EvidenceMatch(
        span=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=acts),
        turn_indices=turn_indices,
        occurrences=occurrences,
        char_start=start,
        char_end=end,
    )


def load_meeting_text(
    meeting_id: str, transcripts_dir: Path = TRANSCRIPTS_DIR
) -> tuple[str, list[FrozenTurn]]:
    """Read the frozen body (front matter removed) and turns of one meeting."""
    markdown = (transcripts_dir / f"{meeting_id}.md").read_text(encoding="utf-8")
    _, body = parse_front_matter(markdown)
    return body, load_frozen_turns(meeting_id, transcripts_dir)


def locate_quote_in_meeting(
    meeting_id: str, quote: str, transcripts_dir: Path = TRANSCRIPTS_DIR
) -> EvidenceMatch | EvidenceMiss:
    """:func:`locate_quote` over the frozen files of ``meeting_id``."""
    body, turns = load_meeting_text(meeting_id, transcripts_dir)
    return locate_quote(meeting_id, body, turns, quote)
