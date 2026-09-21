"""Tests for ``afg gold setup``: one command from a fresh clone to "open this file and
start".

Every test here builds its own synthetic annotation plan and CSV fixtures under
``tmp_path``, and stubs the corpus download and transcript rendering -- nothing in this
file depends on the real AMI corpus or on network access.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
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
from afg.corpus.download import DownloadResult
from afg.corpus.render import RenderResult

# --- synthetic fixtures (mirrors tests/test_cli_gold.py) --------------------------------

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

# gv: ES1 (phase 1) + ES3 (phase 3, solo).
# gm: ES1 (phase 1) + ES2 (phase 3, solo, owns the recall sample).
# jss: maintainer, adjudicates, annotates nothing.
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


@pytest.fixture
def ami_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ami"
    monkeypatch.setattr(afg_cli, "AMI_DIR", root)
    return root


@pytest.fixture
def transcripts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    out = tmp_path / "transcripts"
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", out)
    return out


@pytest.fixture(autouse=True)
def tables_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    out = tmp_path / "reports"
    monkeypatch.setattr(afg_cli, "TABLES_DIR", out)
    return out


@dataclass
class _Calls:
    """How many times each stubbed corpus function was invoked, so a test can assert a
    step was (or was not) skipped without parsing console output."""

    download: int = 0
    discover: int = 0
    render: int = 0
    rendered_meeting_ids: list[str] = field(default_factory=list)


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    tracker = _Calls()

    def _download(dest_dir: Path) -> DownloadResult:
        tracker.download += 1
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "words").mkdir(exist_ok=True)
        (dest_dir / "words" / "STUBa.A.words.xml").write_text("<nite/>", encoding="utf-8")
        return DownloadResult(
            archive_path=dest_dir / "stub.zip", extracted_to=dest_dir, bytes_downloaded=1024
        )

    def _discover(ami_root: Path, series_filter: object = None) -> list[str]:
        tracker.discover += 1
        return ["STUBa"]

    def _render(
        ami_root: Path, meeting_ids: list[str], out_dir: Path, manifest_dir: Path
    ) -> RenderResult:
        tracker.render += 1
        tracker.rendered_meeting_ids = list(meeting_ids)
        out_dir.mkdir(parents=True, exist_ok=True)
        for meeting_id in meeting_ids:
            (out_dir / f"{meeting_id}.md").write_text("stub transcript", encoding="utf-8")
            (out_dir / f"{meeting_id}.jsonl").write_text("{}\n", encoding="utf-8")
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "transcripts_manifest.csv"
        manifest_path.write_text("meeting_id\n" + "\n".join(meeting_ids) + "\n", encoding="utf-8")
        return RenderResult(
            meeting_ids=tuple(meeting_ids),
            total_turns=len(meeting_ids),
            total_characters=100,
            renderer_revision="stub",
            out_dir=out_dir,
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(afg_cli, "download_annotations", _download)
    monkeypatch.setattr(afg_cli, "discover_meeting_ids", _discover)
    monkeypatch.setattr(afg_cli, "render_meetings", _render)
    return tracker


def _mark_corpus_present(ami_root: Path) -> None:
    (ami_root / "words").mkdir(parents=True, exist_ok=True)
    (ami_root / "words" / "REAL.A.words.xml").write_text("<nite/>", encoding="utf-8")


def _mark_transcripts_present(transcripts_dir: Path) -> None:
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    (transcripts_dir / "ya-generado.md").write_text("ya generado", encoding="utf-8")


def _fill_one_row(path: Path) -> None:
    """Write real human annotation into the first row -- enough for
    ``file_contains_annotation`` to see it and for ``prepare``/``setup`` to refuse to
    touch the file again without --force."""
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    rows[0]["status"] = "no_decision"
    rows[0]["annotator"] = "gv"
    _write_csv(path, _DECISION_COLUMNS, rows)


# --- 1. steps are skipped when already satisfied -----------------------------------------


class TestStepsSkippedWhenAlreadyDone:
    def test_corpus_already_present_skips_download(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        assert "se salta" in result.output.lower()
        assert calls.download == 0
        assert calls.render == 1, "transcripts were still missing and must still be rendered"

    def test_transcripts_already_rendered_skips_render(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)
        _mark_transcripts_present(transcripts_dir)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        assert calls.download == 0
        assert calls.render == 0
        # Both skip lines must be present, distinctly.
        lowered = result.output.lower()
        assert "corpus" in lowered and "se salta" in lowered
        assert "transcripci" in lowered

    def test_annotated_workspace_file_is_respected_not_recreated(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)
        _mark_transcripts_present(transcripts_dir)
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.decisions_dir / "ES1.decisions.gv.csv"
        _fill_one_row(target)
        before = target.read_text(encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        assert "respetados" in result.output.lower()
        assert target.read_text(encoding="utf-8") == before


# --- 2. corpus confirmation ----------------------------------------------------------------


class TestCorpusConfirmation:
    def test_confirmation_is_asked_when_corpus_is_missing(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"], input="y\n")

        assert result.exit_code == 0, result.output
        assert "licen" in result.output.lower()  # "Licence:" / "licencia"
        assert "proceed with download" in result.output.lower()
        assert calls.download == 1

    def test_declining_the_confirmation_stops_everything(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"], input="n\n")

        assert result.exit_code != 0
        assert calls.download == 0
        assert calls.render == 0, "declining the corpus must stop before transcripts render"
        assert not (sources.decisions_dir / "ES1.decisions.gv.csv").exists(), (
            "declining the corpus must stop before the workspace is prepared"
        )

    def test_yes_flag_skips_the_prompt(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        runner = CliRunner()
        # No stdin input provided: if the prompt were asked, CliRunner would abort on EOF.
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv", "--yes"])

        assert result.exit_code == 0, result.output
        assert calls.download == 1


# --- 3. setup never destroys work (never passes force) --------------------------------


class TestNeverForces:
    def test_running_twice_preserves_annotated_row(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)
        _mark_transcripts_present(transcripts_dir)
        runner = CliRunner()

        first = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])
        assert first.exit_code == 0, first.output

        target = sources.decisions_dir / "ES1.decisions.gv.csv"
        _fill_one_row(target)
        annotated = target.read_text(encoding="utf-8")

        second = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])
        assert second.exit_code == 0, second.output
        assert target.read_text(encoding="utf-8") == annotated, (
            "setup must never pass --force to prepare: annotated work must survive"
        )


# --- 4. unknown annotator ------------------------------------------------------------------


class TestUnknownAnnotator:
    def test_fails_like_prepare_and_validate(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        runner = CliRunner()
        setup_result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "xx"])
        prepare_result = runner.invoke(afg_cli.app, ["gold", "prepare", "--annotator", "xx"])
        validate_result = runner.invoke(afg_cli.app, ["gold", "validate", "--annotator", "xx"])

        assert setup_result.exit_code == 1
        assert prepare_result.exit_code == 1
        assert validate_result.exit_code == 1
        assert setup_result.output.strip() == prepare_result.output.strip()
        assert setup_result.output.strip() == validate_result.output.strip()
        assert calls.download == 0
        assert calls.render == 0, "an unknown annotator must fail before touching the corpus"


# --- 5. idempotence --------------------------------------------------------------------


class TestIdempotence:
    def test_running_twice_in_a_row_is_safe_and_reports_skips(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        runner = CliRunner()
        first = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv", "--yes"])
        assert first.exit_code == 0, first.output
        assert calls.download == 1
        assert calls.render == 1

        target = sources.decisions_dir / "ES1.decisions.gv.csv"
        first_bytes = target.read_bytes()

        second = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv", "--yes"])
        assert second.exit_code == 0, second.output
        lowered = second.output.lower()
        assert "se salta" in lowered  # corpus and/or transcripts reported as skipped
        assert calls.download == 1, "the second run must not re-download the corpus"
        assert calls.render == 1, "the second run must not re-render the transcripts"
        assert target.read_bytes() == first_bytes


# --- 6. closing message -----------------------------------------------------------------


class TestClosingMessage:
    def test_names_first_series_first_file_and_next_commands(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)
        _mark_transcripts_present(transcripts_dir)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "gv"])

        assert result.exit_code == 0, result.output
        assert "ES1" in result.output
        assert "ES1.decisions.gv.csv" in result.output
        assert "uv run afg gold validate --annotator gv" in result.output

    def test_maintainer_gets_the_adjudicator_message_not_a_file_to_open(
        self,
        plan: AnnotationPlan,
        paths: WorkspacePaths,
        sources: WorkspacePaths,
        ami_root: Path,
        transcripts_dir: Path,
        calls: _Calls,
    ) -> None:
        _mark_corpus_present(ami_root)
        _mark_transcripts_present(transcripts_dir)

        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["gold", "setup", "--annotator", "jss"])

        assert result.exit_code == 0, result.output
        assert "no anota ninguna serie" in result.output.lower()
        assert "afg gold adjudicate" in result.output
