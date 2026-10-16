"""Counts behind the provisional viability estimate of E3 (notebook 01).

The notebook reads two small tables from ``data/interim/`` (the provisional development
adjudication and the by-eye verification of the pilot's claims) and reports how many rows are
real relations or confirmed claims. Those counts live here so the figures shown to the reader
are tested rather than computed inline in a cell.
"""

from __future__ import annotations

import pandas as pd

from afg.domain.relation import RelationType


def count_provisional_positives(adjudication: pd.DataFrame) -> tuple[int, int]:
    """Return ``(positives, total)`` of an adjudication table with a ``relation`` column.

    A positive is any pair whose ``relation`` is not ``no_relacionada``.
    """
    relation = adjudication["relation"]
    positives = int((relation != RelationType.NO_RELACIONADA.value).sum())
    return positives, len(adjudication)


def count_confirmed(verification: pd.DataFrame) -> tuple[int, int]:
    """Return ``(confirmed, total)`` of a verification table with a ``veredicto`` column."""
    confirmed = int((verification["veredicto"] == "confirmado").sum())
    return confirmed, len(verification)
