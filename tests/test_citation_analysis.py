"""Tests for the citation-rule analysis over Experiment B records. No network, no files."""

from __future__ import annotations

from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.experiments.citation_analysis import (
    cited_chunk_summaries,
    compare_records,
    reference_sizes,
    rescore_citation,
    tally_by_verdict,
    tally_variants,
)


def _span(meeting: str, *ids: str) -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting, dialogue_act_ids=ids)


def _question(qid: str, stratum: QuestionStratum, *reference: EvidenceSpan) -> Question:
    return Question(
        id=qid,
        series_id="ES2015",
        stratum=stratum,
        text=f"text {qid}",
        reference_answer=None if stratum is QuestionStratum.E4_UNANSWERABLE else "ref",
        reference_evidence=reference,
    )


def _record(
    qid: str,
    cited: list[EvidenceSpan],
    *,
    outcome: str = "answered",
    correct: bool | None = True,
    supported: bool | None = True,
    attribution: str = "reported",
    raw_reply: str = "Answer.\nUSED: 1",
    abstained: bool = False,
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "condition": "C1",
        "run": 0,
        "stratum": "E1_point_fact",
        "answer": {
            "question_id": qid,
            "condition": "C1",
            "text": "Answer",
            "cited_evidence": [s.model_dump(mode="json") for s in cited],
            "abstained": abstained,
        },
        "trace": {
            "outcome": outcome,
            "attribution": attribution,
            "raw_reply": raw_reply,
            "cited_chunk_ids": [f"c{i}" for i, _ in enumerate(cited)],
        },
        "verdict": {"correct": correct, "evidence_supported": supported},
    }


REF = _span("ES2015a", "a.1", "a.2")
QUESTIONS = {
    "q1": _question("q1", QuestionStratum.E1_POINT_FACT, REF),
    "q2": _question("q2", QuestionStratum.E1_POINT_FACT, _span("ES2015a", "a.5")),
    "q3": _question("q3", QuestionStratum.E4_UNANSWERABLE),
}


def test_reference_sizes_cover_answerable_questions_only() -> None:
    questions = [
        *QUESTIONS.values(),
        _question("q4", QuestionStratum.E2_CURRENT_STATE, _span("ES2015a", "a.1", "a.2", "a.3")),
    ]
    sizes = reference_sizes(questions)
    assert [(s.question, s.acts, s.meetings) for s in sizes] == [
        ("q1", 2, 1),
        ("q2", 1, 1),
        ("q4", 3, 1),
    ]


def test_reference_sizes_count_meetings_and_acts_across_spans() -> None:
    q = _question(
        "q9",
        QuestionStratum.E3_EVOLUTION,
        _span("ES2015a", "a.1"),
        _span("ES2015c", "c.1", "c.2"),
    )
    (size,) = reference_sizes([q])
    assert (size.acts, size.meetings) == (3, 2)


def test_compare_records_keeps_answered_applicable_records() -> None:
    records = [
        _record("q1", [_span("ES2015a", "a.1"), _span("ES2015a", "a.9")]),
        _record("q3", [], outcome="no_answer_in_context", abstained=True),
        _record("q2", [], outcome="no_answer_in_context", abstained=True),
    ]
    rows = compare_records(records, QUESTIONS)
    assert [r.question for r in rows] == ["q1"]
    row = rows[0]
    assert (row.all_hit, row.any_hit, row.precision) == (False, True, 0.5)
    assert (row.cited_spans, row.cited_acts, row.reference_acts) == (2, 2, 2)
    assert row.correct is True
    assert row.inline_used_marker is False


def test_compare_records_flags_the_inline_used_marker() -> None:
    record = _record(
        "q1",
        [_span("ES2015a", "a.9")],
        attribution="absent",
        raw_reply="The answer is X. USED: 2",
    )
    (row,) = compare_records([record], QUESTIONS)
    assert row.inline_used_marker is True


def test_compare_records_rejects_an_unknown_question() -> None:
    with pytest.raises(KeyError):
        compare_records([_record("q99", [REF])], QUESTIONS)


def test_tally_counts_correct_answers_marked_incorrect_per_variant() -> None:
    records = [
        _record("q1", [_span("ES2015a", "a.1")]),
        _record("q1", [_span("ES2015a", "a.1"), _span("ES2015a", "a.9")]),
        _record("q1", [_span("ES2015a", "a.9")]),
        _record("q2", [_span("ES2015a", "a.9")], correct=False),
    ]
    rows = compare_records(records, QUESTIONS)
    tally = tally_variants(rows)
    assert tally.records == 4
    assert tally.correct_answers == 3
    assert tally.all_hit == 1
    assert tally.any_hit == 2
    assert tally.correct_but_all_miss == 2
    assert tally.correct_but_any_miss == 1
    assert tally.mean_precision == pytest.approx((1 + 0.5 + 0 + 0) / 4)
    assert tally.mean_recall == pytest.approx((0.5 + 0.5 + 0 + 0) / 4)


def test_tally_of_no_rows_is_zero() -> None:
    tally = tally_variants([])
    assert (tally.records, tally.mean_precision, tally.mean_recall) == (0, 0.0, 0.0)


def test_cited_chunk_summaries_report_hits_per_chunk() -> None:
    record = _record("q1", [_span("ES2015a", "a.1")])
    record["trace"]["cited_chunk_ids"] = ["c0", "c1"]
    record["trace"]["cited_acts"] = {"c0": ["a.1", "a.7"], "c1": ["a.8"]}
    record["trace"]["context_blocks"] = [
        {
            "index": 1,
            "chunk_id": "c0",
            "meeting_id": "ES2015a",
            "text": "[concept_id: c0 — ES2015a]\nPM: hello there",
        },
        {
            "index": 2,
            "chunk_id": "c1",
            "meeting_id": "ES2015a",
            "text": "[concept_id: c1 — ES2015a]\nPM: other",
        },
    ]
    summaries = cited_chunk_summaries(record, (REF,))
    assert [(s.chunk_id, s.acts, s.acts_in_reference, s.hit) for s in summaries] == [
        ("c0", 2, 1, True),
        ("c1", 1, 0, False),
    ]
    assert summaries[0].snippet == "PM: hello there"


def test_tally_by_verdict_groups_by_correct_and_evidence_supported() -> None:
    records = [
        _record("q1", [_span("ES2015a", "a.1")], correct=True, supported=True),
        _record("q1", [_span("ES2015a", "a.9")], correct=True, supported=False),
        _record("q2", [_span("ES2015a", "a.9")], correct=True, supported=True),
    ]
    groups = tally_by_verdict(compare_records(records, QUESTIONS))
    assert list(groups) == [(True, True), (True, False)]
    assert (groups[(True, True)].records, groups[(True, True)].all_hit) == (2, 1)
    assert groups[(True, False)].any_hit == 0


def test_rescore_citation_applies_the_current_rule_to_stored_answers() -> None:
    stale = _record("q1", [_span("ES2015a", "a.1"), _span("ES2015a", "a.9")])
    stale["citation_correct"] = False  # written under the retired all-cited-must-hit rule
    abstention = _record("q2", [], outcome="no_answer_in_context", abstained=True)
    (rescored, kept) = rescore_citation([stale, abstention], QUESTIONS)
    assert rescored["citation_correct"] is True
    assert rescored["citation_precision"] == 0.5
    assert kept["citation_correct"] is None
    assert kept["citation_precision"] is None
    assert stale["citation_correct"] is False  # the input is not mutated
    assert "citation_precision" not in stale


def test_rescore_citation_leaves_records_without_an_answer_untouched() -> None:
    failed = {"question_id": "q1", "answer": None, "error": "boom", "citation_correct": None}
    assert rescore_citation([failed], QUESTIONS) == [failed]


def test_rescore_citation_rejects_an_unknown_question() -> None:
    with pytest.raises(KeyError):
        rescore_citation([_record("q99", [REF])], QUESTIONS)
