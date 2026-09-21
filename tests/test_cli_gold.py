"""Tests for the ``afg gold validate`` / ``afg gold status`` CLI commands.

Every test here builds its own synthetic annotation plan and CSV fixtures under
``tmp_path``; nothing reads ``config/annotation.toml`` or the AMI corpus, so the whole
file runs on a fresh clone.

Covers two usability defects found while testing ``afg gold validate --annotator
<iniciales>`` without ``--series``:

1. ``validate`` must report an unprepared series as "sin preparar", not as an error --
   ``status`` already makes this distinction (``SeriesProgress.not_started``); ``validate``
   did not.
2. ``status`` had no ``--annotator`` filter, so a single annotator always saw the whole
   team's rows.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.annotation.workspace import (
    AnnotationPlan,
    WorkspacePaths,
    load_annotation_plan,
    prepare_annotator_workspace,
)

# --- synthetic fixtures ------------------------------------------------------------------

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

# gv: ES1 (phase 1, shared with gm) + ES3 (phase 3, solo).
# gm: ES1 (phase 1, shared with gv) + ES2 (phase 3, solo, and owns the recall sample).
_PLAN_CONFIG: dict[str, object] = {
    "annotation": {
        "adjudicator": "jss",
        "phase1_series": ["ES1"],
        "phase2_series": [],
        "recall_sample": {"owner": "gm", "series": "ES2", "n": 1, "seed": 1},
        "question_bank": {
            "author": "gm",
            "validator": "gv",
            "total_questions": 4,
            "questions_per_stratum": 2,
        },
        "annotators": [
            {
                "initials": "gv",
                "name": "Germán Vega",
                "role": "annotator",
                "phase3_series": ["ES3"],
            },
            {
                "initials": "gm",
                "name": "Gustavo Martínez",
                "role": "annotator",
                "phase3_series": ["ES2"],
            },
            {
                "initials": "jss",
                "name": "Jason Sepúlveda",
                "role": "maintainer",
                "phase3_series": [],
            },
        ],
    }
}


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _decision_row(decision_id: str, meeting_id: str) -> dict[str, str]:
    return {
        "decision_id": decision_id,
        "meeting_id": meeting_id,
        "source_sentence_id": f"{meeting_id}.elana.s.1",
        "sentence_text": f"They decide about {decision_id}.",
        "evidence_da_count": "2",
        "evidence_text": f"A: we decide {decision_id}",
        "machine_flags": "",
    }


def _candidate_row(pair_id: str, earlier: str, later: str) -> dict[str, str]:
    return {
        "pair_id": pair_id,
        "earlier_decision_id": earlier,
        "later_decision_id": later,
        "earlier_sentence_id": f"{earlier}.elana.s.1",
        "later_sentence_id": f"{later}.elana.s.2",
        "earlier_text": f"text of {earlier}",
        "later_text": f"text of {later}",
        "blocker_score": "0.4",
    }


@pytest.fixture
def plan() -> AnnotationPlan:
    return load_annotation_plan(_PLAN_CONFIG)


@pytest.fixture(autouse=True)
def _synthetic_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``afg gold`` command reads the plan through ``load_annotation_config``."""
    monkeypatch.setattr("afg.annotation.workspace.load_annotation_config", lambda: _PLAN_CONFIG)


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkspacePaths:
    decisions_dir = tmp_path / "decisions"
    relations_dir = tmp_path / "relations"
    questions_dir = tmp_path / "questions"
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", decisions_dir)
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", relations_dir)
    monkeypatch.setattr(afg_cli, "QUESTIONS_DIR", questions_dir)
    return WorkspacePaths(
        decisions_dir=decisions_dir, relations_dir=relations_dir, questions_dir=questions_dir
    )


@pytest.fixture
def sources(paths: WorkspacePaths) -> WorkspacePaths:
    """The machine-generated base files every assigned series needs."""
    for series_id in ("ES1", "ES2", "ES3"):
        _write_csv(
            paths.decisions_dir / f"{series_id}.decisions.csv",
            _DECISION_COLUMNS,
            [_decision_row(f"{series_id}a.d01", f"{series_id}a")],
        )
        _write_csv(
            paths.relations_dir / f"{series_id}.candidates.csv",
            _CANDIDATE_COLUMNS,
            [_candidate_row(f"{series_id}.p001", f"{series_id}a.d01", f"{series_id}a.d01")],
        )
    _write_csv(
        paths.relations_dir / "ES2.recall-sample.csv",
        _CANDIDATE_COLUMNS,
        [_candidate_row("ES2.r001", "ES2a.d01", "ES2a.d01")],
    )
    return paths


def _corrupt_machine_column(path: Path, columns: tuple[str, ...], column: str) -> None:
    """Hand-edit a machine column so ``_check_machine_columns`` raises a real issue."""
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    rows[0][column] = "tampered"
    _write_csv(path, columns, rows)


def _row_for(output: str, series_id: str) -> str:
    """The one line of ``validate``/``status`` output reporting on this series."""
    for line in output.splitlines():
        if f"{series_id}:" in line or f" {series_id} " in line:
            return line
    raise AssertionError(f"no row for {series_id!r} in output:\n{output}")


# --- defect 1: validate on an unprepared workspace ----------------------------------------


class TestGoldValidateNotStarted:
    def test_unprepared_workspace_reports_sin_preparar_not_errores(
        self, plan: AnnotationPlan, paths: WorkspacePaths
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "validate", "--annotator", "gv"])

        assert result.exit_code == 1, result.output
        assert "sin preparar" in result.output
        assert "errores" not in result.output, (
            "an unprepared workspace is not the same failure as a real data error"
        )
        assert "afg gold prepare --annotator gv" in result.output

    def test_real_errors_are_still_reported_as_errores(
        self, plan: AnnotationPlan, paths: WorkspacePaths, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        # ES3 stays unprepared; ES1 gets a genuine machine-column tamper.
        target = sources.decisions_dir / "ES1.decisions.gv.csv"
        _corrupt_machine_column(target, _DECISION_COLUMNS, "evidence_text")
        (sources.decisions_dir / "ES3.decisions.gv.csv").unlink()
        (sources.relations_dir / "ES3.candidates.gv.csv").unlink()

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "validate", "--annotator", "gv"])

        assert result.exit_code == 1, result.output
        assert "errores" in result.output, "ES1 has a real defect and must still be flagged"
        assert "sin preparar" in result.output, "ES3 was never prepared"
        assert "columna de máquina" in result.output
        assert "afg gold prepare --annotator gv" in result.output

    def test_freshly_prepared_workspace_passes(
        self, plan: AnnotationPlan, paths: WorkspacePaths, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "validate", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        assert "Sin errores" in result.output
        assert "problema(s)" not in result.output
        assert "sin preparar" not in _row_for(result.output, "ES1")
        assert "sin preparar" not in _row_for(result.output, "ES3")
        assert "errores" not in _row_for(result.output, "ES1")
        assert "errores" not in _row_for(result.output, "ES3")


# --- defect 2: status --annotator -----------------------------------------------------


class TestGoldStatusFilter:
    def test_filters_to_one_annotator(
        self, plan: AnnotationPlan, paths: WorkspacePaths, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        prepare_annotator_workspace(plan, "gm", paths=sources)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "status", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        table_text = result.output.partition("Adjudica")[0]
        assert "gv" in table_text
        assert "gm" not in table_text, "the table itself must hold only gv's rows"
        assert "ES2" not in table_text, "ES2 belongs only to gm"

    def test_unfiltered_status_returns_everyone(
        self, plan: AnnotationPlan, paths: WorkspacePaths, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        prepare_annotator_workspace(plan, "gm", paths=sources)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "status"])

        assert result.exit_code == 0, result.output
        assert "gv" in result.output
        assert "gm" in result.output
        assert "ES2" in result.output

    def test_unknown_initials_fails_like_the_other_commands(
        self, plan: AnnotationPlan, paths: WorkspacePaths
    ) -> None:
        runner = CliRunner()
        status_result = runner.invoke(afg_cli.app, ["gold", "status", "--annotator", "xx"])
        prepare_result = runner.invoke(afg_cli.app, ["gold", "prepare", "--annotator", "xx"])

        assert status_result.exit_code == 1
        assert prepare_result.exit_code == 1
        assert status_result.output.strip() == prepare_result.output.strip()
