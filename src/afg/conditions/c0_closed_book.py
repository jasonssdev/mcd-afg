"""C0 -- closed-book diagnostic (development only; NOT a thesis condition).

C0 answers each question with NO retrieved context, using the generative model and the
sampling settings of C1 (``[shared_budget]``). It exists to (1) give the simplest possible
baseline and (2) measure whether the model already knows the AMI scenario (contamination).
It is not part of the C1/C2/C3 set of thesis section 5.3: it is kept out of
``EXPERIMENT_B_CONDITIONS``, so ``afg experiment b`` cannot run it, and it only runs on
development series (ADR 0005).

Prompt choice. C1 answers with ``prompts/answer/system.md``, whose first instruction is to use
ONLY the numbered CONTEXT and "do not use outside knowledge", and whose last one is the
``USED:`` attribution line over the context blocks. With an empty context that prompt would
forbid the very thing this diagnostic measures (what the model knows) and ask for citations of
nothing. The closest faithful equivalent therefore keeps C1's remaining behaviour -- prose
only, an honest "I do not know" instead of guessing -- and drops the context-bound parts: the
user message is the bare question (C1's ``CONTEXT:``/``QUESTION:`` frame without any block) and
no sufficiency call is made, since there is nothing to judge sufficient. The only difference
from C1 is the missing context.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from afg.conditions.c1_document_rag import ChatBackend, GenerationSettings
from afg.domain.question import Answer, Question

CLOSED_BOOK_SYSTEM_PROMPT = (
    "You are a knowledge assistant. Answer the question from what you already know; no "
    "document or other context is provided. Write prose only. If you do not know the answer, "
    "say so plainly rather than guessing."
)


class EvaluationSeriesError(ValueError):
    """Raised when the diagnostic is asked to run on a series that is not a development one."""


def require_development_series(questions: Iterable[Question], development: frozenset[str]) -> None:
    """Refuse any question whose series is outside the development split (ADR 0005)."""
    outside = sorted({q.series_id for q in questions} - development)
    if outside:
        raise EvaluationSeriesError(
            f"El diagnóstico sin contexto solo corre sobre series de desarrollo (ADR 0005); "
            f"no admite: {', '.join(outside)}."
        )


@dataclass(slots=True)
class ClosedBookCondition:
    """C0: the C1 generative model answering with no retrieved context."""

    chat: ChatBackend
    settings: GenerationSettings
    condition_id: str = "C0"

    def with_seed(self, seed: int) -> ClosedBookCondition:
        """A copy that generates with ``seed`` (a run index of Experiment B) and nothing else."""
        return dataclasses.replace(self, settings=dataclasses.replace(self.settings, seed=seed))

    def answer(self, question: Question) -> Answer:
        """Ask the model the bare question; the reply is the answer, with no citations."""
        reply = self.chat.chat(
            [
                {"role": "system", "content": CLOSED_BOOK_SYSTEM_PROMPT},
                {"role": "user", "content": question.text},
            ],
            model=self.settings.model,
            options=self.settings.options,
        )
        return Answer(question_id=question.id, condition=self.condition_id, text=reply.strip())
