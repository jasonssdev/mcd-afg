"""Pure summaries over the records of an Experiment B run (thesis sections 5.6 and 6.2).

Every figure a notebook shows about a run comes from here, so it is tested. The functions take
the record dictionaries written by :mod:`afg.experiments.runner` (one per question, condition
and run, latest per key; see ``load_records(..., latest_only=True)``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ABSTENTION_OUTCOME = "no_answer_in_context"
ANSWERED_OUTCOME = "answered"

_USED_MARKER_RE = re.compile(r"(?i)used[ \t]*:")


@dataclass(frozen=True, slots=True)
class RecordRow:
    """One record, flattened to what a reader needs to inspect it."""

    question: str
    question_text: str
    stratum: str
    outcome: str
    attribution: str
    correct: bool | None
    evidence_supported: bool | None
    citation_correct: bool | None
    cited_chunks: int
    answer_seconds: float
    judge_seconds: float


@dataclass(frozen=True, slots=True)
class StratumSummary:
    """Counts, rates and timings of the records of one stratum (``E1`` to ``E4``)."""

    stratum: str
    n: int
    answered: int
    abstained: int
    correct: int
    correct_rate: float
    abstention_rate: float
    mean_answer_seconds: float
    mean_judge_seconds: float
    total_seconds: float


@dataclass(frozen=True, slots=True)
class CitationTally:
    """Deterministic citation outcome over the answered records that cite something."""

    evaluated: int
    correct: int
    incorrect: int
    incorrect_with_inline_marker: int
    incorrect_with_correct_answer: int

    @property
    def incorrect_rate(self) -> float:
        return self.incorrect / self.evaluated if self.evaluated else 0.0


@dataclass(frozen=True, slots=True)
class ResumeStatus:
    """How much of the expected work the latest records cover."""

    expected: int
    complete: int
    errors: int

    @property
    def pending(self) -> int:
        return self.expected - self.complete


def _stratum_label(stratum: str) -> str:
    return stratum.split("_", 1)[0]


def _trace(record: Mapping[str, Any]) -> Mapping[str, Any]:
    return record.get("trace") or {}


def record_row(record: Mapping[str, Any]) -> RecordRow:
    """Flatten a record; a missing verdict, timing or citation list reads as unknown or zero."""
    trace = _trace(record)
    verdict = record.get("verdict") or {}
    return RecordRow(
        question=str(record["question_id"]).rsplit(".", 1)[-1],
        question_text=str(trace.get("question") or ""),
        stratum=_stratum_label(str(record["stratum"])),
        outcome=str(trace.get("outcome")),
        attribution=str(trace.get("attribution")),
        correct=verdict.get("correct"),
        evidence_supported=verdict.get("evidence_supported"),
        citation_correct=record.get("citation_correct"),
        cited_chunks=len(trace.get("cited_chunk_ids") or []),
        answer_seconds=float(record.get("answer_seconds") or 0.0),
        judge_seconds=float(record.get("judge_seconds") or 0.0),
    )


def record_rows(records: Iterable[Mapping[str, Any]]) -> list[RecordRow]:
    return [record_row(r) for r in records]


def has_inline_used_marker(record: Mapping[str, Any]) -> bool:
    """Whether the reply carries a ``USED:`` marker that OpenKOS did not read.

    OpenKOS v0.5.4 reads the marker only when it is alone on its line. A reply such as
    ``"... twenty five Euros. USED: 2, 3"`` therefore has attribution ``absent`` although the
    model did report which blocks it used. Only a marker with text before it on the same line
    counts here, and only when the attribution was indeed lost.
    """
    trace = _trace(record)
    reply = trace.get("raw_reply")
    if trace.get("attribution") != "absent" or not reply:
        return False
    for match in _USED_MARKER_RE.finditer(reply):
        line_start = reply.rfind("\n", 0, match.start()) + 1
        if reply[line_start : match.start()].strip():
            return True
    return False


def inline_marker_rows(records: Iterable[Mapping[str, Any]]) -> list[RecordRow]:
    return [record_row(r) for r in records if has_inline_used_marker(r)]


def stratum_summary(records: Iterable[Mapping[str, Any]]) -> list[StratumSummary]:
    """One summary per stratum, ordered by stratum label."""
    grouped: dict[str, list[RecordRow]] = {}
    for row in record_rows(records):
        grouped.setdefault(row.stratum, []).append(row)
    summaries = []
    for stratum in sorted(grouped):
        rows = grouped[stratum]
        n = len(rows)
        abstained = sum(1 for r in rows if r.outcome == ABSTENTION_OUTCOME)
        correct = sum(1 for r in rows if r.correct is True)
        answer_total = sum(r.answer_seconds for r in rows)
        judge_total = sum(r.judge_seconds for r in rows)
        summaries.append(
            StratumSummary(
                stratum=stratum,
                n=n,
                answered=sum(1 for r in rows if r.outcome == ANSWERED_OUTCOME),
                abstained=abstained,
                correct=correct,
                correct_rate=correct / n,
                abstention_rate=abstained / n,
                mean_answer_seconds=answer_total / n,
                mean_judge_seconds=judge_total / n,
                total_seconds=answer_total + judge_total,
            )
        )
    return summaries


def citation_tally(records: Sequence[Mapping[str, Any]]) -> CitationTally:
    """Tally the deterministic citation outcome of answered records with at least one citation."""
    correct = incorrect = with_marker = with_correct_answer = 0
    for record in records:
        row = record_row(record)
        if row.outcome != ANSWERED_OUTCOME or not row.cited_chunks:
            continue
        if row.citation_correct is True:
            correct += 1
        elif row.citation_correct is False:
            incorrect += 1
            with_marker += has_inline_used_marker(record)
            with_correct_answer += row.correct is True
    return CitationTally(
        evaluated=correct + incorrect,
        correct=correct,
        incorrect=incorrect,
        incorrect_with_inline_marker=with_marker,
        incorrect_with_correct_answer=with_correct_answer,
    )


def resume_status(records: Iterable[Mapping[str, Any]], *, expected: int) -> ResumeStatus:
    """Complete and failed records among the latest ones, against the expected total."""
    latest = list(records)
    errors = sum(1 for r in latest if r.get("error") is not None)
    return ResumeStatus(expected=expected, complete=len(latest) - errors, errors=errors)


def wiring_summary(records: Iterable[Mapping[str, Any]]) -> dict[str, list[Any]]:
    """The distinct seeds, models and judge settings the records were produced with.

    One value per key means the setting was constant across the run, which is what the
    experiment requires of the judge and of the generation seed within a run index.
    """
    latest = list(records)

    def distinct(values: Iterable[Any]) -> list[Any]:
        return sorted({v for v in values if v is not None})

    def judge_field(name: str) -> list[Any]:
        return distinct((r.get("judge") or {}).get(name) for r in latest)

    return {
        "seeds": distinct(r.get("seed") for r in latest),
        "seed_applied": distinct(r.get("seed_applied") for r in latest),
        "generative_models": distinct(r.get("generative_model") for r in latest),
        "temperatures": distinct(r.get("temperature") for r in latest),
        "partitions": distinct(r.get("partition") for r in latest),
        "judge_models": judge_field("model"),
        "judge_orders": judge_field("order"),
        "judge_seeds": judge_field("seed"),
        "judge_temperatures": judge_field("temperature"),
        "conditions": distinct(r.get("condition") for r in latest),
        "runs": distinct(r.get("run") for r in latest),
    }
