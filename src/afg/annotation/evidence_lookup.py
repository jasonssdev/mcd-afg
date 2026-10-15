"""Find the dialogue act ids an annotator pastes into the question bank's evidence column.

``reference_evidence`` (``meeting:da_id;da_id|meeting:da_id``) needs dialogue act ids, which
live only in the frozen transcripts (``data/interim/transcripts/<meeting>.jsonl``). This
module searches those turns by word, phrase or turn range and formats the ready-to-paste
cell. Errors are :class:`EvidenceLookupError` with a Spanish message, for the CLI to print.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from afg.conditions.c1_chunking import FrozenTurn, load_frozen_turns
from afg.shared.paths import TRANSCRIPTS_DIR

__all__ = [
    "EvidenceLookupError",
    "find_turns",
    "format_evidence",
    "parse_turn_range",
    "turns_with_acts",
]

_SETUP_HINT = "Corre `uv run afg gold setup` para generar las transcripciones."


class EvidenceLookupError(ValueError):
    """A lookup that cannot proceed; the message says what to do next."""


def parse_turn_range(text: str) -> tuple[int, int]:
    """Parse ``--turnos`` (``12`` or ``12-18``) into an inclusive ``(first, last)``."""
    first, _, last = text.strip().partition("-")
    try:
        low = int(first)
        high = int(last) if last.strip() else low
    except ValueError:
        low, high = 1, 0
    if low < 0 or high < low:
        raise EvidenceLookupError(
            f"--turnos {text!r} no es válido: usa un número de turno (12) o un rango (12-18)."
        )
    return low, high


def _meeting_ids(transcripts_dir: Path) -> list[str]:
    if not transcripts_dir.is_dir():
        return []
    return sorted(path.stem for path in transcripts_dir.glob("*.jsonl"))


def _load(meeting_id: str, transcripts_dir: Path) -> list[FrozenTurn]:
    available = _meeting_ids(transcripts_dir)
    if not available:
        raise EvidenceLookupError(f"No hay transcripciones en {transcripts_dir}. {_SETUP_HINT}")
    if meeting_id not in available:
        series = meeting_id[:-1]
        siblings = [
            m for m in available if series and m.startswith(series) and len(m) > len(series)
        ]
        if siblings:
            hint = f"Las reuniones de la serie {series} son: {', '.join(siblings)}."
        else:
            hint = f"Las reuniones disponibles son: {', '.join(available)}."
        raise EvidenceLookupError(f"No existe la reunión {meeting_id!r}. {hint}")
    return load_frozen_turns(meeting_id, transcripts_dir)


def find_turns(
    meeting_id: str,
    *,
    term: str | None = None,
    turn_range: tuple[int, int] | None = None,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> list[FrozenTurn]:
    """Turns of ``meeting_id`` containing ``term`` (case-insensitive) within ``turn_range``."""
    turns = _load(meeting_id, transcripts_dir)
    if turn_range is not None:
        low, high = turn_range
        turns = [t for t in turns if low <= t.turn_index <= high]
    if term:
        needle = term.lower()
        turns = [t for t in turns if needle in t.text.lower()]
    return turns


def turns_with_acts(
    meeting_id: str, act_ids: Iterable[str], *, transcripts_dir: Path = TRANSCRIPTS_DIR
) -> list[FrozenTurn]:
    """The turns that carry at least one of ``act_ids``, in transcript order."""
    wanted = set(act_ids)
    return [
        t for t in _load(meeting_id, transcripts_dir) if wanted.intersection(t.dialogue_act_ids)
    ]


def format_evidence(
    meeting_id: str, turns: Sequence[FrozenTurn], *, only: Iterable[str] | None = None
) -> str:
    """The ``meeting:da_id;da_id`` cell for ``turns`` (optionally restricted to ``only``)."""
    keep = set(only) if only is not None else None
    acts = [act for turn in turns for act in turn.dialogue_act_ids if keep is None or act in keep]
    return f"{meeting_id}:{';'.join(dict.fromkeys(acts))}"
