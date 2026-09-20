"""Tests for ``afg.audit`` -- the computation layer for the thesis section 5.1 data audit.

Two kinds of coverage:

- Corpus-backed regression tests pinned to ground-truth numbers measured by hand against
  the real AMI download at ``data/raw/ami/`` (2026-09-20). Skipped when the corpus is
  absent, so the suite still passes on a fresh clone.
- Every DataFrame-returning function also gets a column-name/dtype assertion, so a
  notebook that reads these columns cannot silently depend on a renamed one -- these run
  whenever the corpus is present, alongside the value assertions.
"""

from __future__ import annotations

import pandas as pd
import pytest

from afg.audit.blocker import TURBO_BUTTON_PAIR, blocker_sensitivity
from afg.audit.coverage import layer_coverage, series_eligibility
from afg.audit.decisions import (
    NON_DECISION_MARKERS,
    decision_counts,
    decisions_by_meeting_position,
    non_decision_markers,
    sentence_shape,
    site_prefix,
)
from afg.audit.evidence import anchoring_rates, role_authorship
from afg.audit.topics import TopicBoundaryOverlapResult, topic_decision_boundary_overlap
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR

_corpus_present = AMI_DIR.exists() and any(
    p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".") for p in AMI_DIR.rglob("*")
)

requires_corpus = pytest.mark.skipif(
    not _corpus_present, reason="AMI corpus not downloaded at data/raw/ami/"
)


def _oe1_series() -> list[str]:
    series: list[str] = load_corpus_config()["oe1"]["series"]
    return series


def _dds_series() -> list[str]:
    series: list[str] = load_corpus_config()["corpus"]["series"]["ids"]
    return series


def _assert_columns_and_dtypes(df: pd.DataFrame, expected: dict[str, str]) -> None:
    assert list(df.columns) == list(expected.keys())
    for column, kind in expected.items():
        dtype = df[column].dtype
        if kind == "int":
            assert pd.api.types.is_integer_dtype(dtype), f"{column} expected int, got {dtype}"
        elif kind == "float":
            assert pd.api.types.is_float_dtype(dtype), f"{column} expected float, got {dtype}"
        elif kind == "bool":
            assert pd.api.types.is_bool_dtype(dtype), f"{column} expected bool, got {dtype}"
        elif kind == "str":
            assert dtype == "object" or pd.api.types.is_string_dtype(dtype), (
                f"{column} expected object/str, got {dtype}"
            )
        else:  # pragma: no cover - programming error in the test itself
            raise AssertionError(f"unknown expected kind {kind!r}")


# --- pure unit tests (no corpus needed) ---------------------------------------------------


class TestSitePrefix:
    def test_extracts_two_letter_site_code(self) -> None:
        assert site_prefix("ES2002") == "ES"
        assert site_prefix("IS1004") == "IS"
        assert site_prefix("TS3005") == "TS"


class TestNonDecisionMarkersConstant:
    def test_is_a_tuple_of_the_expected_phrases(self) -> None:
        assert NON_DECISION_MARKERS == (
            "will consider",
            "will research",
            "should be",
            "might",
            "maybe",
            "could",
        )


class TestEmptySeriesInputs:
    """Every function must degrade gracefully to an empty-but-correctly-shaped result
    when given no series to look at -- this needs no real corpus."""

    def test_decision_counts_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = decision_counts(tmp_path, [])
        assert df.empty
        _assert_columns_and_dtypes(
            df,
            {
                "series_id": "str",
                "meeting_id": "str",
                "site": "str",
                "meeting_letter": "str",
                "n_decisions": "int",
            },
        )

    def test_decisions_by_meeting_position_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = decisions_by_meeting_position(tmp_path, [])
        assert len(df) == 4  # a/b/c/d rows always present
        assert df["total_decisions"].sum() == 0

    def test_sentence_shape_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = sentence_shape(tmp_path, [])
        assert df.empty
        _assert_columns_and_dtypes(
            df,
            {
                "series_id": "str",
                "meeting_id": "str",
                "decision_id": "str",
                "n_tokens": "int",
                "n_chars": "int",
            },
        )

    def test_non_decision_markers_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = non_decision_markers(tmp_path, [])
        assert len(df) == len(NON_DECISION_MARKERS)
        assert (df["n_matches"] == 0).all()
        assert (df["rate"] == 0.0).all()

    def test_anchoring_rates_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = anchoring_rates(tmp_path, [])
        # Only the "total" row survives with zero counts.
        assert len(df) == 1
        assert df.iloc[0]["scope"] == "total"
        assert df.iloc[0]["n_decisions"] == 0

    def test_role_authorship_empty_series(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = role_authorship(tmp_path, [])
        assert df.empty
        _assert_columns_and_dtypes(
            df, {"role": "str", "site": "str", "count": "int", "share": "float"}
        )

    def test_topic_overlap_empty_series_not_computable(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        result = topic_decision_boundary_overlap(tmp_path, ["ES2002"])
        assert isinstance(result, TopicBoundaryOverlapResult)
        assert result.computable is False
        assert result.reason is not None
        assert result.aggregate_coincidence_rate is None


# --- corpus-backed tests --------------------------------------------------------------


@requires_corpus
class TestLayerCoverage:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return layer_coverage(AMI_DIR)

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df,
            {
                "layer": "str",
                "file_count": "int",
                "meetings_covered": "int",
                "oe1_series_complete_count": "int",
                "oe1_series_incomplete": "str",
            },
        )

    def test_file_counts_match_ground_truth(self, df: pd.DataFrame) -> None:
        by_layer = df.set_index("layer")["file_count"].to_dict()
        assert by_layer["abstractive_summary"] == 142
        assert by_layer["extractive_summary_links"] == 137
        assert by_layer["decision_discussion_segmentation"] == 47
        assert by_layer["dialogue_acts"] == 556
        assert by_layer["words"] == 687

    def test_dds_layer_complete_on_exactly_the_six_dds_series(self, df: pd.DataFrame) -> None:
        row = df.set_index("layer").loc["decision_discussion_segmentation"]
        assert row["oe1_series_complete_count"] == 6
        incomplete = set(row["oe1_series_incomplete"].split(","))
        assert incomplete == set(_oe1_series()) - set(_dds_series())


@requires_corpus
class TestSeriesEligibility:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return series_eligibility(AMI_DIR)

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df,
            {
                "series_id": "str",
                "summlink_on_4_of_4": "bool",
                "has_dds": "bool",
                "decision_count": "int",
            },
        )

    def test_33_complete_series(self, df: pd.DataFrame) -> None:
        assert len(df) == 33

    def test_32_have_summlink_on_4_of_4(self, df: pd.DataFrame) -> None:
        assert df["summlink_on_4_of_4"].sum() == 32
        ts3012 = df[df["series_id"] == "TS3012"]
        assert len(ts3012) == 1
        assert bool(ts3012.iloc[0]["summlink_on_4_of_4"]) is False

    def test_6_have_dds(self, df: pd.DataFrame) -> None:
        assert df["has_dds"].sum() == 6
        assert set(df[df["has_dds"]]["series_id"]) == set(_dds_series())


@requires_corpus
class TestDecisionCounts:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return decision_counts(AMI_DIR, _oe1_series())

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df,
            {
                "series_id": "str",
                "meeting_id": "str",
                "site": "str",
                "meeting_letter": "str",
                "n_decisions": "int",
            },
        )

    def test_total_decisions_is_343(self, df: pd.DataFrame) -> None:
        assert int(df["n_decisions"].sum()) == 343

    def test_per_series_totals_match_ground_truth(self, df: pd.DataFrame) -> None:
        expected = {
            "ES2002": 28,
            "ES2008": 33,
            "ES2014": 23,
            "ES2015": 29,
            "ES2016": 24,
            "IS1003": 25,
            "IS1004": 24,
            "IS1006": 17,
            "IS1008": 13,
            "IS1009": 20,
            "TS3003": 31,
            "TS3005": 29,
            "TS3009": 24,
            "TS3011": 23,
        }
        totals = df.groupby("series_id")["n_decisions"].sum().to_dict()
        assert totals == expected

    def test_is1004_per_meeting_matches_ground_truth(self, df: pd.DataFrame) -> None:
        is1004 = df[df["series_id"] == "IS1004"].set_index("meeting_letter")["n_decisions"]
        assert is1004.to_dict() == {"a": 4, "b": 6, "c": 2, "d": 12}

    def test_site_prefix_is_correct(self, df: pd.DataFrame) -> None:
        assert set(df[df["series_id"].str.startswith("ES")]["site"]) == {"ES"}
        assert set(df[df["series_id"].str.startswith("IS")]["site"]) == {"IS"}
        assert set(df[df["series_id"].str.startswith("TS")]["site"]) == {"TS"}


@requires_corpus
class TestDecisionsByMeetingPosition:
    def test_columns_dtypes_and_total(self) -> None:
        df = decisions_by_meeting_position(AMI_DIR, _oe1_series())
        _assert_columns_and_dtypes(
            df,
            {
                "meeting_letter": "str",
                "n_series": "int",
                "total_decisions": "int",
                "mean_decisions": "float",
            },
        )
        assert list(df["meeting_letter"]) == ["a", "b", "c", "d"]
        assert int(df["total_decisions"].sum()) == 343
        assert (df["n_series"] == 14).all()


@requires_corpus
class TestSentenceShape:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return sentence_shape(AMI_DIR, _oe1_series())

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df,
            {
                "series_id": "str",
                "meeting_id": "str",
                "decision_id": "str",
                "n_tokens": "int",
                "n_chars": "int",
            },
        )

    def test_row_count_matches_total_decisions(self, df: pd.DataFrame) -> None:
        assert len(df) == 343

    def test_median_tokens_ground_truth(self, df: pd.DataFrame) -> None:
        es2002_median = df[df["series_id"] == "ES2002"]["n_tokens"].median()
        is1008_median = df[df["series_id"] == "IS1008"]["n_tokens"].median()
        assert es2002_median == pytest.approx(3.5)
        assert is1008_median == pytest.approx(12.0)


@requires_corpus
class TestNonDecisionMarkers:
    def test_columns_dtypes_and_shape(self) -> None:
        df = non_decision_markers(AMI_DIR, _oe1_series())
        _assert_columns_and_dtypes(
            df, {"marker": "str", "n_matches": "int", "n_sentences": "int", "rate": "float"}
        )
        assert list(df["marker"]) == list(NON_DECISION_MARKERS)
        assert (df["n_sentences"] == 343).all()
        # rate is always n_matches / n_sentences.
        for _, row in df.iterrows():
            assert row["rate"] == pytest.approx(row["n_matches"] / 343)


@requires_corpus
class TestAnchoringRates:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return anchoring_rates(AMI_DIR, _oe1_series())

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df,
            {
                "scope": "str",
                "key": "str",
                "n_decisions": "int",
                "n_anchored": "int",
                "n_zero_evidence": "int",
                "anchoring_rate": "float",
            },
        )

    def test_total_row_matches_ground_truth(self, df: pd.DataFrame) -> None:
        total = df[(df["scope"] == "total") & (df["key"] == "ALL")].iloc[0]
        assert int(total["n_decisions"]) == 343
        assert int(total["n_anchored"]) == 317
        assert int(total["n_zero_evidence"]) == 26
        assert total["anchoring_rate"] == pytest.approx(317 / 343, abs=1e-6)

    def test_series_rows_sum_to_total(self, df: pd.DataFrame) -> None:
        series_rows = df[df["scope"] == "series"]
        assert int(series_rows["n_decisions"].sum()) == 343
        assert int(series_rows["n_anchored"].sum()) == 317

    def test_meeting_rows_sum_to_total(self, df: pd.DataFrame) -> None:
        meeting_rows = df[df["scope"] == "meeting"]
        assert int(meeting_rows["n_decisions"].sum()) == 343
        assert int(meeting_rows["n_anchored"].sum()) == 317


@requires_corpus
class TestRoleAuthorship:
    @staticmethod
    @pytest.fixture(scope="class")
    def df() -> pd.DataFrame:
        return role_authorship(AMI_DIR, _oe1_series())

    def test_columns_and_dtypes(self, df: pd.DataFrame) -> None:
        _assert_columns_and_dtypes(
            df, {"role": "str", "site": "str", "count": "int", "share": "float"}
        )

    def test_headline_counts_match_ground_truth(self, df: pd.DataFrame) -> None:
        all_rows = df[df["site"] == "ALL"].set_index("role")
        assert int(all_rows.loc["PM", "count"]) == 322
        assert int(all_rows.loc["ID", "count"]) == 156
        assert int(all_rows.loc["ME", "count"]) == 105
        assert int(all_rows.loc["UI", "count"]) == 102
        assert int(all_rows["count"].sum()) == 685

    def test_headline_shares_match_ground_truth(self, df: pd.DataFrame) -> None:
        all_rows = df[df["site"] == "ALL"].set_index("role")
        assert all_rows.loc["PM", "share"] == pytest.approx(0.470, abs=0.001)
        assert all_rows.loc["ID", "share"] == pytest.approx(0.228, abs=0.001)
        assert all_rows.loc["ME", "share"] == pytest.approx(0.153, abs=0.001)
        assert all_rows.loc["UI", "share"] == pytest.approx(0.149, abs=0.001)

    def test_pm_share_by_site_matches_ground_truth(self, df: pd.DataFrame) -> None:
        pm_by_site = df[df["role"] == "PM"].set_index("site")["share"]
        assert pm_by_site["ES"] == pytest.approx(0.50, abs=0.01)
        assert pm_by_site["IS"] == pytest.approx(0.44, abs=0.01)
        assert pm_by_site["TS"] == pytest.approx(0.47, abs=0.01)


@requires_corpus
class TestTopicDecisionBoundaryOverlap:
    def test_restricted_to_the_six_dds_series(self) -> None:
        result = topic_decision_boundary_overlap(AMI_DIR, _oe1_series())
        assert result.computable is True
        considered_series = {m[:-1] for m in result.meetings_considered}
        assert considered_series <= set(_dds_series())

    def test_per_meeting_columns_and_dtypes(self) -> None:
        result = topic_decision_boundary_overlap(AMI_DIR, _oe1_series())
        _assert_columns_and_dtypes(
            result.per_meeting,
            {
                "meeting_id": "str",
                "n_decisions": "int",
                "n_aligned": "int",
                "coincidence_rate": "float",
            },
        )

    def test_aggregate_rate_is_a_real_measurement_below_one_half(self) -> None:
        """Thesis section 5.1 cites Hsueh & Moore for "less than half the time" -- this
        asserts our own measurement lands in that same qualitative regime (a sanity check
        on the method, not a pin to one exact float, since no ground-truth figure for this
        new measurement was specified up front)."""
        result = topic_decision_boundary_overlap(AMI_DIR, _oe1_series())
        assert result.aggregate_coincidence_rate is not None
        assert 0.0 <= result.aggregate_coincidence_rate < 0.5
        assert result.aggregate_n_decisions > 0

    def test_restricting_to_a_non_dds_series_is_not_computable(self) -> None:
        result = topic_decision_boundary_overlap(AMI_DIR, ["ES2002"])
        assert result.computable is False
        assert result.reason is not None
        assert result.aggregate_coincidence_rate is None


@requires_corpus
class TestBlockerSensitivity:
    def test_columns_and_dtypes(self) -> None:
        df = blocker_sensitivity(
            AMI_DIR, _oe1_series(), thresholds=[0.30], min_overlaps=[1, 2]
        )
        _assert_columns_and_dtypes(
            df,
            {
                "threshold": "float",
                "min_overlap_tokens": "int",
                "n_candidates": "int",
                "pct_of_total_pairs": "float",
                "turbo_button_survives": "bool",
            },
        )

    def test_grid_matches_measured_ground_truth_table(self) -> None:
        df = blocker_sensitivity(
            AMI_DIR, _oe1_series(), thresholds=[0.30, 0.40, 0.50], min_overlaps=[1, 2, 3]
        )

        def _cell(threshold: float, min_overlap: int) -> pd.Series:
            row = df[
                (df["threshold"] == threshold) & (df["min_overlap_tokens"] == min_overlap)
            ]
            assert len(row) == 1
            return row.iloc[0]

        assert int(_cell(0.30, 1)["n_candidates"]) == 712
        assert int(_cell(0.30, 2)["n_candidates"]) == 92
        assert int(_cell(0.40, 2)["n_candidates"]) == 74
        assert int(_cell(0.50, 2)["n_candidates"]) == 53
        assert int(_cell(0.30, 3)["n_candidates"]) == 29

    def test_turbo_button_survives_only_within_the_bounded_operating_region(self) -> None:
        df = blocker_sensitivity(
            AMI_DIR, ["IS1004"], thresholds=[0.30, 0.50], min_overlaps=[2, 3]
        )

        def _survives(threshold: float, min_overlap: int) -> bool:
            row = df[
                (df["threshold"] == threshold) & (df["min_overlap_tokens"] == min_overlap)
            ]
            return bool(row.iloc[0]["turbo_button_survives"])

        assert _survives(0.30, 2) is True
        assert _survives(0.30, 3) is False
        assert _survives(0.50, 2) is False

    def test_turbo_button_pair_constant(self) -> None:
        assert TURBO_BUTTON_PAIR == ("IS1004c.elana.s.29", "IS1004d.elana.s.22")
