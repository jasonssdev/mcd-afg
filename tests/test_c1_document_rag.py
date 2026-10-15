"""Tests for C1's answer orchestration (ADR 0006). No Ollama, no corpus: backends are fakes."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from afg.conditions.answer_prompts import (
    sent_prompt_sha256,
    sufficiency_prompt,
    system_prompt,
)
from afg.conditions.base import Condition
from afg.conditions.c1_document_rag import (
    NO_ANSWER_IN_CONTEXT,
    NO_MATCH,
    ChatError,
    ChatUnavailableError,
    DocumentRagCondition,
    GenerationSettings,
    OllamaChatBackend,
    split_attribution,
    strip_concept_id_scaffolding,
)
from afg.conditions.c1_tuning import PinnedC1Params
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum

SETTINGS = GenerationSettings(
    model="qwen3:8b",
    temperature=0.1,
    seed=42,
    context_window=12288,
    max_generation_tokens=8192,
)
PARAMS = PinnedC1Params(max_chars=120, overlap_turns=0, k=2)


def _write_meeting(directory: Path, meeting_id: str, turns: Sequence[str]) -> None:
    lines = [
        json.dumps(
            {
                "meeting_id": meeting_id,
                "turn_index": i,
                "speaker": "A",
                "role": "PM",
                "text": text,
                "start": None,
                "end": None,
                "char_start": i * 1000,
                "char_end": i * 1000 + len(text),
                "dialogue_act_ids": [f"{meeting_id}.d{i}"],
            }
        )
        for i, text in enumerate(turns)
    ]
    (directory / f"{meeting_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class CountingEmbedder:
    """Deterministic bag-of-letters embedder that counts calls."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(len(texts))
        return [
            [float(t.lower().count(c)) + 0.01 for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts
        ]


class ScriptedChat:
    """Replays scripted replies (or raises scripted errors) and records every call."""

    def __init__(self, *replies: str | Exception) -> None:
        self._replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def chat(
        self, messages: Sequence[Mapping[str, str]], *, model: str, options: Mapping[str, Any]
    ) -> str:
        self.calls.append(
            {"messages": [dict(m) for m in messages], "model": model, "options": dict(options)}
        )
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    _write_meeting(
        tmp_path,
        "ES2015a",
        [
            "the remote control costs twenty five euros",
            "we agreed on a kinetic energy source",
            "banana smoothie for lunch",
        ],
    )
    _write_meeting(tmp_path, "ES2015b", ["the logo is yellow", "the case is rubber"])
    _write_meeting(tmp_path, "IS1004a", ["unrelated series about cats"])
    return tmp_path


def _question(text: str = "what does the remote control cost?", series: str = "ES2015") -> Question:
    return Question(id="q1", series_id=series, stratum=QuestionStratum.E1_POINT_FACT, text=text)


def _condition(
    transcripts: Path, chat: ScriptedChat, embedder: CountingEmbedder | None = None, **kw: Any
) -> DocumentRagCondition:
    return DocumentRagCondition(
        chat=chat,
        embedder=embedder or CountingEmbedder(),
        settings=kw.pop("settings", SETTINGS),
        params=kw.pop("params", PARAMS),
        transcripts_dir=transcripts,
        **kw,
    )


# --- settings --------------------------------------------------------------------------


def test_settings_refuse_an_unfixed_temperature() -> None:
    with pytest.raises(ValueError, match="temperature"):
        dataclasses.replace(SETTINGS, temperature=None)


def test_settings_refuse_an_unfixed_seed() -> None:
    with pytest.raises(ValueError, match="seed"):
        dataclasses.replace(SETTINGS, seed=None)


def test_settings_from_config_match_the_experiment_budget() -> None:
    settings = GenerationSettings.from_config()
    assert settings.model == "qwen3:8b"
    assert settings.temperature == 0.1
    assert settings.seed == 42
    assert settings.context_window == 12288
    assert settings.max_generation_tokens == 8192


def test_ollama_options_are_the_four_openkos_sends() -> None:
    assert SETTINGS.options == {
        "num_predict": 8192,
        "temperature": 0.1,
        "seed": 42,
        "num_ctx": 12288,
    }


def test_condition_satisfies_the_condition_protocol(transcripts: Path) -> None:
    assert isinstance(_condition(transcripts, ScriptedChat()), Condition)


# --- the two-call flow -----------------------------------------------------------------


def test_answer_runs_sufficiency_then_synthesis_with_the_shared_user_message(
    transcripts: Path,
) -> None:
    chat = ScriptedChat("the remote control costs twenty five euros", "Twenty five euros.\nUSED: 1")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())

    assert len(chat.calls) == 2
    sufficiency, synthesis = chat.calls
    assert [m["role"] for m in sufficiency["messages"]] == ["system", "user"]
    assert sufficiency["messages"][0]["content"] == sufficiency_prompt()
    assert synthesis["messages"][0]["content"] == system_prompt()
    user = synthesis["messages"][1]["content"]
    assert sufficiency["messages"][1]["content"] == user
    assert user.startswith("CONTEXT:\n\n[1] [concept_id: ")
    assert "\n\n[2] [concept_id: " in user
    assert user.endswith("\n\nQUESTION:\nwhat does the remote control cost?")
    assert answer.condition == "C1"
    assert answer.question_id == "q1"
    assert answer.text == "Twenty five euros."
    assert answer.abstained is False
    assert trace.outcome == "answered"


def test_every_call_sends_the_model_and_the_fixed_options(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 1")
    _condition(transcripts, chat).answer(_question())
    for call in chat.calls:
        assert call["model"] == "qwen3:8b"
        assert call["options"] == SETTINGS.options


def test_trace_hashes_are_those_of_the_prompts_as_sent(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 1")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    user = chat.calls[1]["messages"][1]["content"]
    assert trace.system_sha256 == sent_prompt_sha256(system_prompt())
    assert trace.sufficiency_sha256 == sent_prompt_sha256(sufficiency_prompt())
    assert trace.user_sha256 == sent_prompt_sha256(user)
    assert trace.sufficiency_invoked is True
    assert trace.sufficiency_raw_reply == "quote"
    assert trace.model == "qwen3:8b"
    assert (trace.temperature, trace.seed) == (0.1, 42)
    assert (trace.context_window, trace.max_generation_tokens) == (12288, 8192)


def test_trace_blocks_are_exactly_the_numbered_text_sent(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 1")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    user = chat.calls[1]["messages"][1]["content"]
    assert [b.index for b in trace.context_blocks] == [1, 2]
    for block in trace.context_blocks:
        assert f"[{block.index}] {block.text}" in user
        assert block.text.startswith(f"[concept_id: {block.chunk_id} — {block.meeting_id}]\n")
    assert [r.chunk_id for r in trace.retrieved] == [b.chunk_id for b in trace.context_blocks]
    assert [r.rank for r in trace.retrieved] == [1, 2]
    assert trace.omitted == ()


def test_trace_is_json_serialisable(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 1")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    json.dumps(dataclasses.asdict(trace))


# --- USED: handling --------------------------------------------------------------------


def test_citations_are_the_acts_of_the_blocks_named_in_used(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 2")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    cited = trace.context_blocks[1]
    assert trace.used_indices == (2,)
    assert trace.attribution == "reported"
    assert trace.cited_chunk_ids == (cited.chunk_id,)
    assert answer.cited_evidence
    cited_acts = {a for span in answer.cited_evidence for a in span.dialogue_act_ids}
    assert cited_acts == set(trace.cited_acts[cited.chunk_id])
    assert "USED" not in answer.text


def test_missing_used_line_cites_every_block_sent(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer without attribution")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.attribution == "absent"
    assert trace.used_indices == ()
    assert len(trace.cited_chunk_ids) == 2
    assert answer.text == "answer without attribution"


def test_unusable_used_line_cites_every_block_and_is_still_stripped(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer\nUSED: 99")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.attribution == "unparsed"
    assert len(trace.cited_chunk_ids) == 2
    assert answer.text == "answer"


def test_used_none_cites_nothing_but_is_not_an_abstention(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "I do not know.\nUSED: none")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.attribution == "reported"
    assert trace.cited_chunk_ids == ()
    assert answer.cited_evidence == ()
    assert answer.abstained is False
    assert trace.outcome == "answered"


def test_citations_group_dialogue_acts_by_meeting(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "answer")
    answer, _ = _condition(transcripts, chat, params=PinnedC1Params(120, 0, 8)).answer_with_trace(
        _question()
    )
    meetings = [span.meeting_id for span in answer.cited_evidence]
    assert meetings == sorted(set(meetings)) == ["ES2015a", "ES2015b"]
    assert all(isinstance(span, EvidenceSpan) for span in answer.cited_evidence)


def test_split_attribution_last_marker_wins_and_is_stripped() -> None:
    prose, used, status = split_attribution("a\nUSED: 1\nb\nUSED: 2, 3", 3)
    assert (prose, used, status) == ("a\nUSED: 1\nb", frozenset({2, 3}), "reported")


def test_strip_concept_id_scaffolding_removes_leaked_labels() -> None:
    text = "It costs 25 [concept_id: ES2015a.c000 — ES2015a] euros."
    assert strip_concept_id_scaffolding(text) == "It costs 25 euros."
    assert strip_concept_id_scaffolding("clean text") == "clean text"


# --- abstention ------------------------------------------------------------------------


@pytest.mark.parametrize("reply", ["NONE", "none.", '  "None" ', "**NONE**"])
def test_sufficiency_none_abstains_without_synthesis(transcripts: Path, reply: str) -> None:
    chat = ScriptedChat(reply)
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question("who won?"))
    assert len(chat.calls) == 1
    assert answer.abstained is True
    assert answer.text == NO_ANSWER_IN_CONTEXT
    assert answer.cited_evidence == ()
    assert trace.outcome == "no_answer_in_context"
    assert trace.system_sha256 is None
    assert trace.user_sha256 is not None
    assert trace.context_blocks


def test_a_reply_that_merely_contains_none_is_not_a_refusal(transcripts: Path) -> None:
    chat = ScriptedChat("There is none left, said the PM.", "answer\nUSED: 1")
    answer, _ = _condition(transcripts, chat).answer_with_trace(_question())
    assert answer.abstained is False


def test_a_blank_question_is_a_no_match_without_any_call(transcripts: Path) -> None:
    chat = ScriptedChat()
    embedder = CountingEmbedder()
    answer, trace = _condition(transcripts, chat, embedder).answer_with_trace(_question("   "))
    assert chat.calls == []
    assert embedder.calls == []
    assert answer.abstained is True
    assert answer.text == NO_MATCH
    assert trace.outcome == "no_match"


def test_transient_sufficiency_failure_fails_open(transcripts: Path) -> None:
    chat = ScriptedChat(ChatError("boom"), "answer\nUSED: 1")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.sufficiency_degraded is True
    assert trace.sufficiency_raw_reply is None
    assert answer.abstained is False


def test_fatal_backend_failure_propagates(transcripts: Path) -> None:
    chat = ScriptedChat(ChatUnavailableError("ollama is down"))
    with pytest.raises(ChatUnavailableError):
        _condition(transcripts, chat).answer(_question())


def test_synthesis_failure_propagates(transcripts: Path) -> None:
    chat = ScriptedChat("quote", ChatError("capped"))
    with pytest.raises(ChatError):
        _condition(transcripts, chat).answer(_question())


# --- index -----------------------------------------------------------------------------


def test_index_covers_the_whole_series_and_nothing_else(transcripts: Path) -> None:
    chat = ScriptedChat("quote", "a\nUSED: 1", "quote", "b\nUSED: 1")
    _, trace = _condition(transcripts, chat, params=PinnedC1Params(120, 0, 8)).answer_with_trace(
        _question()
    )
    meetings = {r.meeting_id for r in trace.retrieved}
    assert meetings == {"ES2015a", "ES2015b"}


def test_index_is_built_once_per_series(transcripts: Path) -> None:
    chat = ScriptedChat("q", "a\nUSED: 1", "q", "b\nUSED: 1", "q", "c\nUSED: 1")
    embedder = CountingEmbedder()
    condition = _condition(transcripts, chat, embedder)
    condition.answer(_question("first?"))
    condition.answer(_question("second?"))
    # one batch for the chunks of ES2015, then one per question
    assert len(embedder.calls) == 3
    condition.answer(_question("cats?", series="IS1004"))
    assert len(embedder.calls) == 5  # IS1004 index + its question


def test_missing_series_transcripts_raise(transcripts: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _condition(transcripts, ScriptedChat()).answer(_question(series="TS3009"))


# --- context budget --------------------------------------------------------------------


def test_blocks_that_do_not_fit_the_window_are_excerpted(tmp_path: Path) -> None:
    long_turns = [f"word{i} " * 600 for i in range(2)]  # ~3,600 chars each
    _write_meeting(tmp_path, "ES2015a", long_turns)
    chat = ScriptedChat("quote", "answer\nUSED: 1")
    tight = dataclasses.replace(SETTINGS, context_window=8192 + 1600)
    _, trace = _condition(
        tmp_path, chat, settings=tight, params=PinnedC1Params(120, 0, 2)
    ).answer_with_trace(_question("word1?"))
    assert trace.context_blocks
    assert all(b.excerpted for b in trace.context_blocks)
    sent = chat.calls[1]["messages"][1]["content"]
    assert len(sent) < sum(len(t) for t in long_turns)


def test_blocks_with_no_room_are_omitted_and_never_cited(tmp_path: Path) -> None:
    _write_meeting(tmp_path, "ES2015a", ["some text here", "more text there"])
    chat = ScriptedChat()
    starved = dataclasses.replace(SETTINGS, context_window=8192 + 8)
    answer, trace = _condition(
        tmp_path, chat, settings=starved, params=PinnedC1Params(5000, 0, 2)
    ).answer_with_trace(_question())
    assert chat.calls == []
    assert trace.context_blocks == ()
    assert [o.reason for o in trace.omitted] == ["context_budget"]
    assert trace.retrieved
    assert answer.abstained is True
    assert answer.text == NO_MATCH
    assert trace.outcome == "no_match"


# --- Ollama backend --------------------------------------------------------------------


class FakeOllamaClient:
    def __init__(self, content: str = "hi", done_reason: str = "stop") -> None:
        self.kwargs: dict[str, Any] = {}
        self._content = content
        self._done_reason = done_reason

    def chat(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        message = type("Msg", (), {"content": self._content})()
        return type("Resp", (), {"message": message, "done_reason": self._done_reason})()


def test_ollama_backend_sends_think_false_and_the_options() -> None:
    client = FakeOllamaClient("reply")
    backend = OllamaChatBackend(client=client)
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert backend.chat(messages, model="qwen3:8b", options=SETTINGS.options) == "reply"
    assert client.kwargs["model"] == "qwen3:8b"
    assert client.kwargs["messages"] == messages
    assert client.kwargs["think"] is False
    assert client.kwargs["stream"] is False
    assert client.kwargs["options"] == SETTINGS.options


def test_ollama_backend_raises_when_generation_is_capped() -> None:
    backend = OllamaChatBackend(client=FakeOllamaClient("cut", done_reason="length"))
    with pytest.raises(ChatError, match="length"):
        backend.chat([{"role": "user", "content": "u"}], model="m", options={})
