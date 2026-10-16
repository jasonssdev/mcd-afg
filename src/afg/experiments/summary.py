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

from afg.conditions.c2_compiled_auto import SOURCE_FULL_TRANSCRIPT
from afg.domain.question import Question
from afg.evaluation.citation_width import summarize_widths, width_rows

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
    citation_precision: float | None
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
    mean_precision: float

    @property
    def incorrect_rate(self) -> float:
        return self.incorrect / self.evaluated if self.evaluated else 0.0


@dataclass(frozen=True, slots=True)
class CitationWidthSummary:
    """Width and coverage of the citations of a set of records (ADR 0009, amendment).

    Reported beside ``citation_correct`` so that a condition that is right because it cites wide
    stays visible. ``answered`` counts the answers the citation rule applies to; with none, the
    width and coverage fields are ``None`` (unknown, never zero). ``source_citations`` counts the
    citations to a full meeting transcript (``sources/*``), which are not evidence; it is ``None``
    (unknown) when a record of a condition that can cite them does not say.
    """

    answered: int
    cited_acts_min: int | None
    cited_acts_median: float | None
    cited_acts_max: int | None
    mean_act_coverage: float | None
    source_citations: int | None


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
        citation_precision=record.get("citation_precision"),
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
    precisions: list[float] = []
    for record in records:
        row = record_row(record)
        if row.outcome != ANSWERED_OUTCOME or not row.cited_chunks:
            continue
        if row.citation_precision is not None:
            precisions.append(row.citation_precision)
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
        mean_precision=sum(precisions) / len(precisions) if precisions else 0.0,
    )


def source_citations(record: Mapping[str, Any]) -> int | None:
    """Citations to a full meeting transcript (``sources/*``) in the record's trace.

    C1 retrieves chunks, not OpenKOS concepts, so it has none (0). For any other condition the
    count needs ``trace.unmapped_cited`` entries that carry a ``reason``; a missing list or
    legacy entries that are bare concept ids (runs before the reason existed) read as unknown.
    """
    if record.get("condition") == "C1":
        return 0
    unmapped = _trace(record).get("unmapped_cited")
    if not isinstance(unmapped, list) or not all(
        isinstance(entry, Mapping) and "reason" in entry for entry in unmapped
    ):
        return None
    return sum(1 for entry in unmapped if entry["reason"] == SOURCE_FULL_TRANSCRIPT)


def _total_source_citations(records: Iterable[Mapping[str, Any]]) -> int | None:
    """Sum over the answered records; unknown as soon as one record's count is unknown."""
    total = 0
    for record in records:
        answer = record.get("answer")
        if answer is None or answer.get("abstained"):
            continue
        count = source_citations(record)
        if count is None:
            return None
        total += count
    return total


def citation_width_summary(
    records: Iterable[Mapping[str, Any]], questions: Mapping[str, Question]
) -> CitationWidthSummary:
    """Citation width, act-level coverage and full-source citations over ``records``.

    The act-level figures are read from the stored answers against the questions' reference
    evidence, exactly as notebook 13 does, so they do not depend on the record's schema version
    and exclude errors, abstentions, E4 questions and questions without reference evidence.

    Raises:
        KeyError: a record with an answer refers to a question not in ``questions``.
    """
    usable = [r for r in records if r.get("error") is None]
    rows = width_rows(usable, questions)
    stats = summarize_widths(rows)
    return CitationWidthSummary(
        answered=stats.answered,
        cited_acts_min=stats.cited_acts_min if rows else None,
        cited_acts_median=stats.cited_acts_median if rows else None,
        cited_acts_max=stats.cited_acts_max if rows else None,
        mean_act_coverage=stats.mean_act_recall if rows else None,
        source_citations=_total_source_citations(usable),
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
