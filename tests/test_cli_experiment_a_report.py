"""Tests for ``afg experiment a-report``. No model: the similarity is a fake."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.reference import ReferenceSet
from tests.relations_workspace import (
    ALPHA,
    BETA,
    reference_decision,
    text_similarity,
    write_transcripts,
)

RUN = "lote"


def _record(run: int, found: list[tuple[str, tuple[str, str]]]) -> str:
    decisions = [
        {
            "id": f"decisions/{i}",
            "series_id": "ES2015",
            "meeting_id": f"ES2015{m}",
            "decision_object": text[0],
            "content": text[1],
            "status": "accepted",
            "evidence": {"meeting_id": f"ES2015{m}", "dialogue_act_ids": ["x1"]},
            "annotator": None,
            "origin_meeting_ids": [],
        }
        for i, (m, text) in enumerate(found)
    ]
    return json.dumps({"series_id": "ES2015", "run": run, "decisions": decisions})


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    run_dir = tmp_path / "out" / RUN
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps({"git_commit": "abc", "openkos": {}}))
    lines = [
        _record(0, [("a", ALPHA), ("b", BETA)]),
        _record(1, [("a", ALPHA)]),
        _record(2, [("a", ALPHA), ("b", BETA)]),
    ]
    (run_dir / "extracciones.jsonl").write_text("\n".join(lines) + "\n")
    write_transcripts(tmp_path / "transcripts")
    reference = ReferenceSet(
        series_id="ES2015",
        decisions=(
            dataclasses.replace(reference_decision("ES2015a.d01", "ES2015a", *ALPHA), role="ID"),
            reference_decision("ES2015b.d01", "ES2015b", *BETA),
        ),
        source_kind="adjudicated",
    )
    languages: list[str] = []

    def load(series: str, language: str = "es") -> ReferenceSet:
        languages.append(language)
        return reference

    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", tmp_path / "out")
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", tmp_path / "transcripts")
    monkeypatch.setattr(afg_cli, "load_series_reference", load)
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: text_similarity)
    return {"dir": run_dir, "languages": languages}


def _run(*args: str):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(afg_cli.app, ["experiment", "a-report", *args])


def test_help_documents_the_options() -> None:
    out = " ".join(_run("--help").output.split())
    for option in ("--c2-extraction", "--descriptive"):
        assert option in out


def test_development_run_without_descriptive_is_refused_and_writes_nothing(
    env: dict[str, Any],
) -> None:
    result = _run("--c2-extraction", RUN)

    assert result.exit_code == 1
    assert "--descriptive" in result.output
    assert not (env["dir"] / "informe.json").exists()
    assert not (env["dir"] / "informe-descriptivo.json").exists()


def test_descriptive_writes_a_separate_report_and_prints_the_table(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN, "--descriptive")

    assert result.exit_code == 0, result.output
    report = json.loads((env["dir"] / "informe-descriptivo.json").read_text())
    assert report["reportable"] is False
    assert report["language"] == "en"
    assert set(env["languages"]) == {"en"}
    assert report["reference_kinds"] == {"ES2015": "adjudicated"}
    principal = next(e for e in report["curve"] if e["role"] == "principal")
    assert principal["tau"] == 0.70
    assert principal["origin_meetings"]["pooled"]["tp"] == 5
    assert "0.70" in result.output
    assert "informe-descriptivo.json" in result.output


def test_embeds_relaciones_json_when_the_run_has_one(env: dict[str, Any]) -> None:
    (env["dir"] / "relaciones.json").write_text(
        json.dumps({"run_name": RUN, "tau": 0.70, "n_errors": 0, "pooled": {"n_gold_links": 2}})
    )

    result = _run("--c2-extraction", RUN, "--descriptive")

    assert result.exit_code == 0, result.output
    report = json.loads((env["dir"] / "informe-descriptivo.json").read_text())
    assert report["relations"]["pooled"] == {"n_gold_links": 2}


def test_without_relaciones_json_the_output_says_how_to_get_it(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", RUN, "--descriptive")

    report = json.loads((env["dir"] / "informe-descriptivo.json").read_text())
    assert report["relations"] is None
    assert "a-relations" in " ".join(result.output.split())


def test_missing_run_exits_with_a_message(env: dict[str, Any]) -> None:
    result = _run("--c2-extraction", "no-existe", "--descriptive")

    assert result.exit_code == 1
    assert "no-existe" in result.output


def test_prints_the_extraction_gap_and_h3_verdicts_when_relations_are_present(
    env: dict[str, Any],
) -> None:
    (env["dir"] / "relaciones.json").write_text(
        json.dumps({"run_name": RUN, "tau": 0.70, "n_errors": 0, "pooled": {"n_gold_links": 2}})
    )

    result = _run("--c2-extraction", RUN, "--descriptive")

    output = " ".join(result.output.split())
    assert "Brecha de extracción" in output and "H3" in output
    assert "not_computable" in output
