"""Condition interface shared by C1/C2/C3 (thesis section 5.3)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from afg.domain.question import Answer, Question


@runtime_checkable
class Condition(Protocol):
    """Anything that can answer a :class:`~afg.domain.question.Question`.

    Implementations must share the generative model, embedding model, hardware, and
    context budget declared in ``config/experiments.toml`` (thesis section 5.3) -- this
    protocol does not enforce that at the type level, but ``src/afg/cli.py`` wires all
    three conditions from the same loaded config so they cannot silently drift apart.
    """

    condition_id: str

    def answer(self, question: Question) -> Answer:
        """Produce an answer (or an explicit abstention) for ``question``."""
        ...
