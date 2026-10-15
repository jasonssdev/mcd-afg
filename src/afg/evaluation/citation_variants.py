"""Readings of the correct-citation rule over one answer (thesis section 5.6; ADR 0009).

Section 5.6 defines the correct-citation rate as "the cited source actually supports the
claim". This module holds the one hit computation behind it and the readings built on it:

* ``any_hit``: at least one cited span hits the reference. This is the adopted rule
  (:func:`afg.evaluation.citation.citation_correct`, ADR 0009).
* ``precision``: the fraction of cited spans that hit the reference, reported beside the rule.
* ``all_hit``: every cited span hits the reference (the retired rule, kept for comparison).
* ``recall``: the fraction of reference dialogue acts covered by the union of the citations.

A span *hits* when it shares its meeting and at least one dialogue act with some reference
span. Act ids are compared within a meeting only. The variants apply exactly where the rule
applies (not to abstentions, E4 questions or questions without reference evidence); an
answer with no citation fails every variant.
"""

from __future__ import annotations

from dataclasses import dataclass

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum


@dataclass(frozen=True, slots=True)
class CitationVariants:
    """Sizes and rule variants of one answer's citations against its reference evidence."""

    cited_spans: int
    spans_hit: int
    cited_acts: int
    reference_acts: int
    reference_acts_covered: int

    @property
    def all_hit(self) -> bool:
        return self.cited_spans > 0 and self.spans_hit == self.cited_spans

    @property
    def any_hit(self) -> bool:
        return self.spans_hit > 0

    @property
    def precision(self) -> float:
        return self.spans_hit / self.cited_spans if self.cited_spans else 0.0

    @property
    def recall(self) -> float:
        return self.reference_acts_covered / self.reference_acts if self.reference_acts else 0.0


def citation_variants(question: Question, answer: Answer) -> CitationVariants | None:
    """The variants for ``answer``, or ``None`` where the citation rate does not apply."""
    if answer.abstained or question.stratum is QuestionStratum.E4_UNANSWERABLE:
        return None
    if not question.reference_evidence:
        return None
    reference = _acts(question.reference_evidence)
    cited = _acts(answer.cited_evidence)
    spans_hit = sum(
        not reference.get(span.meeting_id, set()).isdisjoint(span.dialogue_act_ids)
        for span in answer.cited_evidence
    )
    return CitationVariants(
        cited_spans=len(answer.cited_evidence),
        spans_hit=spans_hit,
        cited_acts=sum(len(acts) for acts in cited.values()),
        reference_acts=sum(len(acts) for acts in reference.values()),
        reference_acts_covered=sum(
            len(acts & cited.get(m, set())) for m, acts in reference.items()
        ),
    )


def _acts(spans: tuple[EvidenceSpan, ...]) -> dict[str, set[str]]:
    acts: dict[str, set[str]] = {}
    for span in spans:
        acts.setdefault(span.meeting_id, set()).update(span.dialogue_act_ids)
    return acts
