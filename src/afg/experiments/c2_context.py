"""What context C2 retrieved per answer, and how it relates to correctness (issue #146).

Descriptive helpers over the records written by :mod:`afg.experiments.runner` for condition
C2. An OpenKOS query returns blocks of a compiled bundle, each identified by a ``concept_id``
whose first path segment is its kind: ``sources/`` (a raw transcript imported verbatim),
``decisions/`` (an extracted Decision), ``concepts/`` (a topic summary) and a few minor
kinds (events, people, projects) that are grouped as ``other``.

Nothing here scores a run or decides anything. The OE4 cascade of thesis section 5.6
(:mod:`afg.evaluation.attribution`) needs two facts per failed answer: whether the correct
fact is in the compiled base and whether it was retrieved. Only a part of that is checkable
from a saved trace: whether the whole reference answer is visible in the retrieved text.
When it is, the cascade gives synthesis; when it is not, the trace cannot separate extraction
from retrieval (the bundle is not versioned), so :attr:`ErrorEvidence.rule_stage` stays
``None`` and the label is left to a human reading the evidence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from afg.domain.question import Question
from afg.evaluation.attribution import ErrorStage, attribute_error

KINDS = ("sources", "decisions", "concepts", "other")
"""The context kinds, with every minor namespace grouped as ``other``."""

_TERM_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it"}
    | {"of", "on", "or", "that", "the", "to", "was", "were", "with"}
)


def concept_kind(concept_id: str) -> str:
    """The kind of a bundle concept: its namespace, or ``other`` for minor or unknown ones."""
    namespace = concept_id.split("/", 1)[0]
    return namespace if namespace in KINDS[:3] and "/" in concept_id else "other"


def _stratum_label(stratum: str) -> str:
    return stratum.split("_", 1)[0]


def _blocks(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list((record.get("trace") or {}).get("context_blocks") or [])


def _correct(record: Mapping[str, Any] | None) -> bool | None:
    verdict = (record or {}).get("verdict") or {}
    value = verdict.get("correct")
    return None if value is None else bool(value)


def _body(block: Mapping[str, Any]) -> str:
    """The block text without the ``[concept_id: ...]`` header and the ``# Title`` line."""
    lines = str(block.get("text", "")).split("\n")
    if lines and lines[0].startswith("[concept_id:"):
        lines = lines[1:]
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines)


def _terms(text: str) -> set[str]:
    return {t for t in _TERM_RE.findall(text.lower()) if t not in _STOPWORDS}


def reference_term_coverage(reference: str, blocks: Iterable[Mapping[str, Any]]) -> float:
    """Share of the content terms of ``reference`` found in the text of ``blocks``.

    A lexical proxy: it cannot tell that "25" and "twenty-five" are the same figure, so a
    low value is a cue to read the trace, not proof that the fact is missing. A reference
    without content terms gives 0.0.
    """
    wanted = _terms(reference)
    if not wanted:
        return 0.0
    seen: set[str] = set()
    for block in blocks:
        seen |= _terms(_body(block))
    return len(wanted & seen) / len(wanted)


@dataclass(frozen=True, slots=True)
class ContextRow:
    """The composition of the context one C2 answer was generated from."""

    question_id: str
    question: str
    stratum: str
    outcome: str
    abstained: bool
    correct: bool | None
    c1_correct: bool | None
    kinds: tuple[str, ...]
    sources: int
    decisions: int
    concepts: int
    other: int
    reference_source_retrieved: bool | None
    """Whether the raw ``sources/`` block of the meeting holding the reference evidence is in
    the context (None when the question has no reference evidence)."""

    @property
    def blocks(self) -> int:
        return len(self.kinds)


def context_rows(
    c2_records: Iterable[Mapping[str, Any]],
    c1_records: Iterable[Mapping[str, Any]],
    questions: Mapping[str, Question],
) -> list[ContextRow]:
    """One row per C2 record, with the C1 verdict of the same question beside it.

    Raises:
        KeyError: if a C2 record refers to a question not in ``questions``.
    """
    c1_by_question = {str(r["question_id"]): r for r in c1_records}
    rows = []
    for record in c2_records:
        qid = str(record["question_id"])
        question = questions[qid]
        concept_ids = [str(b.get("concept_id", "")) for b in _blocks(record)]
        kinds = tuple(concept_kind(c) for c in concept_ids)
        meetings = {span.meeting_id.lower() for span in question.reference_evidence}
        reference_source = (
            any(
                c.removeprefix("sources/").lower() in meetings
                for c in concept_ids
                if c.startswith("sources/")
            )
            if meetings
            else None
        )
        rows.append(
            ContextRow(
                question_id=qid,
                question=qid.rsplit(".", 1)[-1],
                stratum=_stratum_label(str(record.get("stratum", ""))),
                outcome=str((record.get("trace") or {}).get("outcome", "")),
                abstained=bool((record.get("answer") or {}).get("abstained")),
                correct=_correct(record),
                c1_correct=_correct(c1_by_question.get(qid)),
                kinds=kinds,
                sources=kinds.count("sources"),
                decisions=kinds.count("decisions"),
                concepts=kinds.count("concepts"),
                other=kinds.count("other"),
                reference_source_retrieved=reference_source,
            )
        )
    return rows


@dataclass(frozen=True, slots=True)
class StratumComposition:
    """Per stratum: how many answers, how many correct, and the mean blocks of each kind."""

    stratum: str
    answers: int
    correct: int
    c1_correct: int
    with_sources: int
    with_decisions: int
    mean_sources: float
    mean_decisions: float
    mean_concepts: float
    mean_other: float


def stratum_composition(rows: Sequence[ContextRow]) -> list[StratumComposition]:
    """The rows aggregated per stratum, in the order the strata first appear."""
    order: list[str] = []
    for row in rows:
        if row.stratum not in order:
            order.append(row.stratum)
    summaries = []
    for stratum in order:
        group = [r for r in rows if r.stratum == stratum]
        n = len(group)
        summaries.append(
            StratumComposition(
                stratum=stratum,
                answers=n,
                correct=sum(r.correct is True for r in group),
                c1_correct=sum(r.c1_correct is True for r in group),
                with_sources=sum(r.sources > 0 for r in group),
                with_decisions=sum(r.decisions > 0 for r in group),
                mean_sources=sum(r.sources for r in group) / n,
                mean_decisions=sum(r.decisions for r in group) / n,
                mean_concepts=sum(r.concepts for r in group) / n,
                mean_other=sum(r.other for r in group) / n,
            )
        )
    return summaries


@dataclass(frozen=True, slots=True)
class PresenceSplit:
    """Judged answers split by whether their context held at least one block of a kind."""

    kind: str
    with_kind: int
    correct_with_kind: int
    without_kind: int
    correct_without_kind: int


def correctness_by_presence(rows: Iterable[ContextRow], kind: str) -> PresenceSplit:
    """Correct answers among those with and without a block of ``kind`` (unjudged skipped)."""
    judged = [r for r in rows if r.correct is not None]
    present = [r for r in judged if kind in r.kinds]
    absent = [r for r in judged if kind not in r.kinds]
    return PresenceSplit(
        kind=kind,
        with_kind=len(present),
        correct_with_kind=sum(bool(r.correct) for r in present),
        without_kind=len(absent),
        correct_without_kind=sum(bool(r.correct) for r in absent),
    )


@dataclass(frozen=True, slots=True)
class ErrorEvidence:
    """The evidence a reader needs to label one failed C2 answer under OE4."""

    question: str
    stratum: str
    outcome: str
    abstained: bool
    kinds: tuple[str, ...]
    reference_source_retrieved: bool | None
    reference_coverage: float
    """Share of the reference answer's content terms found in any retrieved block."""
    visible_in: tuple[str, ...]
    """Kinds with at least one block that holds every content term of the reference."""
    rule_stage: ErrorStage | None
    """``synthesis`` when the whole reference is visible in the context, else ``None``: the
    trace cannot separate extraction from retrieval and a human labels it."""


def error_evidence(
    rows: Iterable[ContextRow],
    c2_records: Iterable[Mapping[str, Any]],
    questions: Mapping[str, Question],
) -> list[ErrorEvidence]:
    """One entry per judged-incorrect answer; correct and unjudged answers are skipped."""
    by_question = {str(r["question_id"]): r for r in c2_records}
    evidence = []
    for row in rows:
        if row.correct is not False:
            continue
        qid = row.question_id
        record = by_question[qid]
        reference = questions[qid].reference_answer or ""
        blocks = _blocks(record)
        visible = tuple(
            dict.fromkeys(
                concept_kind(str(b.get("concept_id", "")))
                for b in blocks
                if reference_term_coverage(reference, [b]) == 1.0
            )
        )
        evidence.append(
            ErrorEvidence(
                question=row.question,
                stratum=row.stratum,
                outcome=row.outcome,
                abstained=row.abstained,
                kinds=row.kinds,
                reference_source_retrieved=row.reference_source_retrieved,
                reference_coverage=reference_term_coverage(reference, blocks),
                visible_in=visible,
                rule_stage=(
                    attribute_error(fact_in_base=True, fact_retrieved=True) if visible else None
                ),
            )
        )
    return evidence


def same_retrieval(a: Iterable[Mapping[str, Any]], b: Iterable[Mapping[str, Any]]) -> bool:
    """Whether two C2 runs retrieved the same concepts, in the same order, for every question."""

    def retrieved(records: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
        return {
            str(r["question_id"]): [str(x.get("concept_id")) for x in _blocks(r)] for r in records
        }

    first, second = retrieved(a), retrieved(b)
    return bool(first) and first == second


@dataclass(frozen=True, slots=True)
class SourceExcerpts:
    """How much raw transcript text the ``sources/`` blocks of a run carry."""

    blocks: int
    excerpted: int
    mean_chars: float


def source_excerpts(records: Iterable[Mapping[str, Any]]) -> SourceExcerpts:
    """Count the raw ``sources/`` blocks, how many OpenKOS cut, and their mean text length."""
    sources = [
        b
        for record in records
        for b in _blocks(record)
        if concept_kind(str(b.get("concept_id", ""))) == "sources"
    ]
    if not sources:
        return SourceExcerpts(0, 0, 0.0)
    return SourceExcerpts(
        blocks=len(sources),
        excerpted=sum(bool(b.get("excerpted")) for b in sources),
        mean_chars=sum(len(str(b.get("text", ""))) for b in sources) / len(sources),
    )


__all__ = [
    "KINDS",
    "ContextRow",
    "ErrorEvidence",
    "PresenceSplit",
    "SourceExcerpts",
    "StratumComposition",
    "concept_kind",
    "context_rows",
    "correctness_by_presence",
    "error_evidence",
    "reference_term_coverage",
    "same_retrieval",
    "source_excerpts",
    "stratum_composition",
]
