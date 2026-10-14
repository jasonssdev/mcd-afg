"""The judge calibration set: schema and loader (thesis section 5.7).

Each item pairs a question and a system answer with the labels humans gave it; the judge
candidates are scored against those labels (:mod:`afg.evaluation.judge_calibration`). The
labels are always human. The set is built only from development series (ADR 0005): the
content of the evaluation series is never read to choose the judge, so the loader refuses
any other series instead of trusting whoever wrote the file.

The CSV is read with ``utf-8-sig`` because the spreadsheet tools the team edits it with
add a BOM. Boolean cells accept ``si``/``no`` (what people type) as well as ``true``/``false``.
Labels may be empty while answers are still being generated; pass ``require_labels=True`` when
the set is used for scoring.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum, parse_reference_evidence
from afg.shared.config import load_corpus_config, load_experiments_config
from afg.shared.paths import JUDGE_CALIBRATION_DIR

TEMPLATE_PATH: Path = JUDGE_CALIBRATION_DIR / "_plantilla-calibracion-juez.csv"

COLUMNS: tuple[str, ...] = (
    "id",
    "series_id",
    "stratum",
    "question",
    "reference_answer",
    "reference_evidence",
    "answer_text",
    "answer_abstained",
    "correct",
    "evidence_supported",
    "citation_correct",
    "labeler_a",
    "labeler_b",
    "adjudicated",
)


VARIANT_COLUMNS: tuple[str, ...] = ("id", "answer_variant")


def variants_path(calibration_path: Path) -> Path:
    """The sidecar with how each answer was produced, next to the labeling file.

    The variant (grounded, ungrounded, no_context) predicts the expected label, so it is kept
    out of the file the humans label and out of what the judge sees.
    """
    return calibration_path.with_suffix(".variantes.csv")


def load_variants(calibration_path: Path) -> dict[str, str]:
    """``id -> answer_variant`` from the sidecar; empty when there is no sidecar."""
    path = variants_path(calibration_path)
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {
            (row["id"] or "").strip(): (row["answer_variant"] or "").strip()
            for row in csv.DictReader(handle)
        }


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
    reference_evidence: tuple[EvidenceSpan, ...] = Field(
        default_factory=tuple,
        description="Dialogue acts that support the reference answer; empty for E4.",
    )
    answer_variant: str | None = Field(
        default=None,
        description="How the answer was produced (grounded, ungrounded, no_context), read "
        "from the sidecar file (:func:`variants_path`) so the set can be checked for balance. "
        "Never shown to the labelers or the judge.",
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
    if text in {"true", "1", "si", "sí", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise CalibrationSetError(f"item {item_id!r}: column {column!r} is not a boolean: {value!r}")


def development_series() -> frozenset[str]:
    """The frozen development split from ``config/corpus.toml`` (ADR 0005)."""
    return frozenset(load_corpus_config()["oe1"]["development_series"])


def calibration_series() -> frozenset[str]:
    """The series the calibration set may draw from: ``[judge.calibration].series``.

    A subset of the development split (ADR 0005) that is narrower on purpose: a development
    series whose annotations are still pending must not be exposed to question writers.

    Raises:
        CalibrationSetError: if the list is missing or empty.
        DevelopmentSplitError: if the list names a series outside the development split.
    """
    section = load_experiments_config()["judge"]["calibration"]
    configured = frozenset(section.get("series", ()))
    if not configured:
        raise CalibrationSetError("[judge.calibration].series is missing or empty.")
    outside = configured - development_series()
    if outside:
        raise DevelopmentSplitError(
            f"[judge.calibration].series lists {sorted(outside)}, which are not in the "
            f"development split {sorted(development_series())} (ADR 0005)."
        )
    return configured


def load_calibration_items(path: Path, *, require_labels: bool = False) -> list[CalibrationItem]:
    """Read the calibration CSV, rejecting any series outside the calibration series.

    The calibration series (:func:`calibration_series`) are themselves a subset of the
    development split, so an evaluation series can never get through.
    """
    allowed = calibration_series()
    variants = load_variants(path)
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
                    f"item {item_id!r}: series {series!r} is not one of the calibration "
                    f"series {sorted(allowed)} (development split only, ADR 0005)."
                )
            reference = row["reference_answer"] or None
            try:
                item = CalibrationItem(
                    id=item_id,
                    series_id=series,
                    stratum=QuestionStratum((row["stratum"] or "").strip()),
                    question=row["question"],
                    reference_answer=reference,
                    reference_evidence=parse_reference_evidence(row["reference_evidence"] or ""),
                    answer_variant=variants.get(item_id) or None,
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


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    """Size and balance of a calibration set, and whether it can be used for scoring."""

    n_items: int
    n_labeled: int
    by_variant: dict[str, int]
    by_stratum: dict[str, int]

    @property
    def ready(self) -> bool:
        """True when the set is non-empty and every item carries its human labels."""
        return self.n_items > 0 and self.n_labeled == self.n_items


def summarize_calibration_set(items: Sequence[CalibrationItem]) -> CalibrationSummary:
    """Count items, labeled items, answer variants and strata (items without a variant: ``""``)."""
    return CalibrationSummary(
        n_items=len(items),
        n_labeled=sum(1 for item in items if item.is_labeled),
        by_variant=dict(sorted(Counter(item.answer_variant or "" for item in items).items())),
        by_stratum=dict(sorted(Counter(item.stratum.value for item in items).items())),
    )
