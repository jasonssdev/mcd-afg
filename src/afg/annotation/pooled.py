"""Pooled inter-annotator agreement over several adjudicated series (thesis section 3, OE1).

Per-series kappas rest on 3 to 14 items and are unstable; the pooled kappa is ONE Cohen's
kappa per axis over the concatenated items of several series, never the mean of per-series
kappas. Items are built by the same functions as the per-series figures
(:func:`afg.annotation.agreement.series_axis_labels` for Task B,
:func:`afg.annotation.calibration.status_labels` for Task A), and every label is the
annotator's own, never the adjudicated verdict.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.annotation.adjudication import validate_adjudication
from afg.annotation.agreement import annotator_csvs, series_axis_labels
from afg.annotation.calibration import status_labels
from afg.annotation.workspace import AnnotationPlan, WorkspacePaths
from afg.evaluation.metrics import cohen_kappa
from afg.shared.csvio import open_csv_writer

__all__ = [
    "POOLED_AXES",
    "PooledAgreement",
    "PooledAxis",
    "pooled_agreement",
    "pooled_agreement_report",
    "write_pooled_csv",
]

POOLED_AXES = ("status", "existence", "type", "direction")
"""``status`` is the Task A diagnostic; the other three are the reportable Task B kappas."""

_CSV_COLUMNS = (
    "scope",
    "series",
    "axis",
    "n_items",
    "n_disagreements",
    "kappa",
    "percent_agreement",
)


@dataclass(frozen=True, slots=True)
class PooledAxis:
    """Pooled agreement on one axis; ``kappa`` is ``nan`` when it is undefined."""

    axis: str
    n_items: int
    n_disagreements: int
    kappa: float
    percent_agreement: float


@dataclass(frozen=True, slots=True)
class PooledAgreement:
    """Pooled agreement of one group of series (``overall``, ``phase 1``, ...)."""

    scope: str
    series: tuple[str, ...]
    axes: tuple[PooledAxis, ...]

    def axis(self, name: str) -> PooledAxis:
        for item in self.axes:
            if item.axis == name:
                return item
        raise KeyError(name)


def _pooled_axis(axis: str, labels_a: list[str], labels_b: list[str]) -> PooledAxis:
    n = len(labels_a)
    disagreements = sum(x != y for x, y in zip(labels_a, labels_b, strict=True))
    return PooledAxis(
        axis=axis,
        n_items=n,
        n_disagreements=disagreements,
        kappa=cohen_kappa(labels_a, labels_b) if n else math.nan,
        percent_agreement=(n - disagreements) / n if n else math.nan,
    )


def pooled_agreement(
    series_ids: Sequence[str], *, scope: str = "overall", paths: WorkspacePaths | None = None
) -> PooledAgreement:
    """One kappa per axis over the concatenated items of ``series_ids``.

    Raises:
        ValueError: no series given, or the series were not annotated by the same pair.
    """
    if not series_ids:
        raise ValueError("pooled_agreement needs at least one series.")
    workspace = paths or WorkspacePaths()
    pooled: dict[str, tuple[list[str], list[str]]] = {axis: ([], []) for axis in POOLED_AXES}
    annotators: set[tuple[str, str]] = set()
    for series_id in series_ids:
        (a, b), status_a, status_b = status_labels(series_id, paths=workspace)
        labels = series_axis_labels(
            annotator_csvs(workspace.relations_dir, series_id, "candidates")
        )
        annotators.update({(a, b), labels.annotators})
        for axis, (axis_a, axis_b) in {"status": (status_a, status_b), **labels.axes}.items():
            pooled[axis][0].extend(axis_a)
            pooled[axis][1].extend(axis_b)
    if len(annotators) != 1:
        raise ValueError(f"Cannot pool series annotated by different pairs: {sorted(annotators)}.")
    return PooledAgreement(
        scope=scope,
        series=tuple(series_ids),
        axes=tuple(_pooled_axis(axis, *pooled[axis]) for axis in POOLED_AXES),
    )


def pooled_agreement_report(
    plan: AnnotationPlan,
    *,
    paths: WorkspacePaths | None = None,
    is_complete: Callable[[str], bool] | None = None,
) -> tuple[PooledAgreement, ...]:
    """Pooled agreement overall and per phase, from the phases in ``config/annotation.toml``.

    Only series whose adjudication is complete (``validate_adjudication`` finds no issue)
    enter; a phase with no such series is omitted. ``is_complete`` overrides that check.
    """
    workspace = paths or WorkspacePaths()

    def complete(series_id: str) -> bool:
        return not validate_adjudication(series_id, paths=workspace)

    check = is_complete or complete
    groups = [
        ("phase 1", [s for s in plan.phase1_series if check(s)]),
        ("phase 2", [s for s in plan.phase2_series if check(s)]),
    ]
    overall = [s for _, members in groups for s in members]
    if not overall:
        return ()
    report = [pooled_agreement(overall, scope="overall", paths=workspace)]
    report += [pooled_agreement(m, scope=name, paths=workspace) for name, m in groups if m]
    return tuple(report)


def write_pooled_csv(report: Sequence[PooledAgreement], out_path: Path) -> Path:
    """Write one row per scope and axis to ``out_path``."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(out_path, encoding="utf-8") as writer:
        writer.writerow(_CSV_COLUMNS)
        for group in report:
            for item in group.axes:
                writer.writerow(
                    [
                        group.scope,
                        ";".join(group.series),
                        item.axis,
                        item.n_items,
                        item.n_disagreements,
                        item.kappa,
                        item.percent_agreement,
                    ]
                )
    return out_path
