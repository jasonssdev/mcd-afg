"""C2 -- structured base built automatically by LLM extraction (thesis section 5.3).

The proposal under test: extraction with a local model, persistence with provenance,
querying over the compiled objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from afg.domain.question import Answer, Question
from afg.extraction.protocol import Extractor


@dataclass(slots=True)
class CompiledAutoCondition:
    """C2: query over a base compiled automatically by an :class:`Extractor`."""

    condition_id: str = "C2"
    extractor: Extractor | None = None

    def answer(self, question: Question) -> Answer:
        """Answer by querying the automatically compiled base.

        Not implemented: requires a populated compiled base, which requires a working
        :class:`~afg.extraction.protocol.Extractor` (see
        ``src/afg/extraction/openkos_adapter.py``, itself pending the real corpus and the
        `instrument` optional dependency). Implement once extraction runs end-to-end over
        at least one series.
        """
        raise NotImplementedError(
            "CompiledAutoCondition.answer requires a populated compiled base from a "
            "working Extractor (thesis section 5.3, C2; section 5.9 for the OpenKOS "
            "instrument boundary). Run paso cero and wire up "
            "src/afg/extraction/openkos_adapter.py first."
        )
