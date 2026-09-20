"""Decision-sentence measurements for the six OE1 series over which they are called
(thesis section 5.1/5.2 data audit).

Every function here is built on top of :func:`afg.annotation.blocking.decisions_from_abstractive`
-- the same, already-verified, parser used by the blocker -- so this module never
re-parses ``abstractive/<meeting>.abssumm.xml`` on its own.

``series`` is always an explicit sequence of AMI series ids (e.g. ``config/corpus.toml``
``[oe1].series``, or a single-element list for one series). Nothing here hard-codes which
series to look at: the caller decides the scope, exactly as the project rules require.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from afg.annotation.blocking import decisions_from_abstractive, tokenize
from afg.domain.decision import Decision
from afg.shared.paths import AMI_DIR

MEETING_LETTERS: tuple[str, ...] = ("a", "b", "c", "d")

# Open-proposal / hedge marker phrases (thesis section 5.2). These are a HINT only --
# their precision at distinguishing a genuine open proposal from an accepted decision that
# merely discusses future work has not been measured. Do not treat a sentence containing
# one of these markers as a confirmed non-decision without human review; that measurement
# is exactly what thesis section 5.2 / OE1's double annotation is for.
NON_DECISION_MARKERS: tuple[str, ...] = (
    "will consider",
    "will research",
    "should be",
    "might",
    "maybe",
    "could",
)


def site_prefix(series_id: str) -> str:
    """The AMI recording-site code (``ES``/``IS``/``TS``) that prefixes a series id."""
    return series_id[:2]


def _load_decisions(ami_root: Path, series: Sequence[str]) -> list[Decision]:
    """Concatenate :func:`decisions_from_abstractive` over every series in ``series``."""
    decisions: list[Decision] = []
    for series_id in series:
        decisions.extend(decisions_from_abstractive(ami_root, series_id))
    return decisions


def decision_counts(ami_root: Path = AMI_DIR, series: Sequence[str] = ()) -> pd.DataFrame:
    """One row per (series, meeting-letter) in ``series``, with the number of raw
    abstractive DECISIONS sentences found for that meeting.

    Every meeting of every requested series gets a row, even when the count is zero --
    this is a completeness table, not a sparse one. Columns: ``series_id`` (str),
    ``meeting_id`` (str), ``site`` (str, the ``ES``/``IS``/``TS`` prefix), ``meeting_letter``
    (str, one of ``a``/``b``/``c``/``d``), ``n_decisions`` (int).
    """
    decisions = _load_decisions(ami_root, series)
    counts: Counter[str] = Counter(d.meeting_id for d in decisions)

    rows = [
        {
            "series_id": series_id,
            "meeting_id": f"{series_id}{letter}",
            "site": site_prefix(series_id),
            "meeting_letter": letter,
            "n_decisions": counts.get(f"{series_id}{letter}", 0),
        }
        for series_id in series
        for letter in MEETING_LETTERS
    ]
    df = pd.DataFrame(
        rows, columns=["series_id", "meeting_id", "site", "meeting_letter", "n_decisions"]
    )
    return df.astype(
        {
            "series_id": "object",
            "meeting_id": "object",
            "site": "object",
            "meeting_letter": "object",
            "n_decisions": "int64",
        }
    )


def decisions_by_meeting_position(
    ami_root: Path = AMI_DIR, series: Sequence[str] = ()
) -> pd.DataFrame:
    """Aggregate :func:`decision_counts` by meeting letter (a/b/c/d), across ``series``.

    Answers whether decisions cluster late in a series. Columns: ``meeting_letter`` (str),
    ``n_series`` (int, number of series contributing a meeting at this letter),
    ``total_decisions`` (int), ``mean_decisions`` (float).
    """
    counts_df = decision_counts(ami_root, series)
    if counts_df.empty:
        grouped = pd.DataFrame(
            {
                "meeting_letter": list(MEETING_LETTERS),
                "n_series": [0] * len(MEETING_LETTERS),
                "total_decisions": [0] * len(MEETING_LETTERS),
                "mean_decisions": [0.0] * len(MEETING_LETTERS),
            }
        )
    else:
        grouped = counts_df.groupby("meeting_letter", as_index=False).agg(
            n_series=("series_id", "nunique"),
            total_decisions=("n_decisions", "sum"),
            mean_decisions=("n_decisions", "mean"),
        )
        grouped = (
            grouped.set_index("meeting_letter")
            .reindex(list(MEETING_LETTERS))
            .fillna(0)
            .reset_index()
        )

    return grouped.astype(
        {
            "meeting_letter": "object",
            "n_series": "int64",
            "total_decisions": "int64",
            "mean_decisions": "float64",
        }
    )


def sentence_shape(ami_root: Path = AMI_DIR, series: Sequence[str] = ()) -> pd.DataFrame:
    """Per decision sentence: content-token and character counts.

    Uses :func:`afg.annotation.blocking.tokenize` for the token count -- the exact
    tokenisation the blocker scores on -- so this table explains the blocker's per-series
    variance (see ``afg.annotation.blocking`` module docstring) rather than measuring a
    different notion of "token". Columns: ``series_id`` (str), ``meeting_id`` (str),
    ``decision_id`` (str), ``n_tokens`` (int), ``n_chars`` (int).
    """
    decisions = _load_decisions(ami_root, series)
    rows = [
        {
            "series_id": d.series_id,
            "meeting_id": d.meeting_id,
            "decision_id": d.id,
            "n_tokens": len(tokenize(d.content)),
            "n_chars": len(d.content),
        }
        for d in decisions
    ]
    df = pd.DataFrame(
        rows, columns=["series_id", "meeting_id", "decision_id", "n_tokens", "n_chars"]
    )
    return df.astype(
        {
            "series_id": "object",
            "meeting_id": "object",
            "decision_id": "object",
            "n_tokens": "int64",
            "n_chars": "int64",
        }
    )


def non_decision_markers(ami_root: Path = AMI_DIR, series: Sequence[str] = ()) -> pd.DataFrame:
    """Frequency of :data:`NON_DECISION_MARKERS` phrases in decision sentences of ``series``.

    NOTE: this scans the raw abstractive DECISIONS sentences produced by
    :func:`~afg.annotation.blocking.decisions_from_abstractive`, which are all marked
    ``ACCEPTED`` -- P3's real object/content/status split
    (:func:`afg.annotation.goldset.build_gold_decisions`) is not implemented yet, so there
    is no separate pool of genuine non-decisions to scan instead. A sentence matching a
    marker is therefore only a HINT that it might read like an open proposal despite being
    counted as a decision by this provisional adapter -- its precision at flagging true
    false positives is UNMEASURED (thesis section 5.2). Columns: ``marker`` (str),
    ``n_matches`` (int), ``n_sentences`` (int, size of the scanned population),
    ``rate`` (float, ``n_matches / n_sentences``).
    """
    decisions = _load_decisions(ami_root, series)
    total = len(decisions)
    rows = []
    for marker in NON_DECISION_MARKERS:
        n_matches = sum(1 for d in decisions if marker in d.content.lower())
        rows.append(
            {
                "marker": marker,
                "n_matches": n_matches,
                "n_sentences": total,
                "rate": (n_matches / total) if total else 0.0,
            }
        )

    df = pd.DataFrame(rows, columns=["marker", "n_matches", "n_sentences", "rate"])
    return df.astype(
        {"marker": "object", "n_matches": "int64", "n_sentences": "int64", "rate": "float64"}
    )
