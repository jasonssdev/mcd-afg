"""Tests for the deterministic citation-correctness rule (thesis sections 5.6 and 6.2)."""

from __future__ import annotations

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation import citation_correct, citation_precision


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


REF = _span("ES2015c", "da.10", "da.11", "da.12")
ANSWERABLE = _question(QuestionStratum.E1_POINT_FACT, REF)


def test_citation_sharing_a_dialogue_act_with_the_reference_is_correct() -> None:
    assert citation_correct(ANSWERABLE, _answer(_span("ES2015c", "da.11", "da.40"))) is True


def test_citation_in_the_right_meeting_but_other_acts_is_incorrect() -> None:
    assert citation_correct(ANSWERABLE, _answer(_span("ES2015c", "da.40"))) is False


def test_same_act_id_in_another_meeting_does_not_count() -> None:
    assert citation_correct(ANSWERABLE, _answer(_span("ES2015d", "da.11"))) is False


def test_one_supported_span_is_enough_even_if_others_are_not() -> None:
    # ADR 0009: the failure to detect is "no cited source supports the answer", so a valid
    # citation next to an unrelated one is still correct.
    supported = _span("ES2015c", "da.10")
    unsupported = _span("ES2015a", "da.3")
    assert citation_correct(ANSWERABLE, _answer(supported, unsupported)) is True
    assert citation_correct(ANSWERABLE, _answer(unsupported, supported)) is True


def test_no_supported_span_among_several_is_incorrect() -> None:
    cited = (_span("ES2015a", "da.3"), _span("ES2015c", "da.40"), _span("ES2015d", "da.11"))
    assert citation_correct(ANSWERABLE, _answer(*cited)) is False


def test_any_reference_span_can_support_a_citation() -> None:
    question = _question(QuestionStratum.E3_EVOLUTION, REF, _span("ES2015d", "da.7"))
    cited = (_span("ES2015c", "da.12"), _span("ES2015d", "da.7"))
    assert citation_correct(question, _answer(*cited)) is True


def test_unsourced_claim_on_an_answerable_question_is_incorrect() -> None:
    # Section 6.2: an unsourced claim counts as a failure even if it is correct.
    assert citation_correct(ANSWERABLE, _answer()) is False


def test_abstention_is_not_applicable() -> None:
    assert citation_correct(ANSWERABLE, _answer(abstained=True)) is None


def test_unanswerable_question_is_not_applicable() -> None:
    question = _question(QuestionStratum.E4_UNANSWERABLE)
    assert citation_correct(question, _answer(_span("ES2015c", "da.11"))) is None
    assert citation_correct(question, _answer()) is None


def test_answerable_question_without_reference_evidence_is_not_applicable() -> None:
    question = _question(QuestionStratum.E1_POINT_FACT)
    assert citation_correct(question, _answer(_span("ES2015c", "da.11"))) is None


def test_precision_is_the_fraction_of_cited_spans_that_hit() -> None:
    cited = (_span("ES2015c", "da.10"), _span("ES2015a", "da.3"), _span("ES2015c", "da.40"))
    assert citation_precision(ANSWERABLE, _answer(*cited)) == pytest.approx(1 / 3)
    assert citation_precision(ANSWERABLE, _answer(_span("ES2015c", "da.11"))) == 1.0
    assert citation_precision(ANSWERABLE, _answer(_span("ES2015d", "da.11"))) == 0.0


def test_precision_of_an_unsourced_answer_is_zero() -> None:
    # Consistent with section 6.2 and with citation_correct being False: the answer is
    # scored, and it has nothing supported.
    assert citation_precision(ANSWERABLE, _answer()) == 0.0


def test_precision_is_not_applicable_where_the_rate_is_not() -> None:
    cited = _span("ES2015c", "da.11")
    assert citation_precision(ANSWERABLE, _answer(cited, abstained=True)) is None
    unanswerable = _question(QuestionStratum.E4_UNANSWERABLE)
    assert citation_precision(unanswerable, _answer(cited)) is None
    no_reference = _question(QuestionStratum.E1_POINT_FACT)
    assert citation_precision(no_reference, _answer(cited)) is None


def test_correct_citation_iff_precision_is_positive() -> None:
    answers = [
        _answer(),
        _answer(_span("ES2015c", "da.11")),
        _answer(_span("ES2015c", "da.11"), _span("ES2015a", "da.3")),
        _answer(_span("ES2015a", "da.3")),
    ]
    for answer in answers:
        precision = citation_precision(ANSWERABLE, answer)
        assert precision is not None
        assert citation_correct(ANSWERABLE, answer) is (precision > 0)
