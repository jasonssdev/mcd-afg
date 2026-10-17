"""Width of an answer's citations and its dialogue-act-level precision and coverage (issue #97).

ADR 0009 scores a citation as correct when at least one cited span shares a dialogue act with
the reference evidence, and reports the fraction of cited *spans* that do so. Neither reflects
how wide the citation is: a span of 140 acts and one of 5 count the same. This module reads the
same answers at the level of dialogue acts, so conditions that cite units of very different
width (C1 cites chunks, C2 cites concepts and decisions) can be compared on one footing:

* ``cited_acts``: distinct dialogue acts cited, and ``unit_widths``: acts per cited span.
* ``act_precision``: cited acts that are reference acts, over cited acts.
* ``act_recall``: reference acts that are cited, over reference acts.

These are analysis-only measures. They do not replace
:func:`afg.evaluation.citation.citation_correct` or
:func:`afg.evaluation.citation.citation_precision`, and they apply exactly where those do (not
to abstentions, E4 questions or questions without reference evidence). Acts are matched on
``(meeting_id, dialogue_act_id)``. As in ADR 0009, an answer without citations scores ``0.0``
on every proportion, so the unsourced answers are not dropped from an average.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from afg.domain.question import Answer, Question
from afg.evaluation.citation_variants import citation_variants


@dataclass(frozen=True, slots=True)
class CitationWidth:
    """One answered record read at the level of dialogue acts."""

    question: str
    cited_spans: int
    cited_acts: int
    unit_widths: tuple[int, ...]
    reference_acts: int
    acts_in_reference: int
    citation_correct: bool
    unit_precision: float

    @property
    def act_precision(self) -> float:
        return self.acts_in_reference / self.cited_acts if self.cited_acts else 0.0

    @property
    def act_recall(self) -> float:
        return self.acts_in_reference / self.reference_acts if self.reference_acts else 0.0


def citation_width(question: Question, answer: Answer) -> CitationWidth | None:
    """The act-level reading of ``answer``, or ``None`` where the citation rate does not apply."""
    variants = citation_variants(question, answer)
    if variants is None:
        return None
    return CitationWidth(
        question=question.id.rsplit(".", 1)[-1],
        cited_spans=variants.cited_spans,
        cited_acts=variants.cited_acts,
        unit_widths=tuple(len(set(span.dialogue_act_ids)) for span in answer.cited_evidence),
        reference_acts=variants.reference_acts,
        acts_in_reference=variants.reference_acts_covered,
        citation_correct=variants.any_hit,
        unit_precision=variants.precision,
    )


def width_rows(
    records: Iterable[Mapping[str, Any]], questions: Mapping[str, Question]
) -> list[CitationWidth]:
    """Each record with an answer the citation rate applies to, in record order.

    Raises:
        KeyError: if a record with an answer refers to a question not in ``questions``.
    """
    rows = []
    for record in records:
        if record.get("answer") is None:
            continue
        question = questions[str(record["question_id"])]
        row = citation_width(question, Answer.model_validate(record["answer"]))
        if row is not None:
            rows.append(row)
    return rows


@dataclass(frozen=True, slots=True)
class WidthSummary:
    """A condition's answered records, aggregated."""

    answered: int
    citation_correct: int
    mean_unit_precision: float
    mean_act_precision: float
    mean_act_recall: float
    cited_acts_min: int
    cited_acts_median: float
    cited_acts_max: int
    unit_width_min: int
    unit_width_median: float
    unit_width_max: int


def summarize_widths(rows: Sequence[CitationWidth]) -> WidthSummary:
    """Counts, means and width ranges over ``rows``; all zero for no rows."""
    n = len(rows)
    totals = [r.cited_acts for r in rows]
    units = [w for r in rows for w in r.unit_widths]
    return WidthSummary(
        answered=n,
        citation_correct=sum(r.citation_correct for r in rows),
        mean_unit_precision=sum(r.unit_precision for r in rows) / n if n else 0.0,
        mean_act_precision=sum(r.act_precision for r in rows) / n if n else 0.0,
        mean_act_recall=sum(r.act_recall for r in rows) / n if n else 0.0,
        cited_acts_min=min(totals, default=0),
        cited_acts_median=statistics.median(totals) if totals else 0.0,
        cited_acts_max=max(totals, default=0),
        unit_width_min=min(units, default=0),
        unit_width_median=statistics.median(units) if units else 0.0,
        unit_width_max=max(units, default=0),
    )


def low_precision_hits(rows: Sequence[CitationWidth], *, threshold: float) -> int:
    """Rows with a correct citation although under ``threshold`` of its acts are reference acts."""
    return sum(r.citation_correct and r.act_precision < threshold for r in rows)


def trace_unit_widths(record: Mapping[str, Any]) -> dict[str, int]:
    """Distinct dialogue acts per cited unit, read from a record's trace.

    The answer's ``cited_evidence`` merges C1 chunks of one meeting into a single span, so the
    unit the model actually cited (a chunk for C1, a concept or decision for C2) is only in
    ``trace["cited_acts"]``: a list of acts per chunk, or a mapping meeting to acts per concept.
    Acts are counted per ``(meeting, id)``. A record without a trace yields no units.
    """
    cited = (record.get("trace") or {}).get("cited_acts") or {}
    widths = {}
    for unit, acts in cited.items():
        if isinstance(acts, Mapping):
            widths[str(unit)] = sum(len(set(ids)) for ids in acts.values())
        else:
            widths[str(unit)] = len(set(acts))
    return widths
