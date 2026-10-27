"""Tests for the pure summaries over Experiment B records. No network, no files beyond tmp."""

from __future__ import annotations

from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.experiments.summary import (
    abstention_causes,
    citation_tally,
    citation_width_summary,
    failure_split,
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
    precision: float | None = None,
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
        "citation_precision": precision,
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


def test_citation_tally_reports_mean_precision_of_the_evaluated_records() -> None:
    records = [
        _record("ES2015.q001", citation=True, precision=1.0),
        _record("ES2015.q002", citation=True, precision=0.2),
        _record("ES2015.q003", citation=False, precision=0.0),
        _record("ES2015.q004", citation=True),  # an older record without the field
        _abstention("ES2015.q031"),
    ]
    assert citation_tally(records).mean_precision == pytest.approx(0.4)


def test_record_row_reads_precision_and_tolerates_its_absence() -> None:
    assert record_row(_record(precision=0.5)).citation_precision == 0.5
    assert record_row(_record()).citation_precision is None


def test_citation_tally_with_nothing_to_evaluate() -> None:
    tally = citation_tally([_abstention("ES2015.q031")])
    assert tally.evaluated == 0
    assert tally.incorrect_rate == 0.0
    assert tally.mean_precision == 0.0


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


# --- citation width, DA-level coverage and citations to full sources (ADR 0009, amendment) ------


def _span(meeting: str, *ids: str) -> dict[str, Any]:
    return {"meeting_id": meeting, "dialogue_act_ids": list(ids)}


def _question(qid: str, stratum: QuestionStratum = QuestionStratum.E1_POINT_FACT) -> Question:
    reference = (
        ()
        if stratum is QuestionStratum.E4_UNANSWERABLE
        else (EvidenceSpan(meeting_id="m1", dialogue_act_ids=("a.1", "a.2")),)
    )
    return Question(
        id=qid,
        series_id="S",
        stratum=stratum,
        text="?",
        reference_answer=None,
        reference_evidence=reference,
    )


def _cited(
    qid: str,
    *spans: dict[str, Any],
    abstained: bool = False,
    unmapped: list[Any] | None = None,
    error: str | None = None,
    condition: str = "C2",
) -> dict[str, Any]:
    trace: dict[str, Any] = {"outcome": "answered"}
    if unmapped is not None:
        trace["unmapped_cited"] = unmapped
    return {
        "question_id": qid,
        "condition": condition,
        "run": 0,
        "stratum": "E1_point_fact",
        "trace": trace,
        "answer": {
            "question_id": qid,
            "condition": condition,
            "text": "t",
            "cited_evidence": list(spans),
            "abstained": abstained,
        },
        "error": error,
    }


BANK = {f"q{i}": _question(f"q{i}") for i in range(1, 5)}


def test_citation_width_summary_reports_width_and_coverage() -> None:
    records = [
        _cited("q1", _span("m1", "a.1", "a.5", "a.6")),  # 3 acts, covers 1 of 2 reference acts
        _cited("q2", _span("m1", "a.1", "a.2"), _span("m1", "a.2", "a.9")),  # 3 acts, covers 2 of 2
        _cited("q3", _span("m1", *[f"b.{i}" for i in range(11)])),  # 11 acts, covers 0
    ]
    summary = citation_width_summary(records, BANK)
    assert summary.answered == 3
    assert (summary.cited_acts_min, summary.cited_acts_median, summary.cited_acts_max) == (3, 3, 11)
    assert summary.mean_act_coverage == pytest.approx((0.5 + 1.0 + 0.0) / 3)


def test_citation_width_summary_leaves_out_what_the_rule_does_not_apply_to() -> None:
    bank = {**BANK, "q4": _question("q4", QuestionStratum.E4_UNANSWERABLE)}
    records = [
        _cited("q1", _span("m1", "a.1")),
        _cited("q2", _span("m1", "a.1"), abstained=True),
        _cited("q4", _span("m1", "a.1")),
    ]
    assert citation_width_summary(records, bank).answered == 1


def test_citation_width_summary_without_answers_reads_as_unknown_not_zero() -> None:
    summary = citation_width_summary([_cited("q1", abstained=True)], BANK)
    assert summary.answered == 0
    assert summary.cited_acts_min is None
    assert summary.cited_acts_median is None
    assert summary.cited_acts_max is None
    assert summary.mean_act_coverage is None


def test_citation_width_summary_counts_citations_to_full_sources_only() -> None:
    sources = [
        {"concept_id": "sources/ES2015a", "reason": "source_full_transcript"},
        {"concept_id": "sources/ES2015b", "reason": "source_full_transcript"},
        {"concept_id": "concepts/x", "reason": "no_located_excerpt"},
    ]
    records = [
        _cited("q1", _span("m1", "a.1"), unmapped=sources),
        _cited("q2", _span("m1", "a.1"), unmapped=[]),
    ]
    assert citation_width_summary(records, BANK).source_citations == 2


def test_source_citations_of_c1_records_are_zero_without_a_list() -> None:
    records = [_cited("q1", _span("m1", "a.1"), condition="C1")]  # C1 has no OpenKOS concepts
    assert citation_width_summary(records, BANK).source_citations == 0


def test_source_citations_are_unknown_when_a_c2_trace_lacks_the_list() -> None:
    records = [
        _cited("q1", _span("m1", "a.1"), unmapped=[]),
        _cited("q2", _span("m1", "a.1")),  # no `unmapped_cited` key
    ]
    assert citation_width_summary(records, BANK).source_citations is None


def test_source_citations_are_unknown_for_legacy_string_entries() -> None:
    # Pre-fix runs (humo-c2-es2015) list the unmapped concepts as bare ids, with no reason.
    records = [_cited("q1", _span("m1", "a.1"), unmapped=["concepts/design-of-a-remote-control"])]
    assert citation_width_summary(records, BANK).source_citations is None


def test_source_citations_ignore_abstentions_without_the_list() -> None:
    records = [
        _cited("q1", _span("m1", "a.1"), unmapped=[]),
        _cited("q2", abstained=True),
    ]
    assert citation_width_summary(records, BANK).source_citations == 0


def test_citation_width_summary_skips_records_with_errors() -> None:
    records = [_cited("q1", _span("m1", "a.1")), {**_cited("q2"), "answer": None, "error": "boom"}]
    assert citation_width_summary(records, BANK).answered == 1


def test_citation_width_summary_reads_old_schema_records_from_the_answer() -> None:
    record = {**_cited("q1", _span("m1", "a.1", "a.2")), "schema_version": 1}
    assert citation_width_summary([record], BANK).mean_act_coverage == 1.0


def test_failure_split_separates_wrong_answers_from_abstentions() -> None:
    records = [
        _record("ES2015.q001", correct=True),
        _record("ES2015.q002", correct=False),
        _record("ES2015.q003", correct=False),
        _abstention("ES2015.q004", "E1_point_fact", correct=False),
        _abstention("ES2015.q031", "E4_unanswerable", correct=True),
        _record("ES2015.q032", stratum="E4_unanswerable", correct=False),
    ]
    split = {s.stratum: s for s in failure_split(records)}
    e1 = split["E1"]
    assert (e1.n, e1.correct, e1.wrong_answer, e1.abstained_wrong) == (4, 1, 2, 1)
    e4 = split["E4"]
    assert (e4.n, e4.correct, e4.wrong_answer, e4.abstained_wrong) == (2, 1, 1, 0)
    assert e4.abstained_right == 1
    assert e1.abstained_right == 0


def test_failure_split_counts_a_record_without_verdict_as_unjudged() -> None:
    split = {s.stratum: s for s in failure_split([_record(correct=None)])}
    e1 = split["E1"]
    assert (e1.correct, e1.wrong_answer, e1.abstained_wrong, e1.unjudged) == (0, 0, 0, 1)


def test_abstention_causes_reads_both_trace_shapes() -> None:
    c2_refused = _abstention("ES2015.q001", "E1_point_fact", correct=False)
    c2_refused["trace"]["sufficiency"] = {"invoked": True, "refused": True}
    c1_refused = _abstention("ES2015.q002", "E1_point_fact", correct=False)
    c1_refused["trace"].update(sufficiency_invoked=True, sufficiency_raw_reply=' "none". ')
    other = _abstention("ES2015.q003", "E1_point_fact", correct=False)
    other["trace"]["sufficiency"] = {"invoked": True, "refused": False}
    answered = _record("ES2015.q004")
    causes = abstention_causes([c2_refused, c1_refused, other, answered])
    assert causes.n_abstained == 3
    assert causes.refused_by_sufficiency == 2
    assert causes.other == 1


def test_abstention_causes_of_no_abstentions() -> None:
    causes = abstention_causes([_record("ES2015.q001")])
    assert (causes.n_abstained, causes.refused_by_sufficiency, causes.other) == (0, 0, 0)
