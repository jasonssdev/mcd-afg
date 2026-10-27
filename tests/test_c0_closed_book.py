"""Tests for the closed-book diagnostic condition. No Ollama: the chat backend is a fake."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from afg.conditions.base import Condition
from afg.conditions.c0_closed_book import (
    CLOSED_BOOK_SYSTEM_PROMPT,
    ClosedBookCondition,
    EvaluationSeriesError,
    require_development_series,
)
from afg.conditions.c1_document_rag import GenerationSettings
from afg.domain.question import Question, QuestionStratum

SETTINGS = GenerationSettings(
    model="qwen3:8b",
    temperature=0.1,
    seed=42,
    context_window=12288,
    max_generation_tokens=8192,
)


class ScriptedChat:
    def __init__(self, reply: str = "Twenty five Euros.") -> None:
        self._reply = reply
        self.calls: list[dict[str, Any]] = []

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, model: str, options: Mapping[str, Any]
    ) -> str:
        self.calls.append(
            {"messages": [dict(m) for m in messages], "model": model, "options": dict(options)}
        )
        return self._reply


def _question(series: str = "ES2015") -> Question:
    return Question(
        id=f"{series}.q001",
        series_id=series,
        stratum=QuestionStratum.E1_POINT_FACT,
        text="What selling price was set for the remote control?",
        reference_answer="Twenty-five Euros.",
    )


def test_is_a_condition_with_a_distinct_id() -> None:
    condition = ClosedBookCondition(chat=ScriptedChat(), settings=SETTINGS)
    assert isinstance(condition, Condition)
    assert condition.condition_id == "C0"


def test_sends_only_the_question_with_no_context() -> None:
    chat = ScriptedChat()
    ClosedBookCondition(chat=chat, settings=SETTINGS).answer(_question())
    (call,) = chat.calls  # one call: nothing to check for sufficiency
    system, user = call["messages"]
    assert system == {"role": "system", "content": CLOSED_BOOK_SYSTEM_PROMPT}
    assert user == {"role": "user", "content": _question().text}
    assert "CONTEXT" not in user["content"]


def test_uses_the_shared_generation_settings() -> None:
    chat = ScriptedChat()
    ClosedBookCondition(chat=chat, settings=SETTINGS).answer(_question())
    (call,) = chat.calls
    assert call["model"] == "qwen3:8b"
    assert call["options"] == SETTINGS.options


def test_the_answer_carries_the_reply_and_no_citations() -> None:
    answer = ClosedBookCondition(
        chat=ScriptedChat("  Twenty five Euros.\n"), settings=SETTINGS
    ).answer(_question())
    assert answer.condition == "C0"
    assert answer.question_id == "ES2015.q001"
    assert answer.text == "Twenty five Euros."
    assert answer.cited_evidence == ()
    assert answer.abstained is False


def test_with_seed_changes_only_the_seed() -> None:
    chat = ScriptedChat()
    condition = ClosedBookCondition(chat=chat, settings=SETTINGS)
    reseeded = condition.with_seed(44)
    reseeded.answer(_question())
    assert chat.calls[0]["options"]["seed"] == 44
    assert reseeded.settings == dataclasses.replace(SETTINGS, seed=44)
    assert condition.settings.seed == 42


def test_development_series_pass_the_guard() -> None:
    require_development_series([_question("ES2015")], frozenset({"ES2015"}))


def test_evaluation_or_unknown_series_are_refused() -> None:
    with pytest.raises(EvaluationSeriesError, match="IS1009"):
        require_development_series(
            [_question("ES2015"), _question("IS1009")], frozenset({"ES2015"})
        )
