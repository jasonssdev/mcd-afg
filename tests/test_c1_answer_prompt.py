"""Tests for C1's answer prompt: a generic conventional-RAG prompt, frozen and hash-pinned.

The wording adapts the widely used LangChain hub ``rlm/rag-prompt`` (see
``afg.conditions.c1_answer_prompt``). Any edit to the file changes what C1 sends to the
model, so it must come with a new pin here.
"""

from __future__ import annotations

import hashlib

import pytest

from afg.conditions import c1_answer_prompt
from afg.shared.config import load_experiments_config

_PINNED_SHA256 = "2764df018d82e31a39a6bb46590fcd892e9f4fdfa0934cb7cb5adcbe68edbd60"


class TestAnswerPromptFile:
    def test_file_bytes_match_the_pinned_hash(self) -> None:
        raw = c1_answer_prompt.answer_prompt()
        assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == _PINNED_SHA256

    def test_module_constant_pins_the_same_hash(self) -> None:
        assert c1_answer_prompt.PINNED_SHA256 == _PINNED_SHA256

    def test_prompt_states_the_fixed_abstention_sentence_and_the_citation_form(self) -> None:
        text = c1_answer_prompt.answer_prompt()
        assert "{{" not in text
        assert c1_answer_prompt.ABSTENTION_SENTENCE in text
        assert "[1]" in text

    def test_sent_prompt_hash_is_full_sha256_of_utf8_bytes(self) -> None:
        text = c1_answer_prompt.answer_prompt()
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert c1_answer_prompt.sent_prompt_sha256(text) == expected
        assert len(expected) == 64


class TestAbstentionDetection:
    @pytest.mark.parametrize(
        "reply",
        [
            "I don't know.",
            "I don't know",
            '  "I don\'t know."  ',
            "I DON'T KNOW!",
            "**I don't know.**",
            "I don\u2019t know.",
        ],
    )
    def test_the_fixed_sentence_modulo_case_quotes_and_punctuation_abstains(
        self, reply: str
    ) -> None:
        assert c1_answer_prompt.is_abstention(reply) is True

    @pytest.mark.parametrize(
        "reply",
        [
            "I don't know the exact price, but it was about 25 euros [1].",
            "The PM said I don't know.",
            "",
            "Twenty five euros [1].",
        ],
    )
    def test_anything_else_is_an_answer(self, reply: str) -> None:
        assert c1_answer_prompt.is_abstention(reply) is False


class TestSharedAnswerBudget:
    """config/experiments.toml mirrors the parameters ``openkos query`` answers with."""

    def test_shared_budget_matches_openkos_answer_defaults(self) -> None:
        budget = load_experiments_config()["shared_budget"]
        assert budget["generative_model"] == "qwen3:8b"
        assert budget["embedding_model"] == "bge-m3"
        assert budget["context_window_tokens"] == 12288
        assert budget["max_generation_tokens"] == 8192

    def test_sufficiency_model_is_the_openkos_packaged_default(self) -> None:
        """The model OpenKOS uses for the sufficiency check of C2 and C3 (ADR 0006)."""
        openkos_config = pytest.importorskip("openkos.config")
        budget = load_experiments_config()["shared_budget"]
        assert budget["sufficiency_model"] == openkos_config.DEFAULT_TASK_MODELS["sufficiency"]
        assert budget["sufficiency_model"] == openkos_config.DEFAULT_JUDGE_MODEL

    def test_sampling_is_pinned_explicitly(self) -> None:
        budget = load_experiments_config()["shared_budget"]
        assert isinstance(budget["temperature"], float)
        assert isinstance(budget["seed"], int)

    def test_retrieval_mirrors_openkos_fusion(self) -> None:
        retrieval = load_experiments_config()["retrieval"]
        assert retrieval["answer_limit"] == 5
        assert retrieval["rrf_k"] == 60
