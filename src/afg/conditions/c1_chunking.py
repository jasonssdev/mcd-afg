"""Turn-aligned chunking of frozen transcripts for C1 (document RAG baseline).

A chunk is a run of consecutive turns rendered exactly like the frozen ``.md`` body
(``ROLE: text`` blocks separated by a blank line). Turns are never split: cutting at turn
boundaries keeps every chunk traceable to whole turns and therefore to the dialogue acts
that overlap them (``dialogue_act_ids``), which is what lets OE4 attribute a wrong C1
answer to the exact annotated evidence it did or did not retrieve.

``max_chars`` and ``overlap_turns`` are the tunable segmentation parameters. Per ADR 0005
they are tuned on development series only, never on the evaluation series. Chunk ids
(``<meeting_id>.c<NNN>``) are stable for a given ``(max_chars, overlap_turns)`` pair and
the same frozen transcripts; changing either parameter renumbers them.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.corpus.render import split_meeting_id
from afg.shared.paths import TRANSCRIPTS_DIR

_TURN_SEPARATOR = "\n\n"


@dataclass(frozen=True, slots=True)
class FrozenTurn:
    """One turn read back from a frozen ``<meeting_id>.jsonl``."""

    meeting_id: str
    turn_index: int
    speaker: str
    role: str
    text: str
    start: float | None
    end: float | None
    char_start: int
    char_end: int
    dialogue_act_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Chunk:
    """A run of consecutive turns; ``first_turn``/``last_turn`` are inclusive indices."""

    chunk_id: str
    meeting_id: str
    series: str
    first_turn: int
    last_turn: int
    start: float | None
    end: float | None
    dialogue_act_ids: tuple[str, ...]
    text: str


def load_frozen_turns(meeting_id: str, transcripts_dir: Path = TRANSCRIPTS_DIR) -> list[FrozenTurn]:
    """Read ``<meeting_id>.jsonl`` and return its turns sorted by ``turn_index``."""
    path = transcripts_dir / f"{meeting_id}.jsonl"
    if not path.is_file():
        raise FileNotFoundError(
            f"Frozen transcript not found: {path}. Render the transcripts first "
            "(`uv run afg gold setup` / `uv run afg corpus transcripts`)."
        )
    turns: list[FrozenTurn] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row["meeting_id"] != meeting_id:
                raise ValueError(
                    f"{path}:{line_no}: line belongs to meeting {row['meeting_id']!r}, "
                    f"expected {meeting_id!r}"
                )
            turns.append(
                FrozenTurn(
                    meeting_id=row["meeting_id"],
                    turn_index=row["turn_index"],
                    speaker=row["speaker"],
                    role=row["role"],
                    text=row["text"],
                    start=row.get("start"),
                    end=row.get("end"),
                    char_start=row["char_start"],
                    char_end=row["char_end"],
                    dialogue_act_ids=tuple(row.get("dialogue_act_ids", ())),
                )
            )
    turns.sort(key=lambda turn: turn.turn_index)
    return turns


def _render(turn: FrozenTurn) -> str:
    return f"{turn.role}: {turn.text}"


def _build_chunk(meeting_id: str, number: int, turns: Sequence[FrozenTurn]) -> Chunk:
    starts = [t.start for t in turns if t.start is not None]
    ends = [t.end for t in turns if t.end is not None]
    acts = dict.fromkeys(act for t in turns for act in t.dialogue_act_ids)
    return Chunk(
        chunk_id=f"{meeting_id}.c{number:03d}",
        meeting_id=meeting_id,
        series=split_meeting_id(meeting_id)[0],
        first_turn=turns[0].turn_index,
        last_turn=turns[-1].turn_index,
        start=min(starts) if starts else None,
        end=max(ends) if ends else None,
        dialogue_act_ids=tuple(acts),
        text=_TURN_SEPARATOR.join(_render(t) for t in turns),
    )


def chunk_turns(turns: Sequence[FrozenTurn], max_chars: int, overlap_turns: int = 0) -> list[Chunk]:
    """Greedily pack consecutive turns into chunks of at most ``max_chars`` characters.

    A turn longer than ``max_chars`` becomes its own chunk (never split or dropped). The
    next chunk starts ``overlap_turns`` turns before the previous one ended, but always
    advances by at least one turn.
    """
    if max_chars < 1:
        raise ValueError(f"max_chars must be >= 1, got {max_chars}")
    if overlap_turns < 0:
        raise ValueError(f"overlap_turns must be >= 0, got {overlap_turns}")
    if not turns:
        return []
    meeting_id = turns[0].meeting_id
    if any(t.meeting_id != meeting_id for t in turns):
        raise ValueError("chunk_turns expects turns from exactly one meeting")

    lengths = [len(_render(t)) for t in turns]
    chunks: list[Chunk] = []
    begin = 0
    while begin < len(turns):
        stop = begin + 1
        size = lengths[begin]
        while stop < len(turns):
            grown = size + len(_TURN_SEPARATOR) + lengths[stop]
            if grown > max_chars:
                break
            size = grown
            stop += 1
        chunks.append(_build_chunk(meeting_id, len(chunks), turns[begin:stop]))
        if stop >= len(turns):
            break
        begin = max(stop - overlap_turns, begin + 1)
    return chunks


def chunk_meetings(
    meeting_ids: Iterable[str],
    max_chars: int,
    overlap_turns: int = 0,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> list[Chunk]:
    """Chunk several meetings, preserving the given meeting order."""
    chunks: list[Chunk] = []
    for meeting_id in meeting_ids:
        turns = load_frozen_turns(meeting_id, transcripts_dir)
        chunks.extend(chunk_turns(turns, max_chars, overlap_turns))
    return chunks
