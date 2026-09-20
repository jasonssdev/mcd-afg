"""C3 -- structured base built from human gold annotation (thesis section 5.3).

The upper reference: identical to C2 except the compiled objects come from the OE1
annotation rather than automatic extraction. Thesis section 3 (OE3): explicitly NOT called
a "theoretical ceiling" -- a human annotation with measured reliability is a reference, not
a demonstrable upper bound, especially given the negative-kappa precedent (thesis section
1.4).
"""

from __future__ import annotations

from dataclasses import dataclass

from afg.domain.decision import Decision
from afg.domain.question import Answer, Question
from afg.domain.relation import TemporalRelation


@dataclass(slots=True)
class CompiledGoldCondition:
    """C3: query over a base compiled directly from the OE1 gold annotation."""

    condition_id: str = "C3"
    gold_decisions: tuple[Decision, ...] = ()
    gold_relations: tuple[TemporalRelation, ...] = ()

    def answer(self, question: Question) -> Answer:
        """Answer by querying the gold-compiled base.

        Not implemented: requires the OE1 gold set (``src/afg/annotation/goldset.py``,
        itself pending the real corpus). Implement once ``build_gold_decisions`` and the
        cross-meeting relation annotation (``src/afg/annotation/linking.py``) have
        produced a real gold set for at least one series.
        """
        raise NotImplementedError(
            "CompiledGoldCondition.answer requires a real OE1 gold set (thesis section "
            "3, OE1; section 5.3, C3). Build the gold set via "
            "src/afg/annotation/goldset.py first."
        )
