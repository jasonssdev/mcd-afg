"""Tests for the per-annotator workspace (``afg.annotation.workspace``).

Every test here builds its own synthetic decisions/candidates CSVs under ``tmp_path``.
Nothing in this module reads the AMI corpus, so the whole file runs on a fresh clone.

The property that matters most is negative: ``prepare_annotator_workspace`` must never be
able to destroy annotated work. A re-run of ``afg gold prepare`` after a day of labelling
is a plausible accident, and the cost of getting it wrong is a day of somebody's life.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from afg.annotation.workspace import (
    ADJUDICATION_UNRESOLVED,
    AnnotationPlan,
    IssueKind,
    QuestionBankNotEmptyError,
    TaskKind,
    UnknownAnnotatorError,
    WorkspacePaths,
    adjudication_has_resolutions,
    expected_files,
    load_annotation_plan,
    prepare_annotator_workspace,
    question_bank_is_empty,
    series_has_annotated_work,
    validate_annotator,
    write_adjudication_log,
    write_question_bank_template,
)
from afg.domain.decision import AnnotationStatus
from afg.domain.question import QuestionStratum
from afg.domain.relation import Confidence, DirectionOk, RelationType

# --- synthetic fixtures ---------------------------------------------------------------

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

_PLAN_CONFIG: dict[str, object] = {
    "annotation": {
        "adjudicator": "jss",
        "phase1_series": ["ES2015"],
        "phase2_series": ["ES2008"],
        "recall_sample": {"owner": "gv", "series": "IS1004", "n": 50, "seed": 42},
        "question_bank": {
            "author": "gm",
            "validator": "gv",
            "total_questions": 100,
            "questions_per_stratum": 25,
        },
        "annotators": [
            {
                "initials": "gv",
                "name": "Germán Vega",
                "role": "annotator",
                "github": "Vega-German",
                "phase3_series": ["IS1004"],
            },
            {
                "initials": "gm",
                "name": "Gustavo Martínez",
                "role": "annotator",
                "github": "gmartinezbMCD",
                "phase3_series": ["TS3009"],
            },
            {
                "initials": "jss",
                "name": "Jason Sepúlveda",
                "role": "maintainer",
                "github": "jasonssdev",
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


def _decision_row(decision_id: str, meeting_id: str, **overrides: str) -> dict[str, str]:
    row = {
        "decision_id": decision_id,
        "meeting_id": meeting_id,
        "source_sentence_id": f"{meeting_id}.elana.s.{decision_id[-1]}",
        "sentence_text": f"They decide about {decision_id}.",
        "evidence_da_count": "2",
        "evidence_text": f"A: we decide {decision_id}",
        "machine_flags": "",
    }
    row.update(overrides)
    return row


def _candidate_row(pair_id: str, earlier: str, later: str, **overrides: str) -> dict[str, str]:
    row = {
        "pair_id": pair_id,
        "earlier_decision_id": earlier,
        "later_decision_id": later,
        "earlier_sentence_id": f"{earlier}.elana.s.1",
        "later_sentence_id": f"{later}.elana.s.2",
        "earlier_text": f"text of {earlier}",
        "later_text": f"text of {later}",
        "blocker_score": "0.4",
    }
    row.update(overrides)
    return row


@pytest.fixture
def plan() -> AnnotationPlan:
    return load_annotation_plan(_PLAN_CONFIG)


@pytest.fixture
def paths(tmp_path: Path) -> WorkspacePaths:
    return WorkspacePaths(
        decisions_dir=tmp_path / "decisions",
        relations_dir=tmp_path / "relations",
        questions_dir=tmp_path / "questions",
    )


@pytest.fixture
def sources(paths: WorkspacePaths) -> WorkspacePaths:
    """Write the machine-generated base files every assigned series needs."""
    for series_id in ("ES2015", "ES2008", "IS1004", "TS3009"):
        _write_csv(
            paths.decisions_dir / f"{series_id}.decisions.csv",
            _DECISION_COLUMNS,
            [
                _decision_row(f"{series_id}a.d01", f"{series_id}a"),
                _decision_row(f"{series_id}b.d02", f"{series_id}b"),
            ],
        )
        _write_csv(
            paths.relations_dir / f"{series_id}.candidates.csv",
            _CANDIDATE_COLUMNS,
            [_candidate_row(f"{series_id}.p001", f"{series_id}a.d01", f"{series_id}b.d02")],
        )
    _write_csv(
        paths.relations_dir / "IS1004.recall-sample.csv",
        _CANDIDATE_COLUMNS,
        [_candidate_row("IS1004.r001", "IS1004a.d01", "IS1004b.d02")],
    )
    return paths


def _candidate_pair_count(series_id: str) -> int:
    """Row count of the shipped ``<series>.candidates.csv``, data rows only.

    Reads the file that already ships in the repo (``git ls-files`` confirms every OE1
    series has one under ``data/processed/relations/``) and counts lines with
    :mod:`csv`, never touching a text column. ADR 0005 (``docs/decisions/
    0005-adr-development-evaluation-split.md``) forbids reading or asserting on the
    CONTENT of an evaluation-set series' pairs; a row count is not content -- it is
    already public in ``docs/anotacion/asignacion/README.md`` §1 and ``config/
    corpus.toml`` -- and this function never opens a cell beyond ``csv.reader``'s raw
    row iteration.
    """
    path = WorkspacePaths().relations_dir / f"{series_id}.candidates.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Falta {path}: no se puede contar los pares candidatos de la serie "
            f"{series_id!r}. ¿Se añadió o renombró una serie de fase 2 sin generar su "
            "CSV de candidatos?"
        )
    with path.open(newline="", encoding="utf-8") as handle:
        row_count = sum(1 for _ in csv.reader(handle))
    return row_count - 1  # exclude the header row


# --- the plan ---------------------------------------------------------------------------


class TestLoadAnnotationPlan:
    def test_reads_the_shipped_config(self) -> None:
        real_plan = load_annotation_plan()
        assert {a.initials for a in real_plan.annotators} == {"gv", "gm", "jss"}
        assert real_plan.adjudicator == "jss"

    def test_shipped_config_matches_the_assignment_document(self) -> None:
        """Guards the split in docs/anotacion/asignacion/README.md section 1."""
        real_plan = load_annotation_plan()
        gv = real_plan.annotator("gv")
        gm = real_plan.annotator("gm")
        assert gv.phase1_series == ("ES2015",)
        assert gv.phase2_series == ("ES2016", "IS1003", "TS3005", "ES2008")
        assert gv.phase3_series == ("IS1004", "IS1006", "IS1009", "TS3003", "ES2002")
        assert gm.phase3_series == ("TS3009", "TS3011", "IS1008", "ES2014")
        assert real_plan.recall_sample.owner == "gv"
        assert real_plan.recall_sample.series_id == "IS1004"
        assert real_plan.question_bank.author == "gm"
        assert real_plan.question_bank.validator == "gv"

    def test_phase2_is_ordered_by_ascending_candidate_volume(self) -> None:
        """Phase 2 is a list in EXECUTION order, not an alphabetical set.

        ``SeriesAssignment`` promises execution order, and `afg gold setup` prints the
        series in exactly this order, so whoever reads that output starts with the series
        listed first. The control series' candidate-pair counts climb from lightest to
        heaviest (derived below from the shipped CSVs, never hand-copied), so the
        annotator calibrates on the cheapest series and carries the costly one last.
        Sorting this list alphabetically would silently hand them ES2008 -- the
        heaviest -- on day one.
        """
        real_plan = load_annotation_plan()
        volumes = [_candidate_pair_count(s) for s in real_plan.phase2_series]
        assert volumes == sorted(volumes), (
            f"phase2_series debe ir de menor a mayor volumen de candidatos, "
            f"y va {list(real_plan.phase2_series)} ({volumes})"
        )

    def test_phase2_order_reaches_expected_files(self, tmp_path: Path) -> None:
        """The gap between the parsed plan and what the annotator actually opens.

        The test above only proves ``phase2_series`` itself is ordered. It says nothing
        about whether that order survives past the plan: :func:`expected_files` is the
        function ``afg.annotation.setup.run_setup`` walks to name ``first_file`` -- the
        exact file `afg gold setup` tells the annotator to open next (see both
        docstrings) -- so THIS is the boundary the argument actually depends on.
        """
        real_plan = load_annotation_plan()
        gv = real_plan.annotator("gv")
        paths = WorkspacePaths(
            decisions_dir=tmp_path / "decisions",
            relations_dir=tmp_path / "relations",
            questions_dir=tmp_path / "questions",
        )

        files = expected_files(real_plan, gv, paths)

        phase2_in_file_order = tuple(dict.fromkeys(f.series_id for f in files if f.phase == 2))
        assert phase2_in_file_order == gv.phase2_series, (
            "expected_files() reordered phase 2 relative to phase2_series -- the file "
            "`afg gold setup` names first would no longer be the cheapest control series"
        )

    def test_every_series_is_covered_exactly_once_across_the_team(self) -> None:
        real_plan = load_annotation_plan()
        phase3 = [s for a in real_plan.annotators for s in a.phase3_series]
        assert len(phase3) == len(set(phase3)), "a phase-3 series is assigned twice"
        covered = set(phase3) | set(real_plan.phase1_series) | set(real_plan.phase2_series)
        assert len(covered) == 14

    def test_unknown_initials_raise(self, plan: AnnotationPlan) -> None:
        with pytest.raises(UnknownAnnotatorError) as excinfo:
            plan.annotator("zz")
        assert "zz" in str(excinfo.value)
        assert "gv" in str(excinfo.value), "the error must list the valid initials"

    def test_phases_are_shared_by_every_annotator(self, plan: AnnotationPlan) -> None:
        assert plan.annotator("gv").phase1_series == ("ES2015",)
        assert plan.annotator("gm").phase1_series == ("ES2015",)

    def test_maintainer_has_no_assignments(self, plan: AnnotationPlan) -> None:
        assert plan.annotator("jss").assignments == ()

    def test_exposes_each_annotator_github_handle(self, plan: AnnotationPlan) -> None:
        assert plan.annotator("gv").github == "Vega-German"
        assert plan.annotator("gm").github == "gmartinezbMCD"
        assert plan.annotator("jss").github == "jasonssdev"

    def test_shipped_config_github_handles_match_the_real_accounts(self) -> None:
        """The three real GitHub logins in config/annotation.toml, spelled exactly as
        GitHub shows them -- two are mixed case and must not be lowercased."""
        real_plan = load_annotation_plan()
        assert real_plan.annotator("gv").github == "Vega-German"
        assert real_plan.annotator("gm").github == "gmartinezbMCD"
        assert real_plan.annotator("jss").github == "jasonssdev"

    def test_missing_github_fails_loudly(self) -> None:
        """`github` is required like `initials`/`name`: a person without one is a config
        bug, not someone with an empty handle to render."""
        config = {
            "annotation": {
                "adjudicator": "jss",
                "phase1_series": [],
                "phase2_series": [],
                "recall_sample": {"owner": "jss", "series": "ES2015", "n": 1, "seed": 1},
                "question_bank": {
                    "author": "jss",
                    "validator": "jss",
                    "total_questions": 2,
                    "questions_per_stratum": 2,
                },
                "annotators": [
                    {"initials": "jss", "name": "Jason Sepúlveda", "role": "maintainer"},
                ],
            }
        }
        with pytest.raises(KeyError, match="github"):
            load_annotation_plan(config)


# --- prepare ------------------------------------------------------------------------------


class TestPrepare:
    def test_creates_exactly_the_files_the_plan_says(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        outcome = prepare_annotator_workspace(plan, "gv", paths=sources)

        created = {f.target.name for f in outcome.created}
        assert created == {
            "ES2015.decisions.gv.csv",
            "ES2015.candidates.gv.csv",
            "ES2008.decisions.gv.csv",
            "ES2008.candidates.gv.csv",
            "IS1004.decisions.gv.csv",
            "IS1004.candidates.gv.csv",
            "IS1004.recall-sample.gv.csv",
        }
        assert all(f.target.exists() for f in outcome.created)

    def test_only_the_recall_owner_gets_a_recall_sample(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        outcome = prepare_annotator_workspace(plan, "gm", paths=sources)
        kinds = {f.kind for f in outcome.created}
        assert TaskKind.RECALL_SAMPLE not in kinds
        assert not (sources.relations_dir / "IS1004.recall-sample.gm.csv").exists()

    def test_phase_three_files_still_carry_the_initials(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """Single annotation is still attributed: the name always says who labelled it."""
        outcome = prepare_annotator_workspace(plan, "gm", paths=sources)
        phase3 = [f for f in outcome.created if f.phase == 3]
        assert phase3
        assert all(f.target.name.endswith(".gm.csv") for f in phase3)

    def test_human_columns_are_empty_and_machine_columns_are_kept(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        rows = list(
            csv.DictReader(
                (sources.decisions_dir / "ES2015.decisions.gv.csv").open(
                    newline="", encoding="utf-8"
                )
            )
        )
        assert rows
        for row in rows:
            assert row["status"] == ""
            assert row["decision_object"] == ""
            assert row["decision_content"] == ""
            assert row["notes"] == ""
            assert row["annotator"] == "gv", "the only prefilled human column is the identity"
            assert row["sentence_text"].startswith("They decide about")

    def test_writes_lf_line_endings(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        raw = (sources.decisions_dir / "ES2015.decisions.gv.csv").read_bytes()
        assert b"\r\n" not in raw

    def test_refuses_to_clobber_annotated_work(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["status"] = AnnotationStatus.DECISION.value
        rows[0]["decision_object"] = "el precio"
        _write_csv(target, _DECISION_COLUMNS, rows)
        before = target.read_bytes()

        outcome = prepare_annotator_workspace(plan, "gv", paths=sources)

        assert target.read_bytes() == before, "a second prepare destroyed a day of work"
        assert target.name in {f.target.name for f in outcome.skipped_annotated}
        assert target.name not in {f.target.name for f in outcome.created}

    def test_untouched_file_is_regenerated_not_skipped(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        outcome = prepare_annotator_workspace(plan, "gv", paths=sources)
        assert not outcome.skipped_annotated
        assert len(outcome.created) == 7

    def test_force_overwrites_annotated_work(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["status"] = AnnotationStatus.DECISION.value
        _write_csv(target, _DECISION_COLUMNS, rows)

        outcome = prepare_annotator_workspace(plan, "gv", paths=sources, force=True)

        assert target.name in {f.target.name for f in outcome.overwritten}
        rows_after = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        assert all(row["status"] == "" for row in rows_after)

    def test_candidates_annotation_also_blocks_overwrite(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.relations_dir / "ES2015.candidates.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["relation"] = RelationType.REFINA.value
        _write_csv(target, _CANDIDATE_COLUMNS, rows)

        outcome = prepare_annotator_workspace(plan, "gv", paths=sources)
        assert target.name in {f.target.name for f in outcome.skipped_annotated}

    def test_missing_source_is_reported_not_crashed(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        (sources.decisions_dir / "ES2008.decisions.csv").unlink()
        outcome = prepare_annotator_workspace(plan, "gv", paths=sources)
        assert "ES2008.decisions.csv" in {f.source.name for f in outcome.missing_sources}
        assert outcome.created, "the other series must still be prepared"

    def test_maintainer_gets_nothing(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        outcome = prepare_annotator_workspace(plan, "jss", paths=sources)
        assert outcome.created == ()
        assert outcome.is_maintainer

    def test_unknown_annotator_raises(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        with pytest.raises(UnknownAnnotatorError):
            prepare_annotator_workspace(plan, "xx", paths=sources)


# --- series_has_annotated_work -----------------------------------------------------------


class TestSeriesHasAnnotatedWork:
    def test_no_derived_files_at_all_is_empty(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """Nobody ran `prepare` yet: only the base files exist, no derived ones."""
        assert series_has_annotated_work("ES2015", paths=sources) == ()

    def test_untouched_derived_files_are_empty(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """The normal state right after `prepare`: derived files exist but hold no work."""
        prepare_annotator_workspace(plan, "gv", paths=sources)
        prepare_annotator_workspace(plan, "gm", paths=sources)

        assert series_has_annotated_work("ES2015", paths=sources) == ()

    def test_finds_annotated_decisions_file(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["status"] = AnnotationStatus.DECISION.value
        _write_csv(target, _DECISION_COLUMNS, rows)

        found = series_has_annotated_work("ES2015", paths=sources)

        assert target in found

    def test_finds_annotated_candidates_file(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.relations_dir / "ES2015.candidates.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["relation"] = RelationType.REFINA.value
        _write_csv(target, _CANDIDATE_COLUMNS, rows)

        found = series_has_annotated_work("ES2015", paths=sources)

        assert target in found

    def test_only_reports_the_series_asked_about(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.decisions_dir / "ES2008.decisions.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["status"] = AnnotationStatus.DECISION.value
        _write_csv(target, _DECISION_COLUMNS, rows)

        assert series_has_annotated_work("ES2015", paths=sources) == ()
        assert series_has_annotated_work("ES2008", paths=sources) != ()

    def test_ignores_recall_sample_files(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """Recall-sample derived files are a different command's concern (Tarea C)."""
        prepare_annotator_workspace(plan, "gv", paths=sources)
        target = sources.relations_dir / "IS1004.recall-sample.gv.csv"
        rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
        rows[0]["relation"] = RelationType.REFINA.value
        _write_csv(target, _CANDIDATE_COLUMNS, rows)

        assert series_has_annotated_work("IS1004", paths=sources) == ()


# --- validate -----------------------------------------------------------------------------


def _prepared(plan: AnnotationPlan, paths: WorkspacePaths) -> None:
    prepare_annotator_workspace(plan, "gv", paths=paths)


def _fill_decisions(path: Path, **cells: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    for row in rows:
        row.update(
            {
                "status": AnnotationStatus.DECISION.value,
                "decision_object": "el precio",
                "decision_content": "veinticinco euros",
                "annotator": "gv",
            }
        )
    rows[0].update(cells)
    _write_csv(path, _DECISION_COLUMNS, rows)
    return rows


def _fill_candidates(path: Path, **cells: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    for row in rows:
        row.update(
            {
                "relation": RelationType.REFINA.value,
                "direction_ok": DirectionOk.SI.value,
                "confidence": Confidence.ALTA.value,
                "annotator": "gv",
            }
        )
    rows[0].update(cells)
    _write_csv(path, _CANDIDATE_COLUMNS, rows)
    return rows


class TestValidateProgress:
    def test_freshly_prepared_workspace_is_valid_with_zero_progress(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        report = validate_annotator(plan, "gv", paths=sources)
        assert report.ok, [i.message for i in report.issues]
        assert all(p.decisions_filled == 0 for p in report.series)
        assert all(p.decisions_total == 2 for p in report.series)

    def test_counts_filled_rows(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        _prepared(plan, sources)
        _fill_decisions(sources.decisions_dir / "ES2015.decisions.gv.csv")
        _fill_candidates(sources.relations_dir / "ES2015.candidates.gv.csv")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        progress = report.series[0]
        assert (progress.decisions_filled, progress.decisions_total) == (2, 2)
        assert (progress.candidates_filled, progress.candidates_total) == (1, 1)
        assert report.ok

    def test_series_filter_narrows_the_report(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        report = validate_annotator(plan, "gv", paths=sources, series="IS1004")
        assert [p.series_id for p in report.series] == ["IS1004"]

    def test_series_filter_rejects_an_unassigned_series(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        with pytest.raises(ValueError, match="TS3009"):
            validate_annotator(plan, "gv", paths=sources, series="TS3009")

    def test_missing_workspace_file_is_an_issue_not_a_crash(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        report = validate_annotator(plan, "gv", paths=sources)
        assert not report.ok
        assert any("prepare" in issue.message for issue in report.issues)

    def test_unprepared_series_reads_as_not_started_not_as_errors(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """`validate` still fails, but the status table must not accuse someone of
        errors for not having run `prepare` yet."""
        report = validate_annotator(plan, "gv", paths=sources)
        assert all(progress.not_started for progress in report.series)
        assert all(issue.kind is IssueKind.MISSING_FILE for issue in report.issues)

    def test_a_real_defect_is_not_reported_as_not_started(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        _fill_decisions(sources.decisions_dir / "ES2015.decisions.gv.csv", status="accepted")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert not report.series[0].not_started


class TestValidateClosedSets:
    def test_illegal_status_is_reported_with_file_row_and_value(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        _fill_decisions(path, status="accepted")  # the DOMAIN vocabulary, not the CSV one

        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")

        assert not report.ok
        issue = next(i for i in report.issues if i.column == "status")
        assert issue.path == path
        assert issue.row_id == "ES2015a.d01"
        assert issue.value == "accepted"
        assert AnnotationStatus.DECISION.value in issue.message

    def test_illegal_relation_is_reported(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.relations_dir / "ES2015.candidates.gv.csv"
        _fill_candidates(path, relation="supersedes")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        issue = next(i for i in report.issues if i.column == "relation")
        assert issue.value == "supersedes"
        assert issue.row_id == "ES2015.p001"

    @pytest.mark.parametrize(
        ("column", "value"),
        [("direction_ok", "yes"), ("confidence", "high")],
    )
    def test_illegal_direction_and_confidence_are_reported(
        self, plan: AnnotationPlan, sources: WorkspacePaths, column: str, value: str
    ) -> None:
        _prepared(plan, sources)
        path = sources.relations_dir / "ES2015.candidates.gv.csv"
        _fill_candidates(path, **{column: value})
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == column and i.value == value for i in report.issues)

    def test_every_legal_status_passes(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        for status in AnnotationStatus:
            _fill_decisions(path, status=status.value, notes="la evidencia no lo dice")
            report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
            status_issues = [i for i in report.issues if i.column == "status"]
            assert not status_issues, f"{status} rejected: {status_issues}"


class TestValidateHalfFilledRows:
    def test_decision_without_object_is_half_filled(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        _fill_decisions(path, decision_object="")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert not report.ok
        assert any(
            i.column == "decision_object" and i.row_id == "ES2015a.d01" for i in report.issues
        )

    def test_object_without_status_is_half_filled(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        rows[0]["decision_object"] = "el precio"
        _write_csv(path, _DECISION_COLUMNS, rows)
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "status" for i in report.issues)

    def test_sin_soporte_requires_notes(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        _fill_decisions(path, status=AnnotationStatus.SIN_SOPORTE.value, notes="")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "notes" for i in report.issues)

    def test_relation_without_confidence_is_half_filled(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.relations_dir / "ES2015.candidates.gv.csv"
        _fill_candidates(path, confidence="")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "confidence" for i in report.issues)

    def test_half_filled_row_does_not_count_as_progress(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.relations_dir / "ES2015.candidates.gv.csv"
        _fill_candidates(path, confidence="")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert report.series[0].candidates_filled == 0

    def test_annotator_column_must_be_set_on_a_labelled_row(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        _fill_decisions(path, annotator="")
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "annotator" for i in report.issues)


class TestValidateMachineColumns:
    def test_edited_earlier_text_is_caught(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """The check that matters: a silent edit here corrupts the gold set invisibly."""
        _prepared(plan, sources)
        path = sources.relations_dir / "ES2015.candidates.gv.csv"
        rows = _fill_candidates(path)
        rows[0]["earlier_text"] = "something the annotator retyped"
        _write_csv(path, _CANDIDATE_COLUMNS, rows)

        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")

        assert not report.ok
        issue = next(i for i in report.issues if i.column == "earlier_text")
        assert issue.row_id == "ES2015.p001"
        assert "text of ES2015a.d01" in issue.message

    def test_edited_sentence_text_is_caught(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = _fill_decisions(path)
        rows[1]["sentence_text"] = "reworded by hand"
        _write_csv(path, _DECISION_COLUMNS, rows)
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "sentence_text" for i in report.issues)

    def test_deleted_row_is_caught(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = _fill_decisions(path)
        _write_csv(path, _DECISION_COLUMNS, rows[:1])
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.row_id == "ES2015b.d02" for i in report.issues)

    def test_compuesta_child_rows_are_allowed(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        """Manual section 2: a `compuesta` row spawns `-1`, `-2` children that are new ids."""
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = _fill_decisions(path, status=AnnotationStatus.COMPUESTA.value)
        parent = rows[0]
        for index in (1, 2):
            child = dict(parent)
            child["decision_id"] = f"{parent['decision_id']}-{index}"
            child["status"] = AnnotationStatus.DECISION.value
            child["decision_object"] = f"objeto {index}"
            child["decision_content"] = f"contenido {index}"
            rows.append(child)
        _write_csv(path, _DECISION_COLUMNS, rows)

        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")

        assert report.ok, [i.message for i in report.issues]

    def test_compuesta_child_may_not_change_machine_columns(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = _fill_decisions(path, status=AnnotationStatus.COMPUESTA.value)
        child = dict(rows[0])
        child["decision_id"] = f"{rows[0]['decision_id']}-1"
        child["status"] = AnnotationStatus.DECISION.value
        child["evidence_text"] = "invented evidence"
        rows.append(child)
        _write_csv(path, _DECISION_COLUMNS, rows)

        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.column == "evidence_text" for i in report.issues)

    def test_orphan_row_id_is_caught(self, plan: AnnotationPlan, sources: WorkspacePaths) -> None:
        _prepared(plan, sources)
        path = sources.decisions_dir / "ES2015.decisions.gv.csv"
        rows = _fill_decisions(path)
        invented = dict(rows[0])
        invented["decision_id"] = "ES2015z.d99"
        rows.append(invented)
        _write_csv(path, _DECISION_COLUMNS, rows)
        report = validate_annotator(plan, "gv", paths=sources, series="ES2015")
        assert any(i.row_id == "ES2015z.d99" for i in report.issues)


# --- adjudicate ---------------------------------------------------------------------------


class TestAdjudicate:
    @pytest.fixture
    def two_annotators(self, plan: AnnotationPlan, sources: WorkspacePaths) -> WorkspacePaths:
        prepare_annotator_workspace(plan, "gv", paths=sources)
        prepare_annotator_workspace(plan, "gm", paths=sources)
        base = sources.relations_dir / "ES2015.candidates.csv"
        rows = list(csv.DictReader(base.open(newline="", encoding="utf-8")))
        rows.append(_candidate_row("ES2015.p002", "ES2015a.d01", "ES2015b.d02"))
        for initials, relation, direction in (("gv", "refina", "si"), ("gm", "reafirma", "no")):
            annotated = []
            for index, row in enumerate(rows):
                new = dict(row)
                new["relation"] = relation if index == 0 else "reafirma"
                new["direction_ok"] = direction if index == 0 else "si"
                new["confidence"] = "alta"
                new["annotator"] = initials
                annotated.append(new)
            _write_csv(
                sources.relations_dir / f"ES2015.candidates.{initials}.csv",
                _CANDIDATE_COLUMNS,
                annotated,
            )
        return sources

    def test_writes_the_disagreement_table(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        out_path = write_adjudication_log(plan, "ES2015", paths=two_annotators)
        text = out_path.read_text(encoding="utf-8")

        # Annotator A is the lexicographically first file, inherited from
        # `compute_series_agreement` -- `gm` sorts before `gv`.
        assert out_path.name == "ES2015.adjudication.md"
        assert "| `ES2015.p001` | `reafirma` | `refina` |" in text
        assert "`ES2015.p002`" not in text, "agreeing pairs have nothing to adjudicate"
        assert "`si`" in text and "`no`" in text, "direction disagreements go in their own table"

    def test_header_carries_series_people_and_three_kappas(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        text = write_adjudication_log(plan, "ES2015", paths=two_annotators).read_text(
            encoding="utf-8"
        )
        assert "Adjudicación — `ES2015`" in text
        assert "Germán Vega" in text and "Gustavo Martínez" in text
        assert "jss" in text
        assert "Existencia del enlace" in text
        assert "Tipo de relación" in text
        assert "Dirección" in text

    def test_final_label_and_reason_are_left_for_the_human(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        text = write_adjudication_log(plan, "ES2015", paths=two_annotators).read_text(
            encoding="utf-8"
        )
        row = next(line for line in text.splitlines() if "`ES2015.p001` | `reafirma`" in line)
        assert row.count(ADJUDICATION_UNRESOLVED) == 2

    def test_refuses_to_clobber_filled_resolutions(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        out_path = write_adjudication_log(plan, "ES2015", paths=two_annotators)
        resolved = out_path.read_text(encoding="utf-8").replace(
            f"| {ADJUDICATION_UNRESOLVED} | {ADJUDICATION_UNRESOLVED} |",
            "| `refina` | La posterior acota el objeto. |",
            1,
        )
        out_path.write_text(resolved, encoding="utf-8")
        assert adjudication_has_resolutions(out_path)

        with pytest.raises(FileExistsError, match="ES2015"):
            write_adjudication_log(plan, "ES2015", paths=two_annotators)

        assert out_path.read_text(encoding="utf-8") == resolved

    def test_force_overwrites_resolutions(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        out_path = write_adjudication_log(plan, "ES2015", paths=two_annotators)
        out_path.write_text("| `refina` | porque sí |", encoding="utf-8")
        write_adjudication_log(plan, "ES2015", paths=two_annotators, force=True)
        assert "Adjudicación" in out_path.read_text(encoding="utf-8")

    def test_unresolved_log_is_not_treated_as_resolved(
        self, plan: AnnotationPlan, two_annotators: WorkspacePaths
    ) -> None:
        out_path = write_adjudication_log(plan, "ES2015", paths=two_annotators)
        assert not adjudication_has_resolutions(out_path)
        write_adjudication_log(plan, "ES2015", paths=two_annotators)  # must not raise

    def test_missing_annotator_files_fail_clearly(
        self, plan: AnnotationPlan, sources: WorkspacePaths
    ) -> None:
        with pytest.raises(FileNotFoundError, match="ES2015"):
            write_adjudication_log(plan, "ES2015", paths=sources)


# --- question bank ---------------------------------------------------------------------


class TestQuestionBank:
    def test_writes_100_rows_25_per_stratum(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))

        assert len(rows) == 100
        per_stratum: dict[str, int] = {}
        for row in rows:
            per_stratum[row["stratum"]] = per_stratum.get(row["stratum"], 0) + 1
        assert per_stratum == {stratum.value: 25 for stratum in QuestionStratum}

    def test_ids_are_prenumbered_and_unique(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))
        ids = [row["id"] for row in rows]
        assert ids[0] == "q001"
        assert ids[-1] == "q100"
        assert len(set(ids)) == 100

    def test_text_is_empty_and_author_is_prefilled(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(
            paths.questions_dir / "banco-preguntas.csv", author="gm"
        )
        rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))
        assert all(row["text"] == "" for row in rows)
        assert all(row["reference_answer"] == "" for row in rows)
        assert all(row["author"] == "gm" for row in rows)
        assert all(row["validated_by"] == "" for row in rows)

    def test_columns_match_the_shipped_template(self, paths: WorkspacePaths) -> None:
        template = Path("data/processed/questions/_plantilla-banco-preguntas.csv")
        expected = next(csv.reader(template.open(newline="", encoding="utf-8")))
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        actual = next(csv.reader(out_path.open(newline="", encoding="utf-8")))
        assert actual == expected

    def test_writes_lf_line_endings(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        assert b"\r\n" not in out_path.read_bytes()

    def test_an_untouched_bank_is_empty(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        assert question_bank_is_empty(out_path)

    def test_refuses_to_overwrite_a_non_empty_bank(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))
        rows[0]["text"] = "¿Cuál es el precio de venta?"
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        before = out_path.read_bytes()

        assert not question_bank_is_empty(out_path)
        with pytest.raises(QuestionBankNotEmptyError, match="banco-preguntas"):
            write_question_bank_template(out_path)
        assert out_path.read_bytes() == before

    def test_force_overwrites(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        out_path.write_text("id,series_id\nq001,ES2015\n", encoding="utf-8")
        write_question_bank_template(out_path, force=True)
        rows = list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))
        assert len(rows) == 100

    def test_regenerating_an_untouched_bank_is_allowed(self, paths: WorkspacePaths) -> None:
        out_path = write_question_bank_template(paths.questions_dir / "banco-preguntas.csv")
        write_question_bank_template(out_path)  # must not raise
        assert len(list(csv.DictReader(out_path.open(newline="", encoding="utf-8")))) == 100
