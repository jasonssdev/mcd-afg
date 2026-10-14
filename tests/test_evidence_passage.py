"""Tests for the transcript passage the judge and the labelers read (issue #82)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.domain.decision import EvidenceSpan
from afg.evaluation.passage import (
    evidence_passage,
    judge_evidence_passage,
    load_evidence_window_turns,
    transcript_files_text,
)
from afg.shared.config import load_experiments_config


def _act(meeting: str, n: int) -> str:
    return f"{meeting}.A.dialog-act.x.{n}"


def _span(meeting: str, *numbers: int) -> EvidenceSpan:
    return EvidenceSpan(
        meeting_id=meeting, dialogue_act_ids=tuple(_act(meeting, n) for n in numbers)
    )


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    """Two meetings of 30 one-act turns each; the text of turn i is '<meeting>-turn-i'."""
    root = tmp_path / "transcripts"
    root.mkdir()
    for meeting in ("ES2015a", "ES2015b"):
        with (root / f"{meeting}.jsonl").open("w", encoding="utf-8") as handle:
            for i in range(30):
                row = {
                    "meeting_id": meeting,
                    "turn_index": i,
                    "speaker": "A",
                    "role": "PM",
                    "text": f"{meeting}-turn-{i}",
                    "start": float(i),
                    "end": float(i) + 0.5,
                    "char_start": 0,
                    "char_end": 1,
                    "dialogue_act_ids": [_act(meeting, i)],
                }
                handle.write(json.dumps(row) + "\n")
        (root / f"{meeting}.md").write_text("# transcript\n", encoding="utf-8")
    return root


def _turns_in(passage: str, meeting: str) -> list[int]:
    return [
        int(line.rsplit("-", 1)[1]) for line in passage.splitlines() if f"{meeting}-turn-" in line
    ]


class TestEvidencePassage:
    def test_window_of_n_turns_before_and_after_the_reference_turns(
        self, transcripts: Path
    ) -> None:
        passage = evidence_passage(
            (_span("ES2015a", 10, 11),), context_turns=3, transcripts_dir=transcripts
        )
        assert _turns_in(passage, "ES2015a") == list(range(7, 15))
        assert passage.startswith("[ES2015a]")

    def test_overlapping_windows_are_merged_without_repeating_turns(
        self, transcripts: Path
    ) -> None:
        passage = evidence_passage(
            (_span("ES2015a", 10, 13),), context_turns=2, transcripts_dir=transcripts
        )
        assert _turns_in(passage, "ES2015a") == list(range(8, 16))

    def test_distant_windows_stay_apart_and_are_marked(self, transcripts: Path) -> None:
        passage = evidence_passage(
            (_span("ES2015a", 3, 25),), context_turns=1, transcripts_dir=transcripts
        )
        assert _turns_in(passage, "ES2015a") == [2, 3, 4, 24, 25, 26]
        assert "[...]" in passage

    def test_window_is_clipped_at_the_edges_of_the_meeting(self, transcripts: Path) -> None:
        passage = evidence_passage(
            (_span("ES2015a", 0), _span("ES2015b", 29)),
            context_turns=2,
            transcripts_dir=transcripts,
        )
        assert _turns_in(passage, "ES2015a") == [0, 1, 2]
        assert _turns_in(passage, "ES2015b") == [27, 28, 29]

    def test_meetings_come_in_chronological_order_with_a_header_each(
        self, transcripts: Path
    ) -> None:
        passage = evidence_passage(
            (_span("ES2015b", 5), _span("ES2015a", 5)),
            context_turns=1,
            transcripts_dir=transcripts,
        )
        assert passage.index("[ES2015a]") < passage.index("[ES2015b]")
        assert passage.count("[ES2015a]") == 1 and passage.count("[ES2015b]") == 1

    def test_spans_of_one_meeting_are_combined(self, transcripts: Path) -> None:
        passage = evidence_passage(
            (_span("ES2015a", 5), _span("ES2015a", 6)),
            context_turns=0,
            transcripts_dir=transcripts,
        )
        assert _turns_in(passage, "ES2015a") == [5, 6]

    def test_no_evidence_gives_an_empty_passage(self, transcripts: Path) -> None:
        assert evidence_passage((), context_turns=5, transcripts_dir=transcripts) == ""

    def test_an_act_missing_from_the_transcript_is_an_error(self, transcripts: Path) -> None:
        bad = EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.999",))
        with pytest.raises(ValueError, match="999"):
            evidence_passage((bad,), context_turns=1, transcripts_dir=transcripts)


class TestJudgePassage:
    def test_window_comes_from_the_judge_config(self, transcripts: Path) -> None:
        n = load_evidence_window_turns()
        assert n == load_experiments_config()["judge"]["evidence_window_turns"] == 5
        passage = judge_evidence_passage((_span("ES2015a", 15),), transcripts_dir=transcripts)
        assert _turns_in(passage, "ES2015a") == list(range(15 - n, 15 + n + 1))

    def test_no_evidence_gives_an_empty_passage(self, transcripts: Path) -> None:
        assert judge_evidence_passage((), transcripts_dir=transcripts) == ""


class TestTranscriptFiles:
    def test_lists_the_readable_transcript_of_each_cited_meeting_in_order(
        self, transcripts: Path
    ) -> None:
        text = transcript_files_text(
            (_span("ES2015b", 1), _span("ES2015a", 1)), transcripts_dir=transcripts
        )
        names = [Path(part).name for part in text.split(";")]
        assert names == ["ES2015a.md", "ES2015b.md"]

    def test_no_evidence_gives_no_files(self, transcripts: Path) -> None:
        assert transcript_files_text((), transcripts_dir=transcripts) == ""
