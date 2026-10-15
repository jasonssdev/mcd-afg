"""State-driven ``afg gold setup`` / ``status`` / ``validate`` (audit findings C1 and C2).

Plan used here: phase 1 is ES1 then ES4, but jss has only released ES1 (``released_series``).
gv also annotates ES3 alone in phase 3 and owns the recall sample of ES3; gm writes the
question bank, gv validates it. Everything lives under ``tmp_path``; nothing needs the corpus.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.annotation.workspace import (
    TaskKind,
    WorkspacePaths,
    load_annotation_plan,
    prepare_annotator_workspace,
)
from afg.corpus.download import DownloadResult

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
_BANK_COLUMNS = (
    "id",
    "series_id",
    "stratum",
    "text",
    "reference_answer",
    "reference_evidence",
    "author",
    "validated_by",
    "validation_notes",
)


def _config(released: list[str] | None) -> dict[str, Any]:
    section: dict[str, Any] = {
        "adjudicator": "jss",
        "phase1_series": ["ES1", "ES4"],
        "phase2_series": [],
        "recall_sample": {"owner": "gv", "series": ["ES3"], "n": 1, "seed": 1},
        "question_bank": {
            "author": "gm",
            "validator": "gv",
            "questions_per_stratum": 2,
            "rows_per_stratum": {"E3_evolution": 3},
        },
        "annotators": [
            {
                "initials": "gv",
                "name": "Germán Vega",
                "role": "annotator",
                "github": "Vega-German",
                "phase3_series": ["ES3"],
            },
            {
                "initials": "gm",
                "name": "Gustavo Martínez",
                "role": "annotator",
                "github": "gmartinezbMCD",
                "phase3_series": [],
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
    if released is not None:
        section["released_series"] = released
    return {"annotation": section}


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _decision(decision_id: str) -> dict[str, str]:
    meeting = decision_id.split(".")[0]
    return {
        "decision_id": decision_id,
        "meeting_id": meeting,
        "source_sentence_id": f"{meeting}.x.s.1",
        "sentence_text": "They decide.",
        "evidence_da_count": "1",
        "evidence_text": "A: ok",
        "machine_flags": "",
    }


def _pair(pair_id: str) -> dict[str, str]:
    return {
        "pair_id": pair_id,
        "earlier_decision_id": "a",
        "later_decision_id": "b",
        "earlier_sentence_id": "s1",
        "later_sentence_id": "s2",
        "earlier_text": "t1",
        "later_text": "t2",
        "blocker_score": "0.4",
    }


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkspacePaths:
    decisions = tmp_path / "decisions"
    relations = tmp_path / "relations"
    questions = tmp_path / "questions"
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", decisions)
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", relations)
    monkeypatch.setattr(afg_cli, "QUESTIONS_DIR", questions)
    monkeypatch.setattr(afg_cli, "AMI_DIR", tmp_path / "ami")
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", tmp_path / "transcripts")
    monkeypatch.setattr(afg_cli, "TABLES_DIR", tmp_path / "reports")
    (tmp_path / "ami" / "words").mkdir(parents=True)
    (tmp_path / "ami" / "words" / "X.A.words.xml").write_text("<nite/>", encoding="utf-8")
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "ya.md").write_text("x", encoding="utf-8")
    paths = WorkspacePaths(
        decisions_dir=decisions, relations_dir=relations, questions_dir=questions
    )
    for sid, n_dec in (("ES1", 2), ("ES3", 1), ("ES4", 1)):
        _write_csv(
            paths.decisions_dir / f"{sid}.decisions.csv",
            _DECISION_COLUMNS,
            [_decision(f"{sid}a.d{i:02d}") for i in range(1, n_dec + 1)],
        )
        _write_csv(
            paths.relations_dir / f"{sid}.candidates.csv", _CANDIDATE_COLUMNS, [_pair(f"{sid}.p1")]
        )
    _write_csv(paths.relations_dir / "ES3.recall-sample.csv", _CANDIDATE_COLUMNS, [_pair("ES3.r1")])
    return paths


def _use(monkeypatch: pytest.MonkeyPatch, released: list[str] | None) -> None:
    cfg = _config(released)
    monkeypatch.setattr("afg.annotation.workspace.load_annotation_config", lambda: cfg)


def _run(*args: str, input: str | None = None) -> Any:
    return CliRunner().invoke(afg_cli.app, list(args), input=input)


def _flat(output: str) -> str:
    return " ".join(output.split())


def _fill_decisions(path: Path, who: str, *, count: int | None = None) -> None:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    for row in rows[: count if count is not None else len(rows)]:
        row.update(status="no_decision", annotator=who)
    _write_csv(path, _DECISION_COLUMNS, rows)


def _fill_candidates(path: Path, who: str) -> None:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    for row in rows:
        row.update(relation="introduce", direction_ok="si", confidence="alta", annotator=who)
    _write_csv(path, _CANDIDATE_COLUMNS, rows)


def _adjudicate(paths: WorkspacePaths, sid: str) -> None:
    _write_csv(paths.adjudicated(TaskKind.DECISIONS, sid), ("decision_id",), [{"decision_id": "x"}])
    _write_csv(paths.adjudicated(TaskKind.CANDIDATES, sid), ("pair_id",), [{"pair_id": "x"}])


class TestPlanReleased:
    def test_absent_field_means_everything_is_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        plan = load_annotation_plan(_config(None))
        assert plan.is_released("ES4")

    def test_listed_series_only(self) -> None:
        plan = load_annotation_plan(_config(["ES1"]))
        assert plan.is_released("ES1")
        assert not plan.is_released("ES4")


class TestPrepareSkipsUnreleased:
    def test_no_files_for_series_jss_has_not_opened(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))

        outcome = prepare_annotator_workspace(plan, "gv", paths=env)

        assert [f.series_id for f in outcome.created] == ["ES1", "ES1"]
        assert not (env.decisions_dir / "ES4.decisions.gv.csv").exists()
        assert not (env.decisions_dir / "ES3.decisions.gv.csv").exists()
        assert not (env.relations_dir / "ES3.recall-sample.gv.csv").exists()
        assert {f.series_id for f in outcome.not_open} == {"ES4", "ES3"}


class TestValidateWithReleases:
    def test_default_sweep_ignores_unreleased_series(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        prepare_annotator_workspace(load_annotation_plan(_config(["ES1"])), "gv", paths=env)

        result = _run("gold", "validate", "--annotator", "gv")

        assert result.exit_code == 0, result.output
        assert "ES4" not in result.output.split("Sin errores")[0]

    def test_explicit_unreleased_series_says_not_yet(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])

        result = _run("gold", "validate", "--annotator", "gv", "--series", "ES4")

        assert result.exit_code == 1
        assert "aún no" in _flat(result.output)
        assert "jss" in result.output


class TestSetupNextStep:
    def test_names_the_released_active_series_and_labels_the_rest_as_not_yet(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])

        result = _run("gold", "setup", "--annotator", "gv")

        flat = _flat(result.output)
        assert result.exit_code == 0, result.output
        assert "ES1.decisions.gv.csv" in flat
        assert "aún no" in flat
        assert "ES4" in flat  # listed as not yet open
        assert not (env.decisions_dir / "ES4.decisions.gv.csv").exists()

    def test_when_the_open_series_is_adjudicated_says_to_wait_for_jss_not_to_reopen_it(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        prepare_annotator_workspace(load_annotation_plan(_config(["ES1"])), "gv", paths=env)
        _fill_decisions(env.decisions_dir / "ES1.decisions.gv.csv", "gv")
        _fill_candidates(env.relations_dir / "ES1.candidates.gv.csv", "gv")
        _adjudicate(env, "ES1")

        result = _run("gold", "setup", "--annotator", "gv")

        flat = _flat(result.output)
        assert result.exit_code == 0, result.output
        after = flat.split("Qué hacer ahora")[1]
        assert "jss" in after
        assert "ES4" in after
        assert "ES1.decisions.gv.csv" not in after

    def test_licence_prompt_is_spanish_without_maintainer_notes_and_both_sizes(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _use(monkeypatch, ["ES1"])
        import shutil

        shutil.rmtree(tmp_path / "ami")
        calls: list[Path] = []

        def fake_download(dest: Path) -> DownloadResult:
            calls.append(dest)
            (dest / "words").mkdir(parents=True)
            (dest / "words" / "X.A.words.xml").write_text("<nite/>", encoding="utf-8")
            return DownloadResult(
                archive_path=dest / "z.zip", extracted_to=dest, bytes_downloaded=1
            )

        monkeypatch.setattr(afg_cli, "download_annotations", fake_download)
        monkeypatch.setattr(afg_cli, "discover_meeting_ids", lambda *_a, **_k: [])
        result = _run("gold", "setup", "--annotator", "gv", input="n\n")

        flat = _flat(result.output)
        assert "Licencia" in flat
        assert "CC BY 4.0" in flat
        assert "22 MB" in flat and "228 MB" in flat
        for forbidden in ("Verified", "do not present", "Licence:", "Proceed", "Approximate"):
            assert forbidden not in flat
        assert not calls


class TestStatusStates:
    def _plan_state(self, monkeypatch: pytest.MonkeyPatch, released: list[str]) -> None:
        _use(monkeypatch, released)
        plan = load_annotation_plan(_config(released))
        assert plan.annotator("gv")

    def test_unreleased_series_is_pendiente_aun_no_and_next_line_is_present(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan_state(monkeypatch, ["ES1"])
        prepare_annotator_workspace(load_annotation_plan(_config(["ES1"])), "gv", paths=env)

        result = _run("gold", "status", "--annotator", "gv")

        flat = _flat(result.output)
        assert result.exit_code == 0, result.output
        assert "pendiente (aún no)" in flat
        assert result.output.strip().splitlines()[-1].startswith("Siguiente:")
        assert "por empezar" in flat

    def test_in_progress_then_ready_then_adjudicated(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan_state(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        dec = env.decisions_dir / "ES1.decisions.gv.csv"
        cand = env.relations_dir / "ES1.candidates.gv.csv"

        _fill_decisions(dec, "gv", count=1)
        assert "en curso" in _flat(_run("gold", "status", "--annotator", "gv").output)

        _fill_decisions(dec, "gv")
        _fill_candidates(cand, "gv")
        ready = _flat(_run("gold", "status", "--annotator", "gv").output)
        assert "lista para entregar" in ready
        assert "Siguiente: " in ready and "ES1" in ready.split("Siguiente:")[1]

        _adjudicate(env, "ES1")
        done = _flat(_run("gold", "status", "--annotator", "gv").output)
        assert "adjudicada" in done
        assert "jss" in done.split("Siguiente:")[1]

    def test_children_of_compuesta_rows_are_explained(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan_state(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        # gv splits ES1a.d01 into two parts: the base keeps the parent, the copy adds children.
        base = env.decisions_dir / "ES1.decisions.csv"
        rows = list(csv.DictReader(base.open(newline="", encoding="utf-8")))
        extra = {**rows[0], "decision_id": "ES1a.d01-1"}
        extra2 = {**rows[0], "decision_id": "ES1a.d01-2"}
        _write_csv(base, _DECISION_COLUMNS, [*rows, extra, extra2])
        _write_csv(
            env.decisions_dir / "ES1.decisions.gv.csv",
            _DECISION_COLUMNS,
            [{**r, "annotator": "gv"} for r in [*rows, extra, extra2]],
        )

        flat = _flat(_run("gold", "status", "--annotator", "gv").output)

        assert "4 filas (2 originales + 2 partes de compuestas)" in flat

    def test_tarea_c_progress_for_the_recall_owner(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan_state(monkeypatch, ["ES1", "ES3"])
        plan = load_annotation_plan(_config(["ES1", "ES3"]))
        prepare_annotator_workspace(plan, "gv", paths=env)

        before = _flat(_run("gold", "status", "--annotator", "gv").output)
        assert "Tarea C" in before
        assert "ES3" in before.split("Tarea C")[1]
        assert "pendiente (aún no)" in before.split("Tarea C")[1]

        _fill_decisions(env.decisions_dir / "ES3.decisions.gv.csv", "gv")
        _fill_candidates(env.relations_dir / "ES3.candidates.gv.csv", "gv")
        after = _flat(_run("gold", "status", "--annotator", "gv").output)
        assert "0/1" in after.split("Tarea C")[1]
        assert "por empezar" in after.split("Tarea C")[1]

    def test_question_bank_progress_for_author_and_validator(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._plan_state(monkeypatch, [])
        rows = []
        n = 0
        for stratum, count in (
            ("E1_point_fact", 2),
            ("E2_current_state", 2),
            ("E3_evolution", 3),
            ("E4_unanswerable", 2),
        ):
            for _ in range(count):
                n += 1
                rows.append(
                    {"id": f"q{n:03d}", "stratum": stratum, "author": "gm"}
                    | ({"text": "¿Qué?", "series_id": "ES1"} if n <= 3 else {})
                    | ({"validated_by": "gv"} if n == 1 else {})
                )
        _write_csv(env.question_bank, _BANK_COLUMNS, rows)

        gm = _flat(_run("gold", "status", "--annotator", "gm").output)
        assert "Banco de preguntas" in gm
        assert "E1_point_fact 2/2" in gm
        assert "E3_evolution 0/2 (hasta 3)" in gm
        assert "Siguiente:" in gm and "banco" in gm.split("Siguiente:")[1]

        gv = _flat(_run("gold", "status", "--annotator", "gv").output)
        assert "validadas 1" in gv
        assert "banco" in gv.split("Siguiente:")[1].lower()


class TestEvidenceCommandsAreOne:
    """``gold evidence`` (word-level) and ``gold evidencia`` (dialogue acts) were confusing
    twins; the old name is now a hidden alias of the new one."""

    def test_old_name_is_hidden_from_help_and_new_name_explains_both_uses(self) -> None:
        help_text = _flat(_run("gold", "--help").output)
        assert "evidencia" in help_text
        assert " evidence " not in help_text

        detail = _flat(_run("gold", "evidencia", "--help").output)
        assert "Tarea A" in detail and "banco de preguntas" in detail

    def test_old_name_forwards_and_fails_in_spanish_when_transcripts_are_missing(
        self, env: WorkspacePaths
    ) -> None:
        result = _run("gold", "evidence", "--meeting", "ES1a", "--term", "remote")

        flat = _flat(result.output)
        assert result.exit_code == 1
        assert "gold evidencia" in flat
        assert "uv run afg gold setup" in flat
        assert "No words" not in flat

    def test_unknown_meeting_lists_the_valid_meetings_of_the_series(
        self, env: WorkspacePaths, tmp_path: Path
    ) -> None:
        for name in ("ES1a", "ES1b"):
            (tmp_path / "transcripts" / f"{name}.jsonl").write_text("", encoding="utf-8")

        result = _run("gold", "evidence", "--meeting", "ES1z", "--term", "remote")

        flat = _flat(result.output)
        assert result.exit_code == 1
        assert "ES1a, ES1b" in flat
        assert "words" not in flat


class TestBankProgressAndRowCounts:
    def test_missing_bank_has_no_progress(self, tmp_path: Path) -> None:
        from afg.experiments.question_bank import question_bank_progress

        assert question_bank_progress(tmp_path / "no.csv", minimum=2, rows_per_stratum={}) is None

    def test_decision_row_counts_split_originals_from_compuesta_parts(self, tmp_path: Path) -> None:
        from afg.annotation.workspace import decision_row_counts

        path = tmp_path / "d.csv"
        _write_csv(
            path,
            _DECISION_COLUMNS,
            [_decision("ES1a.d01"), _decision("ES1a.d01-1"), _decision("ES1a.d02")],
        )

        assert decision_row_counts(path) == (2, 1)
        assert decision_row_counts(tmp_path / "missing.csv") == (0, 0)
