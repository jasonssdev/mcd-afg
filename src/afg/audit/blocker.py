"""Blocker operating-point sensitivity grid (thesis section 5.1 data audit).

Reproduces, as a queryable table, the exact grid that justified moving the blocker's
default operating point from ``(threshold=0.30, min_overlap_tokens=1)`` to
``(threshold=0.30, min_overlap_tokens=2)`` -- see ``afg.annotation.blocking`` module
docstring for the full argument and the hand-verified table this mirrors.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from afg.annotation.blocking import decisions_from_abstractive, generate_candidates
from afg.domain.decision import Decision
from afg.shared.paths import AMI_DIR

TURBO_BUTTON_PAIR: tuple[str, str] = ("IS1004c.elana.s.29", "IS1004d.elana.s.22")
"""The one hand-verified reversal pair (``afg.annotation.blocking`` module docstring),
used here as the recall control: a grid cell that loses this pair has tightened the
blocker past the point where it still catches a known true positive."""


def _load_decisions(ami_root: Path, series: Sequence[str]) -> list[Decision]:
    decisions: list[Decision] = []
    for series_id in series:
        decisions.extend(decisions_from_abstractive(ami_root, series_id))
    return decisions


def blocker_sensitivity(
    ami_root: Path = AMI_DIR,
    series: Sequence[str] = (),
    thresholds: Sequence[float] = (0.30,),
    min_overlaps: Sequence[int] = (1, 2),
) -> pd.DataFrame:
    """Candidate count at every ``(threshold, min_overlap_tokens)`` cell of the grid,
    over the decisions of ``series``, plus whether :data:`TURBO_BUTTON_PAIR` survives.

    Columns: ``threshold`` (float), ``min_overlap_tokens`` (int), ``n_candidates`` (int),
    ``pct_of_total_pairs`` (float, percentage of the full cross-meeting pair universe for
    ``series``), ``turbo_button_survives`` (bool).
    """
    decisions = _load_decisions(ami_root, series)
    total_pairs = len(generate_candidates(decisions, threshold=0.0, min_overlap_tokens=0))

    rows = []
    for threshold in thresholds:
        for min_overlap in min_overlaps:
            candidates = generate_candidates(
                decisions, threshold=threshold, min_overlap_tokens=min_overlap
            )
            candidate_ids = {(c.earlier_decision_id, c.later_decision_id) for c in candidates}
            rows.append(
                {
                    "threshold": threshold,
                    "min_overlap_tokens": min_overlap,
                    "n_candidates": len(candidates),
                    "pct_of_total_pairs": (
                        (len(candidates) / total_pairs * 100) if total_pairs else 0.0
                    ),
                    "turbo_button_survives": TURBO_BUTTON_PAIR in candidate_ids,
                }
            )

    df = pd.DataFrame(
        rows,
        columns=[
            "threshold",
            "min_overlap_tokens",
            "n_candidates",
            "pct_of_total_pairs",
            "turbo_button_survives",
        ],
    )
    return df.astype(
        {
            "threshold": "float64",
            "min_overlap_tokens": "int64",
            "n_candidates": "int64",
            "pct_of_total_pairs": "float64",
            "turbo_button_survives": "bool",
        }
    )
