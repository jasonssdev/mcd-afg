"""C1 -- document RAG over raw transcripts (thesis section 5.3, "floor" condition).

Must be an honest baseline: segmentation parameters and retrieved-fragment count are to be
tuned on a separate development set, not fixed arbitrarily (thesis section 5.3) -- a
weakened baseline invalidates the whole experiment.
"""

from __future__ import annotations

from dataclasses import dataclass

from afg.domain.question import Answer, Question


@dataclass(slots=True)
class DocumentRagCondition:
    """C1: hybrid lexical + dense retrieval over rendered meeting transcripts."""

    condition_id: str = "C1"
    top_k: int = 8

    def answer(self, question: Question) -> Answer:
        """Answer via hybrid retrieval over transcripts.

        Not implemented: requires a real retrieval index (BM25 + dense embeddings) built
        over rendered transcripts, which in turn requires the AMI corpus to be
        downloaded and ``src/afg/corpus/transcripts.py`` to be validated against it, plus
        the development-set tuning pass required by thesis section 5.3 for an honest
        baseline. Implement after paso cero (thesis section 5.0) and after the `retrieval`
        optional dependency group is wired up.
        """
        raise NotImplementedError(
            "DocumentRagCondition.answer requires a tuned hybrid retrieval index over "
            "real AMI transcripts (thesis section 5.3, C1). Run paso cero first, then "
            "build and tune the index on a development split before answering questions."
        )
