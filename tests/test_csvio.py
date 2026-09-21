"""Tests for the shared CSV writer helper (``afg.shared.csvio``).

``csv.writer`` defaults to CRLF, which git normalizes to LF on commit -- so a CSV
written by our code never matches the one checked out, and the next regeneration shows
the whole file as changed. This module guards the fix at two levels:

- ``TestOpenCsvWriter`` exercises the helper directly.
- ``TestNoWriterEmitsCrlf`` is a regression test over every *public* writer function in
  the package that produces a tracked CSV, parametrized rather than duplicated seven
  times: each one writes a small, synthetic file through its real public API and the
  resulting bytes are asserted to contain no CRLF.
- ``TestGitattributes`` guards the second half of the fix (line-ending normalization at
  commit time) against someone deleting or narrowing the rule.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from afg.annotation.agreement import SeriesAgreementResult, write_agreement_csv
from afg.annotation.blocking import CandidatePair, write_candidate_pairs_csv
from afg.annotation.goldset import GoldDecisionRow, write_gold_decisions_csv
from afg.bibliography.audit import BibliographyAudit
from afg.bibliography.audit import write_csv as write_bibliography_csv
from afg.corpus.inventory import CorpusInventory, MeetingInventory, SeriesInventory
from afg.corpus.inventory import write_csv as write_inventory_csv
from afg.corpus.participants import write_csv as write_participants_csv
from afg.corpus.render import ManifestRow, write_manifest_csv
from afg.domain.participant import Participant, SpeakerRole
from afg.shared.csvio import open_csv_writer
from afg.shared.paths import PROJECT_ROOT


class TestOpenCsvWriter:
    def test_writes_lf_not_crlf(self, tmp_path: Path) -> None:
        out_path = tmp_path / "sample.csv"

        with open_csv_writer(out_path) as writer:
            writer.writerow(["a", "b"])
            writer.writerow(["1", "2"])

        raw = out_path.read_bytes()
        assert b"\r\n" not in raw
        assert raw == b"a,b\n1,2\n"

    def test_sets_newline_empty_so_csv_module_controls_line_endings(self, tmp_path: Path) -> None:
        # A file opened without newline="" would let the platform's text-mode newline
        # translation double up the "\n" the writer already emits, corrupting the file.
        out_path = tmp_path / "sample.csv"

        with open_csv_writer(out_path) as writer:
            writer.writerow(["only", "row"])

        assert out_path.read_bytes().count(b"\n") == 1

    def test_encoding_is_passed_through(self, tmp_path: Path) -> None:
        out_path = tmp_path / "sample.csv"

        with open_csv_writer(out_path, encoding="utf-8") as writer:
            writer.writerow(["café"])

        assert out_path.read_text(encoding="utf-8") == "café\n"


def _write_bibliography_csv(out_dir: Path) -> Path:
    audit = BibliographyAudit(
        total_entries=1,
        entries_per_section={"introduction": 1},
        sections_with_no_entries=(),
        preprint_keys=(),
        missing_doi_keys=(),
        duplicate_doi_groups=(),
    )
    return write_bibliography_csv(audit, out_dir=out_dir)


def _write_inventory_csv(out_dir: Path) -> Path:
    meeting = MeetingInventory(meeting_id="ES2015a", present=True)
    series = SeriesInventory(series_id="ES2015", meetings=(meeting,))
    inventory = CorpusInventory(ami_root=Path("."), series=(series,), dds_meeting_count=0)
    return write_inventory_csv(inventory, out_dir=out_dir)


def _write_participants_csv(out_dir: Path) -> Path:
    participants = [Participant(id="FEE057", role=SpeakerRole.PROJECT_MANAGER)]
    return write_participants_csv(participants, out_dir=out_dir)


def _write_agreement_csv(out_dir: Path) -> Path:
    result = SeriesAgreementResult(
        series_id="IS1004",
        annotator_a="aa",
        annotator_b="bb",
        n_items=1,
        existence_kappa=1.0,
        existence_disagreements=(),
        n_type_items=1,
        type_kappa=1.0,
        type_disagreements=(),
        direction_kappa=1.0,
        direction_disagreements=(),
    )
    return write_agreement_csv(result, out_dir / "IS1004.agreement.csv")


def _write_blocking_csv(out_dir: Path) -> Path:
    pair = CandidatePair(
        pair_id="ES2015.p001",
        earlier_decision_id="ES2015a.d01",
        later_decision_id="ES2015b.d01",
        earlier_sentence_id="ES2015a.elana.s.1",
        later_sentence_id="ES2015b.elana.s.1",
        earlier_meeting_id="ES2015a",
        later_meeting_id="ES2015b",
        earlier_text="use titanium",
        later_text="use titanium casing",
        blocker_score=0.5,
        blocker_version="1.1",
    )
    return write_candidate_pairs_csv([pair], out_dir / "ES2015.pairs.csv")


def _write_goldset_csv(out_dir: Path) -> Path:
    row = GoldDecisionRow(
        decision_id="ES2015a.d01",
        meeting_id="ES2015a",
        source_sentence_id="ES2015a.elana.s.1",
        sentence_text="They decide to use titanium.",
        evidence_da_count=1,
        evidence_text="A: We use titanium .",
        machine_flags="",
    )
    return write_gold_decisions_csv([row], out_dir / "ES2015.decisions.csv")


def _write_render_manifest_csv(out_dir: Path) -> Path:
    row = ManifestRow(
        meeting_id="ES2015a",
        series="ES2015",
        letter="a",
        speakers="PM,ME",
        turns=4,
        dialogue_acts=8,
        characters=120,
        sha256_md="deadbeef",
        sha256_jsonl="beadfeed",
        renderer_revision="test-revision",
        source_archive="ami-manual",
    )
    return write_manifest_csv([row], out_dir=out_dir)


_WRITERS: list[tuple[str, Callable[[Path], Path]]] = [
    ("bibliography.audit.write_csv", _write_bibliography_csv),
    ("corpus.inventory.write_csv", _write_inventory_csv),
    ("corpus.participants.write_csv", _write_participants_csv),
    ("annotation.agreement.write_agreement_csv", _write_agreement_csv),
    ("annotation.blocking.write_candidate_pairs_csv", _write_blocking_csv),
    ("annotation.goldset.write_gold_decisions_csv", _write_goldset_csv),
    ("corpus.render.write_manifest_csv", _write_render_manifest_csv),
]


class TestNoWriterEmitsCrlf:
    @pytest.mark.parametrize("name, write", _WRITERS, ids=[name for name, _ in _WRITERS])
    def test_writer_output_has_no_crlf(
        self, name: str, write: Callable[[Path], Path], tmp_path: Path
    ) -> None:
        out_path = write(tmp_path)

        raw = out_path.read_bytes()
        assert b"\r\n" not in raw, f"{name} wrote CRLF line endings"
        assert b"\n" in raw, f"{name} wrote no rows at all"


class TestGitattributes:
    def test_gitattributes_exists_and_normalizes_csv_to_lf(self) -> None:
        gitattributes_path = PROJECT_ROOT / ".gitattributes"

        assert gitattributes_path.exists(), ".gitattributes is missing at the repo root"
        contents = gitattributes_path.read_text(encoding="utf-8")
        assert "*.csv text eol=lf" in contents
