"""Tests for ``afg judge calibration-*`` (issue #82).

No corpus, no Ollama: the evidence resolver, the generation backend and the calibration run are
stubbed; every path is redirected to ``tmp_path``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.judge_calibration import CandidateMetrics, JudgeDecision
from afg.evaluation.judge_calibration_runner import CalibrationResult, CandidateRun
from afg.evaluation.judge_calibration_worksheet import (
    COLUMNS,
    MIN_SELECTED,
    ResolvedActs,
    load_worksheet,
    write_worksheet,
)
from afg.evaluation.metrics import BootstrapCI

DECISIONS = (
    "decision_id,meeting_id,source_sentence_id,sentence_text,evidence_text,final_status,"
    "final_object,final_content\n"
    "ES2015a.d01,ES2015a,ES2015a.e.s1,Price is 25.,A: 25,decision,precio,fijar 25\n"
)
RELATIONS = "pair_id,earlier_decision_id,later_decision_id,earlier_text,later_text,final_relation\n"


def _out(result: Any) -> str:
    return " ".join(result.output.split())  # the console wraps long lines


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    decisions = tmp_path / "decisions"
    relations = tmp_path / "relations"
    decisions.mkdir()
    relations.mkdir()
    (decisions / "ES2015.decisions.adjudicated.csv").write_text(DECISIONS, encoding="utf-8")
    (relations / "ES2015.candidates.adjudicated.csv").write_text(RELATIONS, encoding="utf-8")
    worksheet = tmp_path / "ES2015.preguntas.csv"
    calibration = tmp_path / "calibracion-juez.csv"
    results = tmp_path / "resultados.json"
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", decisions)
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", relations)
    monkeypatch.setattr(afg_cli, "WORKSHEET_PATH", worksheet)
    monkeypatch.setattr(afg_cli, "CALIBRATION_PATH", calibration)
    monkeypatch.setattr(afg_cli, "RESULTS_PATH", results)
    monkeypatch.setattr(
        afg_cli,
        "make_act_resolver",
        lambda ami_root, transcripts_dir=None: (
            lambda meeting, sentence: ResolvedActs(ids=(f"{meeting}.A.dialog-act.x.1",), dropped=0)
        ),
    )
    return {"worksheet": worksheet, "calibration": calibration, "results": results}


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["judge", *args])


def _selected_rows() -> list[dict[str, str]]:
    rows = []
    for i in range(1, MIN_SELECTED + 1):
        stratum = "E4" if i > MIN_SELECTED - 2 else "E1"
        row = dict.fromkeys(COLUMNS, "")
        row.update(
            fila=str(i),
            origen=f"ES2015a.d{i:02d}",
            reunion="ES2015a",
            usar="si",
            stratum=stratum,
            pregunta=f"Question {i}?",
            respuesta_referencia="" if stratum == "E4" else "Answer.",
            reference_evidence="" if stratum == "E4" else "ES2015a:ES2015a.A.dialog-act.x.1",
        )
        rows.append(row)
    return rows


class TestInit:
    def test_creates_the_prefilled_worksheet_and_reports_counts(
        self, paths: dict[str, Path]
    ) -> None:
        result = _invoke("calibration-init")
        assert result.exit_code == 0, result.output
        rows = load_worksheet(paths["worksheet"])
        assert [r["origen"] for r in rows][:1] == ["ES2015a.d01"]
        assert rows[0]["reference_evidence"] == "ES2015a:ES2015a.A.dialog-act.x.1"
        message = _out(result)
        assert "1 decisiones" in message and "0 pares" in message and "6 filas E4" in message
        assert "Evidencia sin resolver: 0" in message

    def test_refuses_to_overwrite_human_work_unless_forced(self, paths: dict[str, Path]) -> None:
        _invoke("calibration-init")
        rows = load_worksheet(paths["worksheet"])
        rows[0]["pregunta"] = "What is the price?"
        write_worksheet(paths["worksheet"], rows)
        before = paths["worksheet"].read_bytes()

        refused = _invoke("calibration-init")

        assert refused.exit_code == 1 and "--force" in _out(refused)
        assert paths["worksheet"].read_bytes() == before
        assert _invoke("calibration-init", "--force").exit_code == 0
        assert load_worksheet(paths["worksheet"])[0]["pregunta"] == ""


class TestValidate:
    def test_fresh_worksheet_says_nothing_is_selected(self, paths: dict[str, Path]) -> None:
        _invoke("calibration-init")
        result = _invoke("calibration-validate")
        assert result.exit_code == 1
        assert "no hay ninguna fila seleccionada" in _out(result)

    def test_missing_worksheet_points_to_init(self, paths: dict[str, Path]) -> None:
        result = _invoke("calibration-validate")
        assert result.exit_code == 1 and "calibration-init" in _out(result)

    def test_valid_selection_passes_and_prints_the_strata(self, paths: dict[str, Path]) -> None:
        write_worksheet(paths["worksheet"], _selected_rows())
        result = _invoke("calibration-validate")
        assert result.exit_code == 0, result.output
        assert "E1: 18" in _out(result) and "E4: 2" in _out(result)


class TestValidateSizeWarning:
    def test_sixteen_to_nineteen_rows_pass_with_a_warning(self, paths: dict[str, Path]) -> None:
        rows = _selected_rows()
        write_worksheet(paths["worksheet"], rows[:16] + rows[-2:])
        result = _invoke("calibration-validate")
        assert result.exit_code == 0, result.output
        assert "recomendado" in _out(result)


class FakeGenerationBackend:
    def generate(self, system: str, user: str, **kwargs: Any) -> str:
        return "Answer."


class TestAnswers:
    @pytest.fixture(autouse=True)
    def _transcripts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "transcripts"
        root.mkdir()
        with (root / "ES2015a.jsonl").open("w", encoding="utf-8") as handle:
            for i in range(30):
                handle.write(
                    json.dumps(
                        {
                            "meeting_id": "ES2015a",
                            "turn_index": i,
                            "speaker": "A",
                            "role": "PM",
                            "text": f"turn {i}",
                            "start": 0.0,
                            "end": 1.0,
                            "char_start": 0,
                            "char_end": 1,
                            "dialogue_act_ids": [f"ES2015a.A.dialog-act.x.{i + 1}"],
                        }
                    )
                    + "\n"
                )
        monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", root)
        monkeypatch.setattr(afg_cli, "OllamaGenerationBackend", FakeGenerationBackend)

    def test_refuses_an_invalid_selection_without_generating(self, paths: dict[str, Path]) -> None:
        _invoke("calibration-init")
        result = _invoke("calibration-answers")
        assert result.exit_code == 1
        assert not paths["calibration"].exists()

    def test_generates_two_answers_per_selected_question(self, paths: dict[str, Path]) -> None:
        write_worksheet(paths["worksheet"], _selected_rows())
        result = _invoke("calibration-answers")
        assert result.exit_code == 0, result.output
        with paths["calibration"].open(newline="", encoding="utf-8") as handle:
            lines = list(csv.reader(handle))
        assert len(lines) == 1 + 2 * MIN_SELECTED
        assert "correct" in lines[0] and "evidence_supported" in lines[0]
        assert "si/no" in _out(result)


def _run_result() -> CalibrationResult:
    metrics = CandidateMetrics(
        model="m",
        kappa_correct=BootstrapCI(0.8, 0.7, 0.9, 0.95, 100),
        position_consistency=1.0,
        seed_consistency=1.0,
        e4_accuracy=1.0,
        json_valid_rate=1.0,
        verbosity_flip_rate=0.0,
        latency_seconds=1.0,
    )
    return CalibrationResult(
        runs=(CandidateRun(metrics=metrics, evidence_supported=None, calls=3, failures=0),),
        decision=JudgeDecision(selected="m", failures={"m": ()}),
    )


class TestRun:
    def test_without_a_calibration_set_points_to_the_previous_step(
        self, paths: dict[str, Path]
    ) -> None:
        result = _invoke("calibration-run")
        assert result.exit_code == 1 and "calibration-answers" in _out(result)

    def test_refuses_unlabeled_items_and_says_how_many(
        self, paths: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from afg.evaluation.judge_calibration_set import COLUMNS as SET_COLUMNS

        row = dict.fromkeys(SET_COLUMNS, "")
        row.update(
            id="ES2015.q001.grounded",
            series_id="ES2015",
            stratum="E1_point_fact",
            question="q",
            reference_answer="r",
            reference_evidence="ES2015a:ES2015a.A.dialog-act.x.1",
            answer_text="a",
            answer_abstained="false",
            adjudicated="false",
        )
        paths["calibration"].write_text(
            ",".join(SET_COLUMNS) + "\n" + ",".join(row[c] for c in SET_COLUMNS) + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(afg_cli, "run_calibration", lambda *a, **k: pytest.fail("ran"))
        result = _invoke("calibration-run")
        assert result.exit_code == 1
        assert "1 de 1" in _out(result) or "sin etiquetas" in _out(result)

    def test_judge_candidates_get_the_stored_excerpt_the_labeler_saw(
        self, paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from afg.evaluation.judge_calibration_set import COLUMNS as SET_COLUMNS

        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        (transcripts / "ES2015a.jsonl").write_text(
            json.dumps(
                {
                    "meeting_id": "ES2015a",
                    "turn_index": 0,
                    "speaker": "A",
                    "role": "PM",
                    "text": "twenty five euros",
                    "start": 0.0,
                    "end": 1.0,
                    "char_start": 0,
                    "char_end": 1,
                    "dialogue_act_ids": ["ES2015a.A.dialog-act.x.1"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", transcripts)
        row = dict.fromkeys(SET_COLUMNS, "")
        row.update(
            id="ES2015.q001.grounded",
            series_id="ES2015",
            stratum="E1_point_fact",
            question="q",
            reference_answer="r",
            reference_evidence="ES2015a:ES2015a.A.dialog-act.x.1",
            answer_text="a",
            pasaje_transcripcion="STORED PASSAGE",
            answer_abstained="false",
            correct="si",
            evidence_supported="si",
            adjudicated="false",
        )
        paths["calibration"].write_text(
            ",".join(SET_COLUMNS) + "\n" + ",".join(row[c] for c in SET_COLUMNS) + "\n",
            encoding="utf-8",
        )
        seen: dict[str, Any] = {}

        def fake_run(items: Any, **kwargs: Any) -> CalibrationResult:
            seen["excerpt"] = kwargs["excerpt_for"](items[0])
            return _run_result()

        monkeypatch.setattr(afg_cli, "run_calibration", fake_run)
        result = _invoke("calibration-run")
        assert result.exit_code == 0
        assert seen["excerpt"] == "STORED PASSAGE"
        assert "sin pasaje guardado" not in _out(result)

    def test_older_files_without_the_excerpt_column_get_it_rebuilt_and_the_cli_says_so(
        self, paths: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from afg.evaluation.judge_calibration_set import LOADED_COLUMNS as SET_COLUMNS

        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        (transcripts / "ES2015a.jsonl").write_text(
            json.dumps(
                {
                    "meeting_id": "ES2015a",
                    "turn_index": 0,
                    "speaker": "A",
                    "role": "PM",
                    "text": "twenty five euros",
                    "start": 0.0,
                    "end": 1.0,
                    "char_start": 0,
                    "char_end": 1,
                    "dialogue_act_ids": ["ES2015a.A.dialog-act.x.1"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", transcripts)
        row = dict.fromkeys(SET_COLUMNS, "")
        row.update(
            id="ES2015.q001.grounded",
            series_id="ES2015",
            stratum="E1_point_fact",
            question="q",
            reference_answer="r",
            reference_evidence="ES2015a:ES2015a.A.dialog-act.x.1",
            answer_text="a",
            answer_abstained="false",
            correct="si",
            evidence_supported="si",
            adjudicated="false",
        )
        paths["calibration"].write_text(
            ",".join(SET_COLUMNS) + "\n" + ",".join(row[c] for c in SET_COLUMNS) + "\n",
            encoding="utf-8",
        )
        seen: dict[str, Any] = {}

        def fake_run(items: Any, **kwargs: Any) -> CalibrationResult:
            seen["excerpt"] = kwargs["excerpt_for"](items[0])
            return _run_result()

        monkeypatch.setattr(afg_cli, "run_calibration", fake_run)
        result = _invoke("calibration-run")
        assert result.exit_code == 0
        assert "sin pasaje guardado" in _out(result)
        assert seen["excerpt"] == "[ES2015a]\nPM: twenty five euros"

    def test_runs_and_stores_the_results(
        self, paths: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from afg.evaluation.judge_calibration_set import COLUMNS as SET_COLUMNS

        row = dict.fromkeys(SET_COLUMNS, "")
        row.update(
            id="ES2015.q001.grounded",
            series_id="ES2015",
            stratum="E1_point_fact",
            question="q",
            reference_answer="r",
            reference_evidence="ES2015a:ES2015a.A.dialog-act.x.1",
            answer_text="a",
            answer_abstained="false",
            correct="si",
            evidence_supported="no",
            adjudicated="false",
        )
        paths["calibration"].write_text(
            ",".join(SET_COLUMNS) + "\n" + ",".join(row[c] for c in SET_COLUMNS) + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(afg_cli, "run_calibration", lambda *a, **k: _run_result())
        result = _invoke("calibration-run")
        assert result.exit_code == 0, result.output
        stored = json.loads(paths["results"].read_text(encoding="utf-8"))
        assert stored["decision"]["selected"] == "m" and stored["n_items"] == 1
        assert "notebook" in _out(result).lower()
