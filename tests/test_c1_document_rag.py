"""Tests for C1's answer orchestration (ADR 0006). No Ollama, no corpus: backends are fakes."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from afg.conditions.base import Condition
from afg.conditions.c1_answer_prompt import (
    ABSTENTION_SENTENCE,
    answer_prompt,
    sent_prompt_sha256,
)
from afg.conditions.c1_chunking import chunk_meetings
from afg.conditions.c1_document_rag import (
    NO_MATCH,
    AnswerTrace,
    ChatError,
    ChatUnavailableError,
    DocumentRagCondition,
    GenerationSettings,
    OllamaChatBackend,
    assemble_context,
    body_budget,
    parse_citations,
    strip_concept_id_scaffolding,
)
from afg.conditions.c1_tuning import PinnedC1Params
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.evaluation.chunk_acts import ChunkActMapper

from .frozen_fixtures import write_frozen_meeting

SETTINGS = GenerationSettings(
    model="qwen3:8b",
    temperature=0.1,
    seed=42,
    context_window=12288,
    max_generation_tokens=8192,
)
PARAMS = PinnedC1Params(chunk_size=50, chunk_overlap=0, k=2)


def _write_meeting(directory: Path, meeting_id: str, turns: Sequence[str]) -> None:
    write_frozen_meeting(
        directory, meeting_id, [(text, (f"{meeting_id}.d{i}",)) for i, text in enumerate(turns)]
    )


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
        annotator=kw.pop("annotator", ChunkActMapper(transcripts)),
        **kw,
    )


def _user_message(chat: ScriptedChat) -> str:
    (call,) = chat.calls
    return str(call["messages"][1]["content"])


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


# --- the one-call flow ------------------------------------------------------------------


def test_answer_makes_one_call_with_the_generic_prompt_and_the_shared_user_message(
    transcripts: Path,
) -> None:
    chat = ScriptedChat("Twenty five euros [1].")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())

    (call,) = chat.calls
    assert [m["role"] for m in call["messages"]] == ["system", "user"]
    assert call["messages"][0]["content"] == answer_prompt()
    user = call["messages"][1]["content"]
    assert user.startswith("CONTEXT:\n\n[1] [concept_id: ")
    assert "\n\n[2] [concept_id: " in user
    assert user.endswith("\n\nQUESTION:\nwhat does the remote control cost?")
    assert call["model"] == "qwen3:8b"
    assert answer.condition == "C1"
    assert answer.question_id == "q1"
    assert answer.text == "Twenty five euros [1]."
    assert answer.abstained is False
    assert trace.outcome == "answered"


def test_every_call_sends_the_fixed_options(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1]")
    _condition(transcripts, chat).answer(_question())
    assert chat.calls[0]["options"] == SETTINGS.options


def test_there_is_no_sufficiency_call_or_trace_field() -> None:
    names = {f.name for f in dataclasses.fields(AnswerTrace)}
    assert not {n for n in names if "sufficiency" in n}
    assert "sufficiency_check" not in {f.name for f in dataclasses.fields(DocumentRagCondition)}
    assert not hasattr(GenerationSettings, "sufficiency_model")


def test_trace_hashes_are_those_of_the_prompts_as_sent(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1]")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.system_sha256 == sent_prompt_sha256(answer_prompt())
    assert trace.user_sha256 == sent_prompt_sha256(_user_message(chat))
    assert trace.raw_reply == "answer [1]"
    assert trace.model == "qwen3:8b"
    assert (trace.temperature, trace.seed) == (0.1, 42)
    assert (trace.context_window, trace.max_generation_tokens) == (12288, 8192)


def test_trace_blocks_are_exactly_the_numbered_text_sent(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1]")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    user = _user_message(chat)
    assert [b.index for b in trace.context_blocks] == [1, 2]
    for block in trace.context_blocks:
        assert f"[{block.index}] {block.text}" in user
        assert block.text.startswith(f"[concept_id: {block.chunk_id} — {block.meeting_id}]\n")
    assert [r.chunk_id for r in trace.retrieved] == [b.chunk_id for b in trace.context_blocks]
    assert [r.rank for r in trace.retrieved] == [1, 2]
    assert trace.omitted == ()


def test_trace_is_json_serialisable(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1]")
    _, trace = _condition(transcripts, chat).answer_with_trace(_question())
    json.dumps(dataclasses.asdict(trace))


# --- inline [n] citations --------------------------------------------------------------


def test_citations_are_the_acts_of_the_blocks_cited_inline(transcripts: Path) -> None:
    chat = ScriptedChat("It costs twenty five euros [2].")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    cited = trace.context_blocks[1]
    assert trace.used_indices == (2,)
    assert trace.attribution == "reported"
    assert trace.cited_chunk_ids == (cited.chunk_id,)
    assert answer.cited_evidence
    cited_acts = {a for span in answer.cited_evidence for a in span.dialogue_act_ids}
    assert cited_acts == set(trace.cited_acts[cited.chunk_id])


def test_cited_acts_come_from_the_evaluator_mapping_of_the_chunk_span(
    transcripts: Path,
) -> None:
    chat = ScriptedChat("It costs twenty five euros [1].")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    block = trace.context_blocks[0]
    chunk = next(
        c
        for c in chunk_meetings(["ES2015a", "ES2015b"], 50, 0, transcripts)
        if c.chunk_id == block.chunk_id
    )
    expected = ChunkActMapper(transcripts).acts_of(chunk)
    assert expected  # the fixture carries one act per turn
    assert trace.cited_acts == {chunk.chunk_id: expected}
    assert answer.cited_evidence == (
        EvidenceSpan(meeting_id=chunk.meeting_id, dialogue_act_ids=expected),
    )
    assert (block.char_start, block.char_end) == (chunk.char_start, chunk.char_end)


def test_c1_answers_without_any_jsonl(transcripts: Path) -> None:
    """C1 reads only the Markdown: the turn structure is never needed to retrieve or answer."""
    for path in transcripts.glob("*.jsonl"):
        path.unlink()
    chat = ScriptedChat("It costs twenty five euros [1].")
    condition = _condition(transcripts, chat, annotator=None)
    answer, trace = condition.answer_with_trace(_question())
    assert answer.text == "It costs twenty five euros [1]."
    assert trace.cited_chunk_ids
    assert trace.cited_acts == {}
    assert answer.cited_evidence == ()
    prompt = _user_message(chat)
    assert "PM: the remote control costs twenty five euros" in prompt


def test_a_reply_without_markers_cites_nothing(transcripts: Path) -> None:
    chat = ScriptedChat("answer without citations")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.attribution == "absent"
    assert trace.used_indices == ()
    assert trace.cited_chunk_ids == ()
    assert answer.cited_evidence == ()
    assert answer.abstained is False
    assert answer.text == "answer without citations"


def test_out_of_range_markers_are_ignored(transcripts: Path) -> None:
    chat = ScriptedChat("answer [99] [0]")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert trace.attribution == "absent"
    assert trace.cited_chunk_ids == ()
    assert answer.cited_evidence == ()


def test_parse_citations_dedups_orders_and_bounds() -> None:
    assert parse_citations("a [2] b [1][2] c [1, 3]", 3) == (1, 2, 3)
    assert parse_citations("a [3] b [4] [0]", 3) == (3,)
    assert parse_citations("no markers, a list [x] and (2)", 3) == ()


def test_citations_group_dialogue_acts_by_meeting(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1][2][3][4][5][6][7][8]")
    answer, _ = _condition(transcripts, chat, params=PinnedC1Params(50, 0, 8)).answer_with_trace(
        _question()
    )
    meetings = [span.meeting_id for span in answer.cited_evidence]
    assert meetings == sorted(set(meetings)) == ["ES2015a", "ES2015b"]
    assert all(isinstance(span, EvidenceSpan) for span in answer.cited_evidence)


def test_strip_concept_id_scaffolding_removes_leaked_labels() -> None:
    text = "It costs 25 [concept_id: ES2015a.c000 — ES2015a] euros."
    assert strip_concept_id_scaffolding(text) == "It costs 25 euros."
    assert strip_concept_id_scaffolding("clean text") == "clean text"


# --- abstention ------------------------------------------------------------------------


@pytest.mark.parametrize("reply", [ABSTENTION_SENTENCE, "i don't know", ' "I don\'t know!" '])
def test_the_fixed_sentence_is_an_abstention(transcripts: Path, reply: str) -> None:
    chat = ScriptedChat(reply)
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question("who won?"))
    assert len(chat.calls) == 1
    assert answer.abstained is True
    assert answer.text == reply.strip()
    assert answer.cited_evidence == ()
    assert trace.outcome == "no_answer_in_context"
    assert trace.raw_reply == reply
    assert trace.system_sha256 == sent_prompt_sha256(answer_prompt())
    assert trace.cited_chunk_ids == ()
    assert trace.context_blocks


def test_a_reply_that_merely_contains_the_sentence_is_an_answer(transcripts: Path) -> None:
    chat = ScriptedChat("I don't know exactly, but about 25 euros [1].")
    answer, trace = _condition(transcripts, chat).answer_with_trace(_question())
    assert answer.abstained is False
    assert trace.outcome == "answered"
    assert trace.cited_chunk_ids


def test_a_blank_question_is_a_no_match_without_any_call(transcripts: Path) -> None:
    chat = ScriptedChat()
    embedder = CountingEmbedder()
    answer, trace = _condition(transcripts, chat, embedder).answer_with_trace(_question("   "))
    assert chat.calls == []
    assert embedder.calls == []
    assert answer.abstained is True
    assert answer.text == NO_MATCH
    assert trace.outcome == "no_match"


def test_fatal_backend_failure_propagates(transcripts: Path) -> None:
    chat = ScriptedChat(ChatUnavailableError("ollama is down"))
    with pytest.raises(ChatUnavailableError):
        _condition(transcripts, chat).answer(_question())


def test_generation_failure_propagates(transcripts: Path) -> None:
    chat = ScriptedChat(ChatError("capped"))
    with pytest.raises(ChatError):
        _condition(transcripts, chat).answer(_question())


# --- index -----------------------------------------------------------------------------


def test_index_covers_the_whole_series_and_nothing_else(transcripts: Path) -> None:
    chat = ScriptedChat("a [1]", "b [1]")
    _, trace = _condition(transcripts, chat, params=PinnedC1Params(50, 0, 8)).answer_with_trace(
        _question()
    )
    meetings = {r.meeting_id for r in trace.retrieved}
    assert meetings == {"ES2015a", "ES2015b"}


def test_index_is_built_once_per_series(transcripts: Path) -> None:
    chat = ScriptedChat("a [1]", "b [1]", "c [1]")
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
    chat = ScriptedChat("answer [1]")
    tight = dataclasses.replace(SETTINGS, context_window=8192 + 1600)
    _, trace = _condition(
        tmp_path, chat, settings=tight, params=PinnedC1Params(5000, 0, 2)
    ).answer_with_trace(_question("word1?"))
    assert trace.context_blocks
    assert all(b.excerpted for b in trace.context_blocks)
    sent = _user_message(chat)
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


def test_assemble_context_is_what_the_condition_sends(tmp_path: Path) -> None:
    long_turns = [f"word{i} " * 600 for i in range(2)]
    _write_meeting(tmp_path, "ES2015a", long_turns)
    chat = ScriptedChat("answer [1]")
    tight = dataclasses.replace(SETTINGS, context_window=8192 + 1600)
    _, trace = _condition(
        tmp_path, chat, settings=tight, params=PinnedC1Params(5000, 0, 2)
    ).answer_with_trace(_question("word1?"))
    chunks = chunk_meetings(["ES2015a"], 5000, 0, tmp_path)
    by_id = {c.chunk_id: c for c in chunks}
    retrieved = [by_id[b.chunk_id] for b in trace.context_blocks]
    blocks, kept, omitted = assemble_context(
        "word1?",
        retrieved,
        context_window=tight.context_window,
        max_generation_tokens=tight.max_generation_tokens,
    )
    assert blocks == [b.text for b in trace.context_blocks]
    assert [c for c, _ in kept] == retrieved
    assert omitted == []


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


def test_with_seed_changes_only_the_seed_and_shares_the_index(transcripts: Path) -> None:
    chat = ScriptedChat("answer [1]", "answer [1]")
    embedder = CountingEmbedder()
    base = _condition(transcripts, chat, embedder)
    base.answer(_question())
    embedded = len(embedder.calls)
    reseeded = base.with_seed(SETTINGS.seed + 1)
    answer, trace = reseeded.answer_with_trace(_question())
    assert trace.seed == SETTINGS.seed + 1
    assert chat.calls[-1]["options"]["seed"] == SETTINGS.seed + 1
    assert base.settings.seed == SETTINGS.seed  # the original is untouched
    assert len(embedder.calls) == embedded + 1  # only the new question is embedded
    assert answer.condition == base.condition_id


# --- body budget equals the one OpenKOS plans for C2 (ADR 0007, decision 3) ------------


def test_body_budget_equals_the_budget_openkos_plans_for_the_same_question() -> None:
    """C1 and C2 share a TEXT budget by construction: C1 charges OpenKOS's own prompt
    overhead (its larger system prompt) instead of its own shorter generic prompt."""
    from openkos import prompt_budget
    from openkos.retrieval.answer import _SUFFICIENCY_PROMPT, _SYSTEM_PROMPT, _user_content

    question = "What selling price was set for the remote control?"
    labels = [f"[concept_id: ES2015a-c{i} — ES2015a]\n" for i in range(5)]
    expected = prompt_budget.budget_chars(
        planning=12288,
        generation_reserve_tokens=8192,
        overhead_chars=len(_user_content(labels, question))
        + max(len(_SYSTEM_PROMPT), len(_SUFFICIENCY_PROMPT)),
    )
    assert body_budget(labels, question, context_window=12288, max_generation_tokens=8192) == (
        expected
    )
    # The generic C1 prompt is shorter, so charging it would have left MORE room than C2 has.
    assert len(answer_prompt()) < max(len(_SYSTEM_PROMPT), len(_SUFFICIENCY_PROMPT))
