"""Deterministic citation correctness (thesis sections 5.6 and 6.2; ADR 0009).

Section 5.6 defines the correct-citation rate as "the cited source actually supports the
claim", distinct from evidence support: it catches a correct answer whose citation does not
back it. The judge never sees source text, so this is decided here, by comparing the
dialogue acts an answer cites with the question's reference evidence.

A cited span *hits* when it shares its meeting and at least one dialogue act with some
reference span. Dialogue act ids are compared within a meeting only, since ``EvidenceSpan``
makes no claim that ids are unique across meetings. Conditions must express their citations
as ``EvidenceSpan`` before calling this (C1 expands each cited chunk to its dialogue acts).

The citation is correct when at least one cited span hits (ADR 0009): the failure section 5.6
names is a citation that supports nothing, not one that also carries extra material. How much
of the citation is relevant is reported separately as :func:`citation_precision`. The hit
computation lives in :mod:`afg.evaluation.citation_variants`, the single source of truth.
"""

from __future__ import annotations

from afg.domain.question import Answer, Question
from afg.evaluation.citation_variants import citation_variants


def citation_correct(question: Question, answer: Answer) -> bool | None:
    """Whether at least one citation in ``answer`` is backed by the question's reference.

    Returns ``None`` when the rate does not apply: an abstention, an E4 (unanswerable)
    question, or a question without reference evidence. An answer to an answerable
    question with no citation at all is ``False``: section 6.2 counts an unsourced claim
    as a failure even when the claim is correct.
    """
    variants = citation_variants(question, answer)
    return None if variants is None else variants.any_hit


def citation_precision(question: Question, answer: Answer) -> float | None:
    """The fraction of cited spans that hit the reference evidence, as a secondary figure.

    ``None`` exactly where :func:`citation_correct` is ``None``. An answer to an answerable
    question with no citation scores ``0.0``: section 6.2 treats it as a failure, and a
    ``None`` would drop precisely the unsourced answers from any average.
    """
    variants = citation_variants(question, answer)
    return None if variants is None else variants.precision
