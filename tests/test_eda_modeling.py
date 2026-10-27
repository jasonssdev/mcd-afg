"""Tests for ``afg.eda.modeling``: partition volumes and the EDA constraints on modeling."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from afg.eda.modeling import (
    ContextConstraints,
    context_constraints,
    partition_volumes,
)
from afg.eda.tables import EdaTables, load_eda_tables
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR, TRANSCRIPTS_DIR
from tests.markers import requires


def _series_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "series_id": ["A1", "B1", "C1", "D1"],
            "split": ["development", "development", "evaluation", "evaluation"],
            "n_meetings": [4, 4, 4, 4],
            "n_decisions": [10, 10, 30, 50],
            "n_cross_meeting_pairs": [20, 20, 60, 100],
            "n_candidates": [1, 1, 2, 6],
        }
    )


class TestPartitionVolumes:
    def test_counts_and_percentages_per_partition(self) -> None:
        table = partition_volumes(_series_table())
        dev = table.loc["development"]
        assert dev["series"] == 2
        assert dev["meetings"] == 8
        assert dev["decisions"] == 20
        assert dev["pairs"] == 40
        assert dev["candidates"] == 2
        assert dev["pct_series"] == pytest.approx(50.0)
        assert dev["pct_decisions"] == pytest.approx(20.0)
        assert dev["pct_candidates"] == pytest.approx(20.0)
        ev = table.loc["evaluation"]
        assert ev["decisions"] == 80
        assert ev["pct_decisions"] == pytest.approx(80.0)

    def test_total_row_is_the_sum_and_is_one_hundred_percent(self) -> None:
        table = partition_volumes(_series_table())
        total = table.loc["total"]
        assert total["series"] == 4
        assert total["decisions"] == 100
        assert total["pct_decisions"] == pytest.approx(100.0)
        assert table.loc[["development", "evaluation"], "decisions"].sum() == total["decisions"]

    def test_unassigned_series_are_kept_out_of_the_total_and_flagged(self) -> None:
        series = _series_table()
        series.loc[3, "split"] = "unassigned"
        with pytest.raises(ValueError, match="unassigned"):
            partition_volumes(series)

    def test_questions_are_added_per_partition(self) -> None:
        table = partition_volumes(_series_table(), questions={"A1": 21})
        assert table.loc["development", "questions"] == 21
        assert table.loc["evaluation", "questions"] == 0
        assert table.loc["total", "questions"] == 21
        assert table.loc["development", "pct_questions"] == pytest.approx(100.0)

    def test_without_questions_the_column_is_missing_not_zero(self) -> None:
        table = partition_volumes(_series_table())
        assert "questions" not in table.columns

    def test_reserve_row_counts_series_only(self) -> None:
        table = partition_volumes(_series_table(), reserve_series=["R1", "R2", "R3"])
        reserve = table.loc["reserve"]
        assert reserve["series"] == 3
        assert math.isnan(reserve["decisions"])
        assert math.isnan(reserve["pct_decisions"])
        # the reserve is outside the OE1 total
        assert table.loc["total", "series"] == 4

    def test_no_reserve_row_without_reserve_series(self) -> None:
        assert "reserve" not in partition_volumes(_series_table()).index


def _meeting_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "meeting_id": ["A1a", "A1b", "B1a", "B1b"],
            "series_id": ["A1", "A1", "B1", "B1"],
            "n_turns": [100, 300, 200, 400],
            "n_words": [2_000, 9_000, 4_000, 10_000],
            "n_characters": [11_000, 50_000, 22_000, 54_000],
            "position": ["a", "b", "a", "b"],
            "n_decisions": [1, 3, 2, 4],
            "approx_tokens": [2_600, 11_700, 5_200, 13_000],
            "context_ratio": [0.2, 0.9, 0.4, 1.06],
            "fits_context": [True, True, True, False],
        }
    )


def _decision_table() -> pd.DataFrame:
    return pd.DataFrame(
        {"anchored": [True, True, False, True, False, True, True, True, True, True]}
    )


class TestContextConstraints:
    def test_meeting_level_counts(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=12_288)
        assert isinstance(c, ContextConstraints)
        assert c.n_meetings == 4
        assert c.n_fit_context == 3
        assert c.n_over_80_percent == 2
        assert c.max_context_ratio == pytest.approx(1.06)

    def test_window_expressed_in_words(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=13_000)
        assert c.window_words == pytest.approx(13_000 / 1.3)

    def test_series_never_fit_when_larger_than_the_window(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=12_288)
        # series A1: 11,000 words, series B1: 14,000 words; window = 9,452 words
        assert c.series_words_min == 11_000
        assert c.series_words_max == 14_000
        assert c.series_window_ratio_min == pytest.approx(11_000 / (12_288 / 1.3))
        assert c.series_window_ratio_max == pytest.approx(14_000 / (12_288 / 1.3))
        assert c.n_series_fit == 0

    def test_decisions_are_rare_among_turns(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=12_288)
        assert c.n_decisions == 10  # from the decision table
        assert c.decisions_per_1000_turns == pytest.approx(10.0)
        assert c.median_decisions_per_meeting == pytest.approx(2.5)

    def test_meeting_length_in_characters_and_decisions_by_position(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=12_288)
        assert c.meeting_chars_median == pytest.approx(36_000.0)
        assert c.median_decisions_by_position == {"a": 1.5, "b": 3.5}

    def test_decisions_without_evidence(self) -> None:
        c = context_constraints(_meeting_table(), _decision_table(), context_tokens=12_288)
        assert c.n_without_evidence == 2


_oe1 = load_corpus_config()["oe1"]
_ids = [f"{s}{letter}" for s in _oe1["series"] for letter in "abcd"]
_corpus_ready = (AMI_DIR / "corpusResources" / "meetings.xml").exists() and all(
    (TRANSCRIPTS_DIR / f"{m}.jsonl").exists() for m in _ids
)
requires_corpus = requires(
    "requires_corpus",
    available=_corpus_ready,
    reason="AMI corpus or frozen transcripts not available locally",
)


@pytest.fixture(scope="module")
def real() -> EdaTables:
    return load_eda_tables()


@requires_corpus
class TestRealCorpus:
    def test_reproduces_the_adr_0005_numbers(self, real: EdaTables) -> None:
        table = partition_volumes(real.series)
        assert table.loc["development", "decisions"] == 77
        assert table.loc["evaluation", "decisions"] == 266
        assert table.loc["total", "decisions"] == 343
        assert table.loc["development", "candidates"] == 11
        assert table.loc["evaluation", "candidates"] == 81
        assert table.loc["total", "candidates"] == 92
        assert table.loc["development", "series"] == 3
        assert table.loc["evaluation", "series"] == 11
        assert table.loc["total", "meetings"] == 56
        assert table.loc["total", "pairs"] == 3071

    def test_split_matches_the_configuration(self, real: EdaTables) -> None:
        dev = set(_oe1["development_series"])
        got = set(real.series.loc[real.series["split"] == "development", "series_id"])
        assert got == dev

    def test_real_constraints(self, real: EdaTables) -> None:
        c = context_constraints(real.meeting, real.decision, context_tokens=12_288)
        assert c.n_meetings == 56
        assert c.n_decisions == 343
        assert c.n_without_evidence == 26
        assert c.n_series_fit == 0
