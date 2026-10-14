"""Deterministic citation correctness (thesis sections 5.6 and 6.2).

Section 5.6 defines the correct-citation rate as "the cited source actually supports the
claim", distinct from evidence support: it catches a correct answer whose citation does not
back it. The judge never sees source text, so this is decided here, by comparing the
dialogue acts an answer cites with the question's reference evidence.

A cited span is supported when it shares its meeting and at least one dialogue act with
some reference span. Dialogue act ids are compared within a meeting only, since
``EvidenceSpan`` makes no claim that ids are unique across meetings. Conditions must
express their citations as ``EvidenceSpan`` before calling this (C1 expands each cited
chunk to its dialogue acts).
"""

from __future__ import annotations

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum


def citation_correct(question: Question, answer: Answer) -> bool | None:
    """Whether every citation in ``answer`` is backed by the question's reference evidence.

    Returns ``None`` when the rate does not apply: an abstention, an E4 (unanswerable)
    question, or a question without reference evidence. An answer to an answerable
    question with no citation at all is ``False``: section 6.2 counts an unsourced claim
    as a failure even when the claim is correct.
    """
    if answer.abstained or question.stratum is QuestionStratum.E4_UNANSWERABLE:
        return None
    if not question.reference_evidence:
        return None
    if not answer.cited_evidence:
        return False
    reference = _acts_by_meeting(question.reference_evidence)
    return all(
        not reference.get(span.meeting_id, set()).isdisjoint(span.dialogue_act_ids)
        for span in answer.cited_evidence
    )


def _acts_by_meeting(spans: tuple[EvidenceSpan, ...]) -> dict[str, set[str]]:
    acts: dict[str, set[str]] = {}
    for span in spans:
        acts.setdefault(span.meeting_id, set()).update(span.dialogue_act_ids)
    return acts
