"""Values behind the result figures of the AFG2 video, read from the frozen final tables.

Nothing here computes a statistic: each function selects (and, for the latency, regroups) a
number already stored in ``reports/tables/final-*`` or returned by a tested report function, so
the notebook that draws the figures never types a figure by hand.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import pandas as pd

CONDITION_LABELS = {
    "C0": "Sin ayuda (C0)",
    "C1": "Búsqueda en el texto, RAG (C1)",
    "C2": "Base automática (C2)",
    "C3": "Base con decisiones humanas (C3)",
}
STRATUM_LABELS = {"E1": "Hecho puntual", "E2": "Estado vigente", "E3": "Evolución"}
STAGE_LABELS = {"extraccion": "Extracción", "recuperacion": "Recuperación", "sintesis": "Síntesis"}


def total_correctness(cells: pd.DataFrame) -> dict[str, float]:
    """Share of correct answers per condition over all strata (first run of each cell)."""
    total = cells[cells["stratum"] == "ALL"].drop_duplicates("condition")
    return {str(c): float(v) for c, v in zip(total["condition"], total["correct"], strict=True)}


def correctness_by_type(
    cells: pd.DataFrame,
    *,
    conditions: Sequence[str] = ("C1", "C2", "C3"),
    strata: Sequence[str] = ("E1", "E2", "E3"),
) -> dict[str, list[float]]:
    """Correct share per condition for each question type (E4 is left out on purpose).

    E4 has no answer in the corpus, so abstaining is correct and the stratum inflates the
    conditions that abstain more.
    """
    data = cells.drop_duplicates(["condition", "stratum"]).set_index(["condition", "stratum"])
    return {c: [float(data.loc[(c, s), "correct"]) for s in strata] for c in conditions}


def headline_point(
    headline: pd.DataFrame, *, tau: float, scope: str = "origin_meetings"
) -> dict[str, float]:
    """Precision, recall and F1 of Experiment A at a threshold and scope."""
    row = headline[(headline["tau"] == tau) & (headline["scope"] == scope)].iloc[0]
    return {name: float(row[name]) for name in ("precision", "recall", "f1")}


def failure_causes(
    stages: pd.DataFrame, *, condition: str = "C2", basis: str = "todas"
) -> tuple[dict[str, int], int]:
    """Failure count per pipeline stage and the total number of failures of one condition."""
    rows = stages[(stages["condition"] == condition) & (stages["basis"] == basis)]
    causes = {str(s): int(n) for s, n in zip(rows["stage"], rows["cases"], strict=True)}
    return causes, int(rows["n_failures"].iloc[0])


def answer_latency(cost: pd.DataFrame) -> dict[str, float]:
    """Mean seconds per answered query for each condition (the ``answer`` rows)."""
    rows = cost[cost["role"] == "answer"]
    conditions = rows["activity"].str.rsplit("/", n=1).str[-1].str.strip()
    return {str(c): float(v) for c, v in zip(conditions, rows["mean_seconds"], strict=True)}


def phase2_kappas(report: Iterable[Any]) -> dict[str, float]:
    """Cohen's kappa of existence and type in the Phase 2 group of a pooled agreement report.

    Raises:
        ValueError: if the report has no Phase 2 group.
    """
    group = next((g for g in report if g.scope == "phase 2"), None)
    if group is None:
        raise ValueError("the agreement report has no 'phase 2' group.")
    by_axis = {item.axis: float(item.kappa) for item in group.axes}
    return {axis: by_axis[axis] for axis in ("existence", "type")}
