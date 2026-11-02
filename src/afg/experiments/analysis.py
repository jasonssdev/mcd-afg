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

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any

from afg.domain.question import Question
from afg.evaluation.metrics import BootstrapCI, bootstrap_ci
from afg.evaluation.scoring import DevelopmentResultError, IntervalSettings
from afg.experiments.summary import CitationWidthSummary, citation_width_summary

__all__ = [
    "ALL_STRATA",
    "CLOSED_BOOK",
    "H2_NOTE",
    "H4_METRIC",
    "H4_METRICS",
    "H4_NOTE",
    "H4_UPPER_BOUND_METRIC",
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
H4_METRIC = "outdated_among_answered"
H4_UPPER_BOUND_METRIC = "wrong_among_answered"
H4_METRICS: tuple[str, ...] = (H4_METRIC, H4_UPPER_BOUND_METRIC)
H4_STRATUM = "E3"
H4_PAIRS: tuple[tuple[str, str], ...] = (("C1", "C2"), ("C1", "C3"))
SECONDARY_PAIRS: tuple[tuple[str, str], ...] = (("C2", "C1"), ("C2", "C3"))
CLOSED_BOOK = "C0"
DESCRIPTIVE_PAIRS: tuple[tuple[str, str], ...] = (("C1", CLOSED_BOOK), ("C2", CLOSED_BOOK))
"""ADR 0019: C1 - C0 is the value of retrieval and C2 - C0 that of the compiled base, over the
answer correctness only. Descriptive: they decide none of H1-H4 nor D16."""
DESCRIPTIVE_METRICS: tuple[str, ...] = ("correct",)
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
    "original) se informa aparte como robustez y no reemplaza al criterio principal. Desde el "
    "2026-11-02 el veredicto exige el mínimo prerregistrado de preguntas juzgadas por condición "
    "en el estrato; por debajo se informa insufficient_sample (muestra insuficiente) con las "
    "cifras a la vista."
)

H4_NOTE = (
    "H4 (ADR 0017): proporción de preguntas E3 respondidas (sin abstención) cuya respuesta el "
    "juez marca como desactualizada, es decir, que presenta como vigente el estado anterior de "
    "la decisión (columna superseded_answer del banco). Por condición con su intervalo; "
    "C1 - C2 y C1 - C3 se aparean por pregunta respondida en ambas y H4 se respalda si el "
    "intervalo de la diferencia queda por encima de 0. La tasa de respuestas incorrectas entre "
    "las respondidas se informa como cota superior, no como H4. Desde el 2026-11-02, con menos "
    "del mínimo prerregistrado de preguntas juzgadas en E3 en alguna de las dos condiciones, el "
    "veredicto es insufficient_sample (muestra insuficiente)."
)

DESCRIPTIVE_NOTE = (
    "C0 (ADR 0019): el mismo generador sin ningún contexto recuperado, referencia sin "
    "recuperación. C1 - C0 se lee como el valor de recuperar texto y C2 - C0 como el de la base "
    "compilada frente a no recuperar nada; se calculan sobre la corrección, aparean por pregunta "
    "y son descriptivas: no deciden D16 ni H1-H4. C0 no cita ni aporta evidencia, así que sus "
    "métricas de evidencia y de citación no aplican y se informan como no disponibles; una "
    "respuesta de C0 que acierta no prueba conocimiento previo del corpus ni lo descarta."
)

H2_RELATION_STRATUM = "E3"
H2_DECISION_STRATUM = "E1"
H2_NOTE = (
    "H2 (ADR 0018): brecha de corrección C3 - C2 por pregunta (pareada por pregunta) en E3, "
    "preguntas de relación, menos la misma brecha en E1, preguntas de decisión. El intervalo "
    "bootstrap de la diferencia de brechas remuestrea de forma independiente las preguntas de "
    "E1 y de E3. H2 se respalda si el intervalo queda por encima de 0, es contraria si queda "
    "por debajo y en otro caso es no concluyente. E2 no entra: pregunta qué versión prevalece, "
    "lo que ya requiere la relación entre versiones. Desde el 2026-11-02, con menos del mínimo "
    "prerregistrado de preguntas juzgadas en E1 o E3 (en C2 o C3) el veredicto es "
    "insufficient_sample (muestra insuficiente) y las cifras se muestran sin veredicto."
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
    """Primary verdict: ``supported`` only when the paired difference interval is above 0;
    ``insufficient_sample`` below the pre-registered minimum of judged questions."""
    nonoverlap_criterion: str
    """Robustness: ``supported`` only when ``a_above``; every other outcome is ``inconclusive``."""
    descriptive: bool = False
    """A comparison against C0 (ADR 0019): secondary, it never decides D16 or H1-H4."""
    sample_sufficient: bool = True
    """False when a stratum of either condition has fewer judged questions than the
    pre-registered minimum: both verdicts are then ``insufficient_sample`` (2026-11-02)."""

    @property
    def intervals_overlap(self) -> bool:
        return self.direction == "overlap"


@dataclass(frozen=True, slots=True)
class H2Result:
    """H2: the C3 - C2 correctness gap on E3 (relations) minus the gap on E1 (decisions)."""

    verdict: str
    """``supported`` / ``contrary`` / ``inconclusive`` / ``not_computable`` /
    ``insufficient_sample`` (a stratum of C2 or C3 below the pre-registered minimum)."""
    reason: str | None
    gap_e1: float | None
    gap_e3: float | None
    difference: float | None
    difference_lower: float | None
    difference_upper: float | None
    n_e1: int
    n_e3: int


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    partition: str
    reportable: bool
    settings: IntervalSettings
    cells: tuple[CellSummary, ...]
    comparisons: tuple[Comparison, ...]
    warnings: tuple[str, ...]
    h2: H2Result


INSUFFICIENT_SAMPLE = "insufficient_sample"


def verdict_label(verdict: str) -> str:
    """Console wording of a verdict; the too-small-sample case reads in Spanish (2026-11-02)."""
    return "muestra insuficiente" if verdict == INSUFFICIENT_SAMPLE else verdict


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
        if name == "evidence_supported" and record.get("condition") == CLOSED_BOOK:
            return None
        value = record["verdict"].get(name)
        return None if value is None else float(bool(value))

    return extract


def _citation_usable(record: Record) -> bool:
    return (
        record.get("condition") != CLOSED_BOOK
        and not _is_error(record)
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


def _outdated_among_answered(record: Record) -> float | None:
    """H4: 1 when a judged, non-abstaining answer states the superseded version as current.

    Abstentions never enter the denominator (ADR 0014) and a record judged without the flag
    (prompt version 1: the question has no superseded answer) has no value (ADR 0017).
    """
    if _abstained(record):
        return None
    return _verdict_flag("outdated")(record)


def _wrong_among_answered(record: Record) -> float | None:
    """Upper bound of H4: 1 when a judged, non-abstaining answer is incorrect, 0 when correct.

    The judge of the correctness does not say WHY an answer is wrong, so this counts every
    incorrect answered E3 question: it bounds the outdated rate from above (an outdated answer
    is also incorrect against the reference) and is reported next to it, never in its place.
    """
    if _abstained(record):
        return None
    correct = _verdict_flag("correct")(record)
    return None if correct is None else 1.0 - correct


EXTRACTORS: dict[str, Extractor] = {
    "correct": _verdict_flag("correct"),
    "evidence_supported": _verdict_flag("evidence_supported"),
    "citation_correct": _citation_correct,
    "citation_precision": _citation_precision,
    "abstention_correct": _abstention_correct,
    "outdated_among_answered": _outdated_among_answered,
    "wrong_among_answered": _wrong_among_answered,
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
                if name in H4_METRICS and stratum != H4_STRATUM:
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
                        None
                        if questions is None or condition == CLOSED_BOOK
                        else citation_width_summary(subset, questions)
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

    unflagged = sum(
        1
        for r in latest
        if _label(r) == H4_STRATUM
        and _is_judged(r)
        and not _abstained(r)
        and r["verdict"].get("outdated") is None
    )
    if unflagged:
        warnings.append(
            f"{unflagged} respuestas E3 respondidas se juzgaron sin el campo outdated (la "
            "pregunta no tiene superseded_answer): quedan fuera de H4."
        )
    comparisons = _compare(cells, scores_by_cell, strata, settings, warnings, min_questions)
    return AnalysisReport(
        partition=partition,
        reportable=partition == "evaluation",
        settings=settings,
        cells=tuple(cells),
        comparisons=tuple(comparisons),
        warnings=tuple(warnings),
        h2=_h2(scores_by_cell, settings, min_questions),
    )


def _compare(
    cells: Sequence[CellSummary],
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]],
    strata: Sequence[str],
    settings: IntervalSettings,
    warnings: list[str],
    min_questions: int,
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
                    a,
                    b,
                    stratum,
                    metric,
                    cell_a,
                    cell_b,
                    scores_by_cell,
                    settings,
                    min_questions=min_questions,
                )
                if comparison is not None:
                    results.append(comparison)
    for a, b in DESCRIPTIVE_PAIRS:
        if a not in present or b not in present:
            continue
        for stratum in (*strata, ALL_STRATA):
            cell_a, cell_b = by_key.get((a, stratum)), by_key.get((b, stratum))
            if cell_a is None or cell_b is None:
                continue
            for metric in DESCRIPTIVE_METRICS:
                reference = _paired(
                    a,
                    b,
                    stratum,
                    metric,
                    cell_a,
                    cell_b,
                    scores_by_cell,
                    settings,
                    min_questions=min_questions,
                    guard_sample=False,
                )
                if reference is not None:
                    results.append(replace(reference, descriptive=True))
    for a, b in H4_PAIRS:
        cell_a, cell_b = by_key.get((a, H4_STRATUM)), by_key.get((b, H4_STRATUM))
        if cell_a is None or cell_b is None:
            continue
        for metric in H4_METRICS:
            h4 = _paired(
                a,
                b,
                H4_STRATUM,
                metric,
                cell_a,
                cell_b,
                scores_by_cell,
                settings,
                min_questions=min_questions,
            )
            if h4 is not None:
                results.append(h4)
    return results


def _gap_differences(
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]], stratum: str
) -> list[float]:
    """Per question of ``stratum``, C3 minus C2 correctness (questions judged under both)."""
    c3 = scores_by_cell.get(("C3", stratum, "correct"), {})
    c2 = scores_by_cell.get(("C2", stratum, "correct"), {})
    return [c3[q][0] - c2[q][0] for q in sorted(set(c3) & set(c2))]


def _h2(
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]],
    settings: IntervalSettings,
    min_questions: int,
) -> H2Result:
    """H2 of ADR 0018: percentile bootstrap of ``mean(E3 gaps) - mean(E1 gaps)``.

    E1 and E3 questions are resampled independently, with the seed, resamples and level of
    ``[evaluation]`` / ``[shared_budget]`` (the same machinery as every other interval).
    """
    e1 = _gap_differences(scores_by_cell, H2_DECISION_STRATUM)
    e3 = _gap_differences(scores_by_cell, H2_RELATION_STRATUM)
    if not e1 or not e3:
        missing = [
            name
            for name, gaps in ((H2_DECISION_STRATUM, e1), (H2_RELATION_STRATUM, e3))
            if not gaps
        ]
        return H2Result(
            verdict="not_computable",
            reason=f"Sin preguntas juzgadas en C3 y C2 a la vez en {', '.join(missing)}.",
            gap_e1=_mean(e1) if e1 else None,
            gap_e3=_mean(e3) if e3 else None,
            difference=None,
            difference_lower=None,
            difference_upper=None,
            n_e1=len(e1),
            n_e3=len(e3),
        )
    rng = random.Random(settings.seed)
    resampled = sorted(
        _mean([e3[rng.randrange(len(e3))] for _ in e3])
        - _mean([e1[rng.randrange(len(e1))] for _ in e1])
        for _ in range(settings.n_resamples)
    )
    alpha = 1.0 - settings.confidence_level
    lower = resampled[max(0, int((alpha / 2) * settings.n_resamples))]
    upper = resampled[min(settings.n_resamples - 1, int((1 - alpha / 2) * settings.n_resamples))]
    verdict = "supported" if lower > 0.0 else ("contrary" if upper < 0.0 else "inconclusive")
    short = [
        f"{condition} en {stratum} ({n})"
        for stratum in (H2_DECISION_STRATUM, H2_RELATION_STRATUM)
        for condition in ("C2", "C3")
        if (n := len(scores_by_cell.get((condition, stratum, "correct"), {}))) < min_questions
    ]
    reason = None
    if short:
        verdict = "insufficient_sample"
        reason = (
            f"Muestra insuficiente: menos del mínimo prerregistrado de {min_questions} preguntas "
            f"juzgadas en {', '.join(short)}."
        )
    return H2Result(
        verdict=verdict,
        reason=reason,
        gap_e1=_mean(e1),
        gap_e3=_mean(e3),
        difference=_mean(e3) - _mean(e1),
        difference_lower=lower,
        difference_upper=upper,
        n_e1=len(e1),
        n_e3=len(e3),
    )


def _paired(
    a: str,
    b: str,
    stratum: str,
    metric: str,
    cell_a: CellSummary,
    cell_b: CellSummary,
    scores_by_cell: Mapping[tuple[str, str, str], dict[str, tuple[float, int]]],
    settings: IntervalSettings,
    *,
    min_questions: int,
    guard_sample: bool = True,
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
    sufficient = not (
        guard_sample
        and any(
            len(scores_by_cell[(condition, stratum, "correct")]) < min_questions
            for condition in (a, b)
        )
    )
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
        criterion=(
            "insufficient_sample"
            if not sufficient
            else ("supported" if ci.lower > 0.0 else "inconclusive")
        ),
        nonoverlap_criterion=(
            "insufficient_sample"
            if not sufficient
            else ("supported" if direction == "a_above" else "inconclusive")
        ),
        sample_sufficient=sufficient,
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
        "h2": {**asdict(report.h2), "note": H2_NOTE},
        "descriptive_note": DESCRIPTIVE_NOTE,
    }
