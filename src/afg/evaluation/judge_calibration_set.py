"""The judge calibration set: schema and loader (thesis section 5.7).

Each item pairs a question and a system answer with the labels humans gave it; the judge
candidates are scored against those labels (:mod:`afg.evaluation.judge_calibration`). The
labels are always human. The set is built only from development series (ADR 0005): the
content of the evaluation series is never read to choose the judge, so the loader refuses
any other series instead of trusting whoever wrote the file.

The CSV is read with ``utf-8-sig`` because the spreadsheet tools the team edits it with
add a BOM. Labels may be empty while answers are still being generated; pass
``require_labels=True`` when the set is used for scoring.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from afg.domain.question import QuestionStratum
from afg.shared.config import load_corpus_config
from afg.shared.paths import JUDGE_CALIBRATION_DIR

TEMPLATE_PATH: Path = JUDGE_CALIBRATION_DIR / "_plantilla-calibracion-juez.csv"

COLUMNS: tuple[str, ...] = (
    "id",
    "series_id",
    "stratum",
    "question",
    "reference_answer",
    "answer_text",
    "answer_abstained",
    "correct",
    "evidence_supported",
    "citation_correct",
    "labeler_a",
    "labeler_b",
    "adjudicated",
)


class CalibrationSetError(ValueError):
    """Raised when the calibration CSV is malformed."""


class DevelopmentSplitError(CalibrationSetError):
    """Raised when an item belongs to a series outside the development split (ADR 0005)."""


class CalibrationItem(BaseModel):
    """One question-answer pair with its human labels."""

    model_config = ConfigDict(frozen=True)

    id: str
    series_id: str
    stratum: QuestionStratum
    question: str
    reference_answer: str | None = Field(
        default=None, description="None for E4 (unanswerable) questions."
    )
    answer_text: str
    answer_abstained: bool = False
    correct: bool | None = None
    evidence_supported: bool | None = None
    citation_correct: bool | None = Field(
        default=None, description="Optional: not every answer cites evidence."
    )
    labelers: tuple[str, ...] = Field(default_factory=tuple)
    adjudicated: bool = False

    @model_validator(mode="after")
    def _reference_matches_stratum(self) -> CalibrationItem:
        unanswerable = self.stratum is QuestionStratum.E4_UNANSWERABLE
        if unanswerable and self.reference_answer is not None:
            raise ValueError("E4 (unanswerable) items must not carry a reference answer.")
        if not unanswerable and self.reference_answer is None:
            raise ValueError("answerable items need a reference answer.")
        return self

    @property
    def is_labeled(self) -> bool:
        return self.correct is not None and self.evidence_supported is not None


def _parse_bool(value: str, *, column: str, item_id: str) -> bool | None:
    text = value.strip().lower()
    if not text:
        return None
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise CalibrationSetError(f"item {item_id!r}: column {column!r} is not a boolean: {value!r}")


def development_series() -> frozenset[str]:
    """The frozen development split from ``config/corpus.toml`` (ADR 0005)."""
    return frozenset(load_corpus_config()["oe1"]["development_series"])


def load_calibration_items(path: Path, *, require_labels: bool = False) -> list[CalibrationItem]:
    """Read the calibration CSV, rejecting any series outside the development split."""
    allowed = development_series()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise CalibrationSetError(f"{path.name}: missing columns {missing}")
        items: list[CalibrationItem] = []
        seen: set[str] = set()
        for row in reader:
            item_id = (row["id"] or "").strip()
            if item_id in seen:
                raise CalibrationSetError(f"{path.name}: duplicate item id {item_id!r}")
            seen.add(item_id)
            series = (row["series_id"] or "").strip()
            if series not in allowed:
                raise DevelopmentSplitError(
                    f"item {item_id!r}: series {series!r} is not in the development split "
                    f"{sorted(allowed)} (ADR 0005)."
                )
            reference = row["reference_answer"] or None
            try:
                item = CalibrationItem(
                    id=item_id,
                    series_id=series,
                    stratum=QuestionStratum((row["stratum"] or "").strip()),
                    question=row["question"],
                    reference_answer=reference,
                    answer_text=row["answer_text"],
                    answer_abstained=bool(
                        _parse_bool(
                            row["answer_abstained"], column="answer_abstained", item_id=item_id
                        )
                    ),
                    correct=_parse_bool(row["correct"], column="correct", item_id=item_id),
                    evidence_supported=_parse_bool(
                        row["evidence_supported"], column="evidence_supported", item_id=item_id
                    ),
                    citation_correct=_parse_bool(
                        row["citation_correct"], column="citation_correct", item_id=item_id
                    ),
                    labelers=tuple(
                        v.strip() for v in (row["labeler_a"], row["labeler_b"]) if v.strip()
                    ),
                    adjudicated=bool(
                        _parse_bool(row["adjudicated"], column="adjudicated", item_id=item_id)
                    ),
                )
            except (ValidationError, ValueError) as exc:
                if isinstance(exc, CalibrationSetError):
                    raise
                raise CalibrationSetError(f"item {item_id!r}: {exc}") from exc
            if require_labels and not item.is_labeled:
                raise CalibrationSetError(f"item {item_id!r} has no human labels.")
            items.append(item)
    return items
