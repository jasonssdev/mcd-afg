"""Evaluator-side mapping from a C1 chunk to AMI dialogue acts.

C1 chunks the plain ``.md`` body and knows nothing about turns or dialogue acts. To score it
(retrieval recall, citation overlap, OE4 attribution) the evaluator maps a chunk's character
span back to annotations after the fact, using the frozen ``<meeting_id>.jsonl``: the acts of
every turn whose extent overlaps the span. Granularity is the turn, as for C2 evidence
(:func:`afg.extraction.openkos.evidence.locate_quote`).

Offset convention (verified against :func:`afg.corpus.render.render_meeting_artifacts`): the
``.jsonl`` ``char_start``/``char_end`` index the BODY of the ``.md`` (front matter removed,
what :func:`afg.corpus.render.read_meeting_body` returns), and ``char_start`` points past the
``ROLE: `` prefix, so a turn's line occupies :func:`afg.corpus.frozen.turn_extent`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from afg.conditions.c1_chunking import Chunk
from afg.corpus.frozen import FrozenTurn, load_frozen_turns, turn_extent
from afg.shared.paths import TRANSCRIPTS_DIR


def dialogue_acts_for_span(
    turns: Sequence[FrozenTurn], char_start: int, char_end: int
) -> tuple[str, ...]:
    """Dialogue acts of every turn overlapping ``[char_start, char_end)``, in transcript order."""
    acts: dict[str, None] = {}
    for turn in sorted(turns, key=lambda t: t.turn_index):
        start, end = turn_extent(turn)
        if start < char_end and end > char_start:
            acts.update(dict.fromkeys(turn.dialogue_act_ids))
    return tuple(acts)


class ChunkActMapper:
    """Maps chunk spans to dialogue acts, reading each meeting's ``.jsonl`` once."""

    def __init__(self, transcripts_dir: Path = TRANSCRIPTS_DIR) -> None:
        self.transcripts_dir = transcripts_dir
        self._turns: dict[str, list[FrozenTurn]] = {}

    def turns(self, meeting_id: str) -> list[FrozenTurn]:
        if meeting_id not in self._turns:
            self._turns[meeting_id] = load_frozen_turns(meeting_id, self.transcripts_dir)
        return self._turns[meeting_id]

    def acts_for_span(self, meeting_id: str, char_start: int, char_end: int) -> tuple[str, ...]:
        return dialogue_acts_for_span(self.turns(meeting_id), char_start, char_end)

    def acts_of(self, chunk: Chunk) -> tuple[str, ...]:
        """The dialogue acts a chunk contains (turn granularity)."""
        return self.acts_for_span(chunk.meeting_id, chunk.char_start, chunk.char_end)

    def act_extents(self, meeting_id: str, act_id: str) -> tuple[tuple[int, int], ...]:
        """Body extents of every turn carrying ``act_id``, in transcript order."""
        return tuple(
            turn_extent(t)
            for t in sorted(self.turns(meeting_id), key=lambda t: t.turn_index)
            if act_id in t.dialogue_act_ids
        )
