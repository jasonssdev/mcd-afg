"""Tests for the judge guard and ``judge_answer`` (thesis section 5.7). No network."""

from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.judge import (
    JudgeConfigurationError,
    JudgeFailure,
    JudgeVerdict,
    OllamaJudgeBackend,
    judge_answer,
    require_distinct_model_families,
)

GOOD = json.dumps({"correct": True, "evidence_supported": False, "rationale": "matches"})


class FakeBackend:
    def __init__(self, reply: str = GOOD) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        seed: int,
        temperature: float,
        format_schema: dict[str, Any],
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "model": model,
                "seed": seed,
                "temperature": temperature,
                "format_schema": format_schema,
            }
        )
        return self.reply


def _question(stratum: QuestionStratum = QuestionStratum.E1_POINT_FACT) -> Question:
    reference = None if stratum is QuestionStratum.E4_UNANSWERABLE else "REFERENCE-TEXT"
    return Question(
        id="q1",
        series_id="ES2015",
        stratum=stratum,
        text="QUESTION-TEXT",
        reference_answer=reference,
    )


def _answer(**kwargs: Any) -> Answer:
    return Answer(question_id="q1", condition="C2", text="ANSWER-TEXT", **kwargs)


def _judge(backend: FakeBackend, **kwargs: Any) -> JudgeVerdict | JudgeFailure:
    return judge_answer(
        _question(),
        _answer(),
        judge_model="mistral-small3.2:24b",
        generative_model="qwen3:8b",
        backend=backend,
        **kwargs,
    )


class TestGuard:
    def test_same_model_rejected(self) -> None:
        with pytest.raises(JudgeConfigurationError):
            require_distinct_model_families("qwen3:8b", "qwen3:8b")

    def test_empty_judge_rejected(self) -> None:
        with pytest.raises(JudgeConfigurationError):
            require_distinct_model_families("", "qwen3:8b")


class TestJudgeAnswer:
    def test_returns_validated_verdict(self) -> None:
        verdict = _judge(FakeBackend())
        assert verdict == JudgeVerdict("q1", "C2", True, False, None, "matches")

    def test_guard_runs_before_the_backend_is_called(self) -> None:
        backend = FakeBackend()
        with pytest.raises(JudgeConfigurationError):
            judge_answer(
                _question(),
                _answer(),
                judge_model="qwen3:8b",
                generative_model="qwen3:8b",
                backend=backend,
            )
        assert backend.calls == []

    def test_deterministic_parameters_and_schema_are_forwarded(self) -> None:
        backend = FakeBackend()
        _judge(backend, seed=7)
        call = backend.calls[0]
        assert call["model"] == "mistral-small3.2:24b"
        assert call["seed"] == 7
        assert call["temperature"] == 0.0
        assert set(call["format_schema"]["properties"]) == {
            "correct",
            "evidence_supported",
            "rationale",
        }

    def test_presentation_order_is_swappable(self) -> None:
        reference_first, answer_first = FakeBackend(), FakeBackend()
        _judge(reference_first, order="reference_first")
        _judge(answer_first, order="answer_first")
        a = reference_first.calls[0]["user"]
        b = answer_first.calls[0]["user"]
        assert a.index("REFERENCE-TEXT") < a.index("ANSWER-TEXT")
        assert b.index("ANSWER-TEXT") < b.index("REFERENCE-TEXT")
        assert "QUESTION-TEXT" in a and "QUESTION-TEXT" in b

    def test_condition_is_not_leaked_to_the_judge(self) -> None:
        backend = FakeBackend()
        _judge(backend)
        assert "C2" not in backend.calls[0]["user"]

    def test_unanswerable_reference_and_abstention_are_stated(self) -> None:
        backend = FakeBackend()
        judge_answer(
            _question(QuestionStratum.E4_UNANSWERABLE),
            _answer(abstained=True),
            judge_model="m",
            generative_model="qwen3:8b",
            backend=backend,
        )
        user = backend.calls[0]["user"]
        assert "REFERENCE-TEXT" not in user
        assert "no answer" in user.lower()
        assert "abstained" in user.lower()

    def test_unknown_order_rejected(self) -> None:
        with pytest.raises(ValueError):
            _judge(FakeBackend(), order="sideways")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("reply", "reason"),
        [
            ("not json at all", "invalid_json"),
            ("", "invalid_json"),
            ('{"correct": true}', "schema_violation"),
            (
                '{"correct": "yes", "evidence_supported": true, "rationale": "x"}',
                "schema_violation",
            ),
            ("[1, 2]", "schema_violation"),
        ],
    )
    def test_bad_output_becomes_a_typed_failure(self, reply: str, reason: str) -> None:
        result = _judge(FakeBackend(reply))
        assert isinstance(result, JudgeFailure)
        assert result.reason == reason
        assert result.raw_output == reply
        assert (result.question_id, result.condition) == ("q1", "C2")


class TestOllamaBackend:
    def test_calls_chat_with_schema_seed_and_zero_temperature(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        class FakeClient:
            def __init__(self, host: str) -> None:
                seen["host"] = host

            def chat(self, **kwargs: Any) -> Any:
                seen.update(kwargs)
                return types.SimpleNamespace(message=types.SimpleNamespace(content=GOOD))

        monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=FakeClient))
        out = OllamaJudgeBackend(host="http://h:1").complete(
            "SYS", "USR", model="m", seed=3, temperature=0.0, format_schema={"type": "object"}
        )
        assert out == GOOD
        assert seen["host"] == "http://h:1"
        assert seen["model"] == "m"
        assert seen["format"] == {"type": "object"}
        assert seen["options"] == {"temperature": 0.0, "seed": 3}
        assert seen["messages"] == [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "USR"},
        ]

    def test_missing_llm_extra_gives_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "ollama", None)
        with pytest.raises(RuntimeError, match="llm"):
            OllamaJudgeBackend(host="http://h:1").complete(
                "s", "u", model="m", seed=1, temperature=0.0, format_schema={}
            )
