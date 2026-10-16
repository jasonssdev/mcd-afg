"""Tests for the meeting event dates passed to ``openkos ingest --event-date``."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from afg.extraction.openkos.event_dates import (
    EventDateError,
    attach_event_dates,
    date_availability_summary,
    meeting_date_table,
    read_series_event_dates,
    series_date_summary,
    study_series,
)
from afg.extraction.openkos.workspace import (
    MeetingSource,
    OpenKosRunSettings,
    run_series_workspace,
)
from afg.shared.paths import AMI_DIR
from tests.markers import requires
from tests.openkos_fake import FakeRunner

_MEETINGS_XML = AMI_DIR / "corpusResources" / "meetings.xml"
requires_meetings_xml = requires(
    "requires_meetings_xml",
    available=_MEETINGS_XML.exists(),
    reason="AMI meetings.xml not available locally",
)

SETTINGS = OpenKosRunSettings(
    executable="openkos",
    generative_model="qwen3:8b",
    embedding_model="bge-m3",
    base_seed=42,
    temperature=0.1,
)


def _xml(rows: dict[str, tuple[str, str | None]]) -> str:
    """``{meeting: (dateOnly, startTime or None for an absent attribute)}`` as meetings.xml."""
    lines = ['<?xml version="1.0"?>', '<meetings xmlns:nite="http://nite.sourceforge.net/">']
    for meeting, (date, start) in rows.items():
        start_attr = "" if start is None else f' startTime="{start}"'
        lines.append(f'<meeting observation="{meeting}" dateOnly="{date}"{start_attr}/>')
    lines.append("</meetings>")
    return "\n".join(lines)


def _write(tmp_path: Path, rows: dict[str, tuple[str, str | None]]) -> Path:
    path = tmp_path / "meetings.xml"
    path.write_text(_xml(rows), encoding="utf-8")
    return path


def _series(series: str, date: str, starts: tuple[str | None, ...]):  # type: ignore[no-untyped-def]
    return {f"{series}{x}": (date, s) for x, s in zip("abcd", starts, strict=True)}


def test_synthetic_times_when_start_is_empty(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("ES2015", "09-03-05", ("", "", "", "")))
    dates = read_series_event_dates(xml, "ES2015")
    assert [d.meeting_id for d in dates] == ["ES2015a", "ES2015b", "ES2015c", "ES2015d"]
    assert [d.event_date for d in dates] == [
        "2005-03-09T09:00",
        "2005-03-09T10:00",
        "2005-03-09T11:00",
        "2005-03-09T12:00",
    ]
    assert {d.time_source for d in dates} == {"synthetic"}


def test_synthetic_times_when_start_attribute_is_absent(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("TS3003", "19-11-2004", (None, None, None, None)))
    dates = read_series_event_dates(xml, "TS3003")
    assert dates[0].event_date == "2004-11-19T09:00"
    assert dates[3].event_date == "2004-11-19T12:00"
    assert {d.time_source for d in dates} == {"synthetic"}


def test_real_times_use_day_month_order_and_are_marked_ami(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("IS1004", "23-11-2004", ("11h03", "12h03", "14h13", "15h34")))
    dates = read_series_event_dates(xml, "IS1004")
    assert [d.event_date for d in dates] == [
        "2004-11-23T11:03",
        "2004-11-23T12:03",
        "2004-11-23T14:13",
        "2004-11-23T15:34",
    ]
    assert {d.time_source for d in dates} == {"ami"}


def test_mixed_real_and_missing_is_per_meeting(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("IS1003", "11-10-2004", ("08h00", "", "13h00", "14h00")))
    dates = read_series_event_dates(xml, "IS1003")
    assert [d.time_source for d in dates] == ["ami", "synthetic", "ami", "ami"]
    assert dates[1].event_date == "2004-10-11T10:00"


def test_non_increasing_result_raises(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("IS1003", "11-10-2004", ("10h00", "", "13h00", "14h00")))
    with pytest.raises(EventDateError, match="IS1003"):
        read_series_event_dates(xml, "IS1003")


def test_real_times_out_of_order_raise(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("IS1008", "11-10-2004", ("15h00", "12h00", "16h00", "17h00")))
    with pytest.raises(EventDateError, match="strictly increasing"):
        read_series_event_dates(xml, "IS1008")


def test_missing_meeting_or_date_raises(tmp_path: Path) -> None:
    rows = _series("ES2015", "09-03-05", ("", "", "", ""))
    del rows["ES2015c"]
    with pytest.raises(EventDateError, match="ES2015c"):
        read_series_event_dates(_write(tmp_path, rows), "ES2015")
    rows = _series("ES2015", "not-a-date", ("", "", "", ""))
    with pytest.raises(EventDateError, match="dateOnly"):
        read_series_event_dates(_write(tmp_path, rows), "ES2015")


def _sources(tmp_path: Path) -> list[MeetingSource]:
    out = []
    for letter in "abcd":
        path = tmp_path / "src" / f"ES2015{letter}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text("PM: hi\n", encoding="utf-8")
        out.append(MeetingSource(f"ES2015{letter}", path))
    return out


def test_attach_event_dates_fills_all_four_sources(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("ES2015", "09-03-05", ("", "", "", "")))
    dated = attach_event_dates(_sources(tmp_path), xml, "ES2015")
    assert [s.event_date for s in dated] == [
        "2005-03-09T09:00",
        "2005-03-09T10:00",
        "2005-03-09T11:00",
        "2005-03-09T12:00",
    ]
    assert {s.time_source for s in dated} == {"synthetic"}


def test_workspace_passes_dates_and_manifest_records_time_source(tmp_path: Path) -> None:
    xml = _write(tmp_path, _series("ES2015", "09-03-05", ("", "", "", "")))
    dated = attach_event_dates(_sources(tmp_path), xml, "ES2015")
    runner = FakeRunner()
    result = run_series_workspace(
        runner,
        series_id="ES2015",
        run=0,
        base_dir=tmp_path / "ws",
        settings=SETTINGS,
        sources=dated,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["event_dates_passed"] is True
    assert manifest["event_dates"] == [
        {"meeting_id": f"ES2015{x}", "event_date": f"2005-03-09T{h}:00", "time_source": "synthetic"}
        for x, h in zip("abcd", ("09", "10", "11", "12"), strict=True)
    ]
    ingests = [c for c in manifest["commands"] if "ingest" in c["argv"] and "--auto" in c["argv"]]
    assert [c["argv"][c["argv"].index("--event-date") + 1] for c in ingests] == [
        "2005-03-09T09:00",
        "2005-03-09T10:00",
        "2005-03-09T11:00",
        "2005-03-09T12:00",
    ]


@requires_meetings_xml
def test_real_file_es2015_and_is1004() -> None:
    es = read_series_event_dates(_MEETINGS_XML, "ES2015")
    assert [d.event_date for d in es] == [
        "2005-03-09T09:00",
        "2005-03-09T10:00",
        "2005-03-09T11:00",
        "2005-03-09T12:00",
    ]
    assert {d.time_source for d in es} == {"synthetic"}
    is_ = read_series_event_dates(_MEETINGS_XML, "IS1004")
    assert [d.event_date for d in is_] == [
        "2004-11-23T11:03",
        "2004-11-23T12:03",
        "2004-11-23T14:13",
        "2004-11-23T15:34",
    ]
    assert {d.time_source for d in is_} == {"ami"}


# --- evidence tables behind ADR 0008 (notebook 08) -------------------------------------------


def _mixed_xml(tmp_path: Path) -> Path:
    rows: dict[str, tuple[str, str | None]] = {}
    rows.update(_series("ES2015", "09-03-05", ("", "", "", "")))  # empty attribute
    rows.update(_series("TS3003", "02-12-04", (None, None, None, None)))  # absent attribute
    rows.update(_series("IS1004", "23-11-2004", ("11h03", "12h03", "14h13", "15h34")))
    return _write(tmp_path, rows)


def test_meeting_date_table_distinguishes_empty_absent_and_present(tmp_path: Path) -> None:
    table = meeting_date_table(_mixed_xml(tmp_path), ["ES2015", "TS3003", "IS1004"])
    assert list(table["meeting"][:4]) == ["ES2015a", "ES2015b", "ES2015c", "ES2015d"]
    by_series = table.groupby("series")["start_time_state"].agg(lambda s: set(s)).to_dict()
    assert by_series == {"ES2015": {"empty"}, "TS3003": {"absent"}, "IS1004": {"present"}}
    es = table[table["series"] == "ES2015"].iloc[0]
    assert es["date_only_raw"] == "09-03-05"
    assert es["start_time_raw"] == ""
    assert str(es["date"].date()) == "2005-03-09"
    assert es["event_date"] == "2005-03-09T09:00"
    assert es["time_source"] == "synthetic"
    ts = table[table["series"] == "TS3003"].iloc[0]
    assert pd.isna(ts["start_time_raw"])
    assert ts["event_date"] == "2004-12-02T09:00"
    is_ = table[table["meeting"] == "IS1004c"].iloc[0]
    assert is_["start_time_raw"] == "14h13"
    assert is_["start_time"] == "14:13"
    assert is_["event_date"] == "2004-11-23T14:13"
    assert is_["time_source"] == "ami"


def test_meeting_date_table_event_dates_match_read_series_event_dates(tmp_path: Path) -> None:
    xml = _mixed_xml(tmp_path)
    table = meeting_date_table(xml, ["ES2015", "IS1004"])
    for series in ("ES2015", "IS1004"):
        expected = [d.event_date for d in read_series_event_dates(xml, series)]
        assert list(table[table["series"] == series]["event_date"]) == expected


def test_series_date_summary(tmp_path: Path) -> None:
    xml = _mixed_xml(tmp_path)
    summary = series_date_summary(meeting_date_table(xml, ["ES2015", "TS3003", "IS1004"]))
    row = summary.set_index("series")
    assert row.loc["ES2015", "n_distinct_dates"] == 1
    assert row.loc["ES2015", "n_real_times"] == 0
    assert not row.loc["ES2015", "all_real_times"]
    assert row.loc["ES2015", "real_times_increasing"] is None
    assert row.loc["IS1004", "n_real_times"] == 4
    assert row.loc["IS1004", "all_real_times"]
    assert row.loc["IS1004", "real_times_increasing"] is True
    assert (row.loc["IS1004", "gap_ab_min"], row.loc["IS1004", "gap_bc_min"]) == (60, 130)
    assert row.loc["IS1004", "gap_cd_min"] == 81
    assert row.loc["IS1004", "event_dates_increasing"]
    assert pd.isna(row.loc["ES2015", "gap_ab_min"])


def test_series_date_summary_flags_decreasing_real_times(tmp_path: Path) -> None:
    rows = _series("IS1003", "01-01-2005", ("11h00", "10h00", "12h00", "13h00"))
    table = meeting_date_table(_write(tmp_path, rows), ["IS1003"])
    row = series_date_summary(table).iloc[0]
    assert row["real_times_increasing"] is False
    assert not row["event_dates_increasing"]


def test_date_availability_summary_splits_real_none_and_partial_series(tmp_path: Path) -> None:
    rows = {
        **_series("IS1004", "23-11-2004", ("11h03", "12h03", "14h13", "15h34")),
        **_series("ES2015", "09-03-05", ("", "", "", "")),
        **_series("TS3003", "02-12-2004", (None, None, None, None)),
        **_series("IS1003", "19-11-2004", ("09h35", "", "13h51", "15h13")),
    }
    table = meeting_date_table(_write(tmp_path, rows), ["IS1004", "ES2015", "TS3003", "IS1003"])
    summary = date_availability_summary(table)
    assert summary.real_series == ("IS1004",)
    assert summary.none_series == ("ES2015", "TS3003")
    assert summary.partial_series == ("IS1003",)
    assert (summary.n_ami_meetings, summary.n_synthetic_meetings) == (7, 9)
    assert summary.single_date_per_series is True
    assert summary.event_dates_increasing is True


def test_date_availability_summary_reports_the_gaps_between_real_starts(tmp_path: Path) -> None:
    rows = _series("IS1004", "23-11-2004", ("11h03", "12h03", "14h13", "15h34"))
    table = meeting_date_table(_write(tmp_path, rows), ["IS1004"])
    summary = date_availability_summary(table)
    assert summary.n_real_series_increasing == 1
    assert (summary.gap_min, summary.gap_max, summary.gap_median) == (60, 130, 81)


def test_date_availability_summary_without_real_times_has_no_gaps(tmp_path: Path) -> None:
    rows = _series("ES2015", "09-03-05", ("", "", "", ""))
    table = meeting_date_table(_write(tmp_path, rows), ["ES2015"])
    summary = date_availability_summary(table)
    assert summary.gap_min is None and summary.gap_max is None and summary.gap_median is None
    assert summary.n_real_series_increasing == 0


def test_date_availability_summary_lists_series_by_start_time_state(tmp_path: Path) -> None:
    table = meeting_date_table(_mixed_xml(tmp_path), ["ES2015", "TS3003", "IS1004"])
    states = date_availability_summary(table).series_by_start_time_state
    assert states == {"absent": ["TS3003"], "empty": ["ES2015"], "present": ["IS1004"]}


def test_study_series_lists_development_then_evaluation() -> None:
    series = study_series()
    assert len(series) == 14
    assert series[0][1] == "development"
    assert dict(series)["ES2015"] == "development"
    assert dict(series)["ES2002"] == "evaluation"
    assert [p for _, p in series].count("development") == 3


@requires_meetings_xml
def test_real_file_evidence_reproduces_adr_0008_figures() -> None:
    table = meeting_date_table(_MEETINGS_XML)
    summary = series_date_summary(table).set_index("series")
    assert len(summary) == 14
    assert (summary["n_distinct_dates"] == 1).all()
    real = set(summary.index[summary["all_real_times"]])
    assert real == {"ES2008", "IS1003", "IS1004", "IS1006", "IS1008", "IS1009"}
    assert summary.loc[sorted(real), "real_times_increasing"].all()
    state = table.groupby("series")["start_time_state"].first()
    assert {s for s in state.index if state[s] == "empty"} == {
        "ES2002", "ES2014", "ES2015", "ES2016",
    }  # fmt: skip
    assert {s for s in state.index if state[s] == "absent"} == {
        "TS3003", "TS3005", "TS3009", "TS3011",
    }  # fmt: skip


@requires_meetings_xml
def test_date_availability_summary_matches_the_counts_adr_0008_cites() -> None:
    summary = date_availability_summary(meeting_date_table(_MEETINGS_XML))
    assert (len(summary.real_series), len(summary.none_series), len(summary.partial_series)) == (
        6,
        8,
        0,
    )
    assert (summary.n_ami_meetings, summary.n_synthetic_meetings) == (24, 32)
    assert summary.n_real_series_increasing == 6
    assert (summary.gap_min, summary.gap_max, summary.gap_median) == (60, 141, 79.5)
    assert summary.single_date_per_series is True
    assert summary.event_dates_increasing is True
