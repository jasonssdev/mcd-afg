"""Tests for Experiment A scoring: alignment-based P/R/F1, roles, runs, partition guard."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import (
    DevelopmentResultError,
    IntervalSettings,
    SimilarityFn,
    pair_text,
    pool_scores,
    score_runs,
    score_series,
)

SETTINGS = IntervalSettings(n_resamples=500, confidence_level=0.95, seed=7)
EVAL = lambda series: "evaluation"  # noqa: E731
DEV = lambda series: "development"  # noqa: E731


def _ref(i: int, role: str | None = "PM", series: str = "ES2015") -> ReferenceDecision:
    return ReferenceDecision(
        decision_id=f"{series}a.d{i:02d}",
        series_id=series,
        meeting_id=f"{series}a",
        decision_object=f"obj{i}",
        content=f"cont{i}",
        evidence=EvidenceSpan(meeting_id=f"{series}a", dialogue_act_ids=(f"da.{i}",)),
        evidence_method="sentence_id",
        role=role,
        roles=(role,) if role else (),
    )


def _pred(
    i: int,
    series: str = "ES2015",
    status: DecisionStatus = DecisionStatus.ACCEPTED,
    act: str | None = None,
) -> Decision:
    return Decision(
        id=f"p{i}",
        series_id=series,
        meeting_id=f"{series}a",
        decision_object=f"obj{i}",
        content=f"cont{i}",
        status=status,
        evidence=EvidenceSpan(meeting_id=f"{series}a", dialogue_act_ids=(act or f"da.{i}",)),
    )


def _identity_similarity(predicted: Sequence[str], reference: Sequence[str]) -> np.ndarray:
    """1.0 for the same text, 0.0 otherwise: a fake in place of embeddings."""
    return np.array([[1.0 if p == r else 0.0 for r in reference] for p in predicted]).reshape(
        len(predicted), len(reference)
    )


SIM: SimilarityFn = _identity_similarity


def test_pair_text_joins_object_and_content() -> None:
    assert pair_text("precio", "25 euros") == "precio: 25 euros"


def test_counts_and_metrics_from_the_alignment() -> None:
    reference = [_ref(1), _ref(2), _ref(3), _ref(4)]
    predicted = [_pred(1), _pred(2), _pred(9)]

    score = score_series("ES2015", reference, predicted, SIM, tau=0.5)

    assert (score.tp, score.fp, score.fn) == (2, 1, 2)
    assert score.precision == pytest.approx(2 / 3)
    assert score.recall == pytest.approx(0.5)
    assert score.f1 == pytest.approx(2 * (2 / 3) * 0.5 / ((2 / 3) + 0.5))
    assert score.reference_hits == (True, True, False, False)
    assert score.predicted_hits == (True, True, False)


def test_matching_is_one_to_one() -> None:
    reference = [_ref(1)]
    predicted = [_pred(1), _pred(1)]  # two extractions of the same decision

    score = score_series("ES2015", reference, predicted, SIM, tau=0.5)

    assert (score.tp, score.fp, score.fn) == (1, 1, 0)


def test_threshold_decides_what_matches() -> None:
    def graded(predicted: Sequence[str], reference: Sequence[str]) -> np.ndarray:
        return np.full((len(predicted), len(reference)), 0.7)

    reference, predicted = [_ref(1)], [_pred(1)]

    assert score_series("ES2015", reference, predicted, graded, tau=0.7).tp == 1
    assert score_series("ES2015", reference, predicted, graded, tau=0.75).tp == 0


def test_non_decisions_extracted_are_ignored_and_counted() -> None:
    predicted = [_pred(1), _pred(2, status=DecisionStatus.OPEN_PROPOSAL)]

    score = score_series("ES2015", [_ref(1), _ref(2)], predicted, SIM, tau=0.5)

    assert (score.tp, score.fp, score.fn) == (1, 0, 1)
    assert score.n_ignored_non_decisions == 1


def test_empty_sides_do_not_divide_by_zero() -> None:
    nothing = score_series("ES2015", [_ref(1)], [], SIM, tau=0.5)
    assert (nothing.tp, nothing.fp, nothing.fn) == (0, 0, 1)
    assert (nothing.precision, nothing.recall, nothing.f1) == (0.0, 0.0, 0.0)

    spurious = score_series("ES2015", [], [_pred(1)], SIM, tau=0.5)
    assert (spurious.tp, spurious.fp, spurious.fn) == (0, 1, 0)


def test_recall_is_stratified_by_reference_role() -> None:
    reference = [_ref(1, "PM"), _ref(2, "PM"), _ref(3, "ME"), _ref(4, None)]
    predicted = [_pred(1), _pred(3)]

    score = score_series("ES2015", reference, predicted, SIM, tau=0.5)

    assert score.by_role["PM"].n_reference == 2
    assert score.by_role["PM"].recall == pytest.approx(0.5)
    assert score.by_role["ME"].recall == pytest.approx(1.0)
    assert score.by_role["unknown"].n_reference == 1
    assert score.by_role["unknown"].recall == pytest.approx(0.0)
    # No resolver for extracted decisions: precision by role is not reported.
    assert score.by_role["PM"].precision is None


def test_precision_by_role_uses_the_role_of_the_extracted_evidence() -> None:
    roles = {"da.1": "PM", "da.2": "PM", "da.7": "ME"}
    reference = [_ref(1, "PM"), _ref(2, "PM")]
    predicted = [_pred(1), _pred(2), _pred(7)]

    score = score_series(
        "ES2015",
        reference,
        predicted,
        SIM,
        tau=0.5,
        predicted_role_of=lambda d: roles[d.evidence.dialogue_act_ids[0]],
    )

    assert score.by_role["PM"].precision == pytest.approx(1.0)
    assert score.by_role["ME"].n_predicted == 1
    assert score.by_role["ME"].precision == pytest.approx(0.0)
    assert score.by_role["ME"].recall is None  # no reference decision of that role


def test_pooled_score_is_micro_averaged_with_intervals() -> None:
    a = score_series("ES2015", [_ref(1), _ref(2)], [_pred(1)], SIM, tau=0.5)
    b = score_series(
        "IS1004",
        [_ref(1, series="IS1004"), _ref(2, series="IS1004")],
        [_pred(1, series="IS1004"), _pred(2, series="IS1004"), _pred(9, series="IS1004")],
        SIM,
        tau=0.5,
    )

    pooled = pool_scores([a, b], settings=SETTINGS, partition_of=EVAL)

    assert (pooled.tp, pooled.fp, pooled.fn) == (3, 1, 1)
    assert pooled.precision == pytest.approx(3 / 4)
    assert pooled.recall == pytest.approx(3 / 4)
    assert pooled.series == ("ES2015", "IS1004")
    lo, hi = pooled.precision_interval
    assert 0.0 <= lo < 0.75 < hi <= 1.0
    lo, hi = pooled.f1_interval
    assert 0.0 <= lo <= pooled.f1 <= hi <= 1.0
    assert pooled.interval_methods == {
        "precision": "wilson",
        "recall": "wilson",
        "f1": "bootstrap over decisions",
    }


def test_pooled_bootstrap_is_reproducible_for_a_seed() -> None:
    a = score_series("ES2015", [_ref(1), _ref(2)], [_pred(1)], SIM, tau=0.5)

    first = pool_scores([a], settings=SETTINGS, partition_of=EVAL)
    second = pool_scores([a], settings=SETTINGS, partition_of=EVAL)

    assert first.f1_interval == second.f1_interval


def test_pooled_roles_are_summed_across_series() -> None:
    a = score_series("ES2015", [_ref(1, "PM")], [_pred(1)], SIM, tau=0.5)
    b = score_series("IS1004", [_ref(2, "PM", "IS1004")], [], SIM, tau=0.5)

    pooled = pool_scores([a, b], settings=SETTINGS, partition_of=EVAL)

    assert pooled.by_role["PM"].n_reference == 2
    assert pooled.by_role["PM"].recall == pytest.approx(0.5)


def test_pooling_refuses_mixed_thresholds_and_nothing() -> None:
    a = score_series("ES2015", [_ref(1)], [_pred(1)], SIM, tau=0.5)
    b = score_series("IS1004", [_ref(1, series="IS1004")], [], SIM, tau=0.6)

    with pytest.raises(ValueError, match="tau"):
        pool_scores([a, b], settings=SETTINGS, partition_of=EVAL)
    with pytest.raises(ValueError, match="empty"):
        pool_scores([], settings=SETTINGS, partition_of=EVAL)


def test_development_series_are_flagged_and_cannot_be_reported() -> None:
    a = score_series("ES2015", [_ref(1)], [_pred(1)], SIM, tau=0.5)

    pooled = pool_scores([a], settings=SETTINGS, partition_of=DEV)

    assert pooled.partition == "development"
    assert pooled.development_only is True
    assert pooled.reportable is False
    with pytest.raises(DevelopmentResultError):
        pooled.require_reportable()


def test_evaluation_series_are_reportable_and_mixed_are_not() -> None:
    a = score_series("ES2015", [_ref(1)], [_pred(1)], SIM, tau=0.5)
    b = score_series("IS1004", [_ref(1, series="IS1004")], [], SIM, tau=0.5)

    assert pool_scores([a], settings=SETTINGS, partition_of=EVAL).require_reportable() is None
    mixed = pool_scores(
        [a, b],
        settings=SETTINGS,
        partition_of=lambda s: "development" if s == "ES2015" else "evaluation",
    )
    assert mixed.partition == "mixed"
    assert mixed.reportable is False


def test_default_partition_comes_from_the_corpus_config() -> None:
    a = score_series("ES2015", [_ref(1)], [_pred(1)], SIM, tau=0.5)  # ES2015 is development

    assert pool_scores([a], settings=SETTINGS).partition == "development"


def _runs(per_run_hits: list[int]) -> list[dict[str, list[Decision]]]:
    """One run per entry: the first ``n`` of 4 reference decisions are found."""
    return [{"ES2015": [_pred(i) for i in range(1, n + 1)]} for n in per_run_hits]


def test_repeated_runs_report_mean_and_dispersion() -> None:
    references = {"ES2015": [_ref(1), _ref(2), _ref(3), _ref(4)]}

    report = score_runs(
        references,
        _runs([2, 3, 4]),
        SIM,
        tau=0.5,
        settings=SETTINGS,
        partition_of=EVAL,
    )

    assert report.n_runs == 3
    assert [r.recall for r in report.runs] == [0.5, 0.75, 1.0]
    assert report.recall_mean == pytest.approx(0.75)
    assert report.recall_stdev == pytest.approx(0.25)
    assert report.precision_mean == pytest.approx(1.0)
    assert report.precision_stdev == pytest.approx(0.0)
    assert report.partition == "evaluation"
    assert report.reportable is True


def test_fewer_than_three_runs_are_refused() -> None:
    with pytest.raises(ValueError, match="minimum"):
        score_runs(
            {"ES2015": [_ref(1)]}, _runs([1, 1]), SIM, tau=0.5, settings=SETTINGS, partition_of=EVAL
        )


def test_runs_over_development_series_stay_flagged() -> None:
    report = score_runs(
        {"ES2015": [_ref(1)]}, _runs([1, 1, 1]), SIM, tau=0.5, settings=SETTINGS, partition_of=DEV
    )

    assert report.reportable is False
    with pytest.raises(DevelopmentResultError):
        report.require_reportable()


def test_a_series_without_reference_cannot_be_scored() -> None:
    with pytest.raises(KeyError, match="IS1004"):
        score_runs(
            {"ES2015": [_ref(1)]},
            [{"IS1004": [_pred(1, series="IS1004")]}] * 3,
            SIM,
            tau=0.5,
            settings=SETTINGS,
            partition_of=EVAL,
        )


def test_evidence_role_resolver_reads_the_role_from_the_frozen_turns(tmp_path: Path) -> None:
    import json

    from afg.evaluation.scoring import evidence_role_resolver

    turn = {
        "meeting_id": "ES2015a",
        "turn_index": 0,
        "speaker": "A",
        "role": "UI",
        "text": "hello",
        "start": None,
        "end": None,
        "char_start": 4,
        "char_end": 9,
        "dialogue_act_ids": ["da.1"],
    }
    (tmp_path / "ES2015a.jsonl").write_text(json.dumps(turn) + "\n", encoding="utf-8")

    role_of = evidence_role_resolver(tmp_path)

    assert role_of(_pred(1)) == "UI"
    assert role_of(_pred(1, act="other.act")) is None
