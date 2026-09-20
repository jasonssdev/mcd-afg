"""Inter-annotator agreement and adjudication for OE1 (thesis section 3).

Thesis section 3 (OE1): double annotation on at least 25% of series, Cohen's kappa
reported, documented adjudication protocol. Given the negative-kappa precedent between
prior decision-annotation schemes (thesis section 1.4), this project does not assume
agreement will be high -- it measures it and adjudicates disagreements explicitly.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from afg.evaluation.metrics import cohen_kappa

# Manual de anotacion section 6 (Tarea D): the closed relation-type label set includes
# "no_relacionada", which means "the blocker was wrong, there is no link" -- a pair with
# this label is, by definition, not an existing link. "existence" below is derived from
# this exact rule, never from a separate column.
_NO_RELATION_LABEL = "no_relacionada"


class AdjudicationEntry(BaseModel):
    """One disagreement between two annotators, pending (or recording) adjudication."""

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(description="Id of the decision pair / relation being labeled.")
    annotator_a: str
    label_a: str
    annotator_b: str
    label_b: str
    resolution: str | None = Field(
        default=None, description="Final label after adjudication; None while unresolved."
    )
    adjudicator: str | None = Field(default=None)


def compute_agreement(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa between two annotators' labels over the same items, in order.

    Delegates to :func:`afg.evaluation.metrics.cohen_kappa` so there is exactly one
    implementation of the statistic in this codebase.
    """
    return cohen_kappa(labels_a, labels_b)


def build_adjudication_log(
    item_ids: list[str],
    labels_a: list[str],
    labels_b: list[str],
    *,
    annotator_a: str,
    annotator_b: str,
) -> list[AdjudicationEntry]:
    """Build the adjudication log: one entry per item where the two annotators disagree.

    Items where both annotators agree are not included -- there is nothing to adjudicate.
    """
    if not (len(item_ids) == len(labels_a) == len(labels_b)):
        raise ValueError("item_ids, labels_a, and labels_b must have the same length.")

    return [
        AdjudicationEntry(
            item_id=item_id,
            annotator_a=annotator_a,
            label_a=label_a,
            annotator_b=annotator_b,
            label_b=label_b,
        )
        for item_id, label_a, label_b in zip(item_ids, labels_a, labels_b, strict=True)
        if label_a != label_b
    ]


def agreement_meets_threshold(kappa: float, *, threshold: float = 0.60) -> bool:
    """Whether a kappa value meets the reliability bar this project reports against.

    Thesis section 1.4 documents prior decision-annotation kappa in the 0.63-0.73 range
    (and, cautionarily, a negative kappa between two independent schemes on the same
    data). 0.60 is used here as a conventional "substantial agreement" cutoff
    (Landis & Koch, 1977), not a claim of thesis-specified reliability -- the thesis
    itself does not assume agreement and instead requires reporting the observed value.
    """
    return kappa >= threshold


# --- Task D: series-level agreement from candidate-pair CSVs (manual section 6) -----------


class AgreementInputError(RuntimeError):
    """Raised when the annotator CSVs required for `afg gold agreement` are missing or
    unusable (too few files, no items in common, malformed rows)."""


_AGREEMENT_CSV_COLUMNS = (
    "series_id",
    "annotator_a",
    "annotator_b",
    "axis",
    "n_items",
    "kappa",
    "disagreeing_pair_ids",
)


@dataclass(frozen=True, slots=True)
class SeriesAgreementResult:
    """Cohen's kappa for existence, relation type, and direction, computed independently.

    Manual section 6 (Tarea D) is explicit that these are three separate numbers, never one
    combined kappa -- ``existence_kappa`` and ``direction_kappa`` can each be perfect while
    the other is not (a pair both annotators agree exists can still have its direction
    disputed), and collapsing them into a single figure would hide exactly the H3 failure
    mode (inverted direction) this project measures.
    """

    series_id: str
    annotator_a: str
    annotator_b: str
    n_items: int
    existence_kappa: float
    existence_disagreements: tuple[str, ...]
    n_type_items: int
    type_kappa: float | None
    type_disagreements: tuple[str, ...]
    direction_kappa: float
    direction_disagreements: tuple[str, ...]


def _annotator_initials(path: Path) -> str:
    """Extract ``<initials>`` from ``<series>.candidates.<initials>.csv``."""
    stem = path.name.removesuffix(".csv")
    return stem.rsplit(".", 1)[-1]


def _read_candidate_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            pair_id = (row.get("pair_id") or "").strip()
            if pair_id:
                rows[pair_id] = row
    return rows


def compute_series_agreement(paths: Sequence[Path]) -> SeriesAgreementResult:
    """Compute the three independent kappas (manual section 6) from annotator CSV files.

    ``paths`` must contain at least two ``<series>.candidates.<initials>.csv`` files (Cohen's
    kappa is inherently pairwise); when more than two are found, the two with the
    lexicographically smallest filenames are used and the rest are ignored -- the CLI layer
    is responsible for surfacing that to the user.

    Three labelings are derived from each pair of matched rows (aligned on ``pair_id``,
    restricted to ids present in both files):

    - **existence**: ``"exists"`` if ``relation`` is set and not ``"no_relacionada"``, else
      ``"no_relation"`` -- computed over every matched pair.
    - **type**: the raw ``relation`` label -- computed ONLY over pairs where BOTH annotators
      marked existence as ``"exists"``, since a relation type is meaningless for a pair at
      least one annotator says has no relation at all. ``type_kappa`` is ``None`` (with
      ``n_type_items == 0``) when no such pair exists.
    - **direction**: the raw ``direction_ok`` value -- computed over every matched pair, since
      the manual has the annotator fill this column for every row, not only existing links.

    Raises:
        AgreementInputError: fewer than two input files, or the two selected files share no
            ``pair_id`` in common.
    """
    if len(paths) < 2:
        raise AgreementInputError(
            f"Need at least 2 annotator files to compute agreement, found {len(paths)}."
        )

    path_a, path_b = sorted(paths)[:2]
    annotator_a = _annotator_initials(path_a)
    annotator_b = _annotator_initials(path_b)
    rows_a = _read_candidate_rows(path_a)
    rows_b = _read_candidate_rows(path_b)

    common_ids = sorted(set(rows_a) & set(rows_b))
    if not common_ids:
        raise AgreementInputError(
            f"Annotator files {path_a.name!r} and {path_b.name!r} share no pair_id in common."
        )

    existence_a: list[str] = []
    existence_b: list[str] = []
    existence_disagreements: list[str] = []
    direction_a: list[str] = []
    direction_b: list[str] = []
    direction_disagreements: list[str] = []
    type_a: list[str] = []
    type_b: list[str] = []
    type_disagreements: list[str] = []

    for pair_id in common_ids:
        row_a, row_b = rows_a[pair_id], rows_b[pair_id]
        relation_a = (row_a.get("relation") or "").strip()
        relation_b = (row_b.get("relation") or "").strip()
        exists_a = "exists" if relation_a and relation_a != _NO_RELATION_LABEL else "no_relation"
        exists_b = "exists" if relation_b and relation_b != _NO_RELATION_LABEL else "no_relation"
        existence_a.append(exists_a)
        existence_b.append(exists_b)
        if exists_a != exists_b:
            existence_disagreements.append(pair_id)

        direction_value_a = (row_a.get("direction_ok") or "").strip().lower()
        direction_value_b = (row_b.get("direction_ok") or "").strip().lower()
        direction_a.append(direction_value_a)
        direction_b.append(direction_value_b)
        if direction_value_a != direction_value_b:
            direction_disagreements.append(pair_id)

        if exists_a == "exists" and exists_b == "exists":
            type_a.append(relation_a)
            type_b.append(relation_b)
            if relation_a != relation_b:
                type_disagreements.append(pair_id)

    existence_kappa = cohen_kappa(existence_a, existence_b)
    direction_kappa = cohen_kappa(direction_a, direction_b)
    type_kappa = cohen_kappa(type_a, type_b) if type_a else None

    return SeriesAgreementResult(
        series_id=path_a.name.split(".", 1)[0],
        annotator_a=annotator_a,
        annotator_b=annotator_b,
        n_items=len(common_ids),
        existence_kappa=existence_kappa,
        existence_disagreements=tuple(existence_disagreements),
        n_type_items=len(type_a),
        type_kappa=type_kappa,
        type_disagreements=tuple(type_disagreements),
        direction_kappa=direction_kappa,
        direction_disagreements=tuple(direction_disagreements),
    )


def write_agreement_csv(result: SeriesAgreementResult, out_path: Path) -> Path:
    """Write the three independent kappas (existence/type/direction) to ``out_path``.

    One row per axis, never a combined row -- see :class:`SeriesAgreementResult`.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_AGREEMENT_CSV_COLUMNS)
        writer.writerow(
            [
                result.series_id,
                result.annotator_a,
                result.annotator_b,
                "existence",
                result.n_items,
                result.existence_kappa,
                ";".join(result.existence_disagreements),
            ]
        )
        writer.writerow(
            [
                result.series_id,
                result.annotator_a,
                result.annotator_b,
                "type",
                result.n_type_items,
                result.type_kappa if result.type_kappa is not None else "",
                ";".join(result.type_disagreements),
            ]
        )
        writer.writerow(
            [
                result.series_id,
                result.annotator_a,
                result.annotator_b,
                "direction",
                result.n_items,
                result.direction_kappa,
                ";".join(result.direction_disagreements),
            ]
        )
    return out_path
