"""Tests for the deterministic citation-correctness rule (thesis sections 5.6 and 6.2)."""

from __future__ import annotations

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation import citation_correct


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


def test_every_cited_span_must_be_supported() -> None:
    supported = _span("ES2015c", "da.10")
    unsupported = _span("ES2015a", "da.3")
    assert citation_correct(ANSWERABLE, _answer(supported, unsupported)) is False


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
