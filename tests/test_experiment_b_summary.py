"""Tests for the pure summaries over Experiment B records. No network, no files beyond tmp."""

from __future__ import annotations

from typing import Any

import pytest

from afg.experiments.summary import (
    citation_tally,
    has_inline_used_marker,
    inline_marker_rows,
    record_row,
    resume_status,
    stratum_summary,
    wiring_summary,
)


def _record(
    qid: str = "ES2015.q001",
    *,
    stratum: str = "E1_point_fact",
    outcome: str = "answered",
    attribution: str = "reported",
    correct: bool | None = True,
    supported: bool | None = True,
    citation: bool | None = True,
    cited: tuple[str, ...] = ("c1",),
    raw_reply: str | None = "Answer.\nUSED: 1",
    answer_seconds: float = 10.0,
    judge_seconds: float | None = 4.0,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "condition": "C1",
        "run": 0,
        "stratum": stratum,
        "trace": {
            "outcome": outcome,
            "question": "What was decided?",
            "attribution": attribution,
            "cited_chunk_ids": list(cited),
            "raw_reply": raw_reply,
        },
        "verdict": (
            None if correct is None else {"correct": correct, "evidence_supported": supported}
        ),
        "citation_correct": citation,
        "answer_seconds": answer_seconds,
        "judge_seconds": judge_seconds,
        "error": error,
    }


def _abstention(qid: str, stratum: str = "E4_unanswerable", *, correct: bool = True) -> dict:
    return _record(
        qid,
        stratum=stratum,
        outcome="no_answer_in_context",
        attribution="absent",
        correct=correct,
        citation=None,
        cited=(),
        raw_reply=None,
        answer_seconds=3.0,
        judge_seconds=2.0,
    )


def test_record_row_flattens_the_fields_a_reader_needs() -> None:
    row = record_row(_record("ES2015.q004", supported=False))
    assert row.question == "q004"
    assert row.question_text == "What was decided?"
    assert row.stratum == "E1"
    assert row.outcome == "answered"
    assert row.attribution == "reported"
    assert row.correct is True
    assert row.evidence_supported is False
    assert row.citation_correct is True
    assert row.cited_chunks == 1
    assert row.answer_seconds == 10.0
    assert row.judge_seconds == 4.0


def test_record_row_tolerates_a_missing_verdict_and_missing_trace_lists() -> None:
    record = _record(correct=None, judge_seconds=None)
    record["trace"]["cited_chunk_ids"] = None
    row = record_row(record)
    assert row.correct is None
    assert row.evidence_supported is None
    assert row.cited_chunks == 0
    assert row.judge_seconds == 0.0


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("The price is twenty five Euros. USED: 2, 3", True),
        ("The price is 25.\nUSED: 2", False),
        ("  USED: 2", False),
        ("price. used : 2", True),
        ("no marker here", False),
        (None, False),
    ],
)
def test_inline_marker_is_a_used_marker_that_is_not_on_its_own_line(
    reply: str | None, expected: bool
) -> None:
    record = _record(attribution="absent", raw_reply=reply)
    assert has_inline_used_marker(record) is expected


def test_inline_marker_needs_attribution_absent() -> None:
    assert not has_inline_used_marker(_record(attribution="reported", raw_reply="x. USED: 1"))


def test_inline_marker_rows_lists_only_the_affected_questions() -> None:
    records = [
        _record("ES2015.q002", attribution="absent", raw_reply="Euros. USED: 2, 3", citation=False),
        _record("ES2015.q003"),
        _abstention("ES2015.q031"),
    ]
    assert [r.question for r in inline_marker_rows(records)] == ["q002"]


def test_stratum_summary_counts_rates_and_timings() -> None:
    records = [
        _record("ES2015.q001"),
        _record("ES2015.q002", correct=False, answer_seconds=20.0, judge_seconds=6.0),
        _abstention("ES2015.q003", "E1_point_fact", correct=False),
        _abstention("ES2015.q031"),
    ]
    summary = {s.stratum: s for s in stratum_summary(records)}
    e1, e4 = summary["E1"], summary["E4"]
    assert (e1.n, e1.answered, e1.abstained, e1.correct) == (3, 2, 1, 1)
    assert e1.correct_rate == pytest.approx(1 / 3)
    assert e1.abstention_rate == pytest.approx(1 / 3)
    assert e1.mean_answer_seconds == pytest.approx((10 + 20 + 3) / 3)
    assert e1.mean_judge_seconds == pytest.approx((4 + 6 + 2) / 3)
    assert e1.total_seconds == pytest.approx(10 + 4 + 20 + 6 + 3 + 2)
    assert (e4.n, e4.abstained, e4.correct_rate, e4.abstention_rate) == (1, 1, 1.0, 1.0)


def test_stratum_summary_is_ordered_by_stratum() -> None:
    records = [_record("a", stratum="E3_cross"), _record("b", stratum="E1_point_fact")]
    assert [s.stratum for s in stratum_summary(records)] == ["E1", "E3"]


def test_citation_tally_counts_answered_records_with_citations() -> None:
    records = [
        _record("ES2015.q001", citation=True),
        _record("ES2015.q002", citation=False, attribution="absent", raw_reply="x. USED: 1"),
        _record("ES2015.q003", citation=False, correct=False),
        _record("ES2015.q004", citation=False, attribution="reported", cited=("c1", "c2")),
        _abstention("ES2015.q031"),
    ]
    tally = citation_tally(records)
    assert tally.evaluated == 4
    assert tally.correct == 1
    assert tally.incorrect == 3
    assert tally.incorrect_with_inline_marker == 1
    assert tally.incorrect_with_correct_answer == 2
    assert tally.incorrect_rate == pytest.approx(0.75)


def test_citation_tally_with_nothing_to_evaluate() -> None:
    tally = citation_tally([_abstention("ES2015.q031")])
    assert tally.evaluated == 0
    assert tally.incorrect_rate == 0.0


def test_resume_status_counts_complete_and_pending_keys() -> None:
    records = [_record("ES2015.q001"), _record("ES2015.q002", error="boom")]
    status = resume_status(records, expected=3)
    assert (status.expected, status.complete, status.errors, status.pending) == (3, 1, 1, 2)


def test_wiring_summary_lists_the_distinct_settings_seen_in_the_records() -> None:
    first = _record("ES2015.q001")
    second = _record("ES2015.q002")
    for index, record in enumerate((first, second)):
        record.update(
            seed=42,
            seed_applied=True,
            generative_model="gen",
            temperature=0.1,
            partition="development",
            judge={"model": "jdg", "order": "reference_first", "seed": 42, "temperature": 0.0},
        )
        record["run"] = index
    wiring = wiring_summary([first, second])
    assert wiring == {
        "seeds": [42],
        "seed_applied": [True],
        "generative_models": ["gen"],
        "temperatures": [0.1],
        "partitions": ["development"],
        "judge_models": ["jdg"],
        "judge_orders": ["reference_first"],
        "judge_seeds": [42],
        "judge_temperatures": [0.0],
        "conditions": ["C1"],
        "runs": [0, 1],
    }
