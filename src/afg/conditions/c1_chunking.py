"""Generic chunking of the Markdown transcript for C1 (conventional document RAG).

C1 reads the same text OpenKOS ingests, the body of ``<meeting_id>.md`` with the front matter
removed (:func:`afg.corpus.render.read_meeting_body`), and cuts it with LangChain's
``RecursiveCharacterTextSplitter`` (paragraph, line, word, character separators; length in
characters). It knows nothing about speaker turns or dialogue acts: a chunk records only the
character span ``[char_start, char_end)`` it occupies in the body. Mapping a span back to AMI
dialogue acts is the evaluator's job (:mod:`afg.evaluation.chunk_acts`), as it is for C2.

``chunk_size`` and ``chunk_overlap`` (characters) are the tunable parameters. Per ADR 0005 they
are tuned on development series only, never on the evaluation series. Chunk ids
(``<meeting_id>.c<NNN>``) are stable for a given ``(chunk_size, chunk_overlap)`` pair and the
same frozen transcripts; changing either parameter renumbers them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from afg.corpus.render import read_meeting_body, split_meeting_id
from afg.shared.paths import TRANSCRIPTS_DIR


@dataclass(frozen=True, slots=True)
class Chunk:
    """A slice ``body[char_start:char_end]`` of one meeting's Markdown body."""

    chunk_id: str
    meeting_id: str
    series: str
    char_start: int
    char_end: int
    text: str


def chunk_body(meeting_id: str, body: str, chunk_size: int, chunk_overlap: int = 0) -> list[Chunk]:
    """Split ``body`` into chunks of at most ``chunk_size`` characters.

    Uses the splitter's default separators and ``length_function=len``. ``chunk_overlap``
    characters are shared between consecutive chunks. Every chunk carries the span it
    occupies in ``body``.

    Raises:
        ValueError: if ``chunk_size < 1``, ``chunk_overlap < 0`` or ``chunk_overlap >= chunk_size``,
            or if the splitter cannot locate one of its chunks in ``body``.
    """
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be >= 0, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap must be smaller than chunk_size, got {chunk_overlap} >= {chunk_size}"
        )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    series = split_meeting_id(meeting_id)[0]
    chunks: list[Chunk] = []
    for document in splitter.create_documents([body]):
        start = int(document.metadata["start_index"])
        text = document.page_content
        if start < 0 or body[start : start + len(text)] != text:
            raise ValueError(f"{meeting_id}: chunk {len(chunks)} cannot be located in the body.")
        chunks.append(
            Chunk(
                chunk_id=f"{meeting_id}.c{len(chunks):03d}",
                meeting_id=meeting_id,
                series=series,
                char_start=start,
                char_end=start + len(text),
                text=text,
            )
        )
    return chunks


def chunk_meetings(
    meeting_ids: Iterable[str],
    chunk_size: int,
    chunk_overlap: int = 0,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> list[Chunk]:
    """Chunk the Markdown body of several meetings, preserving the given meeting order."""
    chunks: list[Chunk] = []
    for meeting_id in meeting_ids:
        body = read_meeting_body(meeting_id, transcripts_dir)
        chunks.extend(chunk_body(meeting_id, body, chunk_size, chunk_overlap))
    return chunks
