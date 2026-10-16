"""Tests for ``afg.eda.tables``: the five analysis-level tables.

Two layers, as in ``tests/test_audit.py``: small synthetic fixtures (an XML corpus stub, JSONL
transcripts, hand-built decisions) with hand-checkable values, and real-corpus invariants
pinned to the figures the project already reports (14 series, 56 meetings, 343 decisions,
3,071 cross-meeting pairs, 92 candidates, 317 anchored decisions). The real-corpus tests are
skipped when the AMI download or the frozen transcripts are absent.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from afg.annotation.blocking import generate_candidates
from afg.audit.evidence import anchoring_rates
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.eda.dictionary import table_dictionary
from afg.eda.tables import (
    LEN_BINS,
    LEN_LABELS,
    EdaTables,
    add_pair_features,
    build_decision_table,
    build_meeting_table,
    build_pair_table,
    build_series_table,
    build_speaker_table,
    duration_coherence,
    format_thousands,
    load_eda_tables,
    read_meeting_metadata,
    read_speaker_metadata,
    read_transcripts,
    turn_length_distribution,
)
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR, TRANSCRIPTS_DIR
from tests.markers import requires

SPLIT = {"S1": "development", "S2": "evaluation"}

_MEETINGS_XML = """<?xml version="1.0" encoding="ISO-8859-1"?>
<nite:root xmlns:nite="http://nite.sourceforge.net/" nite:id="meetings">
  <meeting nite:id="m1" observation="S1a" dateOnly="29-10-2004" startTime="10h46" duration="600">
    <speaker nite:id="S1a_1" nxt_agent="A" global_name="FEE005" role="PM"/>
    <speaker nite:id="S1a_2" nxt_agent="B" global_name="MEE006" role="ID"/>
  </meeting>
  <meeting nite:id="m2" observation="S1b" dateOnly="29-10-2004" startTime="11h50" duration="1200">
    <speaker nite:id="S1b_1" nxt_agent="A" global_name="FEE005" role="PM"/>
    <speaker nite:id="S1b_2" nxt_agent="B" global_name="NOPE99" role="ID"/>
  </meeting>
  <meeting nite:id="m3" observation="S1c" dateOnly="13-12-04" startTime="" duration="900">
    <speaker nite:id="S1c_1" nxt_agent="A" global_name="FEE005" role="PM"/>
  </meeting>
</nite:root>
"""
_PARTICIPANTS_XML = """<?xml version="1.0" encoding="ISO-8859-1"?>
<nite:root xmlns:nite="http://nite.sourceforge.net/" nite:id="participants">
  <participant nite:id="FEE005" native_language="English" meeting="S1"/>
  <participant nite:id="MEE006" native_language="romanian" meeting="S1"/>
</nite:root>
"""


@pytest.fixture
def stub_ami(tmp_path: Path) -> Path:
    resources = tmp_path / "ami" / "corpusResources"
    resources.mkdir(parents=True)
    (resources / "meetings.xml").write_text(_MEETINGS_XML, encoding="iso-8859-1")
    (resources / "participants.xml").write_text(_PARTICIPANTS_XML, encoding="iso-8859-1")
    return tmp_path / "ami"


@pytest.fixture
def stub_transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    directory.mkdir()
    turns = [
        ("A", "PM", "Okay then.", ["S1a.A.da.1"]),
        ("B", "ID", "Let us start the meeting", ["S1a.B.da.1", "S1a.B.da.2"]),
        ("A", "PM", "Fine.", ["S1a.A.da.2"]),
    ]
    lines = [
        json.dumps(
            {
                "meeting_id": "S1a",
                "turn_index": i,
                "speaker": speaker,
                "role": role,
                "start": float(i),
                "end": float(i) + 0.5,
                "text": text,
                "dialogue_act_ids": acts,
            }
        )
        for i, (speaker, role, text, acts) in enumerate(turns)
    ]
    (directory / "S1a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory


def _decision(meeting: str, n: int, text: str) -> Decision:
    series = meeting[:-1]
    return Decision(
        id=f"{meeting}.d{n:02d}",
        series_id=series,
        meeting_id=meeting,
        decision_object="",
        content=text,
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"{meeting}.x.s.{n}",)),
    )


@pytest.fixture
def decisions() -> list[Decision]:
    return [
        _decision("S1a", 1, "Use the red remote control"),
        _decision("S1b", 1, "The remote control will be red"),
        _decision("S1c", 1, "Battery pack might be solar"),
        _decision("S2a", 1, "Battery pack"),
    ]


ROLES = {("S1a", "A"): "PM", ("S1a", "B"): "ID"}
EVIDENCE = {"S1a.x.s.1": ["S1a.A.da.1", "S1a.A.da.2", "S1a.B.da.1"], "S1b.x.s.1": []}


class TestReaders:
    def test_meeting_metadata_has_duration_and_start(self, stub_ami: Path) -> None:
        meta = read_meeting_metadata(stub_ami, ["S1a", "S1b", "S1c", "S1d"]).set_index("meeting_id")
        assert meta.loc["S1a", "duration_seconds"] == 600
        assert meta.loc["S1b", "start"] == pd.Timestamp("2004-10-29 11:50")
        assert meta.loc["S1a", "recording_date"] == pd.Timestamp("2004-10-29")
        assert math.isnan(meta.loc["S1d", "duration_seconds"])
        assert pd.isna(meta.loc["S1d", "start"]) and pd.isna(meta.loc["S1d", "recording_date"])

    def test_empty_start_time_keeps_the_date_and_leaves_the_time_missing(
        self, stub_ami: Path
    ) -> None:
        # AMI writes two-digit years and an empty startTime for many meetings.
        meta = read_meeting_metadata(stub_ami, ["S1c"]).iloc[0]
        assert meta["recording_date"] == pd.Timestamp("2004-12-13")
        assert pd.isna(meta["start"])

    def test_speaker_metadata_joins_native_language(self, stub_ami: Path) -> None:
        sp = read_speaker_metadata(stub_ami, ["S1a", "S1b"])
        assert len(sp) == 4
        first = sp[(sp["meeting_id"] == "S1a") & (sp["speaker"] == "B")].iloc[0]
        assert first["role"] == "ID"
        assert first["native_language"] == "Romanian"
        assert first["native_status"] == "non_native"
        unknown = sp[(sp["meeting_id"] == "S1b") & (sp["speaker"] == "B")].iloc[0]
        assert pd.isna(unknown["native_language"])
        assert unknown["native_status"] == "unknown"

    def test_transcripts_are_reduced_to_numbers_without_text(self, stub_transcripts: Path) -> None:
        turns, acts = read_transcripts(stub_transcripts, ["S1a", "S1b"])
        assert "text" not in turns.columns
        assert turns["n_words"].tolist() == [2, 5, 1]
        assert turns["n_chars"].tolist() == [10, 24, 5]
        assert turns["n_dialogue_acts"].tolist() == [1, 2, 1]
        assert turns["duration"].tolist() == [0.5, 0.5, 0.5]
        assert set(turns["meeting_id"]) == {"S1a"}  # S1b has no transcript file
        assert sorted(acts["dialogue_act_id"]) == [
            "S1a.A.da.1",
            "S1a.A.da.2",
            "S1a.B.da.1",
            "S1a.B.da.2",
        ]

    def test_turn_length_distribution(self, stub_transcripts: Path) -> None:
        turns, _ = read_transcripts(stub_transcripts, ["S1a"])
        overall = turn_length_distribution(turns).iloc[0]
        assert overall["n_turns"] == 3
        assert overall["median"] == 2
        assert overall["max"] == 5
        assert overall["share_single_word"] == pytest.approx(1 / 3)
        by_role = turn_length_distribution(turns, by="role").set_index("role")
        assert by_role.loc["PM", "n_turns"] == 2
        assert by_role.loc["PM", "mean"] == pytest.approx(1.5)


class TestDecisionAndPairTables:
    def test_decision_table_features(self, decisions: list[Decision]) -> None:
        table, evidence = build_decision_table(decisions, EVIDENCE, ROLES, SPLIT)
        assert "content" not in table.columns and "text" not in table.columns
        row = table.set_index("decision_id")
        assert row.loc["S1a.d01", "n_tokens"] == 3  # red, remote, control
        assert row.loc["S1a.d01", "n_chars"] == len("Use the red remote control")
        assert row.loc["S1a.d01", "n_evidence_acts"] == 3
        assert bool(row.loc["S1a.d01", "anchored"])
        assert not bool(row.loc["S1b.d01", "anchored"])
        assert row.loc["S1a.d01", "position"] == "a"
        assert row.loc["S1c.d01", "position_index"] == 3
        assert row.loc["S1a.d01", "split"] == "development"
        assert row.loc["S2a.d01", "site"] == "S2"[:2]
        assert bool(row.loc["S1c.d01", "has_non_decision_marker"])
        assert not bool(row.loc["S1a.d01", "has_non_decision_marker"])
        assert row.loc["S1a.d01", "evidence_role"] == "PM"
        assert row.loc["S1a.d01", "n_evidence_roles"] == 2
        assert pd.isna(row.loc["S1b.d01", "evidence_role"])
        assert len(evidence) == 3
        assert set(evidence["role"]) == {"PM", "ID"}

    def test_near_duplicates_use_identical_token_sets(self, decisions: list[Decision]) -> None:
        row = build_decision_table(decisions, EVIDENCE, ROLES, SPLIT)[0].set_index("decision_id")
        assert bool(row.loc["S1a.d01", "near_duplicate"])
        assert bool(row.loc["S1b.d01", "near_duplicate"])
        assert not row["exact_duplicate"].any()
        # same token set as S1c would be across SERIES, so it must not count
        assert not bool(row.loc["S2a.d01", "near_duplicate"])

    def test_exact_duplicates_ignore_case_and_whitespace(self) -> None:
        decs = [
            _decision("S1a", 1, "Red  remote"),
            _decision("S1b", 1, "red remote"),
            _decision("S1c", 1, "blue remote"),
        ]
        row = build_decision_table(decs, {}, {}, SPLIT)[0].set_index("decision_id")
        assert row.loc["S1a.d01", "exact_duplicate"] and row.loc["S1b.d01", "exact_duplicate"]
        assert not row.loc["S1c.d01", "exact_duplicate"]

    def test_pair_table_matches_the_blocker(self, decisions: list[Decision]) -> None:
        pairs = build_pair_table(decisions, SPLIT)
        assert len(pairs) == 3  # S1: a-b, a-c, b-c ; S2 has one decision
        assert "earlier_text" not in pairs.columns
        ab = pairs[pairs["later_meeting_id"] == "S1b"].iloc[0]
        assert ab["earlier_decision_id"] == "S1a.d01"
        assert ab["meeting_distance"] == 1
        assert ab["shared_tokens"] == 3
        assert ab["overlap"] == pytest.approx(1.0)
        assert (ab["n_tokens_earlier"], ab["n_tokens_later"]) == (3, 3)
        assert bool(ab["is_candidate"])
        ac = pairs[pairs["later_meeting_id"] == "S1c"].iloc[0]
        assert ac["meeting_distance"] == 2 and not bool(ac["is_candidate"])
        assert pairs["is_candidate"].sum() == len(generate_candidates(decisions))
        assert pairs["split"].eq("development").all()


class TestMeetingSpeakerSeries:
    @pytest.fixture
    def parts(
        self, stub_ami: Path, stub_transcripts: Path, decisions: list[Decision]
    ) -> dict[str, pd.DataFrame]:
        ids = ["S1a", "S1b"]
        meta = read_meeting_metadata(stub_ami, ids)
        speakers = read_speaker_metadata(stub_ami, ids)
        turns, acts = read_transcripts(stub_transcripts, ids)
        dec, evidence = build_decision_table(decisions, EVIDENCE, ROLES, SPLIT)
        return {
            "meta": meta,
            "speakers": speakers,
            "turns": turns,
            "acts": acts,
            "dec": dec,
            "evidence": evidence,
        }

    def test_meeting_table(self, parts: dict[str, pd.DataFrame]) -> None:
        table = build_meeting_table(
            ["S1a", "S1b"],
            parts["meta"],
            parts["turns"],
            parts["acts"],
            parts["dec"],
            SPLIT,
            context_tokens=10,
        ).set_index("meeting_id")
        a = table.loc["S1a"]
        assert (a["series_id"], a["site"], a["position"], a["position_index"]) == (
            "S1",
            "S1",
            "a",
            1,
        )
        assert a["duration_seconds"] == 600
        assert a["recording_date"] == pd.Timestamp("2004-10-29")
        assert (a["n_turns"], a["n_words"], a["n_characters"]) == (3, 8, 39)
        assert a["n_dialogue_acts"] == 4
        assert a["n_speakers"] == 2
        assert a["approx_tokens"] == math.ceil(8 * 1.3)
        assert a["approx_tokens_chars"] == math.ceil(39 / 4)
        assert not bool(a["fits_context"])  # 11 > 10
        assert a["n_decisions"] == 1 and a["n_anchored_decisions"] == 1
        b = table.loc["S1b"]
        assert b["n_turns"] == 0 and b["n_words"] == 0  # no transcript: zeros, not NaN
        assert bool(b["fits_context"])
        assert b["n_decisions"] == 1 and b["n_anchored_decisions"] == 0

    def test_default_context_window_is_12288(self, parts: dict[str, pd.DataFrame]) -> None:
        table = build_meeting_table(
            ["S1a"], parts["meta"], parts["turns"], parts["acts"], parts["dec"], SPLIT
        )
        assert bool(table.iloc[0]["fits_context"])
        assert table.iloc[0]["context_ratio"] == pytest.approx(11 / 12288)

    def test_speaker_table(self, parts: dict[str, pd.DataFrame]) -> None:
        table = build_speaker_table(parts["speakers"], parts["turns"], parts["evidence"])
        assert len(table) == 4
        a = table[(table["meeting_id"] == "S1a") & (table["speaker"] == "A")].iloc[0]
        b = table[(table["meeting_id"] == "S1a") & (table["speaker"] == "B")].iloc[0]
        assert (a["n_turns"], a["n_words"]) == (2, 3)
        assert a["talk_share"] == pytest.approx(3 / 8)
        assert b["talk_share"] == pytest.approx(5 / 8)
        assert a["n_decision_acts"] == 2 and b["n_decision_acts"] == 1
        assert a["native_status"] == "native"
        silent = table[(table["meeting_id"] == "S1b") & (table["speaker"] == "A")].iloc[0]
        assert silent["n_turns"] == 0 and math.isnan(silent["talk_share"])

    def test_series_table(self, parts: dict[str, pd.DataFrame], decisions: list[Decision]) -> None:
        meetings = build_meeting_table(
            ["S1a", "S1b", "S1c", "S1d", "S2a", "S2b", "S2c", "S2d"],
            parts["meta"],
            parts["turns"],
            parts["acts"],
            parts["dec"],
            SPLIT,
        )
        pairs = build_pair_table(decisions, SPLIT)
        series = build_series_table(meetings, parts["dec"], pairs, SPLIT).set_index("series_id")
        s1 = series.loc["S1"]
        assert s1["n_decisions"] == 3
        assert s1["n_cross_meeting_pairs"] == 3
        assert s1["n_candidates"] == 1
        assert s1["candidate_rate"] == pytest.approx(1 / 3)
        assert s1["anchoring_rate"] == pytest.approx(1 / 3)
        assert s1["median_decision_tokens"] == 3
        assert s1["total_turns"] == 3
        assert s1["total_duration_seconds"] == 1800
        assert s1["split"] == "development"
        s2 = series.loc["S2"]
        assert s2["n_cross_meeting_pairs"] == 0
        assert math.isnan(s2["candidate_rate"])


# --- real corpus --------------------------------------------------------------------------

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
    def test_level_sizes(self, real: EdaTables) -> None:
        assert len(real.series) == 14
        assert len(real.meeting) == 56
        assert len(real.decision) == 343
        assert len(real.pair) == 3071

    def test_speaker_level_has_four_roles_per_meeting(self, real: EdaTables) -> None:
        assert len(real.speaker_meeting) == 56 * 4
        assert real.speaker_meeting.groupby("meeting_id")["role"].nunique().eq(4).all()

    def test_known_blocker_and_anchoring_figures(self, real: EdaTables) -> None:
        assert int(real.pair["is_candidate"].sum()) == 92
        assert int(real.decision["anchored"].sum()) == 317
        assert real.series["n_candidates"].sum() == 92

    def test_agrees_with_the_audit_layer(self, real: EdaTables) -> None:
        audit = anchoring_rates(AMI_DIR, _oe1["series"])
        per_series = audit[audit["scope"] == "series"].set_index("key")["n_anchored"]
        mine = real.decision.groupby("series_id")["anchored"].sum()
        assert mine.to_dict() == per_series.to_dict()

    def test_split_follows_the_frozen_configuration(self, real: EdaTables) -> None:
        by_split = real.series.groupby("split").size().to_dict()
        assert by_split == {"development": 3, "evaluation": 11}

    def test_every_meeting_has_a_duration_and_a_transcript(self, real: EdaTables) -> None:
        assert real.meeting["duration_seconds"].notna().all()
        assert (real.meeting["n_turns"] > 0).all()

    def test_known_data_findings(self, real: EdaTables) -> None:
        from afg.eda.quality import consistency_checks

        # 32 of 56 meetings carry an empty startTime in meetings.xml (ES and TS series).
        assert int(real.meeting["start"].isna().sum()) == 32
        assert real.meeting["recording_date"].notna().all()
        checks = consistency_checks(
            real.meeting,
            real.speaker_meeting,
            real.decision,
            real.pair,
            evidence=real.evidence,
            act_ids=real.act_ids,
        ).set_index("check")
        failed = set(checks.index[~checks["passed"]])
        assert failed == {"exact_duplicate_sentences", "near_duplicate_sentences"}
        assert checks.loc["exact_duplicate_sentences", "n_violations"] == 4
        assert checks.loc["near_duplicate_sentences", "n_violations"] == 8

    def test_no_text_column_leaks_into_any_table(self, real: EdaTables) -> None:
        for table in (real.series, real.meeting, real.speaker_meeting, real.decision, real.pair):
            assert not {"content", "text", "earlier_text", "later_text"} & set(table.columns)


class TestVariableRegistry:
    def test_decision_and_pair_columns_are_all_documented(self, decisions: list[Decision]) -> None:
        for table in (
            build_decision_table(decisions, EVIDENCE, ROLES, SPLIT)[0],
            build_pair_table(decisions, SPLIT),
        ):
            dictionary = table_dictionary(table)
            assert (dictionary["description"] != "").all(), dictionary[
                dictionary["description"] == ""
            ]["variable"].tolist()

    def test_unit_and_domain_are_filled_where_they_apply(self, decisions: list[Decision]) -> None:
        dictionary = table_dictionary(build_pair_table(decisions, SPLIT)).set_index("variable")
        assert dictionary.loc["overlap", "valid_domain"] == "[0, 1]"
        assert dictionary.loc["meeting_distance", "valid_domain"] == "{1, 2, 3}"
        assert dictionary.loc["shared_tokens", "unit"] == "tokens"

    def test_unknown_columns_stay_blank(self) -> None:
        out = table_dictionary(pd.DataFrame({"mystery": [1]})).iloc[0]
        assert out["description"] == ""


@requires_corpus
class TestRealRegistry:
    def test_every_column_of_every_level_is_documented(self, real: EdaTables) -> None:
        for name in ("series", "meeting", "speaker_meeting", "decision", "pair"):
            dictionary = table_dictionary(getattr(real, name))
            missing = dictionary.loc[dictionary["description"] == "", "variable"].tolist()
            assert not missing, f"{name}: {missing}"


class TestPairFeatures:
    def test_shorter_decision_and_the_two_blocker_rules(self) -> None:
        pairs = pd.DataFrame(
            {
                "n_tokens_earlier": [3, 8],
                "n_tokens_later": [5, 2],
                "shared_tokens": [1, 2],
                "overlap": [0.5, 1.0],
                "is_candidate": [False, True],
            }
        )
        out = add_pair_features(pairs)
        assert out["shorter_tokens"].tolist() == [3, 2]
        assert out["passes_overlap"].tolist() == [True, True]
        assert out["passes_shared"].tolist() == [False, True]
        assert (out["passes_overlap"] & out["passes_shared"]).tolist() == pairs[
            "is_candidate"
        ].tolist()

    def test_thresholds_are_parameters_and_input_is_not_mutated(self) -> None:
        pairs = pd.DataFrame(
            {
                "n_tokens_earlier": [4],
                "n_tokens_later": [4],
                "shared_tokens": [1],
                "overlap": [0.25],
            }
        )
        out = add_pair_features(pairs, threshold=0.2, min_shared=1)
        assert bool(out.loc[0, "passes_overlap"]) and bool(out.loc[0, "passes_shared"])
        assert "shorter_tokens" not in pairs.columns


class TestDurationCoherence:
    def test_gap_between_recorded_duration_and_last_turn(self) -> None:
        meetings = pd.DataFrame({"meeting_id": ["m1", "m2"], "duration_seconds": [100.0, 50.0]})
        turns = pd.DataFrame({"meeting_id": ["m1", "m1"], "end": [40.0, 90.0]})
        out = duration_coherence(meetings, turns).set_index("meeting_id")
        assert out.loc["m1", "transcript_end_seconds"] == 90.0
        assert out.loc["m1", "gap_seconds"] == pytest.approx(10.0)
        assert out.loc["m1", "gap_share"] == pytest.approx(0.1)
        assert math.isnan(out.loc["m2", "transcript_end_seconds"])
        assert math.isnan(out.loc["m2", "gap_seconds"])


class TestFormatThousands:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0, "0"), (999, "999"), (1000, "1.000"), (5429041, "5.429.041"), (83868, "83.868")],
    )
    def test_integers_use_the_dot_as_thousands_separator(self, value: int, expected: str) -> None:
        assert format_thousands(value) == expected

    def test_decimals_use_the_comma(self) -> None:
        assert format_thousands(1.3, 1) == "1,3"
        assert format_thousands(9452.3, 0) == "9.452"
        assert format_thousands(12288.456, 2) == "12.288,46"

    def test_negative_numbers_keep_the_sign(self) -> None:
        assert format_thousands(-1234) == "-1.234"


class TestLengthBins:
    def test_labels_name_every_bin(self) -> None:
        assert len(LEN_LABELS) == len(LEN_BINS) - 1

    def test_bins_cover_the_shortest_decision_phrases_up_to_eleven_or_more(self) -> None:
        assert LEN_BINS == [0, 1, 2, 3, 4, 6, 10, 30]
        assert LEN_LABELS == ["1", "2", "3", "4", "5-6", "7-10", "11+"]
