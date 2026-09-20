"""OE4: deterministic error attribution cascade (thesis section 5.6).

For each incorrect or unsupported answer produced under C2, thesis section 5.6 specifies a
deterministic cascade: first check whether the correct fact exists in the compiled base
(if not: extraction error); if it exists, check whether it was retrieved (if not: retrieval
error); if it was retrieved and the answer is still wrong: synthesis error.

This is the one piece of OE4 fully specified without reference to any un-downloaded data,
so it is implemented and tested in full; the harder part -- deciding, for a real failed
answer, whether the fact is "in the base" and "retrieved" -- is a downstream judgment call
made by the evaluation pipeline, not by this pure classifier.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorStage(StrEnum):
    """Where a C2 failure originated (thesis section 5.6)."""

    EXTRACTION = "extraction"
    """The fact was never written correctly into the compiled base."""

    RETRIEVAL = "retrieval"
    """The correct fact existed in the base but was not retrieved for this question."""

    SYNTHESIS = "synthesis"
    """The correct fact was retrieved and the generated answer still contradicts it."""


def attribute_error(*, fact_in_base: bool, fact_retrieved: bool) -> ErrorStage:
    """Classify a C2 failure per the thesis section 5.6 cascade.

    Precondition (enforced by the caller, not by this function): this is only meaningful
    for an answer already known to be incorrect or unsupported (thesis section 5.6: "cada
    respuesta fallida de C2"). Calling this for a correct answer produces a stage label
    that is meaningless -- there was no failure to attribute.

    ``fact_retrieved`` is only consulted when ``fact_in_base`` is True: whether the fact
    "was retrieved" is undefined when it was never in the base to retrieve.
    """
    if not fact_in_base:
        return ErrorStage.EXTRACTION
    if not fact_retrieved:
        return ErrorStage.RETRIEVAL
    return ErrorStage.SYNTHESIS
