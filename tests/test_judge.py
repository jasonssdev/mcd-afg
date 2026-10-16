"""Tests for the judge guard and ``judge_answer`` (thesis section 5.7). No network."""

from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.judge import (
    JudgeConfigurationError,
    JudgeFailure,
    JudgeVerdict,
    MissingTranscriptExcerptError,
    OllamaJudgeBackend,
    judge_answer,
    list_installed_models,
    missing_models,
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

    def test_flag_false_allows_the_same_model(self) -> None:
        require_distinct_model_families("qwen3:8b", "qwen3:8b", must_differ=False)

    def test_flag_false_still_requires_a_judge(self) -> None:
        with pytest.raises(JudgeConfigurationError):
            require_distinct_model_families("", "qwen3:8b", must_differ=False)

    def test_flag_true_rejects_the_same_model(self) -> None:
        with pytest.raises(JudgeConfigurationError):
            require_distinct_model_families("qwen3:8b", "qwen3:8b", must_differ=True)

    @pytest.mark.parametrize("flag", [True, False])
    def test_default_honors_the_configured_flag(
        self, monkeypatch: pytest.MonkeyPatch, flag: bool
    ) -> None:
        monkeypatch.setattr(
            "afg.evaluation.judge.load_experiments_config",
            lambda: {"judge": {"must_differ_from_generative_model": flag}},
        )
        if flag:
            with pytest.raises(JudgeConfigurationError):
                require_distinct_model_families("qwen3:8b", "qwen3:8b")
        else:
            require_distinct_model_families("qwen3:8b", "qwen3:8b")


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

    def test_transcript_excerpt_is_a_section_with_a_fixed_position(self) -> None:
        reference_first, answer_first = FakeBackend(), FakeBackend()
        _judge(reference_first, order="reference_first", transcript_excerpt="EXCERPT-TEXT")
        _judge(answer_first, order="answer_first", transcript_excerpt="EXCERPT-TEXT")
        for call in (reference_first.calls[0], answer_first.calls[0]):
            user = call["user"]
            assert "Transcript excerpt:\nEXCERPT-TEXT" in user
            assert user.index("QUESTION-TEXT") < user.index("EXCERPT-TEXT")
            assert user.index("EXCERPT-TEXT") < user.index("REFERENCE-TEXT")
            assert user.index("EXCERPT-TEXT") < user.index("ANSWER-TEXT")
        assert (
            reference_first.calls[0]["user"].split("EXCERPT-TEXT")[0]
            == (answer_first.calls[0]["user"].split("EXCERPT-TEXT")[0])
        )

    @pytest.mark.parametrize("excerpt", [None, ""])
    def test_missing_excerpt_is_stated_not_left_blank(self, excerpt: str | None) -> None:
        backend = FakeBackend()
        _judge(backend, transcript_excerpt=excerpt)
        user = backend.calls[0]["user"]
        assert "Transcript excerpt:\nNone: the material contains no answer" in user

    @pytest.mark.parametrize("excerpt", [None, "", "   "])
    def test_answerable_question_with_evidence_needs_an_excerpt(self, excerpt: str | None) -> None:
        backend = FakeBackend()
        question = _question().model_copy(
            update={
                "reference_evidence": (
                    EvidenceSpan(
                        meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.1",)
                    ),
                )
            }
        )
        with pytest.raises(MissingTranscriptExcerptError, match="q1"):
            judge_answer(
                question,
                _answer(),
                judge_model="m",
                generative_model="qwen3:8b",
                backend=backend,
                transcript_excerpt=excerpt,
            )
        assert backend.calls == []

    def test_answerable_question_with_an_excerpt_is_judged(self) -> None:
        question = _question().model_copy(
            update={
                "reference_evidence": (
                    EvidenceSpan(
                        meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.1",)
                    ),
                )
            }
        )
        backend = FakeBackend()
        judge_answer(
            question,
            _answer(),
            judge_model="m",
            generative_model="qwen3:8b",
            backend=backend,
            transcript_excerpt="EXCERPT-TEXT",
        )
        assert "Transcript excerpt:\nEXCERPT-TEXT" in backend.calls[0]["user"]

    def test_system_prompt_defines_both_fields_against_the_right_sources(self) -> None:
        backend = FakeBackend()
        _judge(backend)
        system = backend.calls[0]["system"]
        assert "transcript excerpt" in system.lower()
        assert "agrees with the reference answer" in system
        assert "supported by the transcript excerpt" in system
        assert "only if" in system and "abstains" in system

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

    def _chat_kwargs(
        self, monkeypatch: pytest.MonkeyPatch, backend: OllamaJudgeBackend, model: str
    ) -> dict[str, Any]:
        seen: dict[str, Any] = {}

        class FakeClient:
            def __init__(self, host: str) -> None: ...

            def chat(self, **kwargs: Any) -> Any:
                seen.update(kwargs)
                # A reasoning model returns its thinking apart from the JSON content.
                return types.SimpleNamespace(
                    message=types.SimpleNamespace(content=GOOD, thinking="long reasoning...")
                )

        monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=FakeClient))
        out = backend.complete(
            "S", "U", model=model, seed=1, temperature=0.0, format_schema={"type": "object"}
        )
        assert out == GOOD  # the content is parsed, never the thinking
        return seen

    def test_think_is_not_sent_unless_configured_for_the_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = OllamaJudgeBackend(host="h", think={"gpt-oss:20b": "low"})
        assert "think" not in self._chat_kwargs(monkeypatch, backend, "mistral-small3.2:24b")
        assert "think" not in self._chat_kwargs(monkeypatch, OllamaJudgeBackend(host="h"), "m")

    def test_configured_think_level_is_sent_together_with_the_json_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = OllamaJudgeBackend(host="h", think={"gpt-oss:20b": "low"})
        seen = self._chat_kwargs(monkeypatch, backend, "gpt-oss:20b")
        assert seen["think"] == "low" and seen["format"] == {"type": "object"}

    def test_think_false_is_sent_as_a_bool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = OllamaJudgeBackend(host="h", think={"m": False})
        assert self._chat_kwargs(monkeypatch, backend, "m")["think"] is False

    def test_missing_llm_extra_gives_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "ollama", None)
        with pytest.raises(RuntimeError, match="llm"):
            OllamaJudgeBackend(host="http://h:1").complete(
                "s", "u", model="m", seed=1, temperature=0.0, format_schema={}
            )


class TestInstalledModels:
    def test_lists_the_models_the_server_reports(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakeClient:
            def __init__(self, host: str) -> None: ...

            def list(self) -> Any:
                names = ["mistral-small3.2:24b", "qwen3:8b"]
                return types.SimpleNamespace(models=[types.SimpleNamespace(model=n) for n in names])

        monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=FakeClient))
        assert list_installed_models(host="h") == ["mistral-small3.2:24b", "qwen3:8b"]

    def test_missing_llm_extra_gives_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "ollama", None)
        with pytest.raises(RuntimeError, match="llm"):
            list_installed_models(host="h")

    def test_missing_models_reports_only_the_absent_ones_in_order(self) -> None:
        installed = ["mistral-small3.2:24b", "qwen3:8b"]
        wanted = ["mistral-small3.2:24b", "atla/selene-mini:q8_0", "gpt-oss:20b"]
        assert missing_models(wanted, installed) == ["atla/selene-mini:q8_0", "gpt-oss:20b"]

    def test_an_untagged_name_means_latest(self) -> None:
        assert missing_models(["bge-m3"], ["bge-m3:latest"]) == []
        assert missing_models(["bge-m3:latest"], ["bge-m3"]) == []
        assert missing_models(["bge-m3:q8"], ["bge-m3:latest"]) == ["bge-m3:q8"]


def test_configured_judge_is_the_one_selected_by_calibration() -> None:
    """``[judge].model`` pins the model that the calibration chose (notebook 05)."""
    from afg.evaluation.judge_calibration_results import load_calibration_results
    from afg.shared.config import load_experiments_config
    from afg.shared.paths import REPORTS_DIR

    config = load_experiments_config()
    stored = load_calibration_results(REPORTS_DIR / "judge-calibration" / "resultados.json")
    assert stored.selected is not None
    assert config["judge"]["model"] == stored.selected
    require_distinct_model_families(
        config["judge"]["model"], config["shared_budget"]["generative_model"]
    )
