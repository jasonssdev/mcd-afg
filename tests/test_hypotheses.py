"""Tests for the extraction gap and the H3 analysis of the Experiment A report (``hypotheses``)."""

from __future__ import annotations

from typing import Any

import pytest

from afg.evaluation.relations import Proportion
from afg.experiments.hypotheses import extraction_gap_analysis, h3_analysis, hypotheses_report


def _prop(successes: int, trials: int) -> dict[str, Any]:
    p = Proportion.of(successes, trials)
    return {
        "successes": p.successes,
        "trials": p.trials,
        "rate": p.rate,
        "lower": p.lower,
        "upper": p.upper,
    }


def _views(e2e: tuple[int, int], cond: tuple[int, int], det: tuple[int, int]) -> dict[str, Any]:
    return {
        "end_to_end": _prop(*e2e),
        "conditional": _prop(*cond),
        "among_detected": _prop(*det),
    }


def _existence(tp: int, fn: int) -> dict[str, Any]:
    return {"tp": tp, "fp": 0, "fn": fn, "recall": _prop(tp, tp + fn)}


def _relations(
    *,
    e2e: tuple[int, int] = (1, 40),
    cond: tuple[int, int] = (1, 2),
    type_det: tuple[int, int] = (9, 10),
    dir_det: tuple[int, int] = (3, 10),
    dir_known: tuple[int, int] = (3, 4),
    unknown: tuple[int, int] = (6, 10),
) -> dict[str, Any]:
    return {
        "existence_end_to_end": _existence(e2e[0], e2e[1] - e2e[0]),
        "existence_conditional": _existence(cond[0], cond[1] - cond[0]),
        "type_principal": _views((0, 1), (0, 1), type_det),
        "direction_principal": _views((0, 1), (0, 1), dir_det),
        "direction_unknown_excluded": _views((0, 1), (0, 1), dir_known),
        "unknown_direction": _prop(*unknown),
    }


def _decisions(tp: int, fn: int, interval: tuple[float, float]) -> dict[str, Any]:
    return {
        "tp": tp,
        "fn": fn,
        "recall": tp / (tp + fn),
        "intervals": {"recall": list(interval)},
    }


def test_gap_gap_is_one_minus_recall_with_the_interval_flipped() -> None:
    result = extraction_gap_analysis(
        _decisions(20, 10, (0.5, 0.8)), _relations(e2e=(2, 40)), tau=0.70
    )

    assert result["decisions"]["gap"] == pytest.approx(1 / 3)
    assert result["decisions"]["gap_interval"] == pytest.approx([0.2, 0.5])
    relations = result["relations"]["end_to_end"]
    assert relations["gap"] == pytest.approx(1 - 2 / 40)
    assert relations["n_reference"] == 40
    assert result["tau"] == 0.70


def test_gap_supported_only_when_the_relation_gap_interval_clears_the_decision_one() -> None:
    result = extraction_gap_analysis(
        _decisions(20, 10, (0.5, 0.8)), _relations(e2e=(1, 40)), tau=0.70
    )

    assert result["relations"]["end_to_end"]["difference"] > 0
    assert result["verdicts"]["end_to_end"] == "supported"
    assert result["verdict"] == "supported"


def test_gap_is_inconclusive_when_the_intervals_overlap_even_if_the_gap_is_larger() -> None:
    result = extraction_gap_analysis(
        _decisions(20, 10, (0.5, 0.8)), _relations(e2e=(14, 40)), tau=0.70
    )

    assert result["relations"]["end_to_end"]["difference"] > 0
    assert result["verdict"] == "inconclusive"


def test_gap_contrary_when_the_decision_gap_clearly_exceeds_the_relation_gap() -> None:
    result = extraction_gap_analysis(
        _decisions(2, 38, (0.01, 0.12)), _relations(e2e=(30, 40)), tau=0.70
    )

    assert result["verdict"] == "contrary"


def test_gap_conditional_view_is_reported_beside_the_end_to_end_one() -> None:
    result = extraction_gap_analysis(
        _decisions(20, 10, (0.5, 0.8)), _relations(cond=(1, 2)), tau=0.70
    )

    assert result["relations"]["conditional"]["n_reference"] == 2
    assert result["verdicts"]["conditional"] == "inconclusive"


def test_gap_not_computable_without_gold_links_or_relations() -> None:
    no_links = _relations(e2e=(0, 0), cond=(0, 0))

    assert extraction_gap_analysis(_decisions(1, 1, (0.1, 0.9)), no_links, tau=0.7)["verdict"] == (
        "not_computable"
    )
    assert extraction_gap_analysis(_decisions(1, 1, (0.1, 0.9)), None, tau=0.7)["verdict"] == (
        "not_computable"
    )


def test_h3_counts_failures_among_detected_links() -> None:
    result = h3_analysis(_relations(), models=["qwen3:8b"])

    assert result["n_detected"] == 10
    assert result["direction"]["errors"] == 7
    assert result["direction"]["unknown"] == 6
    assert result["direction"]["inverted"] == 1
    assert result["type"]["errors"] == 1
    assert result["direction"]["share_of_failures"] == pytest.approx(7 / 8)
    assert result["most_frequent_failure"] == "direction"
    assert result["inverted_among_known"]["trials"] == 4


def test_h3_supported_when_direction_errors_clearly_outnumber_type_errors() -> None:
    result = h3_analysis(
        _relations(type_det=(98, 100), dir_det=(10, 100), unknown=(60, 100)),
        models=["qwen3:8b"],
    )

    assert result["verdict"] == "supported"


def test_h3_inconclusive_when_the_intervals_overlap() -> None:
    assert h3_analysis(_relations(), models=["qwen3:8b"])["verdict"] == "inconclusive"


def test_h3_not_computable_without_detected_links() -> None:
    empty = _relations(type_det=(0, 0), dir_det=(0, 0), dir_known=(0, 0), unknown=(0, 0))

    assert h3_analysis(empty, models=["qwen3:8b"])["verdict"] == "not_computable"
    assert h3_analysis(None, models=["qwen3:8b"])["verdict"] == "not_computable"


def test_h3_scale_component_is_a_declared_gap_with_one_model() -> None:
    scale = h3_analysis(_relations(), models=["qwen3:8b"])["scale"]

    assert scale["measured_models"] == ["qwen3:8b"]
    assert scale["status"] == "single_scale"


def test_report_wraps_both_hypotheses_and_tolerates_partial_relation_figures() -> None:
    full = hypotheses_report(
        decision_figures=_decisions(20, 10, (0.5, 0.8)),
        relations_pooled=_relations(),
        tau=0.70,
        models=["qwen3:8b"],
    )
    partial = hypotheses_report(
        decision_figures=_decisions(20, 10, (0.5, 0.8)),
        relations_pooled={"n_gold_links": 4},
        tau=0.70,
        models=[],
    )

    assert set(full) == {"extraction_gap_relations_vs_decisions", "h3"}
    assert partial["extraction_gap_relations_vs_decisions"]["verdict"] == "not_computable"
    assert partial["h3"]["verdict"] == "not_computable"


def test_gap_carries_the_note_on_the_mechanical_bias() -> None:
    result = extraction_gap_analysis(_decisions(20, 10, (0.5, 0.8)), _relations(), tau=0.70)

    assert "ADR 0018" in result["note"]
    assert "alinea" in result["note"]
