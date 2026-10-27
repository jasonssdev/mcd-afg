"""Numbers the modeling notebook (``19``) needs from the EDA levels.

Two computations, both pure functions over the tables of :mod:`afg.eda.tables`:

- :func:`partition_volumes` -- how much data each partition of ADR 0005 holds (series,
  meetings, decision sentences, candidate pairs and, optionally, questions), as counts and as
  percentages of the OE1 total. Content never leaves this module (ADR 0005): only counts.
- :func:`context_constraints` -- the properties of the data that bound the modeling choices
  (transcript length against the context window, how rare decisions are among turns, how many
  decisions carry no evidence).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from afg.eda.tables import TOKENS_PER_WORD

PARTITIONS: tuple[str, ...] = ("development", "evaluation")
"""The partitions of ADR 0005 that hold annotated OE1 series, in display order."""

_COUNT_COLUMNS: dict[str, str] = {
    "meetings": "n_meetings",
    "decisions": "n_decisions",
    "pairs": "n_cross_meeting_pairs",
    "candidates": "n_candidates",
}


def partition_volumes(
    series: pd.DataFrame,
    *,
    questions: Mapping[str, int] | None = None,
    reserve_series: Sequence[str] = (),
) -> pd.DataFrame:
    """Volumes per partition, with each partition's share of the OE1 total.

    Args:
        series: the series level of :class:`~afg.eda.tables.EdaTables` (columns ``series_id``,
            ``split``, ``n_meetings``, ``n_decisions``, ``n_cross_meeting_pairs``,
            ``n_candidates``).
        questions: questions per series id (for example the calibration questions of the
            development series). When given, a ``questions`` column is added; series that are
            absent count as zero. When omitted the column does not exist.
        reserve_series: series reserved and untouched (ADR 0005). They get a ``reserve`` row
            that counts series only: their volumes have not been measured and stay NaN. The
            row is outside the ``total``.

    Returns:
        A frame indexed by ``development``, ``evaluation``, ``total`` (and ``reserve``) with
        the columns ``series``, ``meetings``, ``decisions``, ``pairs``, ``candidates``
        (and ``questions``) plus a ``pct_<column>`` for each.

    Raises:
        ValueError: if a series is in no partition (``unassigned``), because the total would
            then silently disagree with the partitions.
    """
    unknown = sorted(set(series["split"]) - set(PARTITIONS))
    if unknown:
        raise ValueError(f"Series outside the partitions {PARTITIONS}: {unknown}.")

    rows: dict[str, dict[str, float]] = {}
    for partition in PARTITIONS:
        part = series[series["split"] == partition]
        row: dict[str, float] = {"series": float(len(part))}
        for name, column in _COUNT_COLUMNS.items():
            row[name] = float(part[column].sum())
        if questions is not None:
            row["questions"] = float(sum(questions.get(s, 0) for s in part["series_id"]))
        rows[partition] = row

    columns = list(rows["development"])
    rows["total"] = {c: sum(rows[p][c] for p in PARTITIONS) for c in columns}
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=columns)
    for column in columns:
        total = frame.loc["total", column]
        frame[f"pct_{column}"] = frame[column] / total * 100 if total else float("nan")

    if reserve_series:
        reserve = pd.Series(float("nan"), index=frame.columns, name="reserve")
        reserve["series"] = float(len(reserve_series))
        frame = pd.concat([frame, reserve.to_frame().T])
    return frame.astype({c: "float64" for c in frame.columns})


@dataclass(frozen=True, slots=True)
class ContextConstraints:
    """What the data impose on the modeling choices (all derived from the EDA levels)."""

    n_meetings: int
    n_fit_context: int
    """Meetings whose estimated tokens fit the context window."""
    n_over_80_percent: int
    max_context_ratio: float
    context_tokens: int
    window_words: float
    """The window expressed in words, with the EDA's tokens-per-word estimate."""
    n_series: int
    n_series_fit: int
    series_words_min: int
    series_words_max: int
    series_window_ratio_min: float
    series_window_ratio_max: float
    n_decisions: int
    n_without_evidence: int
    decisions_per_1000_turns: float
    median_decisions_per_meeting: float
    median_decisions_by_position: dict[str, float]
    """Median decisions per meeting for each position in the series (``a`` to ``d``)."""
    meeting_chars_median: float


def context_constraints(
    meeting: pd.DataFrame, decision: pd.DataFrame, *, context_tokens: int
) -> ContextConstraints:
    """Summarise transcript length against the window and the rarity of decisions.

    Args:
        meeting: the meeting level (``series_id``, ``position``, ``n_turns``, ``n_words``,
            ``n_characters``, ``n_decisions``, ``context_ratio``, ``fits_context``).
        decision: the decision level (``anchored``).
        context_tokens: the context window of the generative model, in tokens.
    """
    window_words = context_tokens / TOKENS_PER_WORD
    series_words = meeting.groupby("series_id")["n_words"].sum()
    total_turns = float(meeting["n_turns"].sum())
    return ContextConstraints(
        n_meetings=len(meeting),
        n_fit_context=int(meeting["fits_context"].sum()),
        n_over_80_percent=int((meeting["context_ratio"] > 0.8).sum()),
        max_context_ratio=float(meeting["context_ratio"].max()),
        context_tokens=context_tokens,
        window_words=window_words,
        n_series=len(series_words),
        n_series_fit=int((series_words <= window_words).sum()),
        series_words_min=int(series_words.min()),
        series_words_max=int(series_words.max()),
        series_window_ratio_min=float(series_words.min() / window_words),
        series_window_ratio_max=float(series_words.max() / window_words),
        n_decisions=len(decision),
        n_without_evidence=int((~decision["anchored"]).sum()),
        decisions_per_1000_turns=float(meeting["n_decisions"].sum() / total_turns * 1000),
        median_decisions_per_meeting=float(meeting["n_decisions"].median()),
        median_decisions_by_position={
            str(p): float(v) for p, v in meeting.groupby("position")["n_decisions"].median().items()
        },
        meeting_chars_median=float(meeting["n_characters"].median()),
    )
