"""Tests for the citation-rule variants used to compare readings of thesis section 5.6."""

from __future__ import annotations

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation import citation_correct
from afg.evaluation.citation_variants import citation_variants


def _span(meeting: str, *ids: str) -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting, dialogue_act_ids=ids)


def _question(stratum: QuestionStratum, *reference: EvidenceSpan) -> Question:
    return Question(
        id="q1",
        series_id="ES2015",
        stratum=stratum,
        text="What price was agreed?",
        reference_answer=None if stratum is QuestionStratum.E4_UNANSWERABLE else "25 euros",
        reference_evidence=reference,
    )


def _answer(*cited: EvidenceSpan, abstained: bool = False) -> Answer:
    return Answer(
        question_id="q1", condition="C1", text="...", cited_evidence=cited, abstained=abstained
    )


REF = _span("ES2015c", "da.10", "da.11", "da.12", "da.13")
QUESTION = _question(QuestionStratum.E1_POINT_FACT, REF)


def test_sizes_count_spans_and_distinct_acts() -> None:
    answer = _answer(_span("ES2015c", "da.10", "da.40"), _span("ES2015c", "da.40", "da.41"))
    variants = citation_variants(QUESTION, answer)
    assert variants is not None
    assert variants.cited_spans == 2
    assert variants.cited_acts == 3
    assert variants.reference_acts == 4


def test_all_hit_and_any_hit_differ_when_only_some_spans_hit() -> None:
    answer = _answer(_span("ES2015c", "da.11"), _span("ES2015c", "da.99"))
    variants = citation_variants(QUESTION, answer)
    assert variants is not None
    assert variants.all_hit is False
    assert variants.any_hit is True
    assert variants.spans_hit == 1
    assert variants.precision == pytest.approx(0.5)


def test_every_span_hitting_satisfies_all_variants() -> None:
    answer = _answer(_span("ES2015c", "da.10", "da.40"), _span("ES2015c", "da.12"))
    variants = citation_variants(QUESTION, answer)
    assert variants is not None
    assert (variants.all_hit, variants.any_hit, variants.precision) == (True, True, 1.0)


def test_recall_is_the_share_of_reference_acts_covered_by_the_union_of_citations() -> None:
    answer = _answer(_span("ES2015c", "da.10", "da.40"), _span("ES2015c", "da.11"))
    variants = citation_variants(QUESTION, answer)
    assert variants is not None
    assert variants.reference_acts_covered == 2
    assert variants.recall == pytest.approx(0.5)


def test_same_act_id_in_another_meeting_is_not_a_hit() -> None:
    variants = citation_variants(QUESTION, _answer(_span("ES2015a", "da.10")))
    assert variants is not None
    assert (variants.all_hit, variants.any_hit, variants.precision, variants.recall) == (
        False,
        False,
        0.0,
        0.0,
    )


def test_an_answer_without_citation_fails_every_variant() -> None:
    variants = citation_variants(QUESTION, _answer())
    assert variants is not None
    assert (variants.all_hit, variants.any_hit, variants.precision, variants.recall) == (
        False,
        False,
        0.0,
        0.0,
    )
    assert variants.cited_spans == 0


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        (QUESTION, _answer(_span("ES2015c", "da.10"), abstained=True)),
        (_question(QuestionStratum.E4_UNANSWERABLE), _answer(_span("ES2015c", "da.10"))),
        (_question(QuestionStratum.E1_POINT_FACT), _answer(_span("ES2015c", "da.10"))),
    ],
)
def test_variants_do_not_apply_where_the_current_rule_does_not(
    question: Question, answer: Answer
) -> None:
    assert citation_variants(question, answer) is None


def test_all_hit_agrees_with_the_current_rule() -> None:
    answers = [
        _answer(),
        _answer(_span("ES2015c", "da.11")),
        _answer(_span("ES2015c", "da.11"), _span("ES2015c", "da.99")),
        _answer(_span("ES2015a", "da.11")),
    ]
    for answer in answers:
        variants = citation_variants(QUESTION, answer)
        assert variants is not None
        assert variants.all_hit is citation_correct(QUESTION, answer)
