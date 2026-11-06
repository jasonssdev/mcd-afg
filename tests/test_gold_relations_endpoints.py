"""Every gold relation of the evaluation series links decisions, never a ``compuesta`` parent.

A ``compuesta`` row is replaced by its child rows in the reference, so a relation that points
to the parent can neither be written into C3 nor aligned in Experiment A (issue #298).
"""

from __future__ import annotations

import csv

import pytest

from afg.evaluation.reference import resolve_reference
from afg.experiments.question_bank import evaluation_series
from afg.extraction.openkos.gold_bundle import load_gold_relations

_STATUS_COLUMNS = ("final_status", "status")


def _compuesta_ids(series_id: str) -> set[str]:
    path = resolve_reference(series_id).path
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    column = next(c for c in _STATUS_COLUMNS if rows and c in rows[0])
    return {row["decision_id"] for row in rows if row[column].strip() == "compuesta"}


@pytest.mark.parametrize("series_id", evaluation_series())
def test_no_gold_relation_points_to_a_compuesta_parent(series_id: str) -> None:
    compuesta = _compuesta_ids(series_id)
    offending = [
        f"{relation.earlier_id}>{relation.later_id}"
        for relation in load_gold_relations(series_id)
        if relation.earlier_id in compuesta or relation.later_id in compuesta
    ]
    assert offending == []
