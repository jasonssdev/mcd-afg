"""Tests for the adjudicated reference loader (Experiment A scoring, T1)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from afg.domain.decision import DecisionStatus
from afg.evaluation.reference import (
    NotAdjudicatedError,
    ReferenceSet,
    load_reference,
    load_series_reference,
    primary_role,
)
from afg.shared.paths import AMI_DIR, GOLD_DECISIONS_DIR, TRANSCRIPTS_DIR
from tests.markers import requires

MEETING = "ES2015a"
HEADER = [
    "decision_id",
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_text",
    "final_status",
    "final_object",
    "final_content",
    "razon",
    "adjudicator",
]


def _write_csv(path: Path, rows: list[dict[str, str]], header: list[str] = HEADER) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in header})
    return path


def _row(decision_id: str, status: str, sentence: str = "s.1", **extra: str) -> dict[str, str]:
    base = {
        "decision_id": decision_id,
        "meeting_id": decision_id.split(".")[0],
        "source_sentence_id": f"{MEETING}.x.{sentence}",
        "evidence_text": "",
        "final_status": status,
        "final_object": f"object of {decision_id}",
        "final_content": f"content of {decision_id}",
    }
    base.update(extra)
    return base


def _write_transcript(
    directory: Path, turns: list[tuple[str, str, tuple[str, ...]]], meeting: str = MEETING
) -> None:
    body = ""
    lines = []
    for index, (role, text, acts) in enumerate(turns):
        prefix = f"{role}: "
        start = len(body) + len(prefix)
        body += prefix + text + "\n\n"
        lines.append(
            {
                "meeting_id": meeting,
                "turn_index": index,
                "speaker": role,
                "role": role,
                "text": text,
                "start": None,
                "end": None,
                "char_start": start,
                "char_end": start + len(text),
                "dialogue_act_ids": list(acts),
            }
        )
    (directory / f"{meeting}.md").write_text(
        f"---\nmeeting_id: {meeting}\n---\n{body}", encoding="utf-8"
    )
    (directory / f"{meeting}.jsonl").write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8"
    )


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    directory.mkdir()
    _write_transcript(
        directory,
        [
            ("PM", "we will use a kinetic battery", ("da.1",)),
            ("ME", "agreed, kinetic it is", ("da.2", "da.3")),
            ("ID", "the case is rubber", ("da.4",)),
        ],
    )
    return directory


def _load(
    tmp_path: Path,
    transcripts: Path,
    rows: list[dict[str, str]],
    acts: dict[str, list[str]] | None = None,
) -> ReferenceSet:
    path = _write_csv(tmp_path / "ES2015.decisions.adjudicated.csv", rows)
    return load_reference(path, sentence_acts=acts or {}, transcripts_dir=transcripts)


def test_only_decision_rows_are_reference_decisions(tmp_path: Path, transcripts: Path) -> None:
    rows = [
        _row("ES2015a.d01", "decision"),
        _row("ES2015a.d02", "no_decision"),
        _row("ES2015a.d03", "compuesta"),
        _row("ES2015a.d03-1", "decision"),
        _row("ES2015a.d03-2", "descartar"),
        _row("ES2015a.d04", "sin_soporte"),
    ]
    acts = {f"{MEETING}.x.s.1": ["da.1"]}

    reference = _load(tmp_path, transcripts, rows, acts)

    assert [d.decision_id for d in reference.decisions] == ["ES2015a.d01", "ES2015a.d03-1"]
    assert reference.excluded == {
        "no_decision": 1,
        "compuesta": 1,
        "descartar": 1,
        "sin_soporte": 1,
    }
    assert reference.series_id == "ES2015"


def test_decision_carries_object_content_and_converts_to_domain_decision(
    tmp_path: Path, transcripts: Path
) -> None:
    reference = _load(
        tmp_path,
        transcripts,
        [_row("ES2015a.d01", "decision", adjudicator="jss")],
        {f"{MEETING}.x.s.1": ["da.1"]},
    )

    ref = reference.decisions[0]
    assert (ref.decision_object, ref.content) == ("object of ES2015a.d01", "content of ES2015a.d01")
    decision = ref.as_decision()
    assert decision is not None
    assert decision.status is DecisionStatus.ACCEPTED
    assert decision.series_id == "ES2015"
    assert decision.evidence.dialogue_act_ids == ("da.1",)
    assert decision.annotator == "jss"


def test_evidence_uses_exact_sentence_ids_in_transcript_order(
    tmp_path: Path, transcripts: Path
) -> None:
    # Summlink order is file order, not chronological: the span must follow the transcript.
    reference = _load(
        tmp_path,
        transcripts,
        [_row("ES2015a.d01", "decision")],
        {f"{MEETING}.x.s.1": ["da.4", "da.1"]},
    )

    ref = reference.decisions[0]
    assert ref.evidence is not None
    assert ref.evidence.dialogue_act_ids == ("da.1", "da.4")
    assert ref.evidence_method == "sentence_id"
    assert ref.roles == ("PM", "ID")


def test_primary_role_is_the_role_with_most_evidence_acts(
    tmp_path: Path, transcripts: Path
) -> None:
    reference = _load(
        tmp_path,
        transcripts,
        [_row("ES2015a.d01", "decision")],
        {f"{MEETING}.x.s.1": ["da.1", "da.2", "da.3"]},
    )

    assert reference.decisions[0].role == "ME"


def test_primary_role_tie_goes_to_the_earliest_turn(transcripts: Path) -> None:
    from afg.conditions.c1_chunking import load_frozen_turns

    turns = load_frozen_turns(MEETING, transcripts)

    assert primary_role(("da.4", "da.1"), turns) == "PM"
    assert primary_role(("unknown.act",), turns) is None


def test_falls_back_to_quote_matching_when_sentence_has_no_acts(
    tmp_path: Path, transcripts: Path
) -> None:
    reference = _load(
        tmp_path,
        transcripts,
        [_row("ES2015a.d01", "decision", evidence_text="A: the case is rubber")],
    )

    ref = reference.decisions[0]
    assert ref.evidence_method == "quote"
    assert ref.evidence is not None
    assert ref.evidence.dialogue_act_ids == ("da.4",)
    assert ref.role == "ID"
    assert reference.evidence_misses == ()


def test_unmapped_evidence_is_counted_and_the_decision_is_kept(
    tmp_path: Path, transcripts: Path
) -> None:
    reference = _load(
        tmp_path,
        transcripts,
        [_row("ES2015a.d01", "decision", evidence_text="A: nothing like this was said")],
    )

    ref = reference.decisions[0]
    assert ref.evidence is None
    assert ref.evidence_method == "none"
    assert ref.role is None
    assert ref.as_decision() is None
    assert reference.evidence_misses == ("ES2015a.d01",)
    assert len(reference.decisions) == 1


def test_refuses_a_file_that_is_not_adjudicated(tmp_path: Path, transcripts: Path) -> None:
    path = _write_csv(
        tmp_path / "ES2015.decisions.csv",
        [_row("ES2015a.d01", "decision")],
        header=["decision_id", "meeting_id", "source_sentence_id", "status"],
    )

    with pytest.raises(NotAdjudicatedError, match="final_status"):
        load_reference(path, sentence_acts={}, transcripts_dir=transcripts)


def test_refuses_rows_without_a_verdict(tmp_path: Path, transcripts: Path) -> None:
    with pytest.raises(NotAdjudicatedError, match=r"ES2015a\.d02"):
        _load(
            tmp_path,
            transcripts,
            [_row("ES2015a.d01", "decision"), _row("ES2015a.d02", "")],
            {f"{MEETING}.x.s.1": ["da.1"]},
        )


def test_refuses_a_decision_without_object_or_content(tmp_path: Path, transcripts: Path) -> None:
    with pytest.raises(NotAdjudicatedError, match=r"ES2015a\.d01"):
        _load(
            tmp_path,
            transcripts,
            [_row("ES2015a.d01", "decision", final_content="")],
            {f"{MEETING}.x.s.1": ["da.1"]},
        )


def test_series_loader_requires_the_adjudicated_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="adjudicated"):
        load_series_reference("ES2015", decisions_dir=tmp_path, ami_root=tmp_path)


_REAL = GOLD_DECISIONS_DIR / "ES2015.decisions.adjudicated.csv"
requires_data = requires(
    "requires_data",
    available=(_REAL.is_file() and (AMI_DIR / "extractive").is_dir() and TRANSCRIPTS_DIR.is_dir()),
    reason="needs the adjudicated reference, the AMI corpus and the frozen transcripts",
)


@requires_data
def test_real_es2015_reference_loads_with_every_evidence_mapped() -> None:
    reference = load_series_reference("ES2015")

    assert len(reference.decisions) == 27
    assert reference.evidence_misses == ()
    assert {d.evidence_method for d in reference.decisions} == {"sentence_id"}
    assert all(d.role in {"PM", "ME", "UI", "ID"} for d in reference.decisions)
    assert reference.excluded == {
        "no_decision": 3,
        "compuesta": 2,
        "descartar": 1,
        "sin_soporte": 1,
    }


def test_split_child_with_blank_fields_inherits_them_from_its_compuesta_parent(
    tmp_path: Path, transcripts: Path
) -> None:
    # TS3009 stores the -1, -2 children of a compuesta row with a blank meeting_id,
    # source_sentence_id and evidence_text; ES2015 repeats the parent's values. Both must load
    # the same way: the child is a decision of its parent's meeting, with its parent's evidence.
    rows = [
        _row("ES2015a.d03", "compuesta", sentence="s.3", evidence_text="E: the case is rubber"),
        _row(
            "ES2015a.d03-1",
            "decision",
            meeting_id="",
            source_sentence_id="",
            evidence_text="",
        ),
    ]
    acts = {f"{MEETING}.x.s.3": ["da.4"]}

    reference = _load(tmp_path, transcripts, rows, acts)

    (child,) = reference.decisions
    assert child.decision_id == "ES2015a.d03-1"
    assert child.meeting_id == MEETING
    assert child.evidence is not None
    assert child.evidence.dialogue_act_ids == ("da.4",)
    assert child.evidence_method == "sentence_id"
    assert child.role == "ID"
    assert reference.evidence_misses == ()


def test_split_child_keeps_its_own_fields_when_it_has_them(
    tmp_path: Path, transcripts: Path
) -> None:
    rows = [
        _row("ES2015a.d03", "compuesta", sentence="s.3"),
        _row("ES2015a.d03-1", "decision", sentence="s.1"),
    ]
    acts = {f"{MEETING}.x.s.3": ["da.4"], f"{MEETING}.x.s.1": ["da.1"]}

    reference = _load(tmp_path, transcripts, rows, acts)

    (child,) = reference.decisions
    assert child.evidence is not None
    assert child.evidence.dialogue_act_ids == ("da.1",)
