"""Tests for the alignment protocol (thesis section 5.4)."""

from __future__ import annotations

import numpy as np
import pytest

from afg.evaluation.alignment import align, align_over_tau_grid, concordance


class TestAlign:
    def test_perfect_diagonal_match(self) -> None:
        similarity = np.eye(3)
        result = align(similarity, tau=0.5)

        assert len(result.matches) == 3
        assert result.precision == pytest.approx(1.0)
        assert result.recall == pytest.approx(1.0)
        assert result.f1 == pytest.approx(1.0)

    def test_one_to_one_not_greedy(self) -> None:
        # Two predictions both resemble reference 0 strongly, but only one reference
        # exists that prediction 1 could otherwise match; the Hungarian assignment must
        # not let both predictions claim reference 0.
        similarity = np.array(
            [
                [0.95, 0.10],
                [0.90, 0.85],
            ]
        )
        result = align(similarity, tau=0.5)

        matched_references = [m.reference_index for m in result.matches]
        assert len(matched_references) == len(set(matched_references)), "matches must be one-to-one"
        assert len(result.matches) == 2

    def test_below_threshold_pairs_are_excluded(self) -> None:
        similarity = np.array([[0.1]])
        result = align(similarity, tau=0.5)

        assert result.matches == ()
        assert result.precision == 0.0
        assert result.recall == 0.0

    def test_empty_predicted_set(self) -> None:
        similarity = np.zeros((0, 3))
        result = align(similarity, tau=0.5)

        assert result.n_predicted == 0
        assert result.n_reference == 3
        assert result.recall == 0.0

    def test_empty_reference_set(self) -> None:
        similarity = np.zeros((2, 0))
        result = align(similarity, tau=0.5)

        assert result.n_reference == 0
        assert result.precision == 0.0

    def test_rejects_non_2d_input(self) -> None:
        with pytest.raises(ValueError, match="2-D"):
            align(np.zeros(3), tau=0.5)


class TestAlignOverTauGrid:
    def test_returns_one_result_per_tau(self) -> None:
        similarity = np.eye(2)
        tau_grid = [0.1, 0.5, 0.9]

        results = align_over_tau_grid(similarity, tau_grid)

        assert [r.tau for r in results] == tau_grid

    def test_f1_is_monotonic_non_increasing_as_tau_rises_on_this_matrix(self) -> None:
        similarity = np.array([[0.9, 0.0], [0.0, 0.4]])
        tau_grid = [0.1, 0.5, 0.95]

        results = align_over_tau_grid(similarity, tau_grid)

        f1_values = [r.f1 for r in results]
        assert f1_values == sorted(f1_values, reverse=True)


class TestConcordance:
    def test_identical_sets_is_perfect(self) -> None:
        matches = {(0, 0), (1, 1)}
        assert concordance(matches, matches) == pytest.approx(1.0)

    def test_disjoint_sets_is_zero(self) -> None:
        assert concordance({(0, 0)}, {(1, 1)}) == pytest.approx(0.0)

    def test_both_empty_is_perfect(self) -> None:
        assert concordance(set(), set()) == pytest.approx(1.0)

    def test_partial_overlap(self) -> None:
        automatic = {(0, 0), (1, 1), (2, 2)}
        manual = {(0, 0), (1, 1), (3, 3)}
        # intersection = 2, union = 4
        assert concordance(automatic, manual) == pytest.approx(0.5)
