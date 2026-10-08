"""Tests for the adjudication CSVs (``afg.annotation.adjudication``).

The two ``<series>.*.adjudicated.csv`` files hold both annotators' answers side by side plus
the adjudicator's verdict. The invariant that matters most: the machine only ever copies a
label on which two humans already agree. Every fixture here is synthetic under ``tmp_path``.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.annotation.adjudication import (
    DECISION_ADJUDICATED_FIXED,
    validate_adjudication,
    write_adjudication_csvs,
)
from afg.annotation.agreement import annotator_csvs, compute_series_agreement
from afg.annotation.workspace import (
    AnnotationPlan,
    IssueKind,
    WorkspacePaths,
    load_annotation_plan,
    prepare_annotator_workspace,
    series_has_annotated_work,
    validate_annotator,
)

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
        "phase2_series": [],
        "recall_sample": {"owner": "gv", "series": "IS1004", "n": 1, "seed": 1},
        "question_bank": {
            "author": "gm",
            "validator": "gv",
            "total_questions": 4,
            "questions_per_stratum": 1,
        },
        "annotators": [
            {"initials": "gv", "name": "Germán", "role": "annotator", "github": "g"},
            {"initials": "gm", "name": "Gustavo", "role": "annotator", "github": "m"},
            {"initials": "jss", "name": "Jason", "role": "maintainer", "github": "j"},
        ],
    }
}


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _base_decision(decision_id: str) -> dict[str, str]:
    return {
        "decision_id": decision_id,
        "meeting_id": decision_id.split(".")[0],
        "source_sentence_id": f"{decision_id}.s",
        "sentence_text": f"sentence {decision_id}",
        "evidence_da_count": "1",
        "evidence_text": f"evidence {decision_id}",
    }


def _human(decision_id: str, who: str, status: str, obj: str = "", content: str = "", **kw: str):
    row = _base_decision(decision_id.split("-")[0])  # children inherit machine columns
    row["decision_id"] = decision_id
    row.update(
        status=status,
        decision_object=obj,
        decision_content=content,
        annotator=who,
        notes=kw.get("notes", ""),
    )
    return row


def _pair(pair_id: str, **extra: str) -> dict[str, str]:
    row = {
        "pair_id": pair_id,
        "earlier_decision_id": "ES2015a.d01",
        "later_decision_id": "ES2015b.d02",
        "earlier_sentence_id": "e",
        "later_sentence_id": "l",
        "earlier_text": f"earlier {pair_id}",
        "later_text": f"later {pair_id}",
        "blocker_score": "0.4",
    }
    row.update(extra)
    return row


def _rel(pair_id: str, who: str, relation: str, direction: str, **extra: str) -> dict[str, str]:
    return _pair(
        pair_id,
        relation=relation,
        direction_ok=direction,
        confidence="alta",
        annotator=who,
        **extra,
    )


_BASE_IDS = ("ES2015a.d01", "ES2015a.d02", "ES2015a.d03", "ES2015a.d04", "ES2015a.d05")


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
def series(paths: WorkspacePaths) -> WorkspacePaths:
    """Two annotators over ES2015.

    d01 agree (decision, same object/content apart from case of notes); d02 disagree;
    d03 both compuesta, identical child statuses; d04 compuesta vs decision; d05 both
    compuesta with different child statuses.
    """
    write_csv(
        paths.decisions_dir / "ES2015.decisions.csv",
        _DECISION_COLUMNS,
        [_base_decision(i) for i in _BASE_IDS],
    )
    gm = [
        _human("ES2015a.d01", "gm", "decision", "pantalla", "sin pantalla", notes="n-gm"),
        _human("ES2015a.d02", "gm", "decision", "color", "negro"),
        _human("ES2015a.d03", "gm", "compuesta"),
        _human("ES2015a.d03-1", "gm", "decision", "pantalla LCD", "no incluir una pantalla LCD"),
        _human("ES2015a.d03-2", "gm", "no_decision"),
        _human("ES2015a.d04", "gm", "compuesta"),
        _human("ES2015a.d04-1", "gm", "decision", "a", "b"),
        _human("ES2015a.d04-2", "gm", "decision", "c", "d"),
        _human("ES2015a.d05", "gm", "compuesta"),
        _human("ES2015a.d05-1", "gm", "decision", "a", "b"),
        _human("ES2015a.d05-2", "gm", "decision", "c", "d"),
    ]
    gv = [
        _human("ES2015a.d01", "gv", "decision", "otro objeto", "otro contenido"),
        _human("ES2015a.d02", "gv", "no_decision"),
        _human("ES2015a.d03", "gv", "compuesta"),
        _human("ES2015a.d03-1", "gv", "decision", "x", "y"),
        _human("ES2015a.d03-2", "gv", "no_decision"),
        _human("ES2015a.d04", "gv", "decision", "a", "b"),
        _human("ES2015a.d05", "gv", "compuesta"),
        _human("ES2015a.d05-1", "gv", "decision", "a", "b"),
        _human("ES2015a.d05-2", "gv", "no_decision"),
    ]
    write_csv(paths.decisions_dir / "ES2015.decisions.gm.csv", _DECISION_COLUMNS, gm)
    write_csv(paths.decisions_dir / "ES2015.decisions.gv.csv", _DECISION_COLUMNS, gv)

    write_csv(
        paths.relations_dir / "ES2015.candidates.csv",
        _CANDIDATE_COLUMNS,
        [_pair("ES2015.p001"), _pair("ES2015.p002"), _pair("ES2015.p003")],
    )
    write_csv(
        paths.relations_dir / "ES2015.candidates.gm.csv",
        _CANDIDATE_COLUMNS,
        [
            _rel("ES2015.p001", "gm", "refina", "si", notes="gm-note"),
            _rel("ES2015.p002", "gm", "refina", "si"),
            _rel("ES2015.p003", "gm", "reafirma", "si"),
        ],
    )
    write_csv(
        paths.relations_dir / "ES2015.candidates.gv.csv",
        _CANDIDATE_COLUMNS,
        [
            _rel("ES2015.p001", "gv", "refina", "si"),
            _rel("ES2015.p002", "gv", "revierte", "si"),
            _rel("ES2015.p003", "gv", "reafirma", "no"),
        ],
    )
    return paths


def _written(
    plan: AnnotationPlan, paths: WorkspacePaths, **kw: bool
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    decisions_path, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=paths, **kw)
    return read_csv(decisions_path), read_csv(candidates_path)


# --- generation --------------------------------------------------------------------------


class TestColumns:
    def test_file_names_use_the_adjudicated_suffix(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=series)
        assert decisions_path == series.decisions_dir / "ES2015.decisions.adjudicated.csv"
        assert candidates_path == series.relations_dir / "ES2015.candidates.adjudicated.csv"

    def test_decision_columns_and_order(self, plan: AnnotationPlan, series: WorkspacePaths) -> None:
        decisions_path, _ = write_adjudication_csvs(plan, "ES2015", paths=series)
        header = decisions_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert header == [
            "decision_id",
            "meeting_id",
            "source_sentence_id",
            "sentence_text",
            "evidence_text",
            *(f"gm_{c}" for c in ("status", "object", "content", "notes", "split")),
            *(f"gv_{c}" for c in ("status", "object", "content", "notes", "split")),
            "acuerdo",
            "final_status",
            "final_object",
            "final_content",
            "razon",
            "adjudicator",
        ]
        assert header[:5] == list(DECISION_ADJUDICATED_FIXED)

    def test_candidate_columns_and_order(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=series)
        header = candidates_path.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert header == [
            "pair_id",
            "earlier_decision_id",
            "later_decision_id",
            "earlier_text",
            "later_text",
            "blocker_score",
            *(f"gm_{c}" for c in ("relation", "direction_ok", "confidence", "notes")),
            *(f"gv_{c}" for c in ("relation", "direction_ok", "confidence", "notes")),
            "acuerdo",
            "final_relation",
            "final_direction_ok",
            "razon",
            "adjudicator",
        ]

    def test_one_row_per_base_decision_children_are_not_rows(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions, candidates = _written(plan, series)
        assert [r["decision_id"] for r in decisions] == list(_BASE_IDS)
        assert [r["pair_id"] for r in candidates] == ["ES2015.p001", "ES2015.p002", "ES2015.p003"]

    def test_machine_and_annotator_values_sit_side_by_side(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions, candidates = _written(plan, series)
        d01 = decisions[0]
        assert d01["sentence_text"] == "sentence ES2015a.d01"
        assert d01["evidence_text"] == "evidence ES2015a.d01"
        assert (d01["gm_status"], d01["gm_object"], d01["gm_notes"]) == (
            "decision",
            "pantalla",
            "n-gm",
        )
        assert (d01["gv_object"], d01["gv_content"]) == ("otro objeto", "otro contenido")
        p001 = candidates[0]
        assert p001["earlier_text"] == "earlier ES2015.p001"
        assert (p001["gm_relation"], p001["gm_notes"], p001["gv_relation"]) == (
            "refina",
            "gm-note",
            "refina",
        )

    def test_split_summarises_children_only_when_compuesta(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions, _ = _written(plan, series)
        d03 = decisions[2]
        assert d03["gm_split"] == (
            "ES2015a.d03-1 decision (pantalla LCD: no incluir una pantalla LCD); "
            "ES2015a.d03-2 no_decision"
        )
        assert d03["gv_split"] == "ES2015a.d03-1 decision (x: y); ES2015a.d03-2 no_decision"
        assert decisions[0]["gm_split"] == ""
        assert decisions[3]["gv_split"] == ""  # gv did not mark d04 as compuesta
        assert decisions[3]["gm_split"] != ""


class TestAcuerdo:
    def test_decisions_acuerdo(self, plan: AnnotationPlan, series: WorkspacePaths) -> None:
        decisions, _ = _written(plan, series)
        assert [r["acuerdo"] for r in decisions] == [
            "si",  # same status
            "no",  # decision vs no_decision
            "si",  # both compuesta, same child statuses in order
            "no",  # compuesta vs decision
            "no",  # both compuesta, different child statuses
        ]

    def test_candidates_acuerdo_needs_relation_and_direction(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _, candidates = _written(plan, series)
        assert [r["acuerdo"] for r in candidates] == ["si", "no", "no"]

    def test_unannotated_rows_are_not_agreement(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        for who in ("gm", "gv"):
            write_csv(
                series.relations_dir / f"ES2015.candidates.{who}.csv",
                _CANDIDATE_COLUMNS,
                [_pair("ES2015.p001")],
            )
        _, candidates = _written(plan, series)
        assert candidates[0]["acuerdo"] == "no"
        assert candidates[0]["adjudicator"] == ""


class TestPrefill:
    def test_decisions_prefilled_only_where_humans_agree(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions, _ = _written(plan, series)
        d01 = decisions[0]
        # Object and content come from the alphabetically first annotator (gm).
        assert (d01["final_status"], d01["final_object"], d01["final_content"]) == (
            "decision",
            "pantalla",
            "sin pantalla",
        )
        assert d01["adjudicator"] == "jss"
        assert d01["razon"] == ""
        d03 = decisions[2]
        assert (d03["final_status"], d03["final_object"], d03["adjudicator"]) == (
            "compuesta",
            "",
            "jss",
        )
        for disagreeing in (decisions[1], decisions[3], decisions[4]):
            assert disagreeing["final_status"] == ""
            assert disagreeing["final_object"] == ""
            assert disagreeing["final_content"] == ""
            assert disagreeing["razon"] == ""
            assert disagreeing["adjudicator"] == ""

    def test_candidates_prefilled_only_where_humans_agree(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _, candidates = _written(plan, series)
        assert (
            candidates[0]["final_relation"],
            candidates[0]["final_direction_ok"],
            candidates[0]["adjudicator"],
        ) == ("refina", "si", "jss")
        for disagreeing in candidates[1:]:
            assert disagreeing["final_relation"] == ""
            assert disagreeing["final_direction_ok"] == ""
            assert disagreeing["razon"] == ""
            assert disagreeing["adjudicator"] == ""

    def test_no_markdown_log_is_written(self, plan: AnnotationPlan, series: WorkspacePaths) -> None:
        write_adjudication_csvs(plan, "ES2015", paths=series)
        assert not list(series.relations_dir.glob("*.md"))
        assert not list(series.decisions_dir.glob("*.md"))


class TestOverwriteProtection:
    def test_regenerating_an_untouched_file_is_allowed(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        write_adjudication_csvs(plan, "ES2015", paths=series)
        write_adjudication_csvs(plan, "ES2015", paths=series)  # must not raise

    @pytest.mark.parametrize(
        ("which", "column", "value"),
        [
            ("decisions", "razon", "porque sí"),
            ("decisions", "final_status", "decision"),  # fills a disagreement row
            ("candidates", "razon", "criterio"),
            ("candidates", "final_relation", "revierte"),
        ],
    )
    def test_refuses_to_clobber_verdicts(
        self,
        plan: AnnotationPlan,
        series: WorkspacePaths,
        which: str,
        column: str,
        value: str,
    ) -> None:
        decisions_path, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=series)
        target = decisions_path if which == "decisions" else candidates_path
        rows = read_csv(target)
        rows[1][column] = value
        write_csv(target, tuple(rows[0].keys()), rows)
        before = target.read_text(encoding="utf-8")

        with pytest.raises(FileExistsError, match="ES2015"):
            write_adjudication_csvs(plan, "ES2015", paths=series)
        assert target.read_text(encoding="utf-8") == before

    def test_changing_a_prefilled_value_also_counts(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = write_adjudication_csvs(plan, "ES2015", paths=series)
        rows = read_csv(decisions_path)
        rows[0]["final_content"] = "editado por el adjudicador"
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        with pytest.raises(FileExistsError):
            write_adjudication_csvs(plan, "ES2015", paths=series)

    def test_child_rows_added_by_the_adjudicator_count_as_verdicts(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = write_adjudication_csvs(plan, "ES2015", paths=series)
        rows = read_csv(decisions_path)
        rows.insert(4, {**rows[3], "decision_id": "ES2015a.d04-1", "final_status": "decision"})
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        with pytest.raises(FileExistsError):
            write_adjudication_csvs(plan, "ES2015", paths=series)

    def test_force_overwrites(self, plan: AnnotationPlan, series: WorkspacePaths) -> None:
        decisions_path, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=series)
        rows = read_csv(candidates_path)
        rows[1]["razon"] = "x"
        write_csv(candidates_path, tuple(rows[0].keys()), rows)
        write_adjudication_csvs(plan, "ES2015", paths=series, force=True)
        assert read_csv(candidates_path)[1]["razon"] == ""
        assert decisions_path.exists()


class TestMissingInputs:
    def test_fewer_than_two_annotators_fails_clearly(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        (series.relations_dir / "ES2015.candidates.gv.csv").unlink()
        with pytest.raises(FileNotFoundError, match="ES2015"):
            write_adjudication_csvs(plan, "ES2015", paths=series)

    def test_missing_decision_file_of_an_annotator_fails_clearly(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        (series.decisions_dir / "ES2015.decisions.gv.csv").unlink()
        with pytest.raises(FileNotFoundError, match="decisions"):
            write_adjudication_csvs(plan, "ES2015", paths=series)

    def test_missing_base_file_fails_clearly(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        (series.decisions_dir / "ES2015.decisions.csv").unlink()
        with pytest.raises(FileNotFoundError, match=r"ES2015\.decisions\.csv"):
            write_adjudication_csvs(plan, "ES2015", paths=series)


# --- glob safety ---------------------------------------------------------------------------


class TestGlobSafety:
    def test_annotator_csvs_excludes_the_adjudicated_suffix(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        write_adjudication_csvs(plan, "ES2015", paths=series)
        found = annotator_csvs(series.relations_dir, "ES2015", "candidates")
        assert [p.name for p in found] == [
            "ES2015.candidates.gm.csv",
            "ES2015.candidates.gv.csv",
        ]
        found = annotator_csvs(series.decisions_dir, "ES2015", "decisions")
        assert [p.name for p in found] == [
            "ES2015.decisions.gm.csv",
            "ES2015.decisions.gv.csv",
        ]

    def test_compute_series_agreement_ignores_an_adjudicated_path(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=series)
        result = compute_series_agreement(
            [*series.relations_dir.glob("ES2015.candidates.*.csv"), candidates_path]
        )
        assert (result.annotator_a, result.annotator_b) == ("gm", "gv")

    def test_adjudicated_file_with_annotation_columns_is_not_annotated_work(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        for who in ("gm", "gv"):
            for kind in ("decisions", "candidates"):
                directory = series.decisions_dir if kind == "decisions" else series.relations_dir
                (directory / f"ES2015.{kind}.{who}.csv").unlink()
        # Adjudicated files by hand, with columns that look like annotation.
        write_csv(
            series.decisions_dir / "ES2015.decisions.adjudicated.csv",
            ("decision_id", "status", "notes"),
            [{"decision_id": "ES2015a.d01", "status": "decision", "notes": "x"}],
        )
        assert series_has_annotated_work("ES2015", paths=series) == ()

    def test_validate_and_status_do_not_treat_adjudicated_as_an_annotator(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        prepare_annotator_workspace(plan, "gv", paths=series, force=True)
        before = validate_annotator(plan, "gv", paths=series, series="ES2015")
        write_adjudication_csvs(plan, "ES2015", paths=series)
        after = validate_annotator(plan, "gv", paths=series, series="ES2015")
        assert after == before
        assert [p.series_id for p in after.series] == ["ES2015"]


# --- CLI -----------------------------------------------------------------------------------


@pytest.fixture
def cli_env(
    series: WorkspacePaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> WorkspacePaths:
    monkeypatch.setattr("afg.annotation.workspace.load_annotation_config", lambda: _PLAN_CONFIG)
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", series.decisions_dir)
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", series.relations_dir)
    monkeypatch.setattr(afg_cli, "QUESTIONS_DIR", series.questions_dir)
    monkeypatch.setattr(afg_cli, "TABLES_DIR", tmp_path / "tables")
    return series


class TestAdjudicateCli:
    def test_writes_both_csvs_and_no_markdown(self, cli_env: WorkspacePaths) -> None:
        result = CliRunner().invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        assert result.exit_code == 0, result.output
        assert (cli_env.decisions_dir / "ES2015.decisions.adjudicated.csv").exists()
        assert (cli_env.relations_dir / "ES2015.candidates.adjudicated.csv").exists()
        assert not list(cli_env.relations_dir.glob("*.md"))
        assert result.output.count("Escrito") == 2

    def test_refuses_then_force_overwrites(self, cli_env: WorkspacePaths) -> None:
        runner = CliRunner()
        runner.invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        target = cli_env.relations_dir / "ES2015.candidates.adjudicated.csv"
        rows = read_csv(target)
        rows[1]["razon"] = "criterio"
        write_csv(target, tuple(rows[0].keys()), rows)

        refused = runner.invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        assert refused.exit_code == 1
        assert "--force" in refused.output
        assert read_csv(target)[1]["razon"] == "criterio"

        forced = runner.invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015", "--force"])
        assert forced.exit_code == 0
        assert read_csv(target)[1]["razon"] == ""

    def test_agreement_still_sees_exactly_two_annotators(self, cli_env: WorkspacePaths) -> None:
        runner = CliRunner()
        runner.invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        result = runner.invoke(afg_cli.app, ["gold", "agreement", "--series", "ES2015"])
        assert result.exit_code == 0, result.output
        assert "gm vs gv" in result.output
        assert "Found 3 annotator files" not in result.output
        rows = read_csv(afg_cli.TABLES_DIR / "ES2015.agreement.csv")
        assert {(r["annotator_a"], r["annotator_b"]) for r in rows} == {("gm", "gv")}

    def test_status_and_validate_ignore_the_adjudicated_files(
        self, cli_env: WorkspacePaths
    ) -> None:
        runner = CliRunner()
        prepare_annotator_workspace(load_annotation_plan(_PLAN_CONFIG), "gv", paths=cli_env)
        runner.invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        status = runner.invoke(afg_cli.app, ["gold", "status"])
        assert status.exit_code == 0, status.output
        assert "adjudicated" not in status.output
        validate = runner.invoke(
            afg_cli.app, ["gold", "validate", "--annotator", "gv", "--series", "ES2015"]
        )
        assert validate.exit_code == 0, validate.output
        assert "adjudicated" not in validate.output


# --- validate-adjudication -----------------------------------------------------------------


def _fill_verdicts(paths: WorkspacePaths, plan: AnnotationPlan) -> tuple[Path, Path]:
    """Adjudicate every row so the happy path validates."""
    decisions_path, candidates_path = write_adjudication_csvs(plan, "ES2015", paths=paths)
    rows = read_csv(decisions_path)
    header = tuple(rows[0].keys())

    def child(base: dict[str, str], n: int, status: str) -> dict[str, str]:
        row = dict.fromkeys(header, "")
        row.update(
            decision_id=f"{base['decision_id']}-{n}",
            final_status=status,
            final_object="o" if status == "decision" else "",
            final_content="c" if status == "decision" else "",
            adjudicator="jss",
        )
        return row

    out: list[dict[str, str]] = []
    for row in rows:
        if row["decision_id"] == "ES2015a.d02":
            row.update(
                final_status="decision",
                final_object="color",
                final_content="negro",
                razon="La evidencia lo confirma.",
                adjudicator="jss",
            )
        if row["decision_id"] == "ES2015a.d04":
            row.update(final_status="compuesta", razon="Son dos.", adjudicator="jss")
        if row["decision_id"] == "ES2015a.d05":
            row.update(final_status="no_decision", razon="Es una opinión.", adjudicator="jss")
        out.append(row)
        if row["final_status"] == "compuesta":
            out.extend([child(row, 1, "decision"), child(row, 2, "no_decision")])
    write_csv(decisions_path, header, out)

    candidates = read_csv(candidates_path)
    for index, row in enumerate(candidates):
        if row["acuerdo"] == "no":
            row.update(
                final_relation="refina" if index == 1 else "reafirma",
                final_direction_ok="si",
                razon="Criterio de la guía.",
                adjudicator="jss",
            )
    write_csv(candidates_path, tuple(candidates[0].keys()), candidates)
    return decisions_path, candidates_path


def _messages(paths: WorkspacePaths) -> str:
    return "\n".join(i.message for i in validate_adjudication("ES2015", paths=paths))


class TestValidateAdjudication:
    def test_fully_adjudicated_series_has_no_issues(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _fill_verdicts(series, plan)
        assert validate_adjudication("ES2015", paths=series) == []

    def test_freshly_generated_files_list_every_disagreement(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        write_adjudication_csvs(plan, "ES2015", paths=series)
        issues = validate_adjudication("ES2015", paths=series)
        rows = {(i.row_id, i.column) for i in issues}
        assert ("ES2015a.d02", "final_status") in rows
        assert ("ES2015a.d04", "final_status") in rows
        assert ("ES2015.p002", "final_relation") in rows
        assert ("ES2015.p003", "final_direction_ok") in rows
        # d03 is prefilled as compuesta but has no child rows yet.
        assert ("ES2015a.d03", "final_status") in rows
        assert "fila ES2015a.d02, columna final_status" in _messages(series)

    def test_illegal_final_status(self, plan: AnnotationPlan, series: WorkspacePaths) -> None:
        decisions_path, _ = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        rows[1]["final_status"] = "quizas"
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        assert "ES2015a.d02, columna final_status" in _messages(series)
        assert "quizas" in _messages(series)

    def test_decision_needs_object_and_content(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        rows[1]["final_object"] = ""
        rows[1]["final_content"] = ""
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        columns = {i.column for i in validate_adjudication("ES2015", paths=series)}
        assert {"final_object", "final_content"} <= columns

    def test_razon_is_mandatory_on_disagreement(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, candidates_path = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        rows[1]["razon"] = ""
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        candidates = read_csv(candidates_path)
        candidates[1]["razon"] = ""
        write_csv(candidates_path, tuple(candidates[0].keys()), candidates)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015a.d02", "razon") in found
        assert ("ES2015.p002", "razon") in found

    def test_razon_is_mandatory_for_sin_soporte_even_with_agreement(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        rows[0]["final_status"] = "sin_soporte"
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015a.d01", "razon") in found

    def test_adjudicator_is_required_on_filled_rows(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, candidates_path = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        rows[0]["adjudicator"] = ""
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        candidates = read_csv(candidates_path)
        candidates[0]["adjudicator"] = ""
        write_csv(candidates_path, tuple(candidates[0].keys()), candidates)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015a.d01", "adjudicator") in found
        assert ("ES2015.p001", "adjudicator") in found

    def test_compuesta_needs_two_consecutive_children(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = _fill_verdicts(series, plan)
        rows = [r for r in read_csv(decisions_path) if r["decision_id"] != "ES2015a.d04-2"]
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015a.d04", "final_status") in found

    def test_compuesta_children_must_have_legal_values(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        decisions_path, _ = _fill_verdicts(series, plan)
        rows = read_csv(decisions_path)
        for row in rows:
            if row["decision_id"] == "ES2015a.d04-1":
                row["final_status"] = "decision"
                row["final_object"] = ""
        write_csv(decisions_path, tuple(rows[0].keys()), rows)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015a.d04-1", "final_object") in found

    def test_candidate_finals_must_be_legal(
        self, plan: AnnotationPlan, series: WorkspacePaths
    ) -> None:
        _, candidates_path = _fill_verdicts(series, plan)
        candidates = read_csv(candidates_path)
        candidates[1]["final_relation"] = "inventada"
        candidates[2]["final_direction_ok"] = "tal vez"
        write_csv(candidates_path, tuple(candidates[0].keys()), candidates)
        found = {(i.row_id, i.column) for i in validate_adjudication("ES2015", paths=series)}
        assert ("ES2015.p002", "final_relation") in found
        assert ("ES2015.p003", "final_direction_ok") in found

    def test_missing_files_are_reported(self, series: WorkspacePaths) -> None:
        issues = validate_adjudication("ES2015", paths=series)
        assert len(issues) == 2
        assert all(i.kind is IssueKind.MISSING_FILE for i in issues)


class TestValidateAdjudicationCli:
    def test_passes_exit_zero_when_complete(
        self, plan: AnnotationPlan, cli_env: WorkspacePaths
    ) -> None:
        _fill_verdicts(cli_env, plan)
        result = CliRunner().invoke(
            afg_cli.app, ["gold", "validate-adjudication", "--series", "ES2015"]
        )
        assert result.exit_code == 0, result.output
        assert "Sin errores" in result.output

    def test_fails_with_row_and_column(self, cli_env: WorkspacePaths) -> None:
        CliRunner().invoke(afg_cli.app, ["gold", "adjudicate", "--series", "ES2015"])
        result = CliRunner().invoke(
            afg_cli.app, ["gold", "validate-adjudication", "--series", "ES2015"]
        )
        assert result.exit_code == 1
        assert "ES2015a.d02" in result.output and "final_status" in result.output
        assert "problema(s)" in result.output

    def test_missing_files_exit_nonzero(self, cli_env: WorkspacePaths) -> None:
        result = CliRunner().invoke(
            afg_cli.app, ["gold", "validate-adjudication", "--series", "ES2015"]
        )
        assert result.exit_code == 1
        assert "afg gold adjudicate" in result.output
