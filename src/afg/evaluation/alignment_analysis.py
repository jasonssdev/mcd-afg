"""Analysis helpers for the Experiment A alignment choices (issue #99).

Pure functions that expose what :mod:`afg.evaluation.scoring` computes internally, so a
notebook can inspect it without re-implementing it:

* :func:`scored_matches` returns the matched (extracted, reference) pairs of one series under
  either alignment scope, flagging the pairs that cross meetings.
* :func:`meeting_cluster_intervals` (defined in :mod:`afg.evaluation.scoring`, where it is the
  primary interval of the pooled score, ADR 0011) is re-exported here for the notebooks.
* :func:`embedding_similarity` turns an embedding function into a
  :data:`~afg.evaluation.scoring.SimilarityFn` (cosine).

Nothing here changes a default of the scoring module. Decided in ADR 0011.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from afg.domain.decision import Decision
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import (
    AlignmentScope,
    ClusterIntervals,
    SimilarityFn,
    _align_series,
    meeting_cluster_intervals,
)

__all__ = [
    "ClusterIntervals",
    "ScoredMatch",
    "embedding_similarity",
    "meeting_cluster_intervals",
    "scored_matches",
]


@dataclass(frozen=True, slots=True)
class ScoredMatch:
    """One matched pair; ``crosses_meetings`` when the extracted decision is not from the
    reference decision's meeting (none of its origin meetings is)."""

    predicted: Decision
    reference: ReferenceDecision
    similarity: float
    crosses_meetings: bool


def scored_matches(
    reference: Sequence[ReferenceDecision],
    predicted: Sequence[Decision],
    similarity: SimilarityFn,
    *,
    tau: float,
    alignment_scope: AlignmentScope = "origin_meetings",
) -> tuple[ScoredMatch, ...]:
    """The matches :func:`~afg.evaluation.scoring.score_series` counts as TP, with the pairs."""
    accepted, matches = _align_series(reference, predicted, similarity, tau, alignment_scope)
    return tuple(
        ScoredMatch(
            predicted=accepted[m.predicted_index],
            reference=reference[m.reference_index],
            similarity=m.similarity,
            crosses_meetings=(
                reference[m.reference_index].meeting_id
                not in accepted[m.predicted_index].origin_meetings
            ),
        )
        for m in matches
    )


def embedding_similarity(
    embed: Callable[[Sequence[str]], Sequence[Sequence[float]]],
) -> SimilarityFn:
    """Cosine similarity between the embeddings of two lists of texts."""

    def similarity(predicted: Sequence[str], reference: Sequence[str]) -> np.ndarray:
        def unit(texts: Sequence[str]) -> np.ndarray:
            vectors = np.asarray(embed(texts), dtype=float).reshape(len(texts), -1)
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            return vectors / np.where(norms == 0.0, 1.0, norms)

        return unit(predicted) @ unit(reference).T

    return similarity
