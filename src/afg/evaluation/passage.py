"""Transcript passages built from reference evidence (thesis section 5.7, issue #82).

The annotators read the linked dialogue acts and, when those are not enough, the frozen
transcript. The judge and the people who label the calibration set follow the same method, so
both read the passage built here: for each reference :class:`EvidenceSpan`, a window of
speaker turns around the turns that contain the reference dialogue acts.

* Windows that overlap or touch are merged; distant ones stay apart, marked with ``[...]``.
* Meetings are concatenated in chronological order, each under a ``[<meeting>]`` header.
* No evidence (E4 questions) gives an empty passage.

The same windowing also feeds the answer generator.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from afg.conditions.c1_chunking import FrozenTurn, load_frozen_turns
from afg.domain.decision import EvidenceSpan
from afg.shared.config import load_experiments_config
from afg.shared.paths import PROJECT_ROOT, TRANSCRIPTS_DIR

GAP_MARKER = "[...]"


def _lines(turns: Sequence[FrozenTurn]) -> str:
    return "\n".join(f"{t.role}: {t.text}" for t in turns)


def render_turns(meeting_id: str, turns: Sequence[FrozenTurn]) -> str:
    """``[meeting]`` header followed by one ``ROLE: text`` line per turn."""
    return f"[{meeting_id}]\n{_lines(turns)}"


def load_evidence_window_turns() -> int:
    """``[judge].evidence_window_turns``: the same budget for every judge candidate."""
    return int(load_experiments_config()["judge"]["evidence_window_turns"])


def _acts_by_meeting(spans: Sequence[EvidenceSpan]) -> dict[str, set[str]]:
    acts: dict[str, set[str]] = {}
    for span in spans:
        acts.setdefault(span.meeting_id, set()).update(span.dialogue_act_ids)
    return acts


def _merged_windows(hits: Sequence[int], n_turns: int, context: int) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for hit in sorted(hits):
        low, high = max(hit - context, 0), min(hit + context, n_turns - 1)
        if windows and low <= windows[-1][1] + 1:
            windows[-1] = (windows[-1][0], max(windows[-1][1], high))
        else:
            windows.append((low, high))
    return windows


def evidence_passage(
    spans: Sequence[EvidenceSpan],
    *,
    context_turns: int,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> str:
    """The transcript turns around the reference dialogue acts, ``context_turns`` each side.

    Raises:
        ValueError: if a reference act does not appear in its meeting's frozen transcript.
        FileNotFoundError: if a cited meeting has no frozen transcript.
    """
    blocks: list[str] = []
    for meeting_id, acts in sorted(_acts_by_meeting(spans).items()):
        turns = load_frozen_turns(meeting_id, transcripts_dir)
        absent = sorted(acts - {a for t in turns for a in t.dialogue_act_ids})
        if absent:
            raise ValueError(f"dialogue acts {absent} are not in the transcript of {meeting_id}.")
        hits = [i for i, t in enumerate(turns) if acts.intersection(t.dialogue_act_ids)]
        parts = [
            _lines(turns[low : high + 1])
            for low, high in _merged_windows(hits, len(turns), context_turns)
        ]
        blocks.append(f"[{meeting_id}]\n" + f"\n{GAP_MARKER}\n".join(parts))
    return "\n\n".join(blocks)


def judge_evidence_passage(
    spans: Sequence[EvidenceSpan], *, transcripts_dir: Path = TRANSCRIPTS_DIR
) -> str:
    """The excerpt the judge (and the labelers) read, with the configured window."""
    return evidence_passage(
        spans, context_turns=load_evidence_window_turns(), transcripts_dir=transcripts_dir
    )


def transcript_files_text(
    spans: Sequence[EvidenceSpan], *, transcripts_dir: Path = TRANSCRIPTS_DIR
) -> str:
    """``;``-separated paths of the readable transcripts of the cited meetings, in order."""
    paths = []
    for meeting_id in sorted(_acts_by_meeting(spans)):
        path = transcripts_dir / f"{meeting_id}.md"
        try:
            paths.append(str(path.relative_to(PROJECT_ROOT)))
        except ValueError:
            paths.append(str(path))
    return ";".join(paths)
