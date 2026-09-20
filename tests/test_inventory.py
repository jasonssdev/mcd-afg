"""Tests for paso-cero corpus inventory (thesis section 5.0).

Two kinds of coverage live here:

- Corpus-absence detection, which needs no real download and always runs: this module
  must tell the difference between "no download happened" and "a real download exists",
  rather than silently reporting all-zero counts for a merely-scaffolded directory.
- Regression tests pinned to the ground-truth counts measured by hand against the real
  AMI download at ``data/raw/ami/`` (thesis section 5.0 "paso cero" pass, 2026-09-20).
  These are skipped when the corpus is absent, so the suite still passes on a fresh
  clone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.corpus.inventory import CorpusNotDownloadedError, build_inventory
from afg.shared.paths import AMI_DIR

# Ground truth measured by hand against data/raw/ami/ (2026-09-20). Each tuple is
# (abstractive_decision_sentences, dds_segment_count, external_flag_count,
# recap_flag_count) for that meeting. Do not derive these numbers from the code under
# test -- they are the independent check.
EXPECTED_COUNTS: dict[str, tuple[int, int, int, int]] = {
    "ES2015a": (5, 5, 5, 0),
    "ES2015b": (9, 11, 3, 0),
    "ES2015c": (8, 13, 0, 5),
    "ES2015d": (7, 5, 0, 0),
    "ES2016a": (2, 3, 1, 0),
    "ES2016b": (12, 10, 3, 0),
    "ES2016c": (3, 5, 0, 1),
    "ES2016d": (7, 7, 0, 0),
    "IS1004a": (4, 2, 2, 0),
    "IS1004b": (6, 7, 2, 0),
    "IS1004c": (2, 6, 0, 1),
    "IS1004d": (12, 12, 0, 0),
    "IS1006a": (6, 7, 2, 0),
    "IS1006b": (3, 5, 2, 0),
    "IS1006c": (6, 7, 0, 0),
    "IS1006d": (2, 3, 0, 0),
    "IS1008a": (2, 2, 0, 0),
    "IS1008b": (2, 5, 0, 0),
    "IS1008c": (4, 4, 0, 0),
    "IS1008d": (5, 6, 0, 0),
    "TS3005a": (1, 1, 1, 0),
    "TS3005b": (15, 13, 1, 2),
    "TS3005c": (7, 8, 0, 0),
    "TS3005d": (6, 10, 0, 2),
}

TOTAL_ABSTRACTIVE_DECISIONS = 136
TOTAL_DDS_SEGMENTS = 157
TOTAL_EXTERNAL_FLAGS = 22
TOTAL_RECAP_FLAGS = 11
DDS_MEETING_COUNT = 47
CANDIDATE_CROSS_MEETING_LINKS = 22

_corpus_present = AMI_DIR.exists() and any(
    p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".") for p in AMI_DIR.rglob("*")
)

requires_corpus = pytest.mark.skipif(
    not _corpus_present, reason="AMI corpus not downloaded at data/raw/ami/"
)


class TestBuildInventoryCorpusAbsent:
    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        with pytest.raises(CorpusNotDownloadedError) as exc_info:
            build_inventory(missing)
        assert "afg corpus download" in str(exc_info.value)

    def test_directory_with_only_gitkeep_raises(self, tmp_path: Path) -> None:
        ami_root = tmp_path / "ami"
        ami_root.mkdir()
        (ami_root / ".gitkeep").touch()

        with pytest.raises(CorpusNotDownloadedError):
            build_inventory(ami_root)

    def test_directory_with_a_real_file_does_not_raise(self, tmp_path: Path) -> None:
        ami_root = tmp_path / "ami"
        ami_root.mkdir()
        (ami_root / ".gitkeep").touch()
        (ami_root / "something.xml").write_text("<root/>")

        # No corpus config assumptions are exercised here beyond "does not raise
        # CorpusNotDownloadedError" -- the resulting inventory will report zero decisions
        # for every series, which is correct: this is not real AMI data.
        inventory = build_inventory(ami_root)
        assert inventory.ami_root == ami_root


@requires_corpus
class TestBuildInventoryRealCorpus:
    """Regression tests pinned to the ground-truth table measured 2026-09-20."""

    @staticmethod
    @pytest.fixture(scope="class")
    def inventory():  # type: ignore[no-untyped-def]
        return build_inventory(AMI_DIR)

    def test_per_meeting_counts_match_ground_truth(self, inventory) -> None:  # type: ignore[no-untyped-def]
        observed = {
            meeting.meeting_id: (
                meeting.abstractive_decision_sentences,
                meeting.dds_segment_count,
                meeting.external_flag_count,
                meeting.recap_flag_count,
            )
            for series in inventory.series
            for meeting in series.meetings
        }
        assert observed == EXPECTED_COUNTS

    def test_totals_match_ground_truth(self, inventory) -> None:  # type: ignore[no-untyped-def]
        assert inventory.total_abstractive_decisions == TOTAL_ABSTRACTIVE_DECISIONS
        assert inventory.total_dds_segments == TOTAL_DDS_SEGMENTS
        assert inventory.total_external_flags == TOTAL_EXTERNAL_FLAGS
        assert inventory.total_recap_flags == TOTAL_RECAP_FLAGS

    def test_dds_meeting_count_is_47(self, inventory) -> None:  # type: ignore[no-untyped-def]
        assert inventory.dds_meeting_count == DDS_MEETING_COUNT

    def test_all_six_series_complete(self, inventory) -> None:  # type: ignore[no-untyped-def]
        assert len(inventory.series) == 6
        assert inventory.all_series_complete
        assert inventory.all_series_complete is True

    def test_candidate_cross_meeting_links(self, inventory) -> None:  # type: ignore[no-untyped-def]
        assert inventory.candidate_cross_meeting_links == CANDIDATE_CROSS_MEETING_LINKS
