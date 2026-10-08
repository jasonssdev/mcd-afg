"""Tests for turn-aligned C1 chunking (synthetic fixtures only; no frozen data)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.conditions.c1_chunking import (
    Chunk,
    FrozenTurn,
    chunk_meetings,
    chunk_turns,
    load_frozen_turns,
)

MEETING = "ES2015a"


def _turn(
    index: int,
    text: str = "hello",
    *,
    meeting_id: str = MEETING,
    role: str = "PM",
    start: float | None = None,
    end: float | None = None,
    acts: tuple[str, ...] = (),
) -> FrozenTurn:
    return FrozenTurn(
        meeting_id=meeting_id,
        turn_index=index,
        speaker="A",
        role=role,
        text=text,
        start=start,
        end=end,
        char_start=0,
        char_end=len(text),
        dialogue_act_ids=acts,
    )


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _row(meeting_id: str, index: int, text: str = "hi") -> dict[str, object]:
    return {
        "char_end": 10,
        "char_start": 4,
        "dialogue_act_ids": [f"{meeting_id}.A.dialog-act.x.{index}"],
        "end": None,
        "meeting_id": meeting_id,
        "role": "PM",
        "speaker": "A",
        "start": None,
        "text": text,
        "turn_index": index,
    }


def test_load_sorts_by_turn_index(tmp_path: Path) -> None:
    _write(tmp_path / f"{MEETING}.jsonl", [_row(MEETING, 2), _row(MEETING, 0), _row(MEETING, 1)])
    turns = load_frozen_turns(MEETING, tmp_path)
    assert [t.turn_index for t in turns] == [0, 1, 2]
    assert turns[0].dialogue_act_ids == (f"{MEETING}.A.dialog-act.x.0",)
    assert turns[0].start is None


def test_load_missing_file_has_clear_message(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="afg gold setup"):
        load_frozen_turns(MEETING, tmp_path)


def test_load_rejects_mismatched_meeting_id(tmp_path: Path) -> None:
    _write(tmp_path / f"{MEETING}.jsonl", [_row(MEETING, 0), _row("ES2015b", 1)])
    with pytest.raises(ValueError, match="ES2015b"):
        load_frozen_turns(MEETING, tmp_path)


def test_chunk_text_format() -> None:
    turns = [_turn(0, "one", role="PM"), _turn(1, "two", role="UI")]
    (chunk,) = chunk_turns(turns, max_chars=1000)
    assert chunk.text == "PM: one\n\nUI: two"


def test_greedy_boundary_exact_fit_and_overflow() -> None:
    turns = [_turn(0, "aaaa"), _turn(1, "bbbb")]
    joined = len("PM: aaaa\n\nPM: bbbb")
    assert len(chunk_turns(turns, max_chars=joined)) == 1
    assert len(chunk_turns(turns, max_chars=joined - 1)) == 2


def test_oversized_turn_kept_whole() -> None:
    big = "x" * 500
    chunks = chunk_turns([_turn(0, "a"), _turn(1, big), _turn(2, "b")], max_chars=20)
    assert [(c.first_turn, c.last_turn) for c in chunks] == [(0, 0), (1, 1), (2, 2)]
    assert chunks[1].text == f"PM: {big}"


def test_overlap_repeats_trailing_turns() -> None:
    turns = [_turn(i, "abcd") for i in range(5)]
    per_two = len("PM: abcd\n\nPM: abcd")
    chunks = chunk_turns(turns, max_chars=per_two, overlap_turns=1)
    assert [(c.first_turn, c.last_turn) for c in chunks] == [(0, 1), (1, 2), (2, 3), (3, 4)]


def test_overlap_larger_than_chunk_still_terminates() -> None:
    turns = [_turn(i, "abcd") for i in range(4)]
    one = len("PM: abcd")
    chunks = chunk_turns(turns, max_chars=one, overlap_turns=5)
    assert [(c.first_turn, c.last_turn) for c in chunks] == [(0, 0), (1, 1), (2, 2), (3, 3)]


def test_chunk_ids_series_and_numbering() -> None:
    chunks = chunk_turns([_turn(i, "abcd") for i in range(3)], max_chars=8)
    assert [c.chunk_id for c in chunks] == [f"{MEETING}.c000", f"{MEETING}.c001", f"{MEETING}.c002"]
    assert {c.series for c in chunks} == {"ES2015"}
    assert {c.meeting_id for c in chunks} == {MEETING}


def test_series_for_meeting_without_session_letter() -> None:
    (chunk,) = chunk_turns([_turn(0, meeting_id="IB4001")], max_chars=100)
    assert chunk.series == "IB4001"


def test_time_and_acts_aggregation_with_none() -> None:
    turns = [
        _turn(0, start=None, end=None, acts=("a1", "a2")),
        _turn(1, start=5.0, end=6.0, acts=("a2", "a3")),
        _turn(2, start=7.0, end=None, acts=()),
    ]
    (chunk,) = chunk_turns(turns, max_chars=1000)
    assert chunk.start == 5.0
    assert chunk.end == 6.0
    assert chunk.dialogue_act_ids == ("a1", "a2", "a3")


def test_all_none_times() -> None:
    (chunk,) = chunk_turns([_turn(0), _turn(1)], max_chars=1000)
    assert chunk.start is None
    assert chunk.end is None
    assert chunk.dialogue_act_ids == ()


@pytest.mark.parametrize("kwargs", [{"max_chars": 0}, {"max_chars": 10, "overlap_turns": -1}])
def test_invalid_params(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        chunk_turns([_turn(0)], **kwargs)


def test_empty_input() -> None:
    assert chunk_turns([], max_chars=10) == []


def test_multi_meeting_rejected() -> None:
    with pytest.raises(ValueError, match="one meeting"):
        chunk_turns([_turn(0), _turn(1, meeting_id="ES2015b")], max_chars=100)


def test_chunk_meetings_preserves_order(tmp_path: Path) -> None:
    for mid in ("ES2015b", "ES2015a"):
        _write(tmp_path / f"{mid}.jsonl", [_row(mid, 0), _row(mid, 1)])
    chunks = chunk_meetings(["ES2015b", "ES2015a"], max_chars=10, transcripts_dir=tmp_path)
    assert [c.chunk_id for c in chunks] == [
        "ES2015b.c000",
        "ES2015b.c001",
        "ES2015a.c000",
        "ES2015a.c001",
    ]
    assert all(isinstance(c, Chunk) for c in chunks)
