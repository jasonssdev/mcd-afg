"""Tests for the dialogue-act lookup annotators use to fill ``reference_evidence``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.annotation.evidence_lookup import (
    EvidenceLookupError,
    find_turns,
    format_evidence,
    parse_turn_range,
)
from afg.domain.question import parse_reference_evidence

_TURNS = [
    (0, "PM", "Welcome to the meeting everyone.", ["M1a.A.da.1"]),
    (1, "UI", "I think the remote control should be yellow.", ["M1a.B.da.2", "M1a.B.da.3"]),
    (2, "ID", "Yellow is fine, a Remote is a remote.", ["M1a.C.da.4"]),
    (3, "PM", "Okay, price is twelve euros.", ["M1a.A.da.5"]),
]


def _write_meeting(directory: Path, meeting: str = "M1a") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "meeting_id": meeting,
                "turn_index": index,
                "speaker": "A",
                "role": role,
                "text": text,
                "start": 0.0,
                "end": 1.0,
                "char_start": 0,
                "char_end": 1,
                "dialogue_act_ids": acts,
            }
        )
        for index, role, text, acts in _TURNS
    ]
    (directory / f"{meeting}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / f"{meeting}.md").write_text(f"---\nmeeting_id: {meeting}\n---\n\nbody\n")


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    _write_meeting(directory)
    _write_meeting(directory, "M1b")
    return directory


def test_parse_turn_range() -> None:
    assert parse_turn_range("3") == (3, 3)
    assert parse_turn_range("2-5") == (2, 5)
    with pytest.raises(EvidenceLookupError, match="--turnos"):
        parse_turn_range("5-2")
    with pytest.raises(EvidenceLookupError, match="--turnos"):
        parse_turn_range("abc")


def test_find_by_term_is_case_insensitive_and_returns_turns(transcripts: Path) -> None:
    turns = find_turns("M1a", transcripts_dir=transcripts, term="REMOTE")
    assert [t.turn_index for t in turns] == [1, 2]


def test_find_by_phrase(transcripts: Path) -> None:
    turns = find_turns("M1a", transcripts_dir=transcripts, term="twelve euros")
    assert [t.turn_index for t in turns] == [3]


def test_find_by_range_and_term_combined(transcripts: Path) -> None:
    turns = find_turns("M1a", transcripts_dir=transcripts, term="yellow", turn_range=(2, 3))
    assert [t.turn_index for t in turns] == [2]


def test_find_by_range_alone(transcripts: Path) -> None:
    turns = find_turns("M1a", transcripts_dir=transcripts, turn_range=(0, 1))
    assert [t.turn_index for t in turns] == [0, 1]


def test_unknown_meeting_lists_the_meetings_of_its_series(transcripts: Path) -> None:
    with pytest.raises(EvidenceLookupError) as caught:
        find_turns("M1z", transcripts_dir=transcripts, term="x")
    message = str(caught.value)
    assert "M1z" in message and "M1a" in message and "M1b" in message


def test_unknown_meeting_without_series_lists_all(transcripts: Path) -> None:
    with pytest.raises(EvidenceLookupError, match="M1a"):
        find_turns("ZZ9999a", transcripts_dir=transcripts, term="x")


def test_missing_transcripts_point_to_setup(tmp_path: Path) -> None:
    with pytest.raises(EvidenceLookupError, match="uv run afg gold setup"):
        find_turns("M1a", transcripts_dir=tmp_path / "none", term="x")


def test_format_evidence_is_parseable_by_the_bank_parser(transcripts: Path) -> None:
    turns = find_turns("M1a", transcripts_dir=transcripts, turn_range=(1, 2))
    cell = format_evidence("M1a", turns)
    assert cell == "M1a:M1a.B.da.2;M1a.B.da.3;M1a.C.da.4"
    (span,) = parse_reference_evidence(cell)
    assert span.meeting_id == "M1a"
    assert span.dialogue_act_ids == ("M1a.B.da.2", "M1a.B.da.3", "M1a.C.da.4")


# --- CLI ---------------------------------------------------------------------------------


@pytest.fixture
def cli_env(transcripts: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", transcripts)
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", decisions)
    return decisions


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["gold", "evidencia", *args])


def _flat(output: str) -> str:
    return " ".join(output.split())


def test_cli_by_term_prints_turns_acts_and_paste_string(cli_env: Path) -> None:
    result = _run("--meeting", "M1a", "--term", "price")
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "turno 3" in out and "PM" in out
    assert "Okay, price is twelve euros." in out
    assert "M1a:M1a.A.da.5" in out


def test_cli_by_turn_range_gives_a_combined_string(cli_env: Path) -> None:
    result = _run("--meeting", "M1a", "--turnos", "1-2")
    assert result.exit_code == 0, result.output
    assert "M1a:M1a.B.da.2;M1a.B.da.3;M1a.C.da.4" in _flat(result.output)


def test_cli_no_hits_exits_1_with_hint(cli_env: Path) -> None:
    result = _run("--meeting", "M1a", "--term", "warranty")
    assert result.exit_code == 1
    assert "warranty" in result.output and "Traceback" not in result.output


def test_cli_requires_a_search_mode(cli_env: Path) -> None:
    result = _run("--meeting", "M1a")
    assert result.exit_code == 1
    assert "--term" in result.output and "--turnos" in result.output


def test_cli_unknown_meeting_is_a_clean_error(cli_env: Path) -> None:
    result = _run("--meeting", "M1z", "--term", "x")
    assert result.exit_code == 1
    assert "M1a" in result.output and "Traceback" not in result.output


def test_cli_decision_mode_prints_acts_of_the_adjudicated_decision(
    cli_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cli_env / "M1.decisions.adjudicated.csv").write_text(
        "decision_id,meeting_id,source_sentence_id,sentence_text,evidence_text,final_status,"
        "final_object,final_content\n"
        'M1a.d01,M1a,M1a.x.s.1,The price is twelve euros.,"A: price is twelve euros .",'
        "decision,precio,fijar el precio en 12 euros\n"
        "M1a.d02,M1a,M1a.x.s.2,Other.,,no_decision,,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "afg.annotation.goldset.summlink_dialogue_act_ids",
        lambda ami_root, meeting_id: {"M1a.x.s.1": ["M1a.A.da.5", "M1a.C.da.4"]},
    )
    monkeypatch.setattr(afg_cli, "AMI_DIR", cli_env)  # exists; the lookup itself is faked
    result = _run("--decision", "M1a.d01")
    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    assert "fijar el precio en 12 euros" in out
    assert "M1a:M1a.C.da.4;M1a.A.da.5" in out  # transcript order, not file order


def test_cli_decision_not_a_decision_is_explained(
    cli_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cli_env / "M1.decisions.adjudicated.csv").write_text(
        "decision_id,meeting_id,source_sentence_id,sentence_text,evidence_text,final_status,"
        "final_object,final_content\n"
        "M1a.d02,M1a,M1a.x.s.2,Other.,,no_decision,,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "afg.annotation.goldset.summlink_dialogue_act_ids", lambda ami_root, meeting_id: {}
    )
    monkeypatch.setattr(afg_cli, "AMI_DIR", cli_env)
    result = _run("--decision", "M1a.d02")
    assert result.exit_code == 1
    assert "no_decision" in result.output


def test_cli_decision_without_adjudication_file(cli_env: Path) -> None:
    result = _run("--decision", "M1a.d01")
    assert result.exit_code == 1
    assert "adjudic" in result.output and "Traceback" not in result.output


def test_cli_decision_unknown_id_lists_available(
    cli_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (cli_env / "M1.decisions.adjudicated.csv").write_text(
        "decision_id,meeting_id,source_sentence_id,sentence_text,evidence_text,final_status,"
        "final_object,final_content\n"
        "M1a.d02,M1a,M1a.x.s.2,Other.,,no_decision,,\n",
        encoding="utf-8",
    )
    result = _run("--decision", "M1a.d99")
    assert result.exit_code == 1
    assert "M1a.d99" in result.output and "M1a.d02" in result.output
