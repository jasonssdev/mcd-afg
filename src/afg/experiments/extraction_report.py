"""Report of a stored Experiment A extraction run (OE2): the numbers behind the results table.

Reads the runs of ``reports/experiment-a/<run>/`` (:func:`~afg.experiments.extraction_runs.
load_extraction_runs`), scores every ``(series, run)`` at each threshold of ``tau_grid`` with
:func:`~afg.evaluation.scoring.score_series` and pools the scores with
:func:`~afg.evaluation.scoring.pool_scores`, which attaches the meeting-cluster bootstrap
intervals of ADR 0011 (the independent-decision intervals travel beside them as
``reference_intervals``). The report follows the reporting rules of the ADRs:

- ADR 0011: the primary alignment scope (``origin_meetings``) with the series-wide sensitivity
  (``series``) beside it; the majority role (``by_role``) with every role (``by_role_every_role``)
  beside it; the meeting-cluster interval with the reference interval beside it.
- ADR 0012: the full curve over ``tau_grid``, tau 0.70 as the principal point and 0.75 and
  0.80 as sensitivities, each with the null-coverage floor the ADR records.

Per threshold and scope the report carries the figures pooled over every series and run, the
same figures per series, and the per-run figures with their mean and standard deviation
(thesis section 5.8; the deviation is ``None`` with a single run). Nothing here computes an
embedding: the similarity is injected, as in :mod:`afg.evaluation.scoring`.

A result over development series is not reportable (ADR 0005): without ``descriptive`` the
builder raises :class:`~afg.evaluation.scoring.DevelopmentResultError`; with it the report is
flagged ``reportable: false``.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from afg.domain.decision import Decision
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import (
    AlignmentScope,
    IntervalSettings,
    PooledScore,
    RoleScore,
    SeriesScore,
    SimilarityFn,
    evidence_role_resolver,
    evidence_roles_resolver,
    pool_scores,
    score_series,
)
from afg.experiments.extraction_runs import ExtractionRun
from afg.extraction.runner import MIN_RUNS

__all__ = ["NULL_COVERAGE", "SCOPES", "build_extraction_report"]

SCOPES: tuple[AlignmentScope, ...] = ("origin_meetings", "series")
"""Primary scope first; ``series`` is the sensitivity analysis (ADR 0011)."""

NULL_COVERAGE: Mapping[float, float] = {0.70: 0.138, 0.75: 0.053, 0.80: 0.015}
"""Mean coverage of the null control per tau, as recorded in ADR 0012 (notebook 17, section 3.1)."""

_LANGUAGE = "en"


def _role_table(roles: Mapping[str, RoleScore]) -> dict[str, dict[str, Any]]:
    return {
        role: {
            "n_reference": s.n_reference,
            "n_covered": s.n_covered,
            "recall": s.recall,
            "n_predicted": s.n_predicted,
            "n_correct": s.n_correct,
            "precision": s.precision,
        }
        for role, s in sorted(roles.items())
    }


def _figures(pooled: PooledScore) -> dict[str, Any]:
    return {
        "tp": pooled.tp,
        "fp": pooled.fp,
        "fn": pooled.fn,
        "precision": pooled.precision,
        "recall": pooled.recall,
        "f1": pooled.f1,
        "intervals": {
            "precision": list(pooled.precision_interval),
            "recall": list(pooled.recall_interval),
            "f1": list(pooled.f1_interval),
        },
        "reference_intervals": {
            "precision": list(pooled.precision_interval_reference),
            "recall": list(pooled.recall_interval_reference),
            "f1": list(pooled.f1_interval_reference),
        },
        "n_clusters": pooled.n_clusters,
        "confidence_level": pooled.confidence_level,
        "interval_methods": dict(pooled.interval_methods),
        "reference_interval_methods": dict(pooled.reference_interval_methods),
    }


def _with_roles(pooled: PooledScore) -> dict[str, Any]:
    return {
        **_figures(pooled),
        "by_role": _role_table(pooled.by_role),
        "by_role_every_role": _role_table(pooled.by_role_every_role),
    }


def _mean_stdev(values: Sequence[float]) -> tuple[float, float | None]:
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else None)


def _across_runs(per_run: Sequence[tuple[int, PooledScore]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n_runs": len(per_run)}
    for name in ("precision", "recall", "f1"):
        mean, stdev = _mean_stdev([getattr(pooled, name) for _, pooled in per_run])
        result[f"{name}_mean"] = mean
        result[f"{name}_stdev"] = stdev
    return result


def build_extraction_report(
    *,
    run_name: str,
    runs: Sequence[ExtractionRun],
    reference_of: Callable[[str], Sequence[ReferenceDecision]],
    similarity: SimilarityFn,
    settings: IntervalSettings,
    tau_grid: Sequence[float],
    tau_principal: float,
    tau_sensitivity: Sequence[float],
    partition_of: Callable[[str], str],
    descriptive: bool = False,
    transcripts_dir: Path | None = None,
    reference_kinds: Mapping[str, str] | None = None,
    relations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The report of ``runs`` (all of one extraction run folder) as a JSON-ready dict.

    ``transcripts_dir`` enables the precision by role (the role of an extracted decision is
    read from the frozen turns of its evidence); without it only the reference side of the
    roles (recall) is reported. ``relations`` is the content of ``relaciones.json`` and is
    embedded as is.

    Raises:
        ValueError: ``tau_principal`` or a sensitivity is not in ``tau_grid``; no runs.
        DevelopmentResultError: not ``descriptive`` and the result is not over evaluation
            series only.
    """
    marked = (tau_principal, *tau_sensitivity)
    missing = [tau for tau in marked if tau not in tau_grid]
    if missing:
        raise ValueError(f"tau {missing} is not in the tau grid {list(tau_grid)}.")
    if not runs:
        raise ValueError(f"The run {run_name!r} has no runs to report.")

    decisions: dict[tuple[str, int], list[Decision]] = {
        (r.record["series_id"], r.run): [Decision(**d) for d in r.decisions] for r in runs
    }
    series_ids = sorted({series for series, _ in decisions})
    run_numbers = sorted({run for _, run in decisions})
    references = {series: reference_of(series) for series in series_ids}
    role_kwargs: dict[str, Any] = {}
    if transcripts_dir is not None:
        role_kwargs = {
            "predicted_role_of": evidence_role_resolver(transcripts_dir),
            "predicted_roles_of": evidence_roles_resolver(transcripts_dir),
        }

    def cell(tau: float, scope: AlignmentScope) -> tuple[dict[str, Any], PooledScore]:
        scores: dict[tuple[str, int], SeriesScore] = {
            key: score_series(
                key[0],
                references[key[0]],
                found,
                similarity,
                tau=tau,
                alignment_scope=scope,
                **role_kwargs,
            )
            for key, found in sorted(decisions.items())
        }

        def pool(selected: Sequence[SeriesScore]) -> PooledScore:
            return pool_scores(selected, settings=settings, partition_of=partition_of)

        pooled = pool(list(scores.values()))
        per_run = [
            (run, pool([s for (_, r), s in scores.items() if r == run])) for run in run_numbers
        ]
        content = {
            "pooled": _with_roles(pooled),
            "by_series": {
                series: _with_roles(pool([s for (sid, _), s in scores.items() if sid == series]))
                for series in series_ids
            },
            "per_run": [{"run": run, **_figures(p)} for run, p in per_run],
            "across_runs": _across_runs(per_run),
        }
        return content, pooled

    curve: list[dict[str, Any]] = []
    partitions: set[str] = set()
    for tau in tau_grid:
        entry: dict[str, Any] = {
            "tau": tau,
            "role": "principal"
            if tau == tau_principal
            else ("sensitivity" if tau in tau_sensitivity else None),
            "null_coverage": NULL_COVERAGE.get(round(tau, 2)),
        }
        for scope in SCOPES:
            entry[scope], pooled = cell(tau, scope)
            partitions.add(pooled.partition)
        curve.append(entry)

    partition = partitions.pop() if len(partitions) == 1 else "mixed"
    reportable = partition == "evaluation"
    if not reportable and not descriptive:
        from afg.evaluation.scoring import DevelopmentResultError

        raise DevelopmentResultError(
            f"Result over {', '.join(series_ids)} has partition {partition!r}: only results "
            "over evaluation series enter a results table (ADR 0005)."
        )

    runs_per_series: dict[str, int] = defaultdict(int)
    for series, _ in decisions:
        runs_per_series[series] += 1
    warnings = [
        f"{series}: {count} corrida(s), por debajo del mínimo de {MIN_RUNS} corridas "
        "(sección 5.8 de la tesis); la dispersión entre corridas no es confiable."
        for series, count in sorted(runs_per_series.items())
        if count < MIN_RUNS
    ]
    first = runs[0]
    return {
        "run_name": run_name,
        "partition": partition,
        "reportable": reportable,
        "descriptive": descriptive,
        "language": _LANGUAGE,
        "reference_kinds": dict(reference_kinds or {}),
        "series": series_ids,
        "runs": run_numbers,
        "runs_per_series": dict(sorted(runs_per_series.items())),
        "tau_principal": tau_principal,
        "tau_sensitivity": list(tau_sensitivity),
        "tau_grid": list(tau_grid),
        "alignment_scope_principal": SCOPES[0],
        "interval": {
            "primary": "meeting-cluster bootstrap",
            "reference": "wilson (precision, recall); bootstrap over decisions (f1)",
            "resamples": settings.n_resamples,
            "confidence_level": settings.confidence_level,
            "seed": settings.seed,
        },
        "provenance": {
            "git_commit": first.manifest.get("git_commit"),
            "git_dirty": first.manifest.get("git_dirty"),
            "created_at": first.manifest.get("created_at"),
            "openkos": first.manifest.get("openkos"),
        },
        "warnings": warnings,
        "curve": curve,
        "relations": None
        if relations is None
        else {
            "source": "relaciones.json",
            "tau": relations.get("tau"),
            "alignment_scope": relations.get("alignment_scope"),
            "n_errors": relations.get("n_errors"),
            "reference_kinds": relations.get("reference_kinds"),
            "pooled": relations.get("pooled"),
        },
    }
