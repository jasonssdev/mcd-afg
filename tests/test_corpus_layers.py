"""Tests for the layer-coverage helpers in ``afg.corpus.layers``."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.corpus.layers import disfluency_coverage
from afg.shared.paths import AMI_DIR

_corpus_present = (AMI_DIR / "disfluency").exists()


def _touch(root: Path, *names: str) -> None:
    folder = root / "disfluency"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text("<xml/>", encoding="utf-8")


class TestDisfluencyCoverage:
    def test_a_series_is_covered_when_any_of_its_meetings_has_the_layer(
        self, tmp_path: Path
    ) -> None:
        _touch(
            tmp_path,
            "ES2002a.A.disfluency.xml",
            "ES2002b.B.disfluency.xml",
            "IS1003a.A.disfluency.xml",
        )
        coverage = disfluency_coverage(tmp_path, ["ES2002", "IS1003", "TS3005"])
        assert coverage == {"ES2002": True, "IS1003": True, "TS3005": False}

    def test_the_result_follows_the_order_of_the_requested_series(self, tmp_path: Path) -> None:
        _touch(tmp_path, "ES2002a.A.disfluency.xml")
        assert list(disfluency_coverage(tmp_path, ["TS3005", "ES2002"])) == ["TS3005", "ES2002"]

    def test_files_of_other_series_are_ignored(self, tmp_path: Path) -> None:
        _touch(tmp_path, "ES2008a.A.disfluency.xml")
        assert disfluency_coverage(tmp_path, ["ES2002"]) == {"ES2002": False}

    def test_a_missing_corpus_covers_nothing(self, tmp_path: Path) -> None:
        assert disfluency_coverage(tmp_path / "absent", ["ES2002"]) == {"ES2002": False}

    @pytest.mark.skipif(not _corpus_present, reason="AMI corpus not downloaded")
    def test_five_of_the_fourteen_study_series_are_covered(self) -> None:
        from afg.shared.config import load_corpus_config

        series = load_corpus_config()["oe1"]["series"]
        covered = [s for s, ok in disfluency_coverage(AMI_DIR, series).items() if ok]
        assert covered == ["ES2002", "ES2008", "IS1003", "IS1009", "TS3005"]
