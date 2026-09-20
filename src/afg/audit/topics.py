"""Decision/topic boundary coincidence -- a measurement, not a citation (thesis section
5.1 data audit).

Thesis section 5.1 currently *cites* Hsueh & Moore for the claim that decision-discussion
boundaries coincide with topic boundaries less than half the time. This module measures it
directly on the AMI sample instead, restricted to the 6 series that carry both the
``topics/<meeting>.topic.xml`` layer and the Decision Discussion Segmentation (DDS) layer
(``decision/manual/<meeting>.decision.xml``): ``config/corpus.toml`` ``[corpus.series].ids``
(``ES2015``, ``ES2016``, ``IS1004``, ``IS1006``, ``IS1008``, ``TS3005``). No other AMI
series has the DDS layer at all, so no other series can support this comparison.

## Method

Both layers address word ranges the same way (``<nite:child href="<meeting>.<speaker>.
words.xml#id(a)..id(b)"/>``), across potentially several speakers' word files per segment
(a decision or a topic can span turns from more than one participant). Each ``<w>``/
``<vocalsound>`` element in a words file carries real ``starttime``/``endtime`` attributes
(seconds into the recording), so a segment's start is resolved as the EARLIEST measured
``starttime`` among all the words its ``<nite:child>`` ranges reference -- a real corpus
timestamp, not an inferred one.

Topic boundaries are the start times of TOP-LEVEL ``<topic>`` elements only (direct
children of the topic file's root); nested ``<topic>`` subtopics are not treated as
separate boundaries, matching the coarse granularity Hsueh & Moore's claim is about.

``tolerance_words`` is a word count, but segment starts are timestamps, not word
positions (segments span multiple, independently-numbered speaker channels, so there is
no single, well-defined "word index" that both a decision and a topic segment share). To
compare them, the tolerance is converted to a time window using that MEETING's own mean
observed word duration (``sum(endtime - starttime) / count`` over every ``<w>``/
``<vocalsound>`` in that meeting, across all its speaker files) -- a quantity measured from
that same meeting's real timestamps, not an invented constant. A decision segment counts as
aligned with the topic layer when its start time falls within ``tolerance_words *
mean_word_duration`` seconds of the nearest topic-segment start time in the same meeting.

This conversion is an approximation (speaking rate varies within a meeting), stated here
plainly as a measured limitation, not hidden. If no meeting in the requested scope has
both layers with resolvable word timings, this returns an explicit "not computable" result
(``computable=False``) with a reason, rather than a fabricated rate.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from lxml import etree

from afg.corpus.nxt import (
    NxtParseError,
    discover_annotation_files,
    get_attr_by_local_name,
    iter_elements,
    parse_xml,
)
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR

MEETING_LETTERS: tuple[str, ...] = ("a", "b", "c", "d")
DEFAULT_TOLERANCE_WORDS = 5

_HREF_RE = re.compile(r"^(?P<file>[^#]+)#id\((?P<start>[^)]+)\)(?:\.\.id\((?P<end>[^)]+)\))?$")

_PER_MEETING_COLUMNS = ("meeting_id", "n_decisions", "n_aligned", "coincidence_rate")


@dataclass(frozen=True, slots=True)
class TopicBoundaryOverlapResult:
    """Result of :func:`topic_decision_boundary_overlap`.

    Check ``computable`` before trusting ``aggregate_coincidence_rate`` or ``per_meeting``:
    when ``computable`` is False, ``reason`` explains why and the rate fields carry no
    fabricated value.
    """

    computable: bool
    reason: str | None
    tolerance_words: int
    meetings_considered: tuple[str, ...]
    meetings_skipped: tuple[str, ...]
    per_meeting: pd.DataFrame
    aggregate_n_decisions: int
    aggregate_n_aligned: int
    aggregate_coincidence_rate: float | None


def dds_series_ids() -> list[str]:
    """The 6 AMI series carrying the DDS layer (``config/corpus.toml`` ``[corpus.series].ids``)."""
    series: list[str] = load_corpus_config()["corpus"]["series"]["ids"]
    return series


def _load_word_starttimes(
    ami_root: Path, filename: str, cache: dict[str, dict[str, float]]
) -> dict[str, float]:
    if filename in cache:
        return cache[filename]
    matches = discover_annotation_files(ami_root, filename)
    if not matches:
        cache[filename] = {}
        return cache[filename]
    try:
        root = parse_xml(matches[0])
    except NxtParseError:
        cache[filename] = {}
        return cache[filename]

    times: dict[str, float] = {}
    for element in root:
        word_id = get_attr_by_local_name(element, "id")
        start_raw = element.get("starttime")
        if word_id and start_raw is not None:
            try:
                times[word_id] = float(start_raw)
            except ValueError:
                continue
    cache[filename] = times
    return times


def _segment_start_time(
    ami_root: Path, hrefs: Sequence[str], cache: dict[str, dict[str, float]]
) -> float | None:
    times: list[float] = []
    for href in hrefs:
        match = _HREF_RE.match(href)
        if not match:
            continue
        word_times = _load_word_starttimes(ami_root, match.group("file"), cache)
        start_time = word_times.get(match.group("start"))
        if start_time is not None:
            times.append(start_time)
    return min(times) if times else None


def _child_hrefs(element: etree._Element, *, recursive: bool) -> list[str]:
    hrefs: list[str] = []
    iterable = element.iter() if recursive else iter(element)
    for child in iterable:
        tag = child.tag
        if isinstance(tag, str) and tag.split("}")[-1] == "child":
            href = child.get("href")
            if href:
                hrefs.append(href)
    return hrefs


def _mean_word_duration(ami_root: Path, meeting_id: str) -> float | None:
    word_files = discover_annotation_files(ami_root, f"{meeting_id}.*.words.xml")
    durations: list[float] = []
    for path in word_files:
        try:
            root = parse_xml(path)
        except NxtParseError:
            continue
        for element in root:
            start_raw = element.get("starttime")
            end_raw = element.get("endtime")
            if start_raw is None or end_raw is None:
                continue
            try:
                duration = float(end_raw) - float(start_raw)
            except ValueError:
                continue
            if duration >= 0:
                durations.append(duration)
    if not durations:
        return None
    return sum(durations) / len(durations)


def _empty_per_meeting_df() -> pd.DataFrame:
    df = pd.DataFrame(columns=list(_PER_MEETING_COLUMNS))
    return df.astype(
        {
            "meeting_id": "object",
            "n_decisions": "int64",
            "n_aligned": "int64",
            "coincidence_rate": "float64",
        }
    )


def topic_decision_boundary_overlap(
    ami_root: Path = AMI_DIR,
    series: Sequence[str] = (),
    tolerance_words: int = DEFAULT_TOLERANCE_WORDS,
) -> TopicBoundaryOverlapResult:
    """Measure how often a DDS decision segment's start coincides with a topic-segment
    start, within ``tolerance_words`` (converted to a per-meeting time window -- see the
    module docstring), restricted to the 6 DDS series.

    ``series`` is intersected with :func:`dds_series_ids`; an empty ``series`` means "all 6
    DDS series". Any requested series outside that set is silently excluded from the scope
    (not an error -- it simply has no DDS layer to measure against), and the exclusion is
    never hidden: ``meetings_skipped`` in the result lists every meeting considered but not
    usable, and a fully-empty scope returns ``computable=False``.
    """
    available = dds_series_ids()
    scope = [s for s in series if s in available] if series else list(available)

    if not scope:
        return TopicBoundaryOverlapResult(
            computable=False,
            reason=(
                "None of the requested series carry the DDS layer; the topic/decision "
                f"boundary comparison is only possible for {available}."
            ),
            tolerance_words=tolerance_words,
            meetings_considered=(),
            meetings_skipped=(),
            per_meeting=_empty_per_meeting_df(),
            aggregate_n_decisions=0,
            aggregate_n_aligned=0,
            aggregate_coincidence_rate=None,
        )

    words_cache: dict[str, dict[str, float]] = {}
    per_meeting_rows: list[dict[str, object]] = []
    meetings_considered: list[str] = []
    meetings_skipped: list[str] = []
    total_decisions = 0
    total_aligned = 0

    for series_id in scope:
        for letter in MEETING_LETTERS:
            meeting_id = f"{series_id}{letter}"
            topic_matches = discover_annotation_files(ami_root, f"{meeting_id}.topic.xml")
            decision_matches = discover_annotation_files(ami_root, f"{meeting_id}.decision.xml")
            if not topic_matches or not decision_matches:
                meetings_skipped.append(meeting_id)
                continue

            try:
                topic_root = parse_xml(topic_matches[0])
                decision_root = parse_xml(decision_matches[0])
            except NxtParseError:
                meetings_skipped.append(meeting_id)
                continue

            topic_starts: list[float] = []
            for element in topic_root:
                tag = element.tag
                if isinstance(tag, str) and tag.split("}")[-1] == "topic":
                    start = _segment_start_time(
                        ami_root, _child_hrefs(element, recursive=True), words_cache
                    )
                    if start is not None:
                        topic_starts.append(start)
            topic_starts.sort()

            decision_starts: list[float] = []
            for decision_el in iter_elements(decision_root, "decision"):
                hrefs = _child_hrefs(decision_el, recursive=False)
                start = _segment_start_time(ami_root, hrefs, words_cache)
                if start is not None:
                    decision_starts.append(start)

            mean_duration = _mean_word_duration(ami_root, meeting_id)

            if not topic_starts or not decision_starts or not mean_duration:
                meetings_skipped.append(meeting_id)
                continue

            tolerance_seconds = tolerance_words * mean_duration
            aligned = sum(
                1
                for decision_start in decision_starts
                if min(abs(t - decision_start) for t in topic_starts) <= tolerance_seconds
            )

            n = len(decision_starts)
            per_meeting_rows.append(
                {
                    "meeting_id": meeting_id,
                    "n_decisions": n,
                    "n_aligned": aligned,
                    "coincidence_rate": (aligned / n) if n else 0.0,
                }
            )
            meetings_considered.append(meeting_id)
            total_decisions += n
            total_aligned += aligned

    per_meeting_df = pd.DataFrame(per_meeting_rows, columns=list(_PER_MEETING_COLUMNS))
    per_meeting_df = per_meeting_df.astype(
        {
            "meeting_id": "object",
            "n_decisions": "int64",
            "n_aligned": "int64",
            "coincidence_rate": "float64",
        }
    )

    if not meetings_considered:
        return TopicBoundaryOverlapResult(
            computable=False,
            reason=(
                "No meeting in the requested scope has both a topic file and a decision "
                "file with resolvable word timings."
            ),
            tolerance_words=tolerance_words,
            meetings_considered=(),
            meetings_skipped=tuple(meetings_skipped),
            per_meeting=per_meeting_df,
            aggregate_n_decisions=0,
            aggregate_n_aligned=0,
            aggregate_coincidence_rate=None,
        )

    return TopicBoundaryOverlapResult(
        computable=True,
        reason=None,
        tolerance_words=tolerance_words,
        meetings_considered=tuple(meetings_considered),
        meetings_skipped=tuple(meetings_skipped),
        per_meeting=per_meeting_df,
        aggregate_n_decisions=total_decisions,
        aggregate_n_aligned=total_aligned,
        aggregate_coincidence_rate=(total_aligned / total_decisions) if total_decisions else None,
    )
