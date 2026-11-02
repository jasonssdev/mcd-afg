"""Evaluator-side mapping of a chunk's char span to AMI dialogue acts."""

from __future__ import annotations

from pathlib import Path

from afg.conditions.c1_chunking import Chunk, chunk_body
from afg.corpus.frozen import load_frozen_turns
from afg.evaluation.chunk_acts import ChunkActMapper, dialogue_acts_for_span

from .frozen_fixtures import write_frozen_meeting

MEETING = "ES2015a"
# One turn per paragraph; a turn spans "PM: <text>" in the body.
TURNS = [
    ("alpha", ("a0",)),
    ("beta", ("a1", "shared")),
    ("gamma", ("shared", "a2")),
    ("delta", ()),
]


def _extents(tmp_path: Path) -> list[tuple[int, int]]:
    return [(t.char_start - len("PM: "), t.char_end) for t in load_frozen_turns(MEETING, tmp_path)]


def test_span_inside_one_turn_maps_to_its_acts(tmp_path: Path) -> None:
    write_frozen_meeting(tmp_path, MEETING, TURNS)
    start, end = _extents(tmp_path)[1]
    turns = load_frozen_turns(MEETING, tmp_path)
    assert dialogue_acts_for_span(turns, start + 1, end - 1) == ("a1", "shared")


def test_span_crossing_a_turn_boundary_takes_both_turns_in_order_without_repeats(
    tmp_path: Path,
) -> None:
    write_frozen_meeting(tmp_path, MEETING, TURNS)
    turns = load_frozen_turns(MEETING, tmp_path)
    ext = _extents(tmp_path)
    assert dialogue_acts_for_span(turns, ext[1][1] - 2, ext[2][0] + 2) == ("a1", "shared", "a2")


def test_a_single_overlapping_character_is_enough_and_the_end_is_exclusive(
    tmp_path: Path,
) -> None:
    write_frozen_meeting(tmp_path, MEETING, TURNS)
    turns = load_frozen_turns(MEETING, tmp_path)
    ext = _extents(tmp_path)
    assert dialogue_acts_for_span(turns, 0, ext[0][1]) == ("a0",)
    assert dialogue_acts_for_span(turns, 0, ext[0][0] + 1) == ("a0",)
    # [ext0.end, ext1.start) is the blank-line separator: no turn.
    assert dialogue_acts_for_span(turns, ext[0][1], ext[1][0]) == ()
    # a span starting exactly at a turn's end does not touch it
    assert dialogue_acts_for_span(turns, ext[0][1], ext[1][0] + 1) == ("a1", "shared")


def test_offsets_are_body_relative_not_file_relative(tmp_path: Path) -> None:
    """The .jsonl offsets index the .md BODY: the front matter must not shift the mapping."""
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    file_text = (tmp_path / f"{MEETING}.md").read_text(encoding="utf-8")
    assert file_text != body and file_text.endswith(body)  # front matter exists
    chunks = chunk_body(MEETING, body, chunk_size=12, chunk_overlap=0)
    mapper = ChunkActMapper(tmp_path)
    by_text = {c.text: mapper.acts_of(c) for c in chunks}
    assert by_text["PM: alpha"] == ("a0",)
    assert by_text["PM: beta"] == ("a1", "shared")
    assert by_text["PM: delta"] == ()


def test_chunk_acts_follow_the_chunk_span(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    chunk = Chunk(MEETING + ".c000", MEETING, "ES2015", 0, len(body), body)
    assert ChunkActMapper(tmp_path).acts_of(chunk) == ("a0", "a1", "shared", "a2")


def test_act_extents_list_every_turn_carrying_the_act(tmp_path: Path) -> None:
    write_frozen_meeting(tmp_path, MEETING, TURNS)
    ext = _extents(tmp_path)
    mapper = ChunkActMapper(tmp_path)
    assert mapper.act_extents(MEETING, "shared") == (ext[1], ext[2])
    assert mapper.act_extents(MEETING, "missing") == ()


def test_the_mapper_needs_the_frozen_jsonl(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        ChunkActMapper(tmp_path).acts_for_span(MEETING, 0, 5)
