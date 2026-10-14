"""Tests for the question-bank reference-evidence cell format."""

from __future__ import annotations

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import format_reference_evidence, parse_reference_evidence

SINGLE = "ES2015a:ES2015a.A.dialog-act.dharshi.36"
MULTI = (
    "ES2015a:ES2015a.A.dialog-act.dharshi.36|"
    "ES2015b:ES2015b.D.dialog-act.dharshi.20;ES2015b.C.dialog-act.dharshi.50"
)


def test_empty_cell_means_no_evidence() -> None:
    assert parse_reference_evidence("") == ()
    assert parse_reference_evidence("   ") == ()


def test_single_span() -> None:
    assert parse_reference_evidence(SINGLE) == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.dharshi.36",)),
    )


def test_spans_are_separated_by_pipes_and_acts_by_semicolons() -> None:
    spans = parse_reference_evidence(MULTI)
    assert [s.meeting_id for s in spans] == ["ES2015a", "ES2015b"]
    assert spans[1].dialogue_act_ids == (
        "ES2015b.D.dialog-act.dharshi.20",
        "ES2015b.C.dialog-act.dharshi.50",
    )


@pytest.mark.parametrize("cell", ["ES2015a", "ES2015a:", ":x", "ES2015a:x||ES2015b:y"])
def test_malformed_cells_raise(cell: str) -> None:
    with pytest.raises(ValueError, match="reference_evidence"):
        parse_reference_evidence(cell)


def test_format_round_trips() -> None:
    assert format_reference_evidence(parse_reference_evidence(MULTI)) == MULTI
    assert format_reference_evidence(()) == ""
