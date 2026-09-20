"""The alignment protocol (thesis section 5.4) -- the piece that decides whether OE2's
numbers mean anything.

An extracted decision will not match a gold decision verbatim. This module implements the
declared procedure for deciding correspondence, fully independent of any embedding
backend: it takes a precomputed similarity matrix (dependency injection), so it has no
dependency on how similarity was computed and is fully unit-testable.

Explicitly NOT implemented here (thesis section 5.4): PR-AUC and confusion matrices, which
presuppose a fixed-class classifier. The extraction system emits sets of natural-language
objects, not classifier scores.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

# Cost assigned to a (predicted, reference) pair whose similarity is below tau, so the
# Hungarian algorithm never selects it unless doing so is unavoidable (e.g. more
# predictions than references) -- and even then, such below-threshold picks are filtered
# out of the final match list.
_EXCLUDED_PAIR_COST = 1.0e6


@dataclass(frozen=True, slots=True)
class Match:
    """One matched (predicted, reference) pair."""

    predicted_index: int
    reference_index: int
    similarity: float


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    """Precision/recall/F1 at one similarity threshold tau."""

    tau: float
    matches: tuple[Match, ...]
    n_predicted: int
    n_reference: int
    precision: float
    recall: float
    f1: float


def align(similarity_matrix: np.ndarray, tau: float) -> AlignmentResult:
    """Align predicted decisions to reference decisions at one threshold ``tau``.

    ``similarity_matrix[i, j]`` is the cosine similarity between predicted decision ``i``
    and reference decision ``j`` (thesis section 5.4: computed over the (decision object,
    content) pair -- the embedding step happens before this function is called).

    Matching is one-to-one, resolved as a maximum-weight assignment (Hungarian algorithm),
    never greedy nearest-neighbour (thesis section 5.4, point 2): greedy matching would let
    several predictions claim the same reference decision.
    """
    if similarity_matrix.ndim != 2:
        raise ValueError("similarity_matrix must be 2-D (n_predicted x n_reference).")

    n_predicted, n_reference = similarity_matrix.shape

    if n_predicted == 0 or n_reference == 0:
        precision = 0.0 if n_predicted else 1.0
        recall = 0.0 if n_reference else 1.0
        f1 = 0.0 if (n_predicted or n_reference) else 1.0
        return AlignmentResult(
            tau=tau,
            matches=(),
            n_predicted=n_predicted,
            n_reference=n_reference,
            precision=precision,
            recall=recall,
            f1=f1,
        )

    cost = np.where(similarity_matrix >= tau, -similarity_matrix, _EXCLUDED_PAIR_COST)
    row_indices, col_indices = linear_sum_assignment(cost)

    matches = tuple(
        Match(
            predicted_index=int(r),
            reference_index=int(c),
            similarity=float(similarity_matrix[r, c]),
        )
        for r, c in zip(row_indices, col_indices, strict=True)
        if similarity_matrix[r, c] >= tau
    )

    true_positives = len(matches)
    precision = true_positives / n_predicted
    recall = true_positives / n_reference
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return AlignmentResult(
        tau=tau,
        matches=matches,
        n_predicted=n_predicted,
        n_reference=n_reference,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def align_over_tau_grid(
    similarity_matrix: np.ndarray, tau_grid: list[float]
) -> list[AlignmentResult]:
    """Align at every tau in ``tau_grid``, returning one result per threshold.

    Thesis section 5.4, point 4: F1 is reported as a curve over tau, never a single point.
    If the ordering between conditions changes across the grid, that must be declared in
    the written result -- this function only produces the curve, the declaration is a
    reporting step downstream.
    """
    return [align(similarity_matrix, tau) for tau in tau_grid]


def concordance(
    automatic_matches: set[tuple[int, int]], manual_matches: set[tuple[int, int]]
) -> float:
    """Agreement rate between the automatic alignment and a manual matching sample.

    Thesis section 5.4, point 3: the automatic protocol is validated against manual
    matching on a sample of at least 100 pairs; this computes the concordance (Jaccard-style
    agreement over the matched-pair sets) for that validation. Returns 1.0 when both sets
    are empty (vacuously identical); returns 0.0 when exactly one set is empty.
    """
    if not automatic_matches and not manual_matches:
        return 1.0
    union = automatic_matches | manual_matches
    if not union:
        return 1.0
    intersection = automatic_matches & manual_matches
    return len(intersection) / len(union)
