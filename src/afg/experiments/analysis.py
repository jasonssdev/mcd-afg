"""Analysis of the records of Experiment B (thesis sections 5.6, 5.7 and 6; D16).

Pure functions over the record dictionaries written by :mod:`afg.experiments.runner` (use
``load_records(..., latest_only=True)``). Nothing here calls a model.

How the runs are combined
-------------------------
Each question is answered at least three times per condition (``runs_per_config``). Runs of the
same question are repeated measures of one item, not independent observations, so pooling every
answer would overstate the sample size and narrow the intervals. The unit of analysis is the
QUESTION:

1. For every (condition, question) the metric is averaged over the runs that have a value
   (a per-question score in [0, 1]).
2. The rate of a cell (condition x stratum, or overall) is the mean of the per-question scores.
3. The 95 % interval is a percentile bootstrap that resamples QUESTIONS (never answers), with the
   resamples, confidence level and seed of ``config/experiments.toml``.
4. A paired comparison takes, for each question judged in both conditions, the difference of the
   two per-question scores and bootstraps the mean difference over questions.

Records with a judge failure or an error are left out of every denominator and counted apart.
Citation metrics are computed only from non-abstaining answers of strata that have reference
evidence (E1 to E3) and only from schema version 2 records: version 1 holds the retired
"every span must hit" value (ADR 0009) and has to be rescored first.

D16 criterion
-------------
The primary criterion is the answer correctness on E3, C2 against C1. Since the amendment of
2026-10-15 (``docs/decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md``, made before
any evaluation run and backed by the power simulation of notebook 10) the hypothesis is supported
when the 95 % bootstrap interval of the PAIRED difference C2 - C1 lies above 0; otherwise the
result is inconclusive and never a success. The preregistered wording of 2026-10-13 (the 95 %
intervals of C2 and C1, computed independently, do not overlap) is kept as a robustness field,
``nonoverlap_criterion``, reported next to the primary verdict and never replacing it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from afg.domain.question import Question
from afg.evaluation.metrics import BootstrapCI, bootstrap_ci
from afg.evaluation.scoring import DevelopmentResultError, IntervalSettings
from afg.experiments.summary import CitationWidthSummary, citation_width_summary

__all__ = [
    "ALL_STRATA",
    "AnalysisReport",
    "CellSummary",
    "Comparison",
    "DevelopmentResultError",
    "RateEstimate",
    "analyze_runs",
    "bootstrap_mean_interval",
    "intervals_disjoint_above",
    "report_to_dict",
]

ALL_STRATA = "ALL"
E4 = "E4"
PRIMARY_CONDITION = "C2"
PRIMARY_BASELINE = "C1"
PRIMARY_STRATUM = "E3"
PRIMARY_METRIC = "correct"
COMPARED_METRICS: tuple[str, ...] = ("correct", "evidence_supported")
SECONDARY_PAIRS: tuple[tuple[str, str], ...] = (("C2", "C1"), ("C2", "C3"))
CITATION_SCHEMA_VERSION = 2

COMBINATION_NOTE = (
    "Las corridas de una misma pregunta se promedian por pregunta; la tasa de una celda es el "
    "promedio de esos valores y el intervalo bootstrap remuestrea preguntas, no respuestas, "
    "porque las corridas de una pregunta no son independientes. Las comparaciones se aparean "
    "por pregunta."
)
CRITERION_NOTE = (
    "Criterio D16 (enmendado, ADR 0010): la hipótesis se respalda si el intervalo bootstrap del "
    "95 % de la diferencia pareada C2 - C1 queda por encima de 0; en otro caso el resultado es no "
    "concluyente. La no superposición de los intervalos independientes de C2 y C1 (redacción "
    "original) se informa aparte como robustez y no reemplaza al criterio principal."
)

Record = Mapping[str, Any]
Extractor = Callable[[Record], float | None]


@dataclass(frozen=True, slots=True)
class RateEstimate:
    """A rate over questions with its bootstrap interval."""

    point: float
    lower: float
    upper: float
    n_questions: int
    n_records: int


@dataclass(frozen=True, slots=True)
class CellSummary:
    """All metrics of one condition x stratum cell (``stratum`` is ``ALL`` for the overall one)."""

    condition: str
    stratum: str
    records: int
    questions: int
    judge_failures: int
    errors: int
    citation_records_v1_excluded: int
    below_minimum: bool
    metrics: Mapping[str, RateEstimate | None]
    citation_width: CitationWidthSummary | None = None
    """Width, act-level coverage and full-source citations (ADR 0009, amendment); ``None`` when
    no question bank was given, so the reference evidence is unknown."""


@dataclass(frozen=True, slots=True)
class Comparison:
    """``condition_a`` against ``condition_b`` on one metric and stratum, paired by question."""

    primary: bool
    condition_a: str
    condition_b: str
    stratum: str
    metric: str
    n_pairs: int
    difference: float
    difference_lower: float
    difference_upper: float
    interval_a: tuple[float, float]
    interval_b: tuple[float, float]
    direction: str
    """``a_above`` / ``b_above`` when the independent 95 % intervals are disjoint, else
    ``overlap``."""
    criterion: str
    """Primary verdict: ``supported`` only when the paired difference interval is above 0."""
    nonoverlap_criterion: str
    """Robustness: ``supported`` only when ``a_above``; every other outcome is ``inconclusive``."""

    @property
    def intervals_overlap(self) -> bool:
        return self.direction == "overlap"


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    partition: str
    reportable: bool
    settings: IntervalSettings
    cells: tuple[CellSummary, ...]
    comparisons: tuple[Comparison, ...]
    warnings: tuple[str, ...]


# --- extraction -------------------------------------------------------------------------------


def _label(record: Record) -> str:
    return str(record["stratum"]).split("_", 1)[0]


def _is_error(record: Record) -> bool:
    return record.get("error") is not None


def _is_judge_failure(record: Record) -> bool:
    return not _is_error(record) and record.get("judge_failure") is not None


def _is_judged(record: Record) -> bool:
    return (
        not _is_error(record)
        and record.get("judge_failure") is None
        and bool(record.get("verdict"))
    )


def _abstained(record: Record) -> bool:
    return bool((record.get("answer") or {}).get("abstained"))


def _verdict_flag(name: str) -> Extractor:
    def extract(record: Record) -> float | None:
        if not _is_judged(record):
            return None
        value = record["verdict"].get(name)
        return None if value is None else float(bool(value))

    return extract


def _citation_usable(record: Record) -> bool:
    return (
        not _is_error(record)
        and not _abstained(record)
        and _label(record) != E4
        and int(record.get("schema_version") or 1) >= CITATION_SCHEMA_VERSION
    )


def _citation_correct(record: Record) -> float | None:
    if not _citation_usable(record) or record.get("citation_correct") is None:
        return None
    return float(bool(record["citation_correct"]))


def _citation_precision(record: Record) -> float | None:
    if not _citation_usable(record) or record.get("citation_precision") is None:
        return None
    return float(record["citation_precision"])


def _abstention_correct(record: Record) -> float | None:
    if _is_error(record) or _label(record) != E4:
        return None
    return float(_abstained(record))


EXTRACTORS: dict[str, Extractor] = {
    "correct": _verdict_flag("correct"),
    "evidence_supported": _verdict_flag("evidence_supported"),
    "citation_correct": _citation_correct,
    "citation_precision": _citation_precision,
    "abstention_correct": _abstention_correct,
}


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _question_scores(records: Iterable[Record], extract: Extractor) -> dict[str, tuple[float, int]]:
    """``question -> (mean over its runs with a value, number of those runs)``."""
    per_question: dict[str, list[float]] = {}
    for record in records:
        value = extract(record)
        if value is not None:
            per_question.setdefault(str(record["question_id"]), []).append(value)
    return {q: (_mean(v), len(v)) for q, v in per_question.items()}


def bootstrap_mean_interval(values: Sequence[float], settings: IntervalSettings) -> BootstrapCI:
    """Percentile bootstrap interval of the mean over per-question values (resamples questions).

    The single entry point for every interval of this module; the power simulation
    (:mod:`afg.experiments.power`) calls it too, so it studies the machinery that is reported.
    """
    return bootstrap_ci(
        values,
        _mean,
        n=settings.n_resamples,
        seed=settings.seed,
        confidence_level=settings.confidence_level,
    )


def intervals_disjoint_above(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """True when interval ``a`` lies strictly above interval ``b`` (non-overlap criterion)."""
    return a[0] > b[1]


def _estimate(
    scores: Mapping[str, tuple[float, int]], settings: IntervalSettings
) -> RateEstimate | None:
    if not scores:
        return None
    values = [score for score, _ in scores.values()]
    ci = bootstrap_mean_interval(values, settings)
    return RateEstimate(
        point=ci.point_estimate,
        lower=ci.lower,
        upper=ci.upper,
        n_questions=len(values),
        n_records=sum(n for _, n in scores.values()),
    )


# --- analysis ---------------------------------------------------------------------------------


def _latest(records: Iterable[Record]) -> list[Record]:
    latest: dict[tuple[str, str, int], Record] = {}
    for record in records:
        key = (str(record["question_id"]), str(record["condition"]), int(record["run"]))
        latest[key] = record
    return list(latest.values())


def _partition_of(records: Sequence[Record]) -> str:
    found = {str(r.get("partition") or "unknown") for r in records}
    return found.pop() if len(found) == 1 else "mixed"


def analyze_runs(
    records: Iterable[Record],
    *,
    settings: IntervalSettings,
    min_questions: int,
    min_runs: int = 3,
    allow_development: bool = False,
    questions: Mapping[str, Question] | None = None,
) -> AnalysisReport:
    """Aggregate the records of a run and compare conditions (see the module docstring).

    With ``questions`` (id to question) every cell also carries the width of its citations,
    their act-level coverage of the reference evidence and its citations to full sources, which
    ADR 0009 requires beside ``citation_correct``.

    Raises:
        DevelopmentResultError: the records are not all from the evaluation partition (ADR 0005)
            and ``allow_development`` is false. With it the report is a descriptive view and
            carries ``reportable=False``.
    """
    latest = _latest(records)
    partition = _partition_of(latest)
    if partition != "evaluation" and not allow_development:
        raise DevelopmentResultError(
            f"Los registros tienen partición {partition!r}: solo los resultados sobre series de "
            "evaluación entran en una tabla de resultados (ADR 0005). Usar la vista descriptiva "
            "para explorar."
        )

    warnings: list[str] = []
    conditions = sorted({str(r["condition"]) for r in latest})
    strata = sorted({_label(r) for r in latest})

    cells: list[CellSummary] = []
    scores_by_cell: dict[tuple[str, str, str], dict[str, tuple[float, int]]] = {}
    for condition in conditions:
        of_condition = [r for r in latest if str(r["condition"]) == condition]
        for stratum in (*strata, ALL_STRATA):
            subset = [r for r in of_condition if stratum == ALL_STRATA or _label(r) == stratum]
            if not subset:
                continue
            metrics: dict[str, RateEstimate | None] = {}
            for name, extract in EXTRACTORS.items():
                if name == "abstention_correct" and stratum != E4:
                    continue
                scores = _question_scores(subset, extract)
                scores_by_cell[(condition, stratum, name)] = scores
                metrics[name] = _estimate(scores, settings)
            judged_questions = len(scores_by_cell[(condition, stratum, "correct")])
            below = stratum != ALL_STRATA and judged_questions < min_questions
            if below:
                warnings.append(
                    f"Estrato {stratum} de {condition}: {judged_questions} preguntas juzgadas, "
                    f"menos del mínimo de {min_questions}."
                )
            cells.append(
                CellSummary(
                    condition=condition,
                    stratum=stratum,
                    records=len(subset),
                    questions=len({str(r["question_id"]) for r in subset}),
                    judge_failures=sum(1 for r in subset if _is_judge_failure(r)),
                    errors=sum(1 for r in subset if _is_error(r)),
                    citation_records_v1_excluded=sum(
                        1
                        for r in subset
                        if not _is_error(r)
                        and not _abstained(r)
                        and _label(r) != E4
                        and int(r.get("schema_version") or 1) < CITATION_SCHEMA_VERSION
                    ),
                    below_minimum=below,
                    metrics=metrics,
                    citation_width=(
                        None if questions is None else citation_width_summary(subset, questions)
                    ),
                )
            )

    v1 = sum(c.citation_records_v1_excluded for c in cells if c.stratum == ALL_STRATA)
    if v1:
        warnings.append(
            f"{v1} registros de esquema v1 quedan fuera de las métricas de citación: llevan la "
            "regla retirada (ADR 0009); reevaluarlos con `rescore_citation` antes de incluirlos."
        )
    short = sum(
        1
        for scores in (scores_by_cell[(c, ALL_STRATA, "correct")] for c in conditions)
        for _, n in scores.values()
        if n < min_runs
    )
    if short:
        warnings.append(
            f"{short} combinaciones pregunta-condición tienen menos de {min_runs} corridas "
            "juzgadas."
        )

    comparisons = _compare(cells, scores_by_cell, strata, settings, warnings)
    return AnalysisReport(
        partition=partition,
        reportable=partition == "evaluation",
        settings=settings,
        cells=tuple(cells),
        comparisons=tuple(comparisons),
        warnings=tuple(warnings),
    )


def _compare(
    cells: Sequence[CellSummary],
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]],
    strata: Sequence[str],
    settings: IntervalSettings,
    warnings: list[str],
) -> list[Comparison]:
    present = {c.condition for c in cells}
    for needed in (PRIMARY_CONDITION, PRIMARY_BASELINE):
        if needed not in present:
            warnings.append(
                f"Falta la condición {needed}: no hay comparación principal "
                f"{PRIMARY_CONDITION} frente a {PRIMARY_BASELINE}."
            )
    by_key = {(c.condition, c.stratum): c for c in cells}
    results: list[Comparison] = []
    for a, b in SECONDARY_PAIRS:
        if a not in present or b not in present:
            continue
        for stratum in (*strata, ALL_STRATA):
            cell_a, cell_b = by_key.get((a, stratum)), by_key.get((b, stratum))
            if cell_a is None or cell_b is None:
                continue
            for metric in COMPARED_METRICS:
                comparison = _paired(
                    a, b, stratum, metric, cell_a, cell_b, scores_by_cell, settings
                )
                if comparison is not None:
                    results.append(comparison)
    return results


def _paired(
    a: str,
    b: str,
    stratum: str,
    metric: str,
    cell_a: CellSummary,
    cell_b: CellSummary,
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]],
    settings: IntervalSettings,
) -> Comparison | None:
    scores_a = scores_by_cell[(a, stratum, metric)]
    scores_b = scores_by_cell[(b, stratum, metric)]
    est_a, est_b = cell_a.metrics.get(metric), cell_b.metrics.get(metric)
    shared = sorted(set(scores_a) & set(scores_b))
    if not shared or est_a is None or est_b is None:
        return None
    diffs = [scores_a[q][0] - scores_b[q][0] for q in shared]
    ci = bootstrap_mean_interval(diffs, settings)
    if intervals_disjoint_above((est_a.lower, est_a.upper), (est_b.lower, est_b.upper)):
        direction = "a_above"
    elif intervals_disjoint_above((est_b.lower, est_b.upper), (est_a.lower, est_a.upper)):
        direction = "b_above"
    else:
        direction = "overlap"
    return Comparison(
        primary=(a, b, stratum, metric)
        == (PRIMARY_CONDITION, PRIMARY_BASELINE, PRIMARY_STRATUM, PRIMARY_METRIC),
        condition_a=a,
        condition_b=b,
        stratum=stratum,
        metric=metric,
        n_pairs=len(shared),
        difference=ci.point_estimate,
        difference_lower=ci.lower,
        difference_upper=ci.upper,
        interval_a=(est_a.lower, est_a.upper),
        interval_b=(est_b.lower, est_b.upper),
        direction=direction,
        criterion="supported" if ci.lower > 0.0 else "inconclusive",
        nonoverlap_criterion="supported" if direction == "a_above" else "inconclusive",
    )


def report_to_dict(report: AnalysisReport) -> dict[str, Any]:
    """The report as plain JSON-ready data, with the methodological notes next to the numbers."""
    return {
        "partition": report.partition,
        "reportable": report.reportable,
        "bootstrap": asdict(report.settings),
        "combination": COMBINATION_NOTE,
        "criterion_d16": CRITERION_NOTE,
        "cells": [asdict(c) for c in report.cells],
        "comparisons": [
            {**asdict(c), "intervals_overlap": c.intervals_overlap} for c in report.comparisons
        ],
        "warnings": list(report.warnings),
    }
