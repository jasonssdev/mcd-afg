"""Tests for C1 chunking of the Markdown transcript body (synthetic fixtures only)."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from afg.conditions.c1_chunking import Chunk, chunk_body, chunk_meetings
from afg.corpus.render import read_meeting_body

from .frozen_fixtures import write_frozen_meeting

MEETING = "ES2015a"
TURNS = [(f"turn number {i} " + " ".join(["word"] * 12), (f"d{i}",)) for i in range(8)]


def test_read_meeting_body_strips_the_front_matter(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    assert read_meeting_body(MEETING, tmp_path) == body
    assert not body.startswith("---")


def test_read_meeting_body_missing_file_names_the_render_step(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="corpus transcripts"):
        read_meeting_body(MEETING, tmp_path)


def test_every_chunk_is_the_body_slice_at_its_char_span(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    chunks = chunk_body(MEETING, body, chunk_size=200, chunk_overlap=0)
    assert len(chunks) > 1
    for chunk in chunks:
        assert body[chunk.char_start : chunk.char_end] == chunk.text
        assert len(chunk.text) <= 200


def test_chunks_cover_the_whole_body_without_overlap(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    chunks = chunk_body(MEETING, body, chunk_size=200, chunk_overlap=0)
    covered = "\n\n".join(c.text for c in chunks)
    assert covered == body
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(body)


def test_overlap_makes_consecutive_spans_share_characters(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    chunks = chunk_body(MEETING, body, chunk_size=200, chunk_overlap=100)
    assert any(a.char_end > b.char_start for a, b in pairwise(chunks))
    for chunk in chunks:
        assert body[chunk.char_start : chunk.char_end] == chunk.text


def test_paragraph_boundaries_are_preferred_split_points(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    turn_len = len(TURNS[0][0]) + len("PM: ")
    chunks = chunk_body(MEETING, body, chunk_size=turn_len * 2 + 2, chunk_overlap=0)
    for chunk in chunks[1:]:
        assert body[chunk.char_start - 2 : chunk.char_start] == "\n\n"


def test_chunk_ids_are_stable_and_sequential(tmp_path: Path) -> None:
    body = write_frozen_meeting(tmp_path, MEETING, TURNS)
    first = chunk_body(MEETING, body, chunk_size=200, chunk_overlap=0)
    second = chunk_body(MEETING, body, chunk_size=200, chunk_overlap=0)
    assert [c.chunk_id for c in first] == [f"{MEETING}.c{i:03d}" for i in range(len(first))]
    assert first == second
    assert {c.meeting_id for c in first} == {MEETING}
    assert {c.series for c in first} == {"ES2015"}


def test_empty_body_has_no_chunks() -> None:
    assert chunk_body(MEETING, "", chunk_size=100, chunk_overlap=0) == []


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (100, -1), (100, 100), (100, 101)])
def test_invalid_parameters_are_rejected(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_body(MEETING, "some text", chunk_size=size, chunk_overlap=overlap)


def test_chunk_meetings_reads_only_the_markdown(tmp_path: Path) -> None:
    write_frozen_meeting(tmp_path, "ES2015a", TURNS)
    write_frozen_meeting(tmp_path, "ES2015b", TURNS[:3])
    (tmp_path / "ES2015a.jsonl").unlink()
    (tmp_path / "ES2015b.jsonl").unlink()
    chunks = chunk_meetings(["ES2015b", "ES2015a"], 200, 0, tmp_path)
    assert chunks[0].meeting_id == "ES2015b"
    assert {c.meeting_id for c in chunks} == {"ES2015a", "ES2015b"}
    assert all(isinstance(c, Chunk) for c in chunks)
    assert chunks[-1].chunk_id.startswith("ES2015a.c")
