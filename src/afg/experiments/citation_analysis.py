"""Analysis of the correct-citation rule over an Experiment B run (thesis sections 5.6, 6.2).

Descriptive helpers for deciding whether the current rule (every cited span must hit the
reference evidence) measures what section 5.6 says the metric measures. They never change the
rule: :mod:`afg.evaluation.citation` stays the one that scores runs. The variants themselves
are defined in :mod:`afg.evaluation.citation_variants`; here they are applied to the record
dictionaries written by :mod:`afg.experiments.runner` and tallied.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation_variants import citation_variants
from afg.experiments.summary import has_inline_used_marker

_CHUNK_HEADER_RE = re.compile(r"^\[concept_id:[^\]]*\]\n?")
SNIPPET_CHARS = 140


@dataclass(frozen=True, slots=True)
class ReferenceSize:
    """How much reference evidence an answerable question has (how sparse the linking is)."""

    question: str
    stratum: str
    acts: int
    meetings: int


def reference_sizes(questions: Iterable[Question]) -> list[ReferenceSize]:
    """One row per answerable question that has reference evidence."""
    sizes = []
    for question in questions:
        if question.stratum is QuestionStratum.E4_UNANSWERABLE or not question.reference_evidence:
            continue
        acts = {
            (span.meeting_id, act)
            for span in question.reference_evidence
            for act in span.dialogue_act_ids
        }
        sizes.append(
            ReferenceSize(
                question=question.id.rsplit(".", 1)[-1],
                stratum=question.stratum.value.split("_", 1)[0],
                acts=len(acts),
                meetings=len({meeting for meeting, _ in acts}),
            )
        )
    return sizes


@dataclass(frozen=True, slots=True)
class CitationComparison:
    """One answered record under each rule variant, with the judge verdict beside it."""

    question: str
    correct: bool | None
    evidence_supported: bool | None
    inline_used_marker: bool
    cited_spans: int
    cited_acts: int
    reference_acts: int
    all_hit: bool
    any_hit: bool
    precision: float
    recall: float


def compare_records(
    records: Iterable[Mapping[str, Any]], questions: Mapping[str, Question]
) -> list[CitationComparison]:
    """Each record the citation rate applies to, evaluated under every variant.

    Raises:
        KeyError: if a record's question is not in ``questions``.
    """
    rows = []
    for record in records:
        question = questions[str(record["question_id"])]
        answer = Answer.model_validate(record["answer"])
        variants = citation_variants(question, answer)
        if variants is None:
            continue
        verdict = record.get("verdict") or {}
        rows.append(
            CitationComparison(
                question=str(record["question_id"]).rsplit(".", 1)[-1],
                correct=verdict.get("correct"),
                evidence_supported=verdict.get("evidence_supported"),
                inline_used_marker=has_inline_used_marker(record),
                cited_spans=variants.cited_spans,
                cited_acts=variants.cited_acts,
                reference_acts=variants.reference_acts,
                all_hit=variants.all_hit,
                any_hit=variants.any_hit,
                precision=variants.precision,
                recall=variants.recall,
            )
        )
    return rows


@dataclass(frozen=True, slots=True)
class VariantTally:
    """Counts of a set of comparisons under each variant."""

    records: int
    correct_answers: int
    all_hit: int
    any_hit: int
    correct_but_all_miss: int
    correct_but_any_miss: int
    mean_precision: float
    mean_recall: float


def tally_variants(rows: Sequence[CitationComparison]) -> VariantTally:
    """How many records pass each variant and how many correct answers each one rejects."""
    n = len(rows)
    correct = [r for r in rows if r.correct is True]
    return VariantTally(
        records=n,
        correct_answers=len(correct),
        all_hit=sum(r.all_hit for r in rows),
        any_hit=sum(r.any_hit for r in rows),
        correct_but_all_miss=sum(not r.all_hit for r in correct),
        correct_but_any_miss=sum(not r.any_hit for r in correct),
        mean_precision=sum(r.precision for r in rows) / n if n else 0.0,
        mean_recall=sum(r.recall for r in rows) / n if n else 0.0,
    )


def tally_by_verdict(
    rows: Sequence[CitationComparison],
) -> dict[tuple[bool | None, bool | None], VariantTally]:
    """Tallies per judge verdict ``(correct, evidence_supported)``, in order of first appearance."""
    grouped: dict[tuple[bool | None, bool | None], list[CitationComparison]] = {}
    for row in rows:
        grouped.setdefault((row.correct, row.evidence_supported), []).append(row)
    return {key: tally_variants(group) for key, group in grouped.items()}


@dataclass(frozen=True, slots=True)
class ChunkSummary:
    """One cited chunk: its size, how many of its acts are reference acts, a text snippet."""

    chunk_id: str
    meeting_id: str
    acts: int
    acts_in_reference: int
    hit: bool
    snippet: str


def cited_chunk_summaries(
    record: Mapping[str, Any], reference: Sequence[EvidenceSpan]
) -> list[ChunkSummary]:
    """The chunks a record cited, in citation order, each judged against ``reference``."""
    trace = record.get("trace") or {}
    cited_acts: Mapping[str, Sequence[str]] = trace.get("cited_acts") or {}
    blocks = {b["chunk_id"]: b for b in trace.get("context_blocks") or []}
    reference_acts = {(s.meeting_id, a) for s in reference for a in s.dialogue_act_ids}
    summaries = []
    for chunk_id in trace.get("cited_chunk_ids") or []:
        block = blocks.get(chunk_id, {})
        meeting_id = str(block.get("meeting_id") or chunk_id.split(".", 1)[0])
        acts = cited_acts.get(chunk_id, [])
        in_reference = sum((meeting_id, a) in reference_acts for a in acts)
        text = _CHUNK_HEADER_RE.sub("", str(block.get("text") or "")).strip()
        summaries.append(
            ChunkSummary(
                chunk_id=chunk_id,
                meeting_id=meeting_id,
                acts=len(acts),
                acts_in_reference=in_reference,
                hit=in_reference > 0,
                snippet=" ".join(text.split())[:SNIPPET_CHARS],
            )
        )
    return summaries
