"""Tests for the OE4 deterministic error-attribution cascade (thesis section 5.6)."""

from __future__ import annotations

from afg.evaluation.attribution import ErrorStage, attribute_error


class TestAttributeError:
    def test_fact_not_in_base_is_extraction_error(self) -> None:
        assert attribute_error(fact_in_base=False, fact_retrieved=False) == ErrorStage.EXTRACTION

    def test_fact_not_in_base_is_extraction_error_even_if_retrieved_flag_set(self) -> None:
        # fact_retrieved is meaningless when the fact was never in the base; the cascade
        # must still classify this as extraction, not retrieval.
        assert attribute_error(fact_in_base=False, fact_retrieved=True) == ErrorStage.EXTRACTION

    def test_fact_in_base_but_not_retrieved_is_retrieval_error(self) -> None:
        assert attribute_error(fact_in_base=True, fact_retrieved=False) == ErrorStage.RETRIEVAL

    def test_fact_in_base_and_retrieved_is_synthesis_error(self) -> None:
        assert attribute_error(fact_in_base=True, fact_retrieved=True) == ErrorStage.SYNTHESIS
