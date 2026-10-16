"""Tests for the width of citations and its act-level precision and coverage (issue #97)."""

from __future__ import annotations

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation_width import (
    citation_width,
    low_precision_hits,
    summarize_widths,
    trace_unit_widths,
    width_rows,
)


def _span(meeting: str, *ids: str) -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting, dialogue_act_ids=ids)


def _question(
    qid: str = "q1", stratum: QuestionStratum = QuestionStratum.E1_POINT_FACT
) -> Question:
    reference = () if stratum is QuestionStratum.E4_UNANSWERABLE else (_span("m1", "a.1", "a.2"),)
    return Question(
        id=qid,
        series_id="S",
        stratum=stratum,
        text="?",
        reference_answer=None,
        reference_evidence=reference,
    )


def _answer(*cited: EvidenceSpan, abstained: bool = False, qid: str = "q1") -> Answer:
    return Answer(
        question_id=qid, condition="C1", text="...", cited_evidence=cited, abstained=abstained
    )


def test_width_counts_distinct_acts_and_unit_widths() -> None:
    answer = _answer(_span("m1", "a.1", "a.5", "a.6"), _span("m1", "a.6", "a.7"))
    row = citation_width(_question(), answer)
    assert row is not None
    assert row.cited_acts == 4  # a.1, a.5, a.6, a.7
    assert row.unit_widths == (3, 2)
    assert row.cited_spans == 2


def test_act_precision_and_recall_match_on_meeting_and_act() -> None:
    # a.1 is in the reference of m1; the same id in another meeting must not count.
    answer = _answer(_span("m1", "a.1", "a.5", "a.6"), _span("m2", "a.2"))
    row = citation_width(_question(), answer)
    assert row is not None
    assert row.acts_in_reference == 1
    assert row.act_precision == pytest.approx(1 / 4)
    assert row.act_recall == pytest.approx(1 / 2)
    assert row.citation_correct is True
    assert row.unit_precision == pytest.approx(1 / 2)


def test_answer_without_citations_scores_zero() -> None:
    row = citation_width(_question(), _answer())
    assert row is not None
    assert (row.cited_acts, row.act_precision, row.act_recall) == (0, 0.0, 0.0)
    assert row.citation_correct is False
    assert row.unit_widths == ()


def test_not_applicable_cases_return_none() -> None:
    assert citation_width(_question(), _answer(abstained=True)) is None
    e4 = _question(stratum=QuestionStratum.E4_UNANSWERABLE)
    assert citation_width(e4, _answer(_span("m1", "a.1"))) is None


def _record(qid: str, answer: Answer | None) -> dict[str, object]:
    return {"question_id": qid, "answer": None if answer is None else answer.model_dump()}


def test_width_rows_skip_records_without_answer_or_rule() -> None:
    questions = {"q1": _question("q1"), "q2": _question("q2")}
    records = [
        _record("q1", _answer(_span("m1", "a.1"), qid="q1")),
        _record("q2", None),
        _record("q2", _answer(abstained=True, qid="q2")),
    ]
    rows = width_rows(records, questions)
    assert [r.question for r in rows] == ["q1"]


def test_summary_aggregates_widths_and_means() -> None:
    questions = {"q1": _question("q1")}
    narrow = citation_width(questions["q1"], _answer(_span("m1", "a.1", "a.2")))
    wide = citation_width(
        questions["q1"],
        _answer(_span("m1", "a.1", *[f"b.{i}" for i in range(8)])),
    )
    assert narrow is not None and wide is not None
    summary = summarize_widths([narrow, wide])
    assert summary.answered == 2
    assert summary.citation_correct == 2
    assert summary.cited_acts_min == 2
    assert summary.cited_acts_max == 9
    assert summary.cited_acts_median == pytest.approx(5.5)
    assert summary.mean_act_precision == pytest.approx((1.0 + 1 / 9) / 2)
    assert summary.mean_act_recall == pytest.approx((1.0 + 0.5) / 2)
    assert summary.unit_width_median == pytest.approx(5.5)
    assert (summary.unit_width_min, summary.unit_width_max) == (2, 9)


def test_summary_of_nothing_is_zeroed() -> None:
    summary = summarize_widths([])
    assert summary.answered == 0
    assert summary.mean_act_precision == 0.0
    assert summary.cited_acts_median == 0.0


def test_low_precision_hits_counts_correct_citations_below_threshold() -> None:
    q = _question()
    narrow = citation_width(q, _answer(_span("m1", "a.1", "a.2")))
    wide = citation_width(q, _answer(_span("m1", "a.1", *[f"b.{i}" for i in range(30)])))
    miss = citation_width(q, _answer(_span("m1", "z.1")))
    assert narrow is not None and wide is not None and miss is not None
    assert low_precision_hits([narrow, wide, miss], threshold=0.1) == 1


def test_trace_unit_widths_read_chunks_and_concepts() -> None:
    chunk_record = {"trace": {"cited_acts": {"m1.c1": ["a.1", "a.2"], "m1.c2": ["a.3"]}}}
    concept_record = {
        "trace": {"cited_acts": {"concepts/x": {"m1": ["a.1", "a.2"], "m2": ["a.1"]}}}
    }
    assert trace_unit_widths(chunk_record) == {"m1.c1": 2, "m1.c2": 1}
    # Acts are distinct per (meeting, id): the same id in two meetings counts twice.
    assert trace_unit_widths(concept_record) == {"concepts/x": 3}
    assert trace_unit_widths({"trace": None}) == {}
    assert trace_unit_widths({}) == {}
