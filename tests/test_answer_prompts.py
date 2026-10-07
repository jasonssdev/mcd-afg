"""Tests for the answer prompts C1 copies byte for byte from OpenKOS (ADR 0006).

C2 and C3 answer through ``openkos query``; C1 must answer with the exact same two system
prompts so that any difference between conditions comes from the retrieved material, not
from the instructions. The pinned SHA-256 values are those of
``src/openkos/prompts/answer/{system,sufficiency}.md`` at openkos commit ``473b3fbb``.
"""

from __future__ import annotations

import hashlib

import pytest

from afg.conditions import answer_prompts
from afg.shared.config import load_experiments_config

_PINNED_RAW_SHA256 = {
    "system": "9cbf11e8ac9f8220253b233f1475b5cea9716b86b5868ce78ae31b235917119c",
    "sufficiency": "afc4644b27500c2cd69ea6c28919275d5447baaf7ce8ff938e9de7add7936f56",
}


class TestCopiedPromptFiles:
    @pytest.mark.parametrize("name", ["system", "sufficiency"])
    def test_file_bytes_match_the_pinned_openkos_hash(self, name: str) -> None:
        raw = answer_prompts.read_raw_prompt(name)
        assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == _PINNED_RAW_SHA256[name]

    def test_module_constants_pin_the_same_hashes(self) -> None:
        assert answer_prompts.PINNED_RAW_SHA256 == _PINNED_RAW_SHA256


class TestRenderedPrompts:
    def test_system_prompt_fills_openkos_attribution_values(self) -> None:
        text = answer_prompts.system_prompt()
        assert "{{" not in text
        assert "USED" in text
        assert text != answer_prompts.read_raw_prompt("system")

    def test_sufficiency_prompt_fills_the_none_sentinel(self) -> None:
        text = answer_prompts.sufficiency_prompt()
        assert "{{" not in text
        assert "NONE" in text

    def test_rendering_is_strict_about_placeholders(self) -> None:
        with pytest.raises(ValueError):
            answer_prompts.render_prompt("system", attribution_keyword="USED")
        with pytest.raises(ValueError):
            answer_prompts.render_prompt("sufficiency", sufficiency_none="NONE", extra="x")

    def test_sent_prompt_hash_is_full_sha256_of_utf8_bytes(self) -> None:
        text = answer_prompts.system_prompt()
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert answer_prompts.sent_prompt_sha256(text) == expected
        assert len(expected) == 64


class TestSharedAnswerBudget:
    """config/experiments.toml mirrors the parameters ``openkos query`` answers with."""

    def test_shared_budget_matches_openkos_answer_defaults(self) -> None:
        budget = load_experiments_config()["shared_budget"]
        assert budget["generative_model"] == "qwen3:8b"
        assert budget["embedding_model"] == "bge-m3"
        assert budget["context_window_tokens"] == 12288
        assert budget["max_generation_tokens"] == 8192

    def test_sampling_is_pinned_explicitly(self) -> None:
        budget = load_experiments_config()["shared_budget"]
        assert isinstance(budget["temperature"], float)
        assert isinstance(budget["seed"], int)

    def test_retrieval_mirrors_openkos_fusion(self) -> None:
        retrieval = load_experiments_config()["retrieval"]
        assert retrieval["answer_limit"] == 5
        assert retrieval["rrf_k"] == 60
