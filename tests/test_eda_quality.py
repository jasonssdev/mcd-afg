"""Tests for ``afg.eda.quality``: data dictionary, missingness and business-rule checks."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from afg.eda.quality import (
    consistency_checks,
    data_dictionary,
    missingness_matrix,
    missingness_mechanism,
    missingness_summary,
    record_missingness,
)


class TestDataDictionary:
    @staticmethod
    def _df() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "meeting_id": ["A1a", "A1b", "A1c"],
                "duration": [10.0, 20.0, np.nan],
                "site": ["ES", "ES", "IS"],
                "flag": [True, False, True],
                "start": pd.to_datetime(["2004-01-01", "2004-01-02", "2004-01-03"]),
                "note": ["x" * 80, "y" * 90, "z" * 100],
            }
        )

    def test_kinds_are_inferred(self) -> None:
        out = data_dictionary(self._df()).set_index("variable")
        assert out.loc["meeting_id", "kind"] == "identifier"
        assert out.loc["duration", "kind"] == "numeric"
        assert out.loc["site", "kind"] == "categorical"
        assert out.loc["flag", "kind"] == "categorical"
        assert out.loc["start", "kind"] == "temporal"
        assert out.loc["note", "kind"] == "text"

    def test_counts_and_example(self) -> None:
        out = data_dictionary(self._df()).set_index("variable")
        assert out.loc["duration", "n_missing"] == 1
        assert out.loc["duration", "n_unique"] == 2
        assert out.loc["duration", "example"] == "10.0"
        assert out.loc["site", "n_unique"] == 2

    def test_metadata_is_joined_and_missing_metadata_is_blank(self) -> None:
        out = data_dictionary(
            self._df(),
            descriptions={"duration": "Duración"},
            units={"duration": "s"},
            domains={"duration": ">= 0"},
        ).set_index("variable")
        assert out.loc["duration", "description"] == "Duración"
        assert out.loc["duration", "unit"] == "s"
        assert out.loc["duration", "valid_domain"] == ">= 0"
        assert out.loc["site", "description"] == ""

    def test_kind_can_be_overridden(self) -> None:
        out = data_dictionary(self._df(), kinds={"site": "identifier"}).set_index("variable")
        assert out.loc["site", "kind"] == "identifier"

    def test_one_row_per_column_in_order(self) -> None:
        df = self._df()
        assert list(data_dictionary(df)["variable"]) == list(df.columns)


class TestMissingness:
    @staticmethod
    def _df() -> pd.DataFrame:
        return pd.DataFrame({"a": [1, None, 3, None], "b": [None, None, 3, 4], "c": [1, 2, 3, 4]})

    def test_summary_per_variable(self) -> None:
        out = missingness_summary(self._df()).set_index("variable")
        assert out.loc["a", "n_missing"] == 2
        assert out.loc["b", "share_missing"] == pytest.approx(0.5)
        assert out.loc["c", "n_missing"] == 0

    def test_per_record_counts(self) -> None:
        out = record_missingness(self._df())
        assert out["n_missing"].tolist() == [1, 2, 0, 1]
        assert out["share_missing"].tolist() == pytest.approx([1 / 3, 2 / 3, 0, 1 / 3])

    def test_matrix_is_boolean_and_aligned(self) -> None:
        matrix = missingness_matrix(self._df())
        assert matrix.dtypes.eq(bool).all()
        assert matrix.loc[1, "b"]

    def test_mechanism_detects_dependence_on_a_categorical_covariate(self) -> None:
        covariates = pd.DataFrame({"site": ["ES"] * 20 + ["IS"] * 20})
        indicator = pd.Series([False] * 20 + [True] * 20)
        out = missingness_mechanism(indicator, covariates).iloc[0]
        assert out["test"] == "chi2"
        assert out["effect_name"] == "cramers_v"
        assert out["effect_size"] == pytest.approx(1.0)
        assert out["p_value"] < 0.001
        assert bool(out["associated"])

    def test_mechanism_detects_dependence_on_a_numeric_covariate(self) -> None:
        covariates = pd.DataFrame({"size": list(range(20)) + list(range(100, 120))})
        indicator = pd.Series([False] * 20 + [True] * 20)
        out = missingness_mechanism(indicator, covariates).iloc[0]
        assert out["test"] == "mann_whitney"
        assert out["effect_name"] == "rank_biserial"
        assert out["effect_size"] == pytest.approx(1.0)
        assert out["p_value"] < 0.001

    def test_mechanism_is_quiet_when_independent(self) -> None:
        covariates = pd.DataFrame({"g": list("xy" * 20), "v": [1.0, 2.0] * 20})
        indicator = pd.Series([True, True, False, False] * 10)
        out = missingness_mechanism(indicator, covariates)
        assert not out["associated"].any()

    def test_constant_indicator_gives_nan(self) -> None:
        covariates = pd.DataFrame({"g": list("xyxy")})
        out = missingness_mechanism(pd.Series([False] * 4), covariates).iloc[0]
        assert math.isnan(out["p_value"])
        assert not bool(out["associated"])


def _clean_tables() -> dict[str, pd.DataFrame]:
    meetings = pd.DataFrame(
        {
            "meeting_id": ["S1a", "S1b", "S1c", "S1d"],
            "series_id": ["S1"] * 4,
            "position": list("abcd"),
            "position_index": [1, 2, 3, 4],
            "recording_date": pd.to_datetime(["2004-01-01"] * 4),
            "start": pd.to_datetime(
                ["2004-01-01 10:00", "2004-01-01 11:00", "2004-01-01 12:00", "2004-01-01 13:00"]
            ),
        }
    )
    speakers = pd.DataFrame(
        {
            "meeting_id": ["S1a"] * 4,
            "speaker": list("ABCD"),
            "role": ["PM", "ID", "ME", "UI"],
        }
    )
    decisions = pd.DataFrame(
        {
            "decision_id": ["S1a.d01", "S1b.d01", "S1c.d01"],
            "meeting_id": ["S1a", "S1b", "S1c"],
            "series_id": ["S1"] * 3,
            "exact_duplicate": [False, False, False],
            "near_duplicate": [False, False, False],
        }
    )
    pairs = pd.DataFrame(
        {
            "earlier_decision_id": ["S1a.d01", "S1a.d01", "S1b.d01"],
            "later_decision_id": ["S1b.d01", "S1c.d01", "S1c.d01"],
            "earlier_meeting_id": ["S1a", "S1a", "S1b"],
            "later_meeting_id": ["S1b", "S1c", "S1c"],
            "series_id": ["S1"] * 3,
        }
    )
    evidence = pd.DataFrame(
        {"decision_id": ["S1a.d01", "S1b.d01"], "dialogue_act_id": ["S1a.A.da.1", "S1b.B.da.2"]}
    )
    act_ids = pd.DataFrame(
        {
            "meeting_id": ["S1a", "S1b"],
            "dialogue_act_id": ["S1a.A.da.1", "S1b.B.da.2"],
        }
    )
    return {
        "meetings": meetings,
        "speakers": speakers,
        "decisions": decisions,
        "pairs": pairs,
        "evidence": evidence,
        "act_ids": act_ids,
    }


def _run(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return consistency_checks(
        tables["meetings"],
        tables["speakers"],
        tables["decisions"],
        tables["pairs"],
        evidence=tables["evidence"],
        act_ids=tables["act_ids"],
        meetings_per_series=4,
    ).set_index("check")


class TestConsistencyChecks:
    def test_output_is_tidy(self) -> None:
        out = consistency_checks(
            *(_clean_tables()[k] for k in ("meetings", "speakers", "decisions", "pairs"))
        )
        assert list(out.columns) == ["check", "description", "passed", "n_violations", "detail"]
        assert out["check"].is_unique

    def test_clean_data_passes_everything(self) -> None:
        out = _run(_clean_tables())
        assert out["passed"].all(), out[~out["passed"]]
        assert (out["n_violations"] == 0).all()

    def test_series_with_missing_meeting(self) -> None:
        t = _clean_tables()
        t["meetings"] = t["meetings"].iloc[:3]
        out = _run(t)
        assert not out.loc["meetings_per_series", "passed"]
        assert out.loc["meetings_per_series", "n_violations"] == 1
        assert "S1" in out.loc["meetings_per_series", "detail"]

    def test_chronology_violation(self) -> None:
        t = _clean_tables()
        t["meetings"].loc[1, "start"] = pd.Timestamp("2004-01-01 09:00")
        out = _run(t)
        assert not out.loc["chronological_order", "passed"]

    def test_missing_start_times_are_unverifiable_not_violations(self) -> None:
        t = _clean_tables()
        t["meetings"]["start"] = pd.NaT
        out = _run(t)
        assert out.loc["chronological_order", "passed"]
        assert "0 de 1" in out.loc["chronological_order", "detail"]

    def test_recording_dates_must_not_go_backwards(self) -> None:
        t = _clean_tables()
        t["meetings"].loc[2, "recording_date"] = pd.Timestamp("2003-12-31")
        out = _run(t)
        assert not out.loc["date_order", "passed"]
        assert out.loc["chronological_order", "passed"]

    def test_invalid_role(self) -> None:
        t = _clean_tables()
        t["speakers"].loc[0, "role"] = "XX"
        out = _run(t)
        assert out.loc["valid_roles", "n_violations"] == 1

    def test_repeated_role_in_a_meeting(self) -> None:
        t = _clean_tables()
        t["speakers"].loc[1, "role"] = "PM"
        out = _run(t)
        assert not out.loc["one_speaker_per_role", "passed"]

    def test_decision_with_unknown_meeting(self) -> None:
        t = _clean_tables()
        t["decisions"].loc[0, "meeting_id"] = "ZZ9z"
        out = _run(t)
        assert out.loc["decision_meeting_exists", "n_violations"] == 1

    def test_pair_with_unknown_decision(self) -> None:
        t = _clean_tables()
        t["pairs"].loc[0, "later_decision_id"] = "nope"
        out = _run(t)
        assert out.loc["pair_decisions_exist", "n_violations"] == 1

    def test_pair_that_goes_backwards_in_time(self) -> None:
        t = _clean_tables()
        t["pairs"].loc[0, ["earlier_meeting_id", "later_meeting_id"]] = ["S1b", "S1a"]
        out = _run(t)
        assert out.loc["pair_earlier_precedes_later", "n_violations"] == 1

    def test_duplicate_ids(self) -> None:
        t = _clean_tables()
        t["decisions"].loc[2, "decision_id"] = "S1a.d01"
        out = _run(t)
        assert out.loc["unique_decision_ids", "n_violations"] == 1

    def test_duplicate_pairs(self) -> None:
        t = _clean_tables()
        t["pairs"].loc[1] = t["pairs"].loc[0]
        out = _run(t)
        assert not out.loc["unique_pairs", "passed"]

    def test_unresolved_evidence_act(self) -> None:
        t = _clean_tables()
        t["evidence"].loc[0, "dialogue_act_id"] = "S1a.A.da.999"
        out = _run(t)
        assert out.loc["evidence_acts_resolve", "n_violations"] == 1

    def test_duplicate_sentences_are_counted_from_flags(self) -> None:
        t = _clean_tables()
        t["decisions"].loc[:1, "exact_duplicate"] = True
        t["decisions"].loc[:1, "near_duplicate"] = True
        out = _run(t)
        assert out.loc["exact_duplicate_sentences", "n_violations"] == 2
        assert out.loc["near_duplicate_sentences", "n_violations"] == 2

    def test_pair_count_must_match_decision_counts(self) -> None:
        t = _clean_tables()
        t["pairs"] = t["pairs"].iloc[:2]
        out = _run(t)
        assert not out.loc["pair_count_matches_decisions", "passed"]

    def test_optional_checks_are_skipped_without_inputs(self) -> None:
        t = _clean_tables()
        out = consistency_checks(t["meetings"], t["speakers"], t["decisions"], t["pairs"])
        assert "evidence_acts_resolve" not in set(out["check"])
