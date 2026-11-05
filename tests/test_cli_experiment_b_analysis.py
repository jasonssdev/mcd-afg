"""Tests for ``afg experiment b-report | b-sample | b-human-check`` (synthetic records)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli


def _record(q: int, condition: str, run: int, *, partition: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "question_id": f"ES2015.q{q:03d}",
        "condition": condition,
        "run": run,
        "stratum": "E3_evolution",
        "partition": partition,
        "trace": {"question": f"Question {q}?"},
        "answer": {
            "question_id": f"ES2015.q{q:03d}",
            "condition": condition,
            "text": f"answer {q}",
            "cited_evidence": [
                {"meeting_id": "ES2015a", "dialogue_act_ids": ["d", "e", "f", "g"][: 1 + q % 4]}
            ],
            "abstained": False,
        },
        "verdict": {"correct": q % 2 == 0, "evidence_supported": True},
        "judge_failure": None,
        "citation_correct": True,
        "citation_precision": 1.0,
        "error": None,
    }


def _bank() -> list[Any]:
    from afg.domain.decision import EvidenceSpan
    from afg.domain.question import Question, QuestionStratum

    return [
        Question(
            id=f"ES2015.q{q:03d}",
            series_id="ES2015",
            stratum=QuestionStratum.E3_EVOLUTION,
            text="t",
            reference_answer=f"ref {q}",
            reference_evidence=(EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("d",)),),
            superseded_answer=f"old {q}",
        )
        for q in range(10)
    ]


@pytest.fixture
def out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(afg_cli, "EXPERIMENT_B_DIR", tmp_path)
    monkeypatch.setattr(afg_cli, "load_experiment_questions", lambda path: _bank())
    monkeypatch.setattr("afg.experiments.runner.default_excerpt_for", lambda q: f"P-{q.id}")
    monkeypatch.setattr(
        "afg.evaluation.passage.transcript_files_text", lambda spans: "t/ES2015a.md"
    )
    return tmp_path


def _write_run(out: Path, name: str, partition: str) -> Path:
    run = out / name
    run.mkdir()
    lines = [
        json.dumps(_record(q, c, r, partition=partition))
        for c in ("C1", "C2")
        for q in range(10)
        for r in range(3)
    ]
    (run / "respuestas.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", *args])


def test_report_refuses_development_records(out: Path) -> None:
    _write_run(out, "dev", "development")
    result = _invoke("b-report", "--run-name", "dev", "--questions", "q.csv")
    assert result.exit_code == 1
    assert "descriptive" in result.output
    assert not (out / "dev" / "analisis.json").exists()


def test_descriptive_report_is_written_apart_and_marked(out: Path) -> None:
    run = _write_run(out, "dev", "development")
    result = _invoke("b-report", "--run-name", "dev", "--descriptive", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    payload = json.loads((run / "analisis-descriptivo.json").read_text(encoding="utf-8"))
    assert payload["reportable"] is False
    assert not (run / "analisis.json").exists()


def test_report_on_evaluation_records_writes_reportable_file(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    result = _invoke("b-report", "--run-name", "ev", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    payload = json.loads((run / "analisis.json").read_text(encoding="utf-8"))
    assert payload["reportable"] is True


def _invoke_wide(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", *args], env={"COLUMNS": "300"})


def test_report_shows_citation_width_beside_citation_correct(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    result = _invoke_wide("b-report", "--run-name", "ev", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    assert "Actos citados" in result.output
    assert "Cobertura por acto" in result.output
    assert "Citas a fuentes" in result.output
    # Widths 1..4 over the 10 questions (median 2); the reference is the single act "d".
    assert "2 (1-4)" in result.output
    payload = json.loads((run / "analisis.json").read_text(encoding="utf-8"))
    cell = next(c for c in payload["cells"] if c["condition"] == "C1" and c["stratum"] == "E3")
    assert cell["citation_width"]["cited_acts_median"] == 2
    assert cell["citation_width"]["mean_act_coverage"] == pytest.approx(1.0)
    assert cell["citation_width"]["source_citations"] == 0


def test_report_requires_the_question_bank(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    result = _invoke_wide("b-report", "--run-name", "ev")
    assert result.exit_code == 1
    assert "--questions" in result.output
    assert not (run / "analisis.json").exists()


def test_unknown_run_is_an_error(out: Path) -> None:
    result = _invoke("b-report", "--run-name", "nada", "--questions", "q.csv")
    assert result.exit_code == 1


def test_sample_then_human_check_roundtrip(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    sampled = _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    assert sampled.exit_code == 0, sampled.output
    sheet, key = run / "muestra-juez.csv", run / "muestra-juez.clave.csv"
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    keys = {k["id"]: k for k in csv.DictReader(key.open(encoding="utf-8"))}
    assert len(rows) == 12  # ceil(0.2 * 30) per condition
    for row in rows:
        row["correct"] = keys[row["id"]]["judge_correct"]
        row["evidence_supported"] = keys[row["id"]]["judge_evidence_supported"]
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    checked = _invoke("b-human-check", "--run-name", "ev")
    assert checked.exit_code == 0, checked.output
    payload = json.loads((run / "juez-humano.json").read_text(encoding="utf-8"))
    assert payload["keep_automatic_judging"] is True

    again = _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    assert again.exit_code == 1  # would erase labels


def test_human_check_with_empty_sheet_is_an_error(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv")
    result = _invoke("b-human-check", "--run-name", "ev")
    assert result.exit_code == 1


def test_sample_requires_questions_so_passages_are_never_blank(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    result = CliRunner().invoke(afg_cli.app, ["experiment", "b-sample", "--run-name", "ev"])
    assert result.exit_code != 0
    assert not (out / "ev" / "muestra-juez.csv").exists()


def test_sample_passes_the_judge_passage_for_each_question(out: Path, tmp_path: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    q = tmp_path / "q.csv"
    q.write_text("x", encoding="utf-8")
    result = _invoke("b-sample", "--run-name", "ev", "--questions", str(q))
    assert result.exit_code == 0, result.output
    rows = list(csv.DictReader((run / "muestra-juez.csv").open(encoding="utf-8")))
    keys = {
        k["id"]: k for k in csv.DictReader((run / "muestra-juez.clave.csv").open(encoding="utf-8"))
    }
    for row in rows:
        assert row["pasaje_transcripcion"] == f"P-{keys[row['id']]['question_id']}"
        assert row["archivos_transcripcion"] == "t/ES2015a.md"
        assert row["reference_answer"].startswith("ref ")


def test_report_prints_h4_and_its_upper_bound(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    lines = [json.loads(x) for x in (run / "respuestas.jsonl").read_text().splitlines()]
    for line in lines:
        line["stratum"] = "E3_evolution"
        line["verdict"]["outdated"] = line["condition"] == "C1"
    (run / "respuestas.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8"
    )
    result = _invoke_wide("b-report", "--run-name", "ev", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    assert "H4 C1 en E3: desactualizadas entre las respondidas 1.00" in result.output
    assert "H4 C1 frente a C2: diferencia +1.00" in result.output
    assert "Cota superior de H4 C1 frente a C2" in result.output


def test_sample_and_human_check_cover_the_outdated_label(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    lines = [json.loads(x) for x in (run / "respuestas.jsonl").read_text().splitlines()]
    for line in lines:
        line["verdict"]["outdated"] = line["question_id"].endswith(("0", "2", "4"))
    (run / "respuestas.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8"
    )
    assert _invoke("b-sample", "--run-name", "ev", "--questions", "q.csv").exit_code == 0
    sheet, key = run / "muestra-juez.csv", run / "muestra-juez.clave.csv"
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    keys = {k["id"]: k for k in csv.DictReader(key.open(encoding="utf-8"))}
    assert all(row["respuesta_superada"].startswith("old ") for row in rows)
    for row in rows:
        row["correct"] = keys[row["id"]]["judge_correct"]
        row["evidence_supported"] = keys[row["id"]]["judge_evidence_supported"]
        row["outdated"] = keys[row["id"]]["judge_outdated"]
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    checked = _invoke_wide("b-human-check", "--run-name", "ev")
    assert checked.exit_code == 0, checked.output
    assert "outdated (H4" in checked.output
    payload = json.loads((run / "juez-humano.json").read_text(encoding="utf-8"))
    assert payload["outdated_reliable"] is True


def test_report_prints_h2_as_not_computable_without_c3(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    result = _invoke_wide("b-report", "--run-name", "ev", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    assert "H2: no calculable" in result.output
    data = json.loads((out / "ev" / "analisis.json").read_text())
    assert data["h2"]["verdict"] == "not_computable"


def test_report_includes_c0_and_labels_its_comparisons_as_secondary(out: Path) -> None:
    run = _write_run(out, "ev", "evaluation")
    lines = (run / "respuestas.jsonl").read_text(encoding="utf-8").splitlines()
    for q in range(10):
        for r in range(3):
            c0 = _record(q, "C0", r, partition="evaluation")
            c0["answer"]["cited_evidence"] = []
            c0["verdict"] = {"correct": False, "evidence_supported": False}
            c0["citation_correct"], c0["citation_precision"] = False, 0.0
            lines.append(json.dumps(c0))
    (run / "respuestas.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _invoke_wide("b-report", "--run-name", "ev", "--questions", "q.csv")

    assert result.exit_code == 0, result.output
    assert "C0" in result.output
    assert "Secundaria descriptiva (ADR 0019) C1 frente a C0 en E3" in result.output
    assert "Secundaria descriptiva (ADR 0019) C2 frente a C0 en E3" in result.output
    assert "Principal (D16) C2 frente a C1 en E3" in result.output
    payload = json.loads((run / "analisis.json").read_text(encoding="utf-8"))
    assert [c["primary"] for c in payload["comparisons"] if c["condition_b"] == "C0"] == [False] * 4
    assert "descriptive_note" in payload


def test_report_labels_verdicts_on_too_small_samples(out: Path) -> None:
    _write_run(out, "ev", "evaluation")
    result = _invoke_wide("b-report", "--run-name", "ev", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    principal = next(line for line in result.output.splitlines() if "Principal (D16)" in line)
    assert "muestra insuficiente" in principal
    assert "supported" not in principal


# --- evaluation runs must match the freeze record ------------------------------------------------


def _freeze_wired(out: Path, monkeypatch: pytest.MonkeyPatch, manifest: dict[str, Any]) -> Path:
    from afg.experiments.freeze import read_freeze_record, write_freeze_record
    from tests.freeze_fixtures import COMMIT, SERIES, make_sources

    sources = make_sources(out / "tree")
    record_path = out / "freeze.json"
    write_freeze_record(record_path, sources, series=SERIES, adr="0017", commit=COMMIT)
    record = read_freeze_record(record_path)
    monkeypatch.setattr(afg_cli, "FREEZE_PATH", record_path)
    monkeypatch.setattr("afg.experiments.freeze.code_changes_since", lambda *a, **k: [])
    run = _write_run(out, "ev-frozen", "evaluation")
    full = {
        "series": ["ES2002"],
        "conditions": ["C1", "C2"],
        "questions_sha256": record["question_bank"]["sha256"],
        "git_dirty": False,
        "git_commit": COMMIT,
        **manifest,
    }
    (run / "manifest.json").write_text(json.dumps(full), encoding="utf-8")
    return run


def test_report_of_an_evaluation_run_that_matches_the_freeze_is_reportable(
    out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _freeze_wired(out, monkeypatch, {})
    result = _invoke("b-report", "--run-name", "ev-frozen", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    assert "reportable" in result.output


@pytest.mark.parametrize(
    ("command", "extra"),
    [("b-report", ["--questions", "q.csv"]), ("b-sample", ["--questions", "q.csv"])],
)
def test_evaluation_run_with_another_bank_or_dirty_tree_is_refused(
    out: Path, monkeypatch: pytest.MonkeyPatch, command: str, extra: list[str]
) -> None:
    _freeze_wired(out, monkeypatch, {"questions_sha256": "0" * 64, "git_dirty": True})
    result = _invoke(command, "--run-name", "ev-frozen", *extra)
    text = " ".join(result.output.split())
    assert result.exit_code == 1
    assert "congelamiento" in text and "banco de preguntas" in text and "árbol" in text
    assert not (out / "ev-frozen" / "muestra-juez.csv").exists()


def test_descriptive_report_of_a_mismatched_evaluation_run_is_not_reportable(
    out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _freeze_wired(out, monkeypatch, {"git_dirty": True})
    result = _invoke("b-report", "--run-name", "ev-frozen", "--descriptive", "--questions", "q.csv")
    assert result.exit_code == 0, result.output
    assert "no es reportable" in " ".join(result.output.split())
    assert "(reportable)" not in result.output
