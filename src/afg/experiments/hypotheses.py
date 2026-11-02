"""Extraction gap and H3 over the Experiment A figures (ADR 0016, ADR 0018; document 08, 4.3).

Pure functions over figures that the Experiment A report already holds: the pooled decision
figures at the principal tau (:mod:`afg.experiments.extraction_report`) and the pooled relation
score of ``relaciones.json`` (:mod:`afg.evaluation.relations`). Nothing here scores, embeds or
calls a model, and no new statistic is introduced: every interval is one the scoring already
produced (the meeting-cluster bootstrap of ADR 0011 for decisions, Wilson for relations).

Extraction gap: relations against decisions (complementary figure, NOT H2)
--------------------------------------------------------------------------
H2 is measured in Experiment B (ADR 0018, :mod:`afg.experiments.analysis`). This figure is its
complementary view on the extraction itself, and it is biased by construction: a relation is
found only if both of its decisions align, so its end-to-end gap is at least about the decision
gap.
C3 is the reference base (no extraction error), so against the reference its score is 1 and the
C3 - C2 gap of an extraction layer is ``1 - recall`` of C2 on it. Decisions: ``1 - recall`` of the
decision alignment. Relations: ``1 - recall`` of link existence, in two views of ADR 0016: end to
end (principal) and conditional on both decisions being aligned (the figure that separates
relation extraction from decision extraction). The gap difference is ``gap(relations) -
gap(decisions)``.

Verdict rule (no threshold is invented): the project reads a difference as a finding only when
the intervals do not overlap (proposal section 5.0; document 08, 4.4). ``supported`` when the
relation gap interval lies entirely above the decision gap interval;
``contrary`` for the mirror case; ``inconclusive`` otherwise; ``not_computable`` without gold
links or relations.

H3: direction is a dominant failure mode of the relations
---------------------------------------------------------
Over the detected links (true positives of existence, ADR 0016's "among detected" view) a link
fails on type, on direction, or both. Direction failures are the inverted ones plus the
unknown ones (the principal view counts an unknown direction as an error). ``dominant`` is read
two ways: the most frequent failure mode by count, and a verdict with the same non-overlap rule
as the gap between the direction and type error rates. The second clause of H3 (no proportional
improvement with model size) needs a second model scale; ``scale`` records which models were
measured.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from afg.evaluation.relations import Proportion

__all__ = ["GAP_NOTE", "extraction_gap_analysis", "h3_analysis", "hypotheses_report"]

_REQUIRED_RELATION_KEYS = (
    "existence_end_to_end",
    "existence_conditional",
    "type_principal",
    "direction_principal",
    "direction_unknown_excluded",
    "unknown_direction",
)
_NOT_COMPUTABLE = "not_computable"
GAP_NOTE = (
    "Cifra complementaria, no es H2 (ADR 0018). Sesgo mecánico: una relación solo se encuentra "
    "si sus dos decisiones se alinean, así que la brecha de relaciones de extremo a extremo "
    "incluye la de decisiones; la vista condicionada lo quita pero tiene pocos enlaces."
)


def _complete(relations: Mapping[str, Any] | None) -> bool:
    return relations is not None and all(key in relations for key in _REQUIRED_RELATION_KEYS)


def _verdict(first: tuple[float, float] | None, second: tuple[float, float] | None) -> str:
    """``supported`` when ``first`` lies entirely above ``second``, ``contrary`` entirely below."""
    if first is None or second is None:
        return _NOT_COMPUTABLE
    if first[0] > second[1]:
        return "supported"
    if first[1] < second[0]:
        return "contrary"
    return "inconclusive"


def _gap(
    recall: float | None, interval: Sequence[float] | None, n_reference: int
) -> dict[str, Any]:
    if recall is None or interval is None or n_reference == 0:
        return {"n_reference": n_reference, "recall": None, "gap": None, "gap_interval": None}
    return {
        "n_reference": n_reference,
        "recall": recall,
        "gap": 1 - recall,
        "gap_interval": [1 - interval[1], 1 - interval[0]],
    }


def _relation_gap(existence: Mapping[str, Any]) -> dict[str, Any]:
    recall = existence["recall"]
    return _gap(
        recall["rate"],
        None if recall["rate"] is None else (recall["lower"], recall["upper"]),
        existence["tp"] + existence["fn"],
    )


def _compare(relations: dict[str, Any], decisions: dict[str, Any]) -> str:
    if relations["gap"] is None or decisions["gap"] is None:
        return _NOT_COMPUTABLE
    relations["difference"] = relations["gap"] - decisions["gap"]
    return _verdict(tuple(relations["gap_interval"]), tuple(decisions["gap_interval"]))


def extraction_gap_analysis(
    decision_figures: Mapping[str, Any] | None,
    relations_pooled: Mapping[str, Any] | None,
    *,
    tau: float,
) -> dict[str, Any]:
    """The gap to the reference for relations against the gap for decisions (not H2).

    ``decision_figures`` is the pooled figures dict of the report at the principal tau and
    scope (``tp``, ``fn``, ``recall`` and ``intervals["recall"]``).
    """
    if decision_figures is None:
        decisions = _gap(None, None, 0)
    else:
        decisions = _gap(
            decision_figures["recall"],
            decision_figures["intervals"]["recall"],
            decision_figures["tp"] + decision_figures["fn"],
        )
    result: dict[str, Any] = {
        "tau": tau,
        "definition": "gap C3 - C2 = 1 - recall of C2 against the reference (C3 scores 1)",
        "note": GAP_NOTE,
        "decisions": decisions,
        "relations": {"end_to_end": None, "conditional": None},
        "verdicts": {"end_to_end": _NOT_COMPUTABLE, "conditional": _NOT_COMPUTABLE},
        "verdict": _NOT_COMPUTABLE,
    }
    if not _complete(relations_pooled):
        return result
    assert relations_pooled is not None
    for view, key in (
        ("end_to_end", "existence_end_to_end"),
        ("conditional", "existence_conditional"),
    ):
        gap = _relation_gap(relations_pooled[key])
        result["relations"][view] = gap
        result["verdicts"][view] = _compare(gap, decisions)
    result["verdict"] = result["verdicts"]["end_to_end"]
    return result


def _proportion(successes: int, trials: int) -> dict[str, Any]:
    p = Proportion.of(successes, trials)
    return {
        "successes": p.successes,
        "trials": p.trials,
        "rate": p.rate,
        "lower": p.lower,
        "upper": p.upper,
    }


def h3_analysis(
    relations_pooled: Mapping[str, Any] | None, *, models: Sequence[str]
) -> dict[str, Any]:
    """H3: direction as a failure mode of the detected links, with the scale component."""
    scale = {
        "measured_models": list(models),
        "status": "single_scale" if len(models) <= 1 else "multiple_scales",
        "note": "H3's second clause (no proportional improvement with model size) needs a "
        "second scale; none is measured by this report.",
    }
    result: dict[str, Any] = {
        "definition": "failures among detected links (true positives of existence): "
        "direction = inverted + unknown (principal view); type = principal view",
        "n_detected": 0,
        "direction": None,
        "type": None,
        "inverted_among_known": None,
        "most_frequent_failure": None,
        "verdict": _NOT_COMPUTABLE,
        "scale": scale,
    }
    if not _complete(relations_pooled):
        return result
    assert relations_pooled is not None
    direction = relations_pooled["direction_principal"]["among_detected"]
    kind = relations_pooled["type_principal"]["among_detected"]
    detected = direction["trials"]
    result["n_detected"] = detected
    if detected == 0:
        return result
    direction_errors = detected - direction["successes"]
    type_errors = kind["trials"] - kind["successes"]
    unknown = relations_pooled["unknown_direction"]["successes"]
    failures = direction_errors + type_errors
    direction_rate = _proportion(direction_errors, detected)
    type_rate = _proportion(type_errors, kind["trials"])
    result["direction"] = {
        "errors": direction_errors,
        "unknown": unknown,
        "inverted": direction_errors - unknown,
        "rate": direction_rate,
        "share_of_failures": direction_errors / failures if failures else None,
    }
    result["type"] = {"errors": type_errors, "rate": type_rate}
    result["inverted_among_known"] = relations_pooled["direction_unknown_excluded"][
        "among_detected"
    ]
    if direction_errors == type_errors:
        result["most_frequent_failure"] = "none" if failures == 0 else "tie"
    else:
        result["most_frequent_failure"] = "direction" if direction_errors > type_errors else "type"
    dir_interval = (direction_rate["lower"], direction_rate["upper"])
    type_interval = (type_rate["lower"], type_rate["upper"])
    result["verdict"] = _verdict(dir_interval, type_interval)
    return result


def hypotheses_report(
    *,
    decision_figures: Mapping[str, Any] | None,
    relations_pooled: Mapping[str, Any] | None,
    tau: float,
    models: Sequence[str],
) -> dict[str, Any]:
    """Both analyses as one JSON-ready dict."""
    return {
        "extraction_gap_relations_vs_decisions": extraction_gap_analysis(
            decision_figures, relations_pooled, tau=tau
        ),
        "h3": h3_analysis(relations_pooled, models=models),
    }
