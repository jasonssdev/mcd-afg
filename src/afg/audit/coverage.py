"""Corpus-wide annotation-layer coverage and OE1 series eligibility (thesis section 5.1
data audit).

Reuses ``afg.corpus.layers`` discovery (never re-globs the corpus) and
``afg.audit.decisions.decision_counts`` (never re-parses ``abssumm.xml``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from afg.audit.decisions import MEETING_LETTERS, decision_counts
from afg.corpus.layers import AnnotationLayer, discover_layer_files, discover_meetings_with_layer
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR

_LETTER_SET = set(MEETING_LETTERS)


def _oe1_series() -> list[str]:
    series: list[str] = load_corpus_config()["oe1"]["series"]
    return series


def layer_coverage(ami_root: Path = AMI_DIR) -> pd.DataFrame:
    """Per annotation layer: file count, distinct meetings covered, and how many of the
    14 OE1 series (``config/corpus.toml`` ``[oe1].series``) have all four meetings present
    for that layer.

    Columns: ``layer`` (str), ``file_count`` (int), ``meetings_covered`` (int),
    ``oe1_series_complete_count`` (int, out of 14), ``oe1_series_incomplete`` (str,
    comma-joined ids of OE1 series missing at least one meeting for this layer -- empty
    string when none are missing).
    """
    oe1_series = _oe1_series()
    rows = []
    for layer in AnnotationLayer:
        files = discover_layer_files(ami_root, layer)
        meetings = discover_meetings_with_layer(ami_root, layer)

        complete: list[str] = []
        incomplete: list[str] = []
        for series_id in oe1_series:
            letters_present = {m[-1] for m in meetings if m[:-1] == series_id}
            (complete if letters_present == _LETTER_SET else incomplete).append(series_id)

        rows.append(
            {
                "layer": layer.value,
                "file_count": len(files),
                "meetings_covered": len(meetings),
                "oe1_series_complete_count": len(complete),
                "oe1_series_incomplete": ",".join(sorted(incomplete)),
            }
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "layer",
            "file_count",
            "meetings_covered",
            "oe1_series_complete_count",
            "oe1_series_incomplete",
        ],
    )
    return df.astype(
        {
            "layer": "object",
            "file_count": "int64",
            "meetings_covered": "int64",
            "oe1_series_complete_count": "int64",
            "oe1_series_incomplete": "object",
        }
    )


def series_eligibility(ami_root: Path = AMI_DIR) -> pd.DataFrame:
    """For every complete abstractive series (all 4 meetings have an ``abssumm.xml``
    file) found in ``ami_root``: whether it has summlink on 4/4 meetings, whether it has
    the DDS layer on all 4 meetings, and its total decision-sentence count.

    This is the table that justified ADR 0004 (``docs/decisions/0004-adr-oe1-series-selection.md``,
    not read or written by this module). Expected on the real corpus: 33 complete series,
    32 with summlink on 4/4 (TS3012 has only 3), 6 with DDS on all 4. Columns: ``series_id``
    (str), ``summlink_on_4_of_4`` (bool), ``has_dds`` (bool), ``decision_count`` (int).
    """
    abssumm_meetings = discover_meetings_with_layer(ami_root, AnnotationLayer.ABSTRACTIVE_SUMMARY)
    summlink_meetings = discover_meetings_with_layer(
        ami_root, AnnotationLayer.EXTRACTIVE_SUMMARY_LINKS
    )
    dds_meetings = discover_meetings_with_layer(
        ami_root, AnnotationLayer.DECISION_DISCUSSION_SEGMENTATION
    )

    letters_by_series: dict[str, set[str]] = {}
    for meeting_id in abssumm_meetings:
        letters_by_series.setdefault(meeting_id[:-1], set()).add(meeting_id[-1])
    complete_series = sorted(
        series_id for series_id, letters in letters_by_series.items() if letters == _LETTER_SET
    )

    rows = []
    for series_id in complete_series:
        summlink_letters = {m[-1] for m in summlink_meetings if m[:-1] == series_id}
        dds_letters = {m[-1] for m in dds_meetings if m[:-1] == series_id}
        counts = decision_counts(ami_root, [series_id])
        rows.append(
            {
                "series_id": series_id,
                "summlink_on_4_of_4": summlink_letters == _LETTER_SET,
                "has_dds": dds_letters == _LETTER_SET,
                "decision_count": int(counts["n_decisions"].sum()),
            }
        )

    df = pd.DataFrame(
        rows, columns=["series_id", "summlink_on_4_of_4", "has_dds", "decision_count"]
    )
    return df.astype(
        {
            "series_id": "object",
            "summlink_on_4_of_4": "bool",
            "has_dds": "bool",
            "decision_count": "int64",
        }
    )
