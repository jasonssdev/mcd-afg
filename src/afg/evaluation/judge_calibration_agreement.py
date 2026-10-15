"""Human-human agreement on the judge calibration set (thesis section 5.7).

The judge is calibrated against the labels of one person; a second person labels a seeded
sample independently so that the reference itself is shown to be reliable. This module builds
that second sheet reproducibly and computes Cohen's kappa per label column. The threshold is
the one in ``[judge.calibration]`` (the same bar as the judge-human check), passed in by the
caller, never repeated here. Labels are parsed with the calibration set's own parser.
"""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.evaluation.judge_calibration_set import CalibrationSetError, _parse_bool
from afg.evaluation.metrics import cohen_kappa
from afg.shared.csvio import open_csv_reader
from afg.shared.paths import JUDGE_CALIBRATION_DIR, REPORTS_DIR

SECOND_SHEET_PATH: Path = JUDGE_CALIBRATION_DIR / "calibracion-juez.segunda-etiqueta.csv"
AGREEMENT_PATH: Path = REPORTS_DIR / "judge-calibration" / "acuerdo-humano.json"

LABEL_COLUMNS: tuple[str, ...] = ("correct", "evidence_supported")
SECOND_SHEET_COLUMNS: tuple[str, ...] = (
    "id",
    "stratum",
    "question",
    "reference_answer",
    "answer_text",
    "pasaje_transcripcion",
    "archivos_transcripcion",
    *LABEL_COLUMNS,
)
DEFAULT_SAMPLE_SIZE = 15
DEFAULT_SAMPLE_SEED = 42


class AgreementError(ValueError):
    """The two label sets cannot be compared."""


class SecondSheetLabeledError(AgreementError):
    """Writing the second sheet would erase labels someone already entered."""


@dataclass(frozen=True, slots=True)
class ColumnAgreement:
    """Agreement of the two labelers on one label column."""

    column: str
    n_items: int
    n_agree: int
    kappa: float | None
    disagreements: tuple[str, ...]
    passes: bool


def read_label_rows(path: Path) -> list[dict[str, str]]:
    """Read a calibration or second-labeler CSV as raw rows (BOM tolerated)."""
    with open_csv_reader(path) as handle:
        return [{k: v or "" for k, v in row.items()} for row in csv.DictReader(handle)]


def _label(row: Mapping[str, str], column: str, *, who: str) -> bool:
    item_id = row["id"]
    try:
        value = _parse_bool(row.get(column, ""), column=column, item_id=item_id)
    except CalibrationSetError as exc:
        raise AgreementError(f"{who}: {exc}") from exc
    if value is None:
        raise AgreementError(f"{who}: item {item_id!r}: column {column!r} has no label.")
    return value


def compute_human_agreement(
    primary_rows: Sequence[Mapping[str, str]],
    second_rows: Sequence[Mapping[str, str]],
    *,
    min_kappa: float,
) -> tuple[ColumnAgreement, ...]:
    """Cohen's kappa between the primary and second labeler, per label column.

    Items are matched by ``id``; only the second labeler's items are compared.

    Raises:
        AgreementError: no second-labeler rows, an id missing from the primary set, or an
            empty or invalid label (the message names the item and the column).
    """
    if not second_rows:
        raise AgreementError("The second labeler has no rows.")
    primary = {row["id"]: row for row in primary_rows}
    unknown = [row["id"] for row in second_rows if row["id"] not in primary]
    if unknown:
        raise AgreementError(f"Second-labeler ids not in the primary set: {unknown}")
    results: list[ColumnAgreement] = []
    for column in LABEL_COLUMNS:
        ids = [row["id"] for row in second_rows]
        first = [_label(primary[i], column, who="primary") for i in ids]
        second = [_label(row, column, who="second labeler") for row in second_rows]
        disagreements = tuple(i for i, a, b in zip(ids, first, second, strict=True) if a != b)
        kappa = cohen_kappa(
            ["si" if v else "no" for v in first], ["si" if v else "no" for v in second]
        )
        value = None if kappa != kappa else kappa  # NaN: both labelers used a single class
        results.append(
            ColumnAgreement(
                column=column,
                n_items=len(ids),
                n_agree=len(ids) - len(disagreements),
                kappa=value,
                disagreements=disagreements,
                passes=value is not None and value >= min_kappa,
            )
        )
    return tuple(results)


def select_second_sheet_rows(
    primary_rows: Sequence[Mapping[str, str]], *, n: int, seed: int
) -> list[dict[str, str]]:
    """The seeded sample for the second labeler, labels blanked.

    Ids are sorted, shuffled with ``random.Random(seed)`` and the first ``n`` kept, so the
    sample does not depend on the row order of the primary file.
    """
    by_id = {row["id"]: row for row in primary_rows}
    if n > len(by_id):
        raise AgreementError(f"Cannot sample {n} items from {len(by_id)}.")
    ids = sorted(by_id)
    random.Random(seed).shuffle(ids)
    return [
        {
            column: ("" if column in LABEL_COLUMNS else by_id[i].get(column, ""))
            for column in SECOND_SHEET_COLUMNS
        }
        for i in ids[:n]
    ]


def write_second_sheet(
    path: Path, rows: Sequence[Mapping[str, str]], *, force: bool = False
) -> None:
    """Write the second-labeler sheet; refuse to erase a sheet that already has labels."""
    if path.exists() and not force:
        labeled = [
            row["id"]
            for row in read_label_rows(path)
            if any(row.get(column, "").strip() for column in LABEL_COLUMNS)
        ]
        if labeled:
            raise SecondSheetLabeledError(
                f"{path.name} already has labels ({len(labeled)} item(s)); use force to overwrite."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SECOND_SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def save_agreement(
    path: Path,
    agreements: Sequence[ColumnAgreement],
    *,
    min_kappa: float,
    labelers: Sequence[str],
) -> None:
    """Store the agreement so the notebook reads it without recomputing."""
    payload = {
        "min_kappa": min_kappa,
        "labelers": list(labelers),
        "columns": [
            {
                "column": a.column,
                "n_items": a.n_items,
                "n_agree": a.n_agree,
                "kappa": a.kappa,
                "disagreements": list(a.disagreements),
                "passes": a.passes,
            }
            for a in agreements
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_agreement(path: Path) -> tuple[tuple[ColumnAgreement, ...], float, tuple[str, ...]]:
    """Read what :func:`save_agreement` wrote: the columns, the threshold and the labelers."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    columns = tuple(
        ColumnAgreement(
            column=c["column"],
            n_items=int(c["n_items"]),
            n_agree=int(c["n_agree"]),
            kappa=None if c["kappa"] is None else float(c["kappa"]),
            disagreements=tuple(c["disagreements"]),
            passes=bool(c["passes"]),
        )
        for c in payload["columns"]
    )
    return columns, float(payload["min_kappa"]), tuple(payload["labelers"])
