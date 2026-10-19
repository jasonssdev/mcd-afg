"""Tests for the C2 retrieved-context analysis over Experiment B traces. No network, no files."""

from __future__ import annotations

from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.evaluation.attribution import ErrorStage
from afg.experiments.c2_context import (
    concept_kind,
    context_rows,
    correctness_by_presence,
    error_evidence,
    reference_term_coverage,
    same_retrieval,
    source_excerpts,
    stratum_composition,
)


def _question(
    qid: str,
    reference: str = "Twenty Euros.",
    meeting: str = "ES2015a",
    stratum: QuestionStratum = QuestionStratum.E1_POINT_FACT,
) -> Question:
    return Question(
        id=qid,
        series_id="ES2015",
        stratum=stratum,
        text=f"text {qid}",
        reference_answer=reference,
        reference_evidence=(EvidenceSpan(meeting_id=meeting, dialogue_act_ids=("a1",)),),
    )


def _block(concept_id: str, text: str = "body") -> dict[str, Any]:
    return {
        "index": 1,
        "concept_id": concept_id,
        "title": "T",
        "excerpted": False,
        "text": f"[concept_id: {concept_id} — T]\n# T\n\n{text}",
    }


def _c2(
    qid: str,
    blocks: list[dict[str, Any]],
    *,
    correct: bool | None,
    outcome: str = "answered",
    abstained: bool = False,
    stratum: str = "E1_point_fact",
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "condition": "C2",
        "run": 0,
        "stratum": stratum,
        "answer": {"abstained": abstained},
        "trace": {
            "outcome": outcome,
            "context_blocks": blocks,
            "retrieved": [{"concept_id": b["concept_id"]} for b in blocks],
        },
        "verdict": None if correct is None else {"correct": correct},
    }


def _c1(qid: str, correct: bool) -> dict[str, Any]:
    return {
        "question_id": qid,
        "condition": "C1",
        "run": 0,
        "stratum": "E1_point_fact",
        "answer": {"abstained": False},
        "trace": {},
        "verdict": {"correct": correct},
    }


@pytest.mark.parametrize(
    ("concept_id", "kind"),
    [
        ("sources/es2015a", "sources"),
        ("decisions/x-y", "decisions"),
        ("concepts/design", "concepts"),
        ("events/e", "other"),
        ("people/p", "other"),
        ("weird", "other"),
    ],
)
def test_concept_kind_groups_unknown_namespaces_as_other(concept_id: str, kind: str) -> None:
    assert concept_kind(concept_id) == kind


def test_context_rows_count_blocks_by_kind_and_carry_both_verdicts() -> None:
    questions = {"q1": _question("q1")}
    c2 = [
        _c2(
            "q1",
            [
                _block("sources/es2015a"),
                _block("decisions/d"),
                _block("concepts/c"),
                _block("events/e"),
            ],
            correct=False,
        )
    ]
    (row,) = context_rows(c2, [_c1("q1", True)], questions)
    assert (row.sources, row.decisions, row.concepts, row.other) == (1, 1, 1, 1)
    assert row.kinds == ("sources", "decisions", "concepts", "other")
    assert (row.correct, row.c1_correct) == (False, True)
    assert row.stratum == "E1"
    assert row.reference_source_retrieved is True


def test_reference_source_retrieved_is_false_for_another_meeting() -> None:
    questions = {"q1": _question("q1", meeting="ES2015c")}
    (row,) = context_rows([_c2("q1", [_block("sources/es2015a")], correct=True)], [], questions)
    assert row.reference_source_retrieved is False
    assert row.c1_correct is None


def test_reference_source_is_none_without_reference_evidence() -> None:
    question = Question(
        id="q9",
        series_id="ES2015",
        stratum=QuestionStratum.E4_UNANSWERABLE,
        text="t",
        reference_answer=None,
        reference_evidence=(),
    )
    (row,) = context_rows(
        [_c2("q9", [_block("sources/es2015a")], correct=True, stratum="E4_unanswerable")],
        [],
        {"q9": question},
    )
    assert row.reference_source_retrieved is None


def test_record_without_trace_blocks_gives_empty_composition() -> None:
    record = _c2("q1", [], correct=None)
    record["trace"] = {}
    (row,) = context_rows([record], [], {"q1": _question("q1")})
    assert row.kinds == ()
    assert row.correct is None


def test_reference_term_coverage_ignores_header_and_stopwords() -> None:
    blocks = [_block("decisions/d", "The price was set at twenty Euros for the remote.")]
    assert reference_term_coverage("Twenty Euros.", blocks) == 1.0
    assert reference_term_coverage("Twenty-five Euros.", blocks) == pytest.approx(2 / 3)


def test_reference_term_coverage_does_not_count_the_header_title() -> None:
    block = _block("concepts/price", "nothing relevant")
    block["text"] = "[concept_id: concepts/price — Price]\n# Price\n\nnothing relevant"
    assert reference_term_coverage("Price", [block]) == 0.0


def test_reference_term_coverage_without_content_terms_is_zero() -> None:
    assert reference_term_coverage("the of", [_block("sources/s", "the of")]) == 0.0


def test_stratum_composition_aggregates_means_and_correctness() -> None:
    questions = {"q1": _question("q1"), "q2": _question("q2")}
    c2 = [
        _c2("q1", [_block("sources/es2015a"), _block("decisions/d")], correct=False),
        _c2("q2", [_block("decisions/d"), _block("decisions/e")], correct=True),
    ]
    rows = context_rows(c2, [_c1("q1", True), _c1("q2", True)], questions)
    (summary,) = stratum_composition(rows)
    assert summary.stratum == "E1"
    assert (summary.answers, summary.correct, summary.c1_correct) == (2, 1, 2)
    assert summary.with_sources == 1
    assert summary.mean_sources == pytest.approx(0.5)
    assert summary.mean_decisions == pytest.approx(1.5)


def test_correctness_by_presence_splits_on_a_kind() -> None:
    questions = {"q1": _question("q1"), "q2": _question("q2"), "q3": _question("q3")}
    c2 = [
        _c2("q1", [_block("sources/es2015a")], correct=False),
        _c2("q2", [_block("sources/es2015a")], correct=True),
        _c2("q3", [_block("decisions/d")], correct=True),
    ]
    split = correctness_by_presence(context_rows(c2, [], questions), "sources")
    assert (split.with_kind, split.correct_with_kind) == (2, 1)
    assert (split.without_kind, split.correct_without_kind) == (1, 1)


def test_correctness_by_presence_skips_unjudged_answers() -> None:
    rows = context_rows(
        [_c2("q1", [_block("sources/s")], correct=None)], [], {"q1": _question("q1")}
    )
    split = correctness_by_presence(rows, "sources")
    assert (split.with_kind, split.without_kind) == (0, 0)


def test_error_evidence_lists_only_failed_answers_and_leaves_label_open() -> None:
    questions = {"q1": _question("q1"), "q2": _question("q2")}
    c2 = [
        _c2("q1", [_block("sources/es2015a", "nothing here")], correct=False),
        _c2("q2", [_block("sources/es2015a", "twenty euros")], correct=True),
    ]
    (evidence,) = error_evidence(context_rows(c2, [], questions), c2, questions)
    assert evidence.question == "q1"
    assert evidence.rule_stage is None
    assert evidence.reference_coverage == 0.0
    assert evidence.reference_source_retrieved is True


def test_error_evidence_attributes_synthesis_only_when_the_whole_reference_is_in_context() -> None:
    questions = {"q1": _question("q1", reference="Twenty Euros.")}
    c2 = [_c2("q1", [_block("decisions/d", "price twenty euros")], correct=False)]
    (evidence,) = error_evidence(context_rows(c2, [], questions), c2, questions)
    assert evidence.rule_stage is ErrorStage.SYNTHESIS
    assert evidence.visible_in == ("decisions",)


def test_error_evidence_records_every_kind_that_holds_the_reference() -> None:
    questions = {"q1": _question("q1", reference="Twenty Euros.")}
    blocks = [
        _block("sources/es2015a", "twenty euros"),
        _block("concepts/c", "nothing"),
        _block("decisions/d", "euros twenty"),
    ]
    c2 = [_c2("q1", blocks, correct=False)]
    (evidence,) = error_evidence(context_rows(c2, [], questions), c2, questions)
    assert evidence.visible_in == ("sources", "decisions")


def test_same_retrieval_compares_concept_ids_per_question() -> None:
    a = [_c2("q1", [_block("sources/s"), _block("decisions/d")], correct=True)]
    b = [_c2("q1", [_block("sources/s"), _block("decisions/d")], correct=False)]
    c = [_c2("q1", [_block("sources/s")], correct=True)]
    assert same_retrieval(a, b) is True
    assert same_retrieval(a, c) is False
    assert same_retrieval(a, []) is False


def test_source_excerpts_counts_raw_blocks_and_how_many_are_cut() -> None:
    cut = _block("sources/es2015a", "x" * 10)
    cut["excerpted"] = True
    whole = _block("sources/es2015b", "y" * 4)
    other = _block("decisions/d")
    stats = source_excerpts([_c2("q1", [cut, whole, other], correct=True)])
    assert (stats.blocks, stats.excerpted) == (2, 1)
    assert stats.mean_chars == pytest.approx((len(cut["text"]) + len(whole["text"])) / 2)


def test_source_excerpts_without_raw_blocks_is_empty() -> None:
    stats = source_excerpts([_c2("q1", [_block("decisions/d")], correct=True)])
    assert (stats.blocks, stats.excerpted, stats.mean_chars) == (0, 0, 0.0)
