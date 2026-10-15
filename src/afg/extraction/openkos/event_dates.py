"""Event dates of the AMI meetings, for ``openkos ingest --event-date`` (ADR 0008).

OpenKOS orders the decisions of a workspace by the event date of their source, so the four
meetings of a series need strictly increasing dates. In AMI the four meetings of a series
share one ``dateOnly`` and, for 8 of the 14 study series, ``startTime`` is empty or absent.

Rule (approved by the project lead):

* real date plus real ``startTime`` when the latter exists (``time_source = "ami"``);
* real date plus a SYNTHETIC clock time otherwise, by meeting letter a=09:00, b=10:00,
  c=11:00, d=12:00 (``time_source = "synthetic"``). The AMI scenario defines the meetings in
  sequence, so this only encodes ORDER, never real duration or gaps;
* the result must be strictly increasing a to d; otherwise :class:`EventDateError` is raised
  and nothing is reordered.

Date parsing (day-month order, two- or four-digit years) is the one of the EDA tables.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Literal

import pandas as pd

from afg.corpus.nxt import find_by_local_name, get_attr, parse_xml
from afg.eda.tables import _parse_date, _parse_start
from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos.workspace import MeetingSource
from afg.shared.config import load_corpus_config

TimeSource = Literal["ami", "synthetic"]

POSITION_LETTERS: tuple[str, ...] = ("a", "b", "c", "d")
SYNTHETIC_HOURS: dict[str, int] = {"a": 9, "b": 10, "c": 11, "d": 12}
_FORMAT = "%Y-%m-%dT%H:%M"


class EventDateError(OpenKosError):
    """The event dates of a series cannot be built or are not strictly increasing."""


@dataclass(frozen=True, slots=True)
class MeetingEventDate:
    """``event_date`` is ``YYYY-MM-DDTHH:MM``, ready for ``--event-date``."""

    meeting_id: str
    event_date: str
    time_source: TimeSource


def _attributes(meetings_xml: Path) -> dict[str, tuple[str | None, str | None]]:
    root = parse_xml(meetings_xml)
    found: dict[str, tuple[str | None, str | None]] = {}
    for element in find_by_local_name(root, "meeting"):
        observation = get_attr(element, "observation")
        if observation:
            found[observation] = (get_attr(element, "dateOnly"), get_attr(element, "startTime"))
    return found


def _meeting_event_date(
    meeting_id: str, letter: str, date_only: str | None, start_time: str | None
) -> tuple[pd.Timestamp, pd.Timestamp, MeetingEventDate]:
    """Parsed date, real start (NaT when absent) and the resulting event date of one meeting."""
    day = _parse_date(date_only)
    if pd.isna(day):
        raise EventDateError(f"{meeting_id}: unparseable dateOnly {date_only!r}.")
    start = _parse_start(date_only, start_time)
    source: TimeSource = "ami"
    moment = start
    if pd.isna(start):
        moment, source = day + pd.Timedelta(hours=SYNTHETIC_HOURS[letter]), "synthetic"
    return day, start, MeetingEventDate(meeting_id, moment.strftime(_FORMAT), source)


def read_series_event_dates(meetings_xml: Path, series_id: str) -> tuple[MeetingEventDate, ...]:
    """Event dates of meetings ``<series_id>a`` to ``d`` from AMI ``meetings.xml``.

    Raises:
        EventDateError: a meeting or its ``dateOnly`` is missing or unparseable, or the
            resulting datetimes are not strictly increasing from a to d.
    """
    attributes = _attributes(meetings_xml)
    out: list[MeetingEventDate] = []
    for letter in POSITION_LETTERS:
        meeting_id = f"{series_id}{letter}"
        if meeting_id not in attributes:
            raise EventDateError(f"{meeting_id} is not in {meetings_xml}.")
        date_only, start_time = attributes[meeting_id]
        out.append(_meeting_event_date(meeting_id, letter, date_only, start_time)[2])
    stamps = [d.event_date for d in out]
    if any(later <= earlier for earlier, later in pairwise(stamps)):
        raise EventDateError(
            f"{series_id}: event dates are not strictly increasing a to d: {stamps}."
        )
    return tuple(out)


# --- evidence behind ADR 0008 (notebook 08) ---------------------------------------------------

_TABLE_COLUMNS = [
    "series",
    "meeting",
    "partition",
    "date_only_raw",
    "date",
    "start_time_raw",
    "start_time_state",
    "start_time",
    "event_date",
    "time_source",
]


def study_series() -> list[tuple[str, str]]:
    """The 14 study series as ``(series, partition)``: development first, then evaluation."""
    oe1 = load_corpus_config()["oe1"]
    return [(s, "development") for s in oe1["development_series"]] + [
        (s, "evaluation") for s in oe1["evaluation_series"]
    ]


def meeting_date_table(meetings_xml: Path, series_ids: Sequence[str] | None = None) -> pd.DataFrame:
    """One row per meeting: the raw ``dateOnly`` / ``startTime`` and what the rule makes of them.

    ``start_time_state`` tells an attribute that is ``"present"`` with a value from one that is
    ``"empty"`` (``startTime=""``) or ``"absent"`` (no attribute at all); ``start_time_raw``
    keeps ``""`` and a missing value (None or NaN) accordingly. ``series_ids`` defaults to
    :func:`study_series`.
    The strict-increase check of :func:`read_series_event_dates` is NOT applied here: this
    table is evidence, so it reports the order instead of refusing to build.

    Raises:
        EventDateError: a meeting of the series is missing or has an unparseable ``dateOnly``.
    """
    partitions = dict(study_series())
    attributes = _attributes(meetings_xml)
    rows: list[dict[str, object]] = []
    for series in series_ids if series_ids is not None else list(partitions):
        for letter in POSITION_LETTERS:
            meeting_id = f"{series}{letter}"
            if meeting_id not in attributes:
                raise EventDateError(f"{meeting_id} is not in {meetings_xml}.")
            date_only, start_time = attributes[meeting_id]
            day, start, event = _meeting_event_date(meeting_id, letter, date_only, start_time)
            state = "absent" if start_time is None else "empty" if start_time == "" else "present"
            rows.append(
                {
                    "series": series,
                    "meeting": meeting_id,
                    "partition": partitions.get(series),
                    "date_only_raw": date_only,
                    "date": day,
                    "start_time_raw": start_time,
                    "start_time_state": state,
                    "start_time": None if pd.isna(start) else start.strftime("%H:%M"),
                    "event_date": event.event_date,
                    "time_source": event.time_source,
                }
            )
    return pd.DataFrame(rows, columns=_TABLE_COLUMNS)


def series_date_summary(table: pd.DataFrame) -> pd.DataFrame:
    """One row per series from :func:`meeting_date_table`.

    Columns: ``n_distinct_dates``, ``n_real_times`` (meetings with an AMI start time),
    ``all_real_times``, ``real_times_increasing`` (``True``/``False`` over the real times, in
    a to d order; ``None`` with fewer than two), ``gap_ab_min`` / ``gap_bc_min`` /
    ``gap_cd_min`` (minutes between consecutive meetings when both have a real time, else NaN;
    descriptive only) and ``event_dates_increasing`` (the resulting event dates, strictly).
    """
    rows: list[dict[str, object]] = []
    for series, group in table.groupby("series", sort=False):
        group = group.sort_values("meeting")
        real = [
            None if pd.isna(t) else pd.Timestamp(f"{d.date()} {t}")
            for d, t in zip(group["date"], group["start_time"], strict=True)
        ]
        present = [t for t in real if t is not None]
        increasing: bool | None = (
            all(b > a for a, b in pairwise(present)) if len(present) >= 2 else None
        )
        gaps: dict[str, float] = {}
        for (x, y), (a, b) in zip(pairwise("abcd"), pairwise(real), strict=True):
            both = a is not None and b is not None
            gaps[f"gap_{x}{y}_min"] = (b - a).total_seconds() / 60 if both else float("nan")  # type: ignore[operator]
        stamps = list(group["event_date"])
        rows.append(
            {
                "series": series,
                "partition": group["partition"].iloc[0],
                "n_distinct_dates": int(group["date"].nunique()),
                "n_real_times": len(present),
                "all_real_times": len(present) == len(real),
                "real_times_increasing": increasing,
                **gaps,
                "event_dates_increasing": all(b > a for a, b in pairwise(stamps)),
            }
        )
    out = pd.DataFrame(rows)
    out["real_times_increasing"] = out["real_times_increasing"].astype(object)
    return out


def attach_event_dates(
    sources: Sequence[MeetingSource], meetings_xml: Path, series_id: str
) -> list[MeetingSource]:
    """Return ``sources`` with ``event_date`` and ``time_source`` set for every meeting.

    Raises:
        EventDateError: dates cannot be built, or a source is not a meeting of the series.
    """
    dates = {d.meeting_id: d for d in read_series_event_dates(meetings_xml, series_id)}
    unknown = [s.meeting_id for s in sources if s.meeting_id not in dates]
    if unknown:
        raise EventDateError(f"Not meetings of series {series_id}: {unknown}.")
    return [
        replace(
            s,
            event_date=dates[s.meeting_id].event_date,
            time_source=dates[s.meeting_id].time_source,
        )
        for s in sources
    ]
