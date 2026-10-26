"""Tests for ``afg c1 tune``. No Ollama, no corpus: embedder and models are stubbed."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.conditions.c1_retrieval import configured_embedding_model
from afg.conditions.c1_tuning import PinnedC1Params, TuningConfig

_HEADER = (
    "id,series_id,stratum,question,reference_answer,reference_evidence,answer_text,"
    "pasaje_transcripcion,archivos_transcripcion,answer_abstained,correct,evidence_supported,"
    "citation_correct,labeler_a,labeler_b,adjudicated\n"
)
_ROWS = [
    "ES2015.q001.grounded,ES2015,E1_point_fact,budget euros?,ans,ES2015a:d2,t,,,no,,,,,,no",
    "ES2015.q001.ungrounded,ES2015,E1_point_fact,budget euros?,ans,ES2015a:d2,t,,,no,,,,,,no",
    "ES2015.q002.grounded,ES2015,E3_evolution,logo colour?,ans,ES2015a:d4,t,,,no,,,,,,no",
    "ES2015.q003.grounded,ES2015,E4_unanswerable,Q three?,,,t,,,no,,,,,,no",
]


class LetterEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(ord(c) % 7) for c in (t.lower() + "abcdefg")[:8]] for t in texts]


def _config(**overrides: Any) -> TuningConfig:
    values: dict[str, Any] = {
        "series": ("ES2015",),
        "max_chars": (40, 400),
        "overlap_turns": (0,),
        "k": (1, 2),
        "char_budget": 1000,
        "tie_margin": 0.02,
    }
    values.update(overrides)
    return TuningConfig(**values)


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    turns = ["remote control battery", "budget twelve euros", "banana", "logo and colour"]
    lines = [
        json.dumps(
            {
                "meeting_id": "ES2015a",
                "turn_index": i,
                "speaker": "A",
                "role": "PM",
                "text": text,
                "start": None,
                "end": None,
                "char_start": i * 100,
                "char_end": i * 100 + len(text),
                "dialogue_act_ids": [f"d{i + 1}"],
            }
        )
        for i, text in enumerate(turns)
    ]
    (transcripts / "ES2015a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    calibration = tmp_path / "calibracion.csv"
    calibration.write_text(_HEADER + "\n".join(_ROWS) + "\n", encoding="utf-8")
    results = tmp_path / "out" / "resultados.json"
    monkeypatch.setattr(afg_cli, "TRANSCRIPTS_DIR", transcripts)
    monkeypatch.setattr(afg_cli, "CALIBRATION_PATH", calibration)
    monkeypatch.setattr(afg_cli, "C1_TUNING_RESULTS_PATH", results)
    ablation = tmp_path / "out" / "ablacion.json"
    monkeypatch.setattr(afg_cli, "C1_ABLATION_PATH", ablation)
    monkeypatch.setattr(
        afg_cli, "load_pinned_c1_params", lambda: PinnedC1Params(max_chars=40, overlap_turns=0, k=1)
    )
    monkeypatch.setattr(afg_cli, "load_tuning_config", lambda: _config())
    monkeypatch.setattr(afg_cli, "make_c1_embedder", lambda: LetterEmbedder())
    monkeypatch.setattr(
        afg_cli, "list_installed_models", lambda: [f"{configured_embedding_model()}:latest"]
    )
    monkeypatch.setattr(
        "afg.evaluation.judge_calibration_set.calibration_series",
        lambda: frozenset({"ES2015"}),
    )
    return {"results": results, "calibration": calibration, "ablation": ablation}


def _tune() -> Any:
    return CliRunner().invoke(afg_cli.app, ["c1", "tune"])


def _out(result: Any) -> str:
    return " ".join(result.output.split())


def test_tune_runs_the_grid_prints_the_winner_and_saves(env: dict[str, Path]) -> None:
    result = _tune()
    assert result.exit_code == 0, result.output
    out = _out(result)
    assert "2 preguntas" in out
    assert "Ganador" in out
    stored = json.loads(env["results"].read_text(encoding="utf-8"))
    assert stored["n_questions"] == 2
    assert len(stored["results"]) == 4  # 2 max_chars x 1 overlap x 2 k
    assert {"max_chars", "overlap_turns", "k"} <= set(stored["decision"])


def test_tune_stops_when_the_embedding_model_is_missing(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "list_installed_models", lambda: ["other:latest"])
    result = _tune()
    assert result.exit_code == 1
    assert f"ollama pull {configured_embedding_model()}" in _out(result)
    assert not env["results"].exists()


def test_tune_stops_when_ollama_is_unreachable(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> list[str]:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(afg_cli, "list_installed_models", boom)
    result = _tune()
    assert result.exit_code == 1
    assert "Ollama" in _out(result)


def test_tune_refuses_series_outside_development(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse() -> TuningConfig:
        raise ValueError("not development series (ADR 0005)")

    monkeypatch.setattr(afg_cli, "load_tuning_config", refuse)
    result = _tune()
    assert result.exit_code == 1
    assert "ADR 0005" in _out(result)


def test_tune_fails_clearly_when_nothing_fits_the_budget(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "load_tuning_config", lambda: _config(char_budget=1))
    result = _tune()
    assert result.exit_code == 1
    assert "presupuesto" in _out(result)


def test_tune_needs_the_calibration_file(env: dict[str, Path]) -> None:
    env["calibration"].unlink()
    result = _tune()
    assert result.exit_code == 1
    assert "calibracion" in _out(result)


def _ablate() -> Any:
    return CliRunner().invoke(afg_cli.app, ["c1", "ablate"])


def test_ablate_prints_the_three_modes_and_saves(env: dict[str, Path]) -> None:
    result = _ablate()
    assert result.exit_code == 0, result.output
    out = _out(result)
    assert "2 preguntas" in out
    stored = json.loads(env["ablation"].read_text(encoding="utf-8"))
    assert [m["mode"] for m in stored["modes"]] == ["bm25", "dense", "hybrid"]
    assert stored["params"] == {"max_chars": 40, "overlap_turns": 0, "k": 1}
    assert "git_commit" in stored
    assert not env["results"].exists()  # the tuning results are never touched


def test_ablate_refuses_series_outside_development(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse() -> TuningConfig:
        raise ValueError("not development series (ADR 0005)")

    monkeypatch.setattr(afg_cli, "load_tuning_config", refuse)
    result = _ablate()
    assert result.exit_code == 1
    assert "ADR 0005" in _out(result)
    assert not env["ablation"].exists()


def test_ablate_stops_when_the_embedding_model_is_missing(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "list_installed_models", lambda: ["other:latest"])
    result = _ablate()
    assert result.exit_code == 1
    assert f"ollama pull {configured_embedding_model()}" in _out(result)
    assert not env["ablation"].exists()


# --- afg c1 ask ------------------------------------------------------------------------


class _AskChat:
    def __init__(self, *replies: str) -> None:
        self._replies = list(replies)

    def chat(self, messages: Any, *, model: str, options: Any) -> str:
        return self._replies.pop(0)


@pytest.fixture
def ask_env(env: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Path:
    from afg.conditions.c1_document_rag import DocumentRagCondition, GenerationSettings
    from afg.conditions.c1_tuning import PinnedC1Params

    replies: list[str] = ["quote", "Twelve euros.\nUSED: 1"]

    def make() -> DocumentRagCondition:
        return DocumentRagCondition(
            chat=_AskChat(*replies),
            embedder=LetterEmbedder(),
            settings=GenerationSettings("qwen3:8b", 0.1, 42, 12288, 8192),
            params=PinnedC1Params(max_chars=60, overlap_turns=0, k=2),
            transcripts_dir=afg_cli.TRANSCRIPTS_DIR,
        )

    monkeypatch.setattr(afg_cli, "make_c1_condition", make)
    monkeypatch.setattr(
        afg_cli,
        "list_installed_models",
        lambda: [f"{configured_embedding_model()}:latest", "qwen3:8b"],
    )
    return env["results"]


def _ask(*extra: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["c1", "ask", "budget in euros?", *extra])


def test_ask_prints_answer_citations_and_outcome(ask_env: Path) -> None:
    result = _ask("--series", "ES2015")
    assert result.exit_code == 0, result.output
    out = _out(result)
    assert "Twelve euros." in out
    assert "USED" not in out
    assert "answered" in out
    assert "ES2015a" in out


def test_ask_reports_an_abstention(ask_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from afg.conditions.c1_document_rag import NO_ANSWER_IN_CONTEXT, DocumentRagCondition

    make = afg_cli.make_c1_condition

    def make_abstaining() -> DocumentRagCondition:
        condition = make()
        condition.chat = _AskChat("NONE")
        return condition

    monkeypatch.setattr(afg_cli, "make_c1_condition", make_abstaining)
    result = _ask("--series", "ES2015")
    assert result.exit_code == 0, result.output
    assert "no_answer_in_context" in _out(result)
    assert NO_ANSWER_IN_CONTEXT in _out(result)


def test_ask_stops_when_the_generative_model_is_missing(
    ask_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        afg_cli, "list_installed_models", lambda: [f"{configured_embedding_model()}:latest"]
    )
    result = _ask("--series", "ES2015")
    assert result.exit_code == 1
    assert "ollama pull qwen3:8b" in _out(result)


def test_ask_stops_when_ollama_is_unreachable(
    ask_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> list[str]:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(afg_cli, "list_installed_models", boom)
    result = _ask("--series", "ES2015")
    assert result.exit_code == 1
    assert "Ollama" in _out(result)


def test_ask_stops_when_the_series_has_no_transcripts(ask_env: Path) -> None:
    result = _ask("--series", "TS3009")
    assert result.exit_code == 1
    assert "TS3009" in _out(result)
