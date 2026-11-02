"""Frozen transcripts as the evaluator sees them: ``<meeting_id>.jsonl`` turns.

Each line of a frozen ``<meeting_id>.jsonl`` is one turn with its AMI dialogue acts and its
``char_start``/``char_end`` inside the BODY of ``<meeting_id>.md`` (front matter removed, see
:func:`afg.corpus.render.parse_front_matter`). Conditions that must read the plain Markdown
(C1) never import this module; the evaluator uses it to map text spans back to annotations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from afg.shared.paths import TRANSCRIPTS_DIR

_ROLE_SEPARATOR = ": "


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


def turn_extent(turn: FrozenTurn) -> tuple[int, int]:
    """``[start, end)`` of the whole ``ROLE: text`` line of ``turn`` inside the ``.md`` body.

    ``char_start`` points at the text after the role prefix, so the extent starts earlier.
    """
    return turn.char_start - len(turn.role) - len(_ROLE_SEPARATOR), turn.char_end
