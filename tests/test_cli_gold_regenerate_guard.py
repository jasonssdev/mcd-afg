"""Tests for the ``afg gold build`` / ``afg gold candidates`` regeneration guard (issue #8).

Both commands rebuild their base file (``<series>.decisions.csv`` /
``<series>.candidates.csv``) from scratch from the AMI abstractive summary. Once an
annotator has copied that base into their own ``<series>.<kind>.<initials>.csv`` and split
a ``compuesta`` row or filled in machine-compared columns, regenerating the base silently
destroys that work and desyncs every annotator's file against ``afg gold validate``.

Every test here builds synthetic fixtures under ``tmp_path`` and stubs the AMI-reading
functions (``build_gold_decisions``, ``decisions_from_abstractive``); nothing in this file
depends on the real AMI corpus.
"""

from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.annotation.goldset import GoldDecisionRow
from afg.annotation.workspace import WorkspacePaths
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan

_DECISION_COLUMNS = (
    "decision_id",
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_da_count",
    "evidence_text",
    "status",
    "decision_object",
    "decision_content",
    "annotator",
    "notes",
    "machine_flags",
)

_CANDIDATE_COLUMNS = (
    "pair_id",
    "earlier_decision_id",
    "later_decision_id",
    "earlier_sentence_id",
    "later_sentence_id",
    "earlier_text",
    "later_text",
    "blocker_score",
    "relation",
    "direction_ok",
    "confidence",
    "annotator",
    "notes",
)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _untouched_decision_row(decision_id: str, meeting_id: str) -> dict[str, str]:
    return {
        "decision_id": decision_id,
        "meeting_id": meeting_id,
        "source_sentence_id": f"{meeting_id}.elana.s.1",
        "sentence_text": f"They decide about {decision_id}.",
        "evidence_da_count": "1",
        "evidence_text": f"A: we decide {decision_id}",
        "machine_flags": "",
        "status": "",
        "decision_object": "",
        "decision_content": "",
        "annotator": "gv",
        "notes": "",
    }


def _untouched_candidate_row(pair_id: str, earlier: str, later: str) -> dict[str, str]:
    return {
        "pair_id": pair_id,
        "earlier_decision_id": earlier,
        "later_decision_id": later,
        "earlier_sentence_id": f"{earlier}.elana.s.1",
        "later_sentence_id": f"{later}.elana.s.2",
        "earlier_text": f"text of {earlier}",
        "later_text": f"text of {later}",
        "blocker_score": "0.4",
        "relation": "",
        "direction_ok": "",
        "confidence": "",
        "annotator": "gv",
        "notes": "",
    }


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkspacePaths:
    decisions_dir = tmp_path / "decisions"
    relations_dir = tmp_path / "relations"
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", decisions_dir)
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", relations_dir)
    return WorkspacePaths(decisions_dir=decisions_dir, relations_dir=relations_dir)


@pytest.fixture(autouse=True)
def _fake_ami_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`ami_root.exists()` must be true; nothing under it is ever actually read."""
    ami_root = tmp_path / "ami"
    ami_root.mkdir()
    monkeypatch.setattr(afg_cli, "get_settings", lambda: SimpleNamespace(ami_root=ami_root))


@pytest.fixture
def stub_build_gold_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        GoldDecisionRow(
            decision_id="ES2015a.d01",
            meeting_id="ES2015a",
            source_sentence_id="ES2015a.elana.s.1",
            sentence_text="They decide about the budget.",
            evidence_da_count=1,
            evidence_text="A: we decide the budget",
            machine_flags="",
        )
    ]
    monkeypatch.setattr(
        "afg.annotation.goldset.build_gold_decisions", lambda ami_root, series: rows
    )


@pytest.fixture
def stub_decisions_from_abstractive(monkeypatch: pytest.MonkeyPatch) -> None:
    decisions = [
        Decision(
            id="ES2015a.d01",
            series_id="ES2015",
            meeting_id="ES2015a",
            decision_object="",
            content="They decide about the budget.",
            status=DecisionStatus.ACCEPTED,
            evidence=EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.elana.s.1",)),
            annotator=None,
        )
    ]
    monkeypatch.setattr(afg_cli, "decisions_from_abstractive", lambda ami_root, series: decisions)


runner = CliRunner()


# --- afg gold build -----------------------------------------------------------------------


class TestGoldBuildRegenerationGuard:
    def test_refuses_when_a_derived_decisions_file_has_annotation(
        self, paths: WorkspacePaths
    ) -> None:
        target = paths.decisions_dir / "ES2015.decisions.gv.csv"
        row = _untouched_decision_row("ES2015a.d01", "ES2015a")
        row["status"] = "decision"
        _write_csv(target, _DECISION_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "build", "--series", "ES2015"])

        assert result.exit_code == 1, result.output
        assert "ES2015" in result.output
        assert "ES2015.decisions.gv.csv" in result.output
        assert "--force" in result.output

    def test_refuses_when_a_derived_candidates_file_has_annotation(
        self, paths: WorkspacePaths
    ) -> None:
        target = paths.relations_dir / "ES2015.candidates.gv.csv"
        row = _untouched_candidate_row("ES2015.p001", "ES2015a.d01", "ES2015a.d02")
        row["relation"] = "refina"
        _write_csv(target, _CANDIDATE_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "build", "--series", "ES2015"])

        assert result.exit_code == 1, result.output
        assert "ES2015.candidates.gv.csv" in result.output

    def test_regenerates_when_derived_files_are_untouched(
        self,
        paths: WorkspacePaths,
        stub_build_gold_decisions: None,
    ) -> None:
        """The normal state right after `prepare`: derived files exist but hold no work."""
        _write_csv(
            paths.decisions_dir / "ES2015.decisions.gv.csv",
            _DECISION_COLUMNS,
            [_untouched_decision_row("ES2015a.d01", "ES2015a")],
        )

        result = runner.invoke(afg_cli.app, ["gold", "build", "--series", "ES2015"])

        assert result.exit_code == 0, result.output
        assert (paths.decisions_dir / "ES2015.decisions.csv").exists()

    def test_regenerates_when_no_derived_file_exists_at_all(
        self,
        paths: WorkspacePaths,
        stub_build_gold_decisions: None,
    ) -> None:
        result = runner.invoke(afg_cli.app, ["gold", "build", "--series", "ES2015"])

        assert result.exit_code == 0, result.output
        assert (paths.decisions_dir / "ES2015.decisions.csv").exists()

    def test_force_regenerates_and_warns(
        self,
        paths: WorkspacePaths,
        stub_build_gold_decisions: None,
    ) -> None:
        target = paths.decisions_dir / "ES2015.decisions.gv.csv"
        row = _untouched_decision_row("ES2015a.d01", "ES2015a")
        row["status"] = "decision"
        _write_csv(target, _DECISION_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "build", "--series", "ES2015", "--force"])

        assert result.exit_code == 0, result.output
        assert "ES2015.decisions.gv.csv" in result.output
        assert (paths.decisions_dir / "ES2015.decisions.csv").exists()


# --- afg gold candidates -------------------------------------------------------------------


class TestGoldCandidatesRegenerationGuard:
    def test_refuses_when_a_derived_decisions_file_has_annotation(
        self, paths: WorkspacePaths
    ) -> None:
        target = paths.decisions_dir / "ES2015.decisions.gv.csv"
        row = _untouched_decision_row("ES2015a.d01", "ES2015a")
        row["decision_content"] = "el presupuesto"
        _write_csv(target, _DECISION_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "candidates", "--series", "ES2015"])

        assert result.exit_code == 1, result.output
        assert "ES2015" in result.output
        assert "ES2015.decisions.gv.csv" in result.output
        assert "--force" in result.output

    def test_refuses_when_a_derived_candidates_file_has_annotation(
        self, paths: WorkspacePaths
    ) -> None:
        target = paths.relations_dir / "ES2015.candidates.gv.csv"
        row = _untouched_candidate_row("ES2015.p001", "ES2015a.d01", "ES2015a.d02")
        row["confidence"] = "alta"
        _write_csv(target, _CANDIDATE_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "candidates", "--series", "ES2015"])

        assert result.exit_code == 1, result.output
        assert "ES2015.candidates.gv.csv" in result.output

    def test_regenerates_when_derived_files_are_untouched(
        self,
        paths: WorkspacePaths,
        stub_decisions_from_abstractive: None,
    ) -> None:
        """The normal state right after `prepare`: derived files exist but hold no work."""
        _write_csv(
            paths.relations_dir / "ES2015.candidates.gv.csv",
            _CANDIDATE_COLUMNS,
            [_untouched_candidate_row("ES2015.p001", "ES2015a.d01", "ES2015a.d02")],
        )

        result = runner.invoke(afg_cli.app, ["gold", "candidates", "--series", "ES2015"])

        assert result.exit_code == 0, result.output
        assert (paths.relations_dir / "ES2015.candidates.csv").exists()

    def test_regenerates_when_no_derived_file_exists_at_all(
        self,
        paths: WorkspacePaths,
        stub_decisions_from_abstractive: None,
    ) -> None:
        result = runner.invoke(afg_cli.app, ["gold", "candidates", "--series", "ES2015"])

        assert result.exit_code == 0, result.output
        assert (paths.relations_dir / "ES2015.candidates.csv").exists()

    def test_force_regenerates_and_warns(
        self,
        paths: WorkspacePaths,
        stub_decisions_from_abstractive: None,
    ) -> None:
        target = paths.relations_dir / "ES2015.candidates.gv.csv"
        row = _untouched_candidate_row("ES2015.p001", "ES2015a.d01", "ES2015a.d02")
        row["relation"] = "refina"
        _write_csv(target, _CANDIDATE_COLUMNS, [row])

        result = runner.invoke(afg_cli.app, ["gold", "candidates", "--series", "ES2015", "--force"])

        assert result.exit_code == 0, result.output
        assert "ES2015.candidates.gv.csv" in result.output
        assert (paths.relations_dir / "ES2015.candidates.csv").exists()
