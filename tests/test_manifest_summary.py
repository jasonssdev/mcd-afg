"""Tests for the figures notebook 02 reads from the frozen-transcripts manifest."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from afg.corpus.render import (
    MANIFEST_CSV_NAME,
    load_manifest,
    manifest_prefix_summary,
    manifest_summary,
)
from afg.shared.paths import TABLES_DIR


def _manifest() -> pd.DataFrame:
    rows = [
        # meeting_id, series, dialogue_acts, turns, characters
        ("ES2002a", "ES2002", 10, 100, 1000),
        ("ES2002b", "ES2002", 12, 120, 1200),
        ("IS1004a", "IS1004", 5, 50, 500),
        ("EN2001a", "EN2001", 0, 30, 300),
        ("IB4001", "IB4001", 0, 20, 200),
        ("IB4003", "IB4003", 7, 40, 400),
    ]
    return pd.DataFrame(
        rows, columns=["meeting_id", "series", "dialogue_acts", "turns", "characters"]
    )


class TestManifestSummary:
    def test_totals_cover_every_meeting(self) -> None:
        summary = manifest_summary(_manifest(), ["ES2002", "IS1004"])
        assert (summary.n_meetings, summary.n_turns, summary.n_characters) == (6, 360, 3600)

    def test_meetings_without_dialogue_acts_and_their_prefixes(self) -> None:
        summary = manifest_summary(_manifest(), ["ES2002", "IS1004"])
        assert summary.n_without_acts == 2
        assert summary.prefixes_without_acts == ("EN", "IB")

    def test_non_scenario_meetings_that_do_have_acts_are_the_exception(self) -> None:
        summary = manifest_summary(_manifest(), ["ES2002", "IS1004"])
        assert summary.exceptions_with_acts == ("IB4003",)

    def test_study_series_meetings_are_counted_with_and_without_acts(self) -> None:
        summary = manifest_summary(_manifest(), ["ES2002", "IS1004"])
        assert (summary.n_study_meetings, summary.n_study_with_acts) == (3, 3)

    def test_a_study_meeting_without_acts_is_not_counted_as_covered(self) -> None:
        summary = manifest_summary(_manifest(), ["ES2002", "EN2001"])
        assert (summary.n_study_meetings, summary.n_study_with_acts) == (3, 2)


class TestManifestPrefixSummary:
    def test_one_row_per_prefix_with_meetings_acts_turns_and_characters(self) -> None:
        table = manifest_prefix_summary(_manifest())
        assert list(table.columns) == [
            "prefix",
            "meetings",
            "with_acts",
            "without_acts",
            "turns",
            "characters",
        ]
        row = table.set_index("prefix").loc["IB"]
        assert (row["meetings"], row["with_acts"], row["without_acts"]) == (2, 1, 1)
        assert (row["turns"], row["characters"]) == (60, 600)
        assert list(table["prefix"]) == ["EN", "ES", "IB", "IS"]


def test_load_manifest_adds_the_prefix_column(tmp_path: Path) -> None:
    path = tmp_path / MANIFEST_CSV_NAME
    _manifest().to_csv(path, index=False)
    loaded = load_manifest(path)
    assert list(loaded["prefix"]) == ["ES", "ES", "IS", "EN", "IB", "IB"]


@pytest.mark.skipif(
    not (TABLES_DIR / MANIFEST_CSV_NAME).exists(), reason="frozen manifest not generated"
)
def test_the_committed_manifest_matches_the_figures_notebook_02_reports() -> None:
    from afg.shared.config import load_corpus_config

    manifest = load_manifest()
    summary = manifest_summary(manifest, load_corpus_config()["oe1"]["series"])
    assert (summary.n_meetings, summary.n_without_acts) == (171, 32)
    assert (summary.n_study_meetings, summary.n_study_with_acts) == (56, 56)
    assert summary.prefixes_without_acts == ("EN", "IB", "IN")
    assert summary.exceptions_with_acts == ("IB4003",)
