"""Tests for the quote -> dialogue acts mapping (OpenKOS decision-pass evidence)."""

from __future__ import annotations

import json
from pathlib import Path

from afg.conditions.c1_chunking import FrozenTurn
from afg.extraction.openkos.evidence import (
    EvidenceMatch,
    EvidenceMiss,
    MissReason,
    locate_quote,
    locate_quote_in_meeting,
    normalize_with_offsets,
)

MEETING = "ES2015a"


def _transcript(rows: list[tuple[str, str, tuple[str, ...]]]) -> tuple[str, list[FrozenTurn]]:
    """Build a body in the frozen-transcript layout (``ROLE: text`` + blank line)."""
    body = ""
    turns: list[FrozenTurn] = []
    for index, (role, text, acts) in enumerate(rows):
        prefix = f"{role}: "
        start = len(body) + len(prefix)
        body += prefix + text
        turns.append(
            FrozenTurn(
                meeting_id=MEETING,
                turn_index=index,
                speaker=role,
                role=role,
                text=text,
                start=None,
                end=None,
                char_start=start,
                char_end=start + len(text),
                dialogue_act_ids=acts,
            )
        )
        body += "\n\n"
    return body.rstrip("\n"), turns


ROWS = [
    ("PM", "Welcome everyone.", ("a1",)),
    ("ME", "We should go with the remote control in rubber.", ("a2", "a3")),
    ("PM", "Okay, rubber it is.", ("a4",)),
    ("UI", "No acts here.", ()),
    ("PM", "Okay, rubber it is.", ("a5",)),
]


def test_single_turn_quote() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "remote control in rubber")
    assert isinstance(result, EvidenceMatch)
    assert result.span.meeting_id == MEETING
    assert result.span.dialogue_act_ids == ("a2", "a3")
    assert result.turn_indices == (1,)


def test_match_is_casefolded_and_whitespace_normalized() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "  WE should   go\nwith the REMOTE control ")
    assert isinstance(result, EvidenceMatch)
    assert result.span.dialogue_act_ids == ("a2", "a3")


def test_trailing_punctuation_of_the_quote_is_ignored_like_openkos() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "Welcome everyone!!")
    assert isinstance(result, EvidenceMatch)
    assert result.span.dialogue_act_ids == ("a1",)


def test_quote_spanning_turns_unions_acts_in_order() -> None:
    body, turns = _transcript(ROWS)
    quote = "in rubber.\n\nPM: Okay, rubber"
    result = locate_quote(MEETING, body, turns, quote)
    assert isinstance(result, EvidenceMatch)
    assert result.turn_indices == (1, 2)
    assert result.span.dialogue_act_ids == ("a2", "a3", "a4")


def test_quote_with_role_prefix_includes_that_turn() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "PM: Welcome everyone.")
    assert isinstance(result, EvidenceMatch)
    assert result.turn_indices == (0,)


def test_quote_made_only_of_a_prefix_still_maps_to_its_turn() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "ME: We should")
    assert isinstance(result, EvidenceMatch)
    assert result.turn_indices == (1,)


def test_multiple_occurrences_use_the_first_and_report_the_count() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "Okay, rubber it is")
    assert isinstance(result, EvidenceMatch)
    assert result.occurrences == 2
    assert result.turn_indices == (2,)
    assert result.span.dialogue_act_ids == ("a4",)


def test_not_found_is_a_typed_miss_not_an_exception() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "something never said")
    assert result == EvidenceMiss(reason=MissReason.NOT_FOUND, quote="something never said")


def test_empty_and_punctuation_only_quotes_are_misses() -> None:
    body, turns = _transcript(ROWS)
    for quote in ("", "   \n ", "...", " ?! "):
        result = locate_quote(MEETING, body, turns, quote)
        assert isinstance(result, EvidenceMiss)
        assert result.reason is MissReason.EMPTY_QUOTE


def test_turn_without_dialogue_acts_is_a_miss_that_names_the_turns() -> None:
    body, turns = _transcript(ROWS)
    result = locate_quote(MEETING, body, turns, "No acts here")
    assert isinstance(result, EvidenceMiss)
    assert result.reason is MissReason.NO_DIALOGUE_ACTS
    assert result.turn_indices == (3,)


def test_acts_are_deduplicated_keeping_first_position() -> None:
    rows = [("PM", "one two", ("a1", "a2")), ("ME", "three", ("a2", "a3"))]
    body, turns = _transcript(rows)
    result = locate_quote(MEETING, body, turns, "one two\n\nME: three")
    assert isinstance(result, EvidenceMatch)
    assert result.span.dialogue_act_ids == ("a1", "a2", "a3")


def test_offsets_survive_casefold_that_changes_length() -> None:
    rows = [("PM", "Straße zu", ("a1",)), ("ME", "second turn", ("a2",))]
    body, turns = _transcript(rows)
    result = locate_quote(MEETING, body, turns, "second turn")
    assert isinstance(result, EvidenceMatch)
    assert result.turn_indices == (1,)


def test_normalize_with_offsets_maps_back_to_the_original() -> None:
    text, offsets = normalize_with_offsets("  Ab \n\n cD")
    assert text == "ab cd"
    assert offsets == [2, 3, 4, 8, 9]


def test_locate_quote_in_meeting_reads_the_frozen_files(tmp_path: Path) -> None:
    body, turns = _transcript(ROWS)
    front = f"---\nmeeting_id: {MEETING}\nseries: ES2015\n---\n\n"
    (tmp_path / f"{MEETING}.md").write_text(front + body, encoding="utf-8")
    with (tmp_path / f"{MEETING}.jsonl").open("w", encoding="utf-8") as handle:
        for turn in turns:
            row = {
                "meeting_id": turn.meeting_id,
                "turn_index": turn.turn_index,
                "speaker": turn.speaker,
                "role": turn.role,
                "text": turn.text,
                "start": None,
                "end": None,
                "char_start": turn.char_start,
                "char_end": turn.char_end,
                "dialogue_act_ids": list(turn.dialogue_act_ids),
            }
            handle.write(json.dumps(row) + "\n")
    result = locate_quote_in_meeting(MEETING, "remote control in rubber", tmp_path)
    assert isinstance(result, EvidenceMatch)
    assert result.span.dialogue_act_ids == ("a2", "a3")
