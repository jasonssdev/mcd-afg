"""Counts behind the provisional viability estimate (notebook 01)."""

from __future__ import annotations

import pandas as pd
import pytest

from afg.audit.provisional import count_confirmed, count_provisional_positives


def test_positives_exclude_the_no_relacionada_label() -> None:
    adjudication = pd.DataFrame(
        {"relation": ["refina", "no_relacionada", "reafirma", "no_relacionada", "contradice"]}
    )

    assert count_provisional_positives(adjudication) == (3, 5)


def test_positives_of_an_empty_table() -> None:
    assert count_provisional_positives(pd.DataFrame({"relation": []})) == (0, 0)


def test_positives_require_the_relation_column() -> None:
    with pytest.raises(KeyError):
        count_provisional_positives(pd.DataFrame({"otra": ["x"]}))


def test_confirmed_counts_only_the_confirmado_verdict() -> None:
    verification = pd.DataFrame(
        {"veredicto": ["confirmado", "corregido", "confirmado", "descartado"]}
    )

    assert count_confirmed(verification) == (2, 4)
