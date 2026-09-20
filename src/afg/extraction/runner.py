"""Repeated-run variance reporting for LLM extraction (thesis section 5.8).

Thesis section 5.8: LLM extraction is not deterministic even at low temperature. Each
configuration must be run at least 3 times, reporting mean and dispersion rather than a
single run. This module implements that aggregation generically over any
:class:`~afg.extraction.protocol.Extractor`, so it is fully testable with a fake extractor
and does not depend on the corpus or OpenKOS being available.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from afg.extraction.protocol import ExtractionResult, Extractor

MIN_RUNS = 3


@dataclass(frozen=True, slots=True)
class RunVariance:
    """Mean and dispersion of extraction counts across repeated runs."""

    n_runs: int
    decision_counts: tuple[int, ...]
    relation_counts: tuple[int, ...]
    mean_decision_count: float
    stdev_decision_count: float
    mean_relation_count: float
    stdev_relation_count: float


def run_repeated(
    extractor: Extractor, meeting_id: str, transcript: str, *, n_runs: int = MIN_RUNS
) -> tuple[list[ExtractionResult], RunVariance]:
    """Run ``extractor`` ``n_runs`` times over the same input and summarize variance.

    Raises:
        ValueError: if ``n_runs`` is below :data:`MIN_RUNS` -- thesis section 5.8 requires
            a minimum of three runs per configuration; fewer would silently under-report
            variance.
    """
    if n_runs < MIN_RUNS:
        raise ValueError(
            f"n_runs={n_runs} is below the thesis section 5.8 minimum of {MIN_RUNS} runs "
            "per configuration."
        )

    results = [extractor.extract(meeting_id, transcript) for _ in range(n_runs)]
    decision_counts = tuple(len(r.decisions) for r in results)
    relation_counts = tuple(len(r.relations) for r in results)

    variance = RunVariance(
        n_runs=n_runs,
        decision_counts=decision_counts,
        relation_counts=relation_counts,
        mean_decision_count=statistics.mean(decision_counts),
        stdev_decision_count=statistics.stdev(decision_counts) if n_runs > 1 else 0.0,
        mean_relation_count=statistics.mean(relation_counts),
        stdev_relation_count=statistics.stdev(relation_counts) if n_runs > 1 else 0.0,
    )
    return results, variance
