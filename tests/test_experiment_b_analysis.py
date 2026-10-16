"""Tests for the Experiment B analysis (T1): aggregation, intervals and D16 comparisons."""

from __future__ import annotations

from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.evaluation.scoring import DevelopmentResultError, IntervalSettings
from afg.experiments.analysis import (
    ALL_STRATA,
    AnalysisReport,
    analyze_runs,
    report_to_dict,
)

SETTINGS = IntervalSettings(n_resamples=400, confidence_level=0.95, seed=7)


def _record(
    question: str,
    condition: str,
    run: int,
    *,
    stratum: str = "E3_evolution",
    partition: str = "evaluation",
    correct: bool | None = True,
    supported: bool = True,
    citation: bool | None = True,
    precision: float | None = 1.0,
    abstained: bool = False,
    judge_failure: str | None = None,
    error: str | None = None,
    schema: int = 2,
) -> dict[str, Any]:
    judged = error is None and judge_failure is None
    return {
        "schema_version": schema,
        "question_id": f"ES2015.{question}",
        "condition": condition,
        "run": run,
        "stratum": stratum,
        "partition": partition,
        "answer": {"text": "x", "abstained": abstained},
        "verdict": {"correct": correct, "evidence_supported": supported} if judged else None,
        "judge_failure": judge_failure,
        "citation_correct": citation,
        "citation_precision": precision,
        "error": error,
    }


def _bank(
    condition: str, outcomes: list[list[bool]], *, stratum: str = "E3_evolution", **kw: Any
) -> list[dict[str, Any]]:
    """One question per outer element, one run per inner element."""
    return [
        _record(f"{stratum[:2]}q{q:02d}", condition, r, stratum=stratum, correct=ok, **kw)
        for q, runs in enumerate(outcomes)
        for r, ok in enumerate(runs)
    ]


def _cell(report: AnalysisReport, condition: str, stratum: str):
    return next(c for c in report.cells if c.condition == condition and c.stratum == stratum)


def test_runs_are_averaged_per_question_before_the_rate() -> None:
    # q0: 3/3 correct, q1: 0/3. Per-question mean -> (1 + 0) / 2 = 0.5 (answer pooling: 0.5 too),
    # q2 has 1 run only 1/1: question mean = (1 + 0 + 1) / 3, pooled answers would be 4/7.
    records = _bank("C1", [[True, True, True], [False, False, False], [True]])
    report = analyze_runs(records, settings=SETTINGS, min_questions=1)
    est = _cell(report, "C1", "E3").metrics["correct"]
    assert est is not None
    assert est.point == pytest.approx(2 / 3)
    assert est.n_questions == 3
    assert est.n_records == 7
    assert est.lower <= est.point <= est.upper


def test_bootstrap_resamples_questions_not_answers() -> None:
    # Perfectly consistent questions: with 2 questions (one always right, one always wrong) the
    # interval must span the whole [0, 1] range, which only question-level resampling gives.
    records = _bank("C1", [[True] * 5, [False] * 5])
    est = _cell(analyze_runs(records, settings=SETTINGS, min_questions=1), "C1", "E3").metrics[
        "correct"
    ]
    assert est is not None
    assert (est.lower, est.upper) == (0.0, 1.0)


def test_judge_failures_and_errors_are_excluded_but_counted() -> None:
    records = _bank("C1", [[True, True]])
    records.append(_record("E3q00", "C1", 2, judge_failure="unparseable"))
    records.append(_record("E3q00", "C1", 3, error="boom"))
    cell = _cell(analyze_runs(records, settings=SETTINGS, min_questions=1), "C1", "E3")
    est = cell.metrics["correct"]
    assert est is not None and est.n_records == 2
    assert cell.judge_failures == 1
    assert cell.errors == 1
    assert cell.records == 4


def test_latest_record_of_a_key_wins() -> None:
    records = [
        _record("E3q00", "C1", 0, correct=False),
        _record("E3q00", "C1", 0, correct=True),
    ]
    est = _cell(analyze_runs(records, settings=SETTINGS, min_questions=1), "C1", "E3").metrics[
        "correct"
    ]
    assert est is not None and est.point == 1.0 and est.n_records == 1


def test_cells_by_stratum_and_overall() -> None:
    records = _bank("C1", [[True]], stratum="E1_point_fact") + _bank(
        "C1", [[False]], stratum="E3_evolution"
    )
    report = analyze_runs(records, settings=SETTINGS, min_questions=1)
    assert _cell(report, "C1", "E1").metrics["correct"].point == 1.0  # type: ignore[union-attr]
    assert _cell(report, "C1", "E3").metrics["correct"].point == 0.0  # type: ignore[union-attr]
    assert _cell(report, "C1", ALL_STRATA).metrics["correct"].point == 0.5  # type: ignore[union-attr]


def test_citation_metrics_skip_abstentions_and_v1_records() -> None:
    records = [
        _record("E3q00", "C1", 0, citation=True, precision=0.5),
        _record("E3q01", "C1", 0, citation=False, precision=0.0),
        _record("E3q02", "C1", 0, citation=False, precision=None, abstained=True),
        _record("E3q03", "C1", 0, citation=True, precision=1.0, schema=1),
    ]
    report = analyze_runs(records, settings=SETTINGS, min_questions=1)
    cell = _cell(report, "C1", "E3")
    assert cell.metrics["citation_correct"].point == 0.5  # type: ignore[union-attr]
    assert cell.metrics["citation_precision"].point == 0.25  # type: ignore[union-attr]
    assert cell.citation_records_v1_excluded == 1
    assert any("v1" in w for w in report.warnings)


def test_e4_abstention_correctness() -> None:
    records = [
        _record("E4q00", "C1", 0, stratum="E4_unanswerable", abstained=True),
        _record("E4q00", "C1", 1, stratum="E4_unanswerable", abstained=True),
        _record("E4q01", "C1", 0, stratum="E4_unanswerable", abstained=False),
        _record("E3q00", "C1", 0, abstained=True),
    ]
    report = analyze_runs(records, settings=SETTINGS, min_questions=1)
    assert _cell(report, "C1", "E4").metrics["abstention_correct"].point == 0.5  # type: ignore[union-attr]
    assert "abstention_correct" not in _cell(report, "C1", "E3").metrics


def test_development_records_are_refused() -> None:
    records = _bank("C1", [[True]], partition="development")
    with pytest.raises(DevelopmentResultError):
        analyze_runs(records, settings=SETTINGS, min_questions=1)
    report = analyze_runs(records, settings=SETTINGS, min_questions=1, allow_development=True)
    assert report.partition == "development"
    assert report.reportable is False


def test_mixed_partitions_are_refused() -> None:
    records = _bank("C1", [[True]]) + _bank("C2", [[True]], partition="development")
    with pytest.raises(DevelopmentResultError):
        analyze_runs(records, settings=SETTINGS, min_questions=1)
    report = analyze_runs(records, settings=SETTINGS, min_questions=1, allow_development=True)
    assert report.partition == "mixed" and report.reportable is False


def test_evaluation_report_is_reportable() -> None:
    report = analyze_runs(_bank("C1", [[True]]), settings=SETTINGS, min_questions=1)
    assert report.partition == "evaluation" and report.reportable is True


def test_minimum_questions_warning_per_stratum() -> None:
    report = analyze_runs(_bank("C1", [[True]] * 3), settings=SETTINGS, min_questions=25)
    assert any("E3" in w and "3" in w and "25" in w for w in report.warnings)
    assert _cell(report, "C1", "E3").below_minimum is True
    assert _cell(report, "C1", ALL_STRATA).below_minimum is False


def test_few_runs_warning() -> None:
    report = analyze_runs(
        _bank("C1", [[True, True]]), settings=SETTINGS, min_questions=1, min_runs=3
    )
    assert any("corridas" in w for w in report.warnings)


def _primary(report: AnalysisReport):
    return next(c for c in report.comparisons if c.primary)


def test_primary_comparison_supported_when_intervals_do_not_overlap() -> None:
    c1 = _bank("C1", [[False, False, False]] * 30)
    c2 = _bank("C2", [[True, True, True]] * 30)
    cmp = _primary(analyze_runs(c1 + c2, settings=SETTINGS, min_questions=25))
    assert (cmp.condition_a, cmp.condition_b, cmp.stratum, cmp.metric) == (
        "C2",
        "C1",
        "E3",
        "correct",
    )
    assert cmp.n_pairs == 30
    assert cmp.difference == pytest.approx(1.0)
    assert cmp.intervals_overlap is False
    assert cmp.criterion == "supported"
    assert cmp.nonoverlap_criterion == "supported"
    assert cmp.difference_lower > 0


def test_primary_criterion_is_the_paired_difference_not_the_non_overlap() -> None:
    # Shared easy/hard questions make the independent intervals overlap, but C2 never does worse
    # than C1 on any question, so the paired difference interval excludes 0 (D16, ADR 0010).
    c1 = _bank("C1", [[True, False, True]] * 4 + [[False]] * 4)
    c2 = _bank("C2", [[True, True, True]] * 4 + [[False]] * 4)
    cmp = _primary(analyze_runs(c1 + c2, settings=SETTINGS, min_questions=1))
    assert cmp.intervals_overlap is True
    assert cmp.nonoverlap_criterion == "inconclusive"
    assert cmp.difference_lower > 0
    assert cmp.criterion == "supported"


def test_primary_inconclusive_when_the_paired_interval_includes_zero() -> None:
    same = [[True, False, True]] * 4 + [[False]] * 4
    cmp = _primary(
        analyze_runs(_bank("C1", same) + _bank("C2", same), settings=SETTINGS, min_questions=1)
    )
    assert cmp.difference == 0
    assert cmp.criterion == "inconclusive"
    assert cmp.nonoverlap_criterion == "inconclusive"


def test_reverse_direction_is_never_success() -> None:
    c1 = _bank("C1", [[True, True, True]] * 30)
    c2 = _bank("C2", [[False, False, False]] * 30)
    cmp = _primary(analyze_runs(c1 + c2, settings=SETTINGS, min_questions=25))
    assert cmp.criterion == "inconclusive"
    assert cmp.nonoverlap_criterion == "inconclusive"
    assert cmp.direction == "b_above"
    assert cmp.difference_upper < 0


def test_pairing_uses_only_questions_judged_in_both_conditions() -> None:
    c1 = _bank("C1", [[False]] * 5)
    c2 = _bank("C2", [[True]] * 3)  # only the first three questions exist for C2
    cmp = _primary(analyze_runs(c1 + c2, settings=SETTINGS, min_questions=1))
    assert cmp.n_pairs == 3


def test_secondary_comparisons_are_labelled_and_cover_c2_vs_c3() -> None:
    records = (
        _bank("C1", [[True]] * 3)
        + _bank("C2", [[True]] * 3)
        + _bank("C3", [[False]] * 3)
        + _bank("C1", [[True]] * 3, stratum="E1_point_fact")
        + _bank("C2", [[True]] * 3, stratum="E1_point_fact")
    )
    report = analyze_runs(records, settings=SETTINGS, min_questions=1)
    assert sum(1 for c in report.comparisons if c.primary) == 1
    assert any(
        not c.primary and (c.condition_a, c.condition_b, c.stratum) == ("C2", "C3", "E3")
        for c in report.comparisons
    )
    assert any(
        not c.primary and (c.condition_a, c.condition_b, c.stratum) == ("C2", "C1", "E1")
        for c in report.comparisons
    )


def test_missing_conditions_produce_no_comparison_but_a_warning() -> None:
    report = analyze_runs(_bank("C1", [[True]]), settings=SETTINGS, min_questions=1)
    assert report.comparisons == ()
    assert any("C2" in w for w in report.warnings)


def test_analysis_is_deterministic_and_serialisable() -> None:
    records = _bank("C1", [[True, False]] * 5) + _bank("C2", [[True, True]] * 5)
    a = report_to_dict(analyze_runs(records, settings=SETTINGS, min_questions=1))
    b = report_to_dict(analyze_runs(records, settings=SETTINGS, min_questions=1))
    assert a == b
    assert a["partition"] == "evaluation"
    assert a["combination"]


def test_report_states_the_paired_criterion_and_keeps_non_overlap_as_robustness() -> None:
    records = _bank("C1", [[False]] * 30) + _bank("C2", [[True]] * 30)
    data = report_to_dict(analyze_runs(records, settings=SETTINGS, min_questions=25))
    assert "pareada" in data["criterion_d16"]
    assert "robustez" in data["criterion_d16"]
    primary = next(c for c in data["comparisons"] if c["primary"])
    assert primary["criterion"] == "supported"
    assert primary["nonoverlap_criterion"] == "supported"


# --- citation width beside citation_correct (ADR 0009, amendment) --------------------------------


def _cited_record(question: str, condition: str, ids: tuple[str, ...], **kw: Any) -> dict[str, Any]:
    record = _record(question, condition, 0, **kw)
    qid = record["question_id"]
    record["answer"] = {
        "question_id": qid,
        "condition": condition,
        "text": "x",
        "cited_evidence": [{"meeting_id": "m1", "dialogue_act_ids": list(ids)}],
        "abstained": False,
    }
    return record


def _width_questions(*names: str) -> dict[str, Question]:
    return {
        f"ES2015.{n}": Question(
            id=f"ES2015.{n}",
            series_id="ES2015",
            stratum=QuestionStratum.E3_EVOLUTION,
            text="?",
            reference_answer=None,
            reference_evidence=(EvidenceSpan(meeting_id="m1", dialogue_act_ids=("a.1", "a.2")),),
        )
        for n in names
    }


def test_cells_carry_citation_width_when_questions_are_given() -> None:
    records = [
        _cited_record("E3q00", "C1", ("a.1", "b.1", "b.2")),
        _cited_record("E3q01", "C1", ("a.1", "a.2")),
        _cited_record("E3q00", "C2", ("a.1", *(f"c.{i}" for i in range(9)))),
        _cited_record("E3q01", "C2", ("c.1",)),
    ]
    questions = _width_questions("E3q00", "E3q01")
    report = analyze_runs(records, settings=SETTINGS, min_questions=1, questions=questions)
    c1, c2 = _cell(report, "C1", "E3").citation_width, _cell(report, "C2", "ALL").citation_width
    assert c1 is not None and c2 is not None
    assert (c1.cited_acts_min, c1.cited_acts_median, c1.cited_acts_max) == (2, 2.5, 3)
    assert c1.mean_act_coverage == pytest.approx((0.5 + 1.0) / 2)
    assert (c2.cited_acts_min, c2.cited_acts_median, c2.cited_acts_max) == (1, 5.5, 10)
    assert c2.mean_act_coverage == pytest.approx((0.5 + 0.0) / 2)


def test_citation_width_is_unknown_without_the_question_bank() -> None:
    report = analyze_runs([_record("E3q00", "C1", 0)], settings=SETTINGS, min_questions=1)
    assert _cell(report, "C1", "E3").citation_width is None


def test_citation_width_is_serialised_with_the_cell() -> None:
    records = [_cited_record("E3q00", "C1", ("a.1",))]
    report = analyze_runs(
        records, settings=SETTINGS, min_questions=1, questions=_width_questions("E3q00")
    )
    cell = report_to_dict(report)["cells"][0]
    assert cell["citation_width"]["cited_acts_median"] == 1
    assert cell["citation_width"]["source_citations"] == 0
