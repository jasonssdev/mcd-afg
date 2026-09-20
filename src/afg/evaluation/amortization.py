"""Amortized break-even point (thesis section 5.6).

Replaces isolated latency comparisons: the real comparison is a high upfront investment
(compiling C2/C3) with cheap subsequent queries, against zero investment with expensive
repeated queries (RAG). The break-even point is the number of queries at which the
structured representation starts to win, and its absence -- when it never does -- is
itself a reportable result.
"""

from __future__ import annotations


def break_even_queries(
    compile_cost: float, structured_query_cost: float, rag_query_cost: float
) -> float | None:
    """Smallest ``n`` such that ``compile_cost + n * structured_query_cost < n * rag_query_cost``.

    Returns None when no break-even point exists, i.e. the structured query is not
    strictly cheaper per query than the RAG query -- compiling can never pay for itself
    under those costs, however many queries are run.

    Raises:
        ValueError: for a negative cost input, which is not a meaningful cost.
    """
    if compile_cost < 0 or structured_query_cost < 0 or rag_query_cost < 0:
        raise ValueError("Costs must be non-negative.")

    per_query_savings = rag_query_cost - structured_query_cost
    if per_query_savings <= 0:
        return None

    return compile_cost / per_query_savings
