"""Tests for the amortized break-even point (thesis section 5.6)."""

from __future__ import annotations

import pytest

from afg.evaluation.amortization import break_even_queries


class TestBreakEvenQueries:
    def test_returns_none_when_structured_query_not_cheaper(self) -> None:
        assert (
            break_even_queries(compile_cost=10.0, structured_query_cost=1.0, rag_query_cost=1.0)
            is None
        )
        assert (
            break_even_queries(compile_cost=10.0, structured_query_cost=2.0, rag_query_cost=1.0)
            is None
        )

    def test_known_break_even_point(self) -> None:
        # compile=100, structured=1, rag=6 -> n > 100/5 = 20
        result = break_even_queries(
            compile_cost=100.0, structured_query_cost=1.0, rag_query_cost=6.0
        )
        assert result == pytest.approx(20.0)

    def test_zero_compile_cost_breaks_even_immediately(self) -> None:
        result = break_even_queries(compile_cost=0.0, structured_query_cost=1.0, rag_query_cost=2.0)
        assert result == pytest.approx(0.0)

    def test_negative_cost_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            break_even_queries(compile_cost=-1.0, structured_query_cost=1.0, rag_query_cost=2.0)
