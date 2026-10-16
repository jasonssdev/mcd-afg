"""Blocker operating-point sensitivity grid (thesis section 5.1 data audit).

Reproduces, as a queryable table, the exact grid that justified moving the blocker's
default operating point from ``(threshold=0.30, min_overlap_tokens=1)`` to
``(threshold=0.30, min_overlap_tokens=2)`` -- see ``afg.annotation.blocking`` module
docstring for the full argument and the hand-verified table this mirrors.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from afg.annotation.blocking import decisions_from_abstractive, generate_candidates
from afg.domain.decision import Decision
from afg.shared.paths import AMI_DIR

TURBO_BUTTON_PAIR: tuple[str, str] = ("IS1004c.elana.s.29", "IS1004d.elana.s.22")
"""The one hand-verified reversal pair (``afg.annotation.blocking`` module docstring),
used here as the recall control: a grid cell that loses this pair has tightened the
blocker past the point where it still catches a known true positive.

Identified by ABSTRACTIVE SENTENCE id, not decision id. The pilot verified this pair by
reading those two sentences, so the sentence id is the stable anchor; decision ids are
derived from sentence position and would silently follow a renumbering."""


MINUTES_PER_PAIR: float = 1.5
"""Annotation effort per candidate pair, in minutes (notebook 00 section 4.1 and the
annotation plan); the hours quoted for the blocker funnel are ``pairs * this / 60``."""


def funnel_hours(counts: Sequence[int], minutes_per_pair: float = MINUTES_PER_PAIR) -> list[float]:
    """Annotation hours for each pair count of a funnel, at ``minutes_per_pair`` per pair."""
    return [n * minutes_per_pair / 60 for n in counts]


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
            candidate_ids = {(c.earlier_sentence_id, c.later_sentence_id) for c in candidates}
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


@dataclass(frozen=True, slots=True)
class CandidateFunnel:
    """The three stages of the blocker funnel over a set of series (ADR decision D9)."""

    total_pairs: int
    """Every cross-meeting pair of decisions within a series (the exhaustive universe)."""
    coefficient_candidates: int
    """Pairs that pass the overlap coefficient alone (``min_overlap_tokens = 1``)."""
    full_candidates: int
    """Pairs that pass the coefficient and share at least two tokens (the operating point)."""
    turbo_survives_coefficient: bool
    turbo_survives_full: bool

    @property
    def counts(self) -> tuple[int, int, int]:
        return (self.total_pairs, self.coefficient_candidates, self.full_candidates)


def candidate_funnel(
    ami_root: Path = AMI_DIR, series: Sequence[str] = (), threshold: float = 0.30
) -> CandidateFunnel:
    """Pair counts at each stage of the blocker, from the real blocking functions.

    Same numbers as :func:`blocker_sensitivity` at ``min_overlaps = (1, 2)``, plus the size of
    the exhaustive universe, loaded once.
    """
    decisions = _load_decisions(ami_root, series)
    total = len(generate_candidates(decisions, threshold=0.0, min_overlap_tokens=0))

    def stage(min_overlap: int) -> tuple[int, bool]:
        candidates = generate_candidates(
            decisions, threshold=threshold, min_overlap_tokens=min_overlap
        )
        ids = {(c.earlier_sentence_id, c.later_sentence_id) for c in candidates}
        return len(candidates), TURBO_BUTTON_PAIR in ids

    n_coefficient, turbo_coefficient = stage(1)
    n_full, turbo_full = stage(2)
    return CandidateFunnel(total, n_coefficient, n_full, turbo_coefficient, turbo_full)
