"""Tests for the tables and figure data of notebook 33 (ADR 0026): no model, no Ollama."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from afg.experiments.hosted_extraction import load_hosted_config
from afg.experiments.hosted_notebook import (
    baseline_figures,
    bridge_frame,
    bridge_state,
    format_es,
    format_interval,
    local_baseline_state,
    models_frame,
    operation_table,
    quality_table,
    recall_forest_rows,
    run_status,
    time_forest_rows,
    version_effect_table,
)

SERIES = ["ES2002", "ES2003"]


def _informe() -> dict[str, Any]:
    pooled = {
        "precision": 0.15,
        "recall": 0.31,
        "f1": 0.20,
        "intervals": {"precision": [0.1, 0.2], "recall": [0.25, 0.37], "f1": [0.16, 0.24]},
        "n_clusters": 44,
    }
    return {"curve": [{"tau": 0.7, "origin_meetings": {"pooled": pooled}}]}


def _cost(total: float | None, *, lower_bound: bool = False) -> dict[str, Any]:
    if total is None:
        return {
            "status": "pendiente",
            "total_usd": None,
            "median_per_meeting_usd": None,
            "lower_bound": False,
            "n_lower_bound_meetings": 0,
            "prices": None,
        }
    return {
        "status": "ok",
        "total_usd": total,
        "median_per_meeting_usd": total / 10,
        "lower_bound": lower_bound,
        "n_lower_bound_meetings": 1 if lower_bound else 0,
        "prices": {"input_usd_per_mtok": 1.0, "output_usd_per_mtok": 2.0},
    }


def _block(
    *,
    ratio: dict[str, Any] | None,
    cost: float | None,
    shift: float = 0.0,
    lower_bound: bool = False,
) -> dict[str, Any]:
    entry = {
        "tau": 0.7,
        "baseline": {"precision": 0.15, "recall": 0.30, "f1": 0.20},
        "candidate": {"precision": 0.30, "recall": 0.50, "f1": 0.375},
        "diff": {
            "precision": {"estimate": 0.15, "interval": [0.05, 0.25]},
            "recall": {"estimate": 0.20 + shift, "interval": [0.10, 0.30]},
            "f1": {"estimate": 0.175, "interval": [0.09, 0.26]},
        },
        "verdict": "mejora",
        "recall_up_precision_drop": False,
    }
    return {
        "status": "ok",
        "series_covered": ["ES2002"],
        "n_series": 1,
        "n_meetings": 4,
        "taus": {"0.70": entry},
        "verdict": "mejora",
        "operation": {
            "time": {
                "baseline_median_s": 300.0,
                "candidate_median_s": 60.0,
                "ratio": ratio,
                "verdict": "más rápido" if ratio else "sin datos",
                "n_meetings": 4,
            },
            "completeness": {
                "baseline": {"complete": 4, "expected": 4, "share": 1.0},
                "candidate": {"complete": 3, "expected": 4, "share": 0.75},
            },
            "decisions_per_meeting": {
                "baseline": {"mean": 6.0, "median": 6.0},
                "candidate": {"mean": 2.5, "median": 2.0},
            },
            "extraction_status": {
                "baseline": dict.fromkeys(STATUSES, 0),
                "candidate": {**dict.fromkeys(STATUSES, 0), "failed": 1},
            },
            "tokens": {
                "baseline": None,
                "candidate": {
                    "n_meetings": 4,
                    "calls": 40,
                    "reported_calls": 40,
                    "prompt": 1_234_567,
                    "completion": 89_000,
                    "total": 1_500_000,
                    "median_total_per_meeting": 375_000,
                    "lower_bound": lower_bound,
                },
            },
            "cost": _cost(cost, lower_bound=lower_bound),
            "cost_usd": cost,
            "dashboard_usd": None,
        },
    }


STATUSES = ("failed", "no-concepts-found", "no-extractable-text", "blocked-by-sensitivity")


def _candidate(label: str, *, ratio: dict[str, Any] | None, cost: float | None) -> dict[str, Any]:
    return {
        "label": label,
        "model": "m",
        "run_name": f"experimento-a-hosted-{label}",
        "status": "ok",
        "vs_formal": _block(ratio=ratio, cost=cost),
        "vs_local": _block(ratio=ratio, cost=cost, shift=-0.05),
    }


def _payload() -> dict[str, Any]:
    flagged = _candidate("c", ratio=None, cost=None)
    flagged["vs_formal"]["taus"]["0.70"]["recall_up_precision_drop"] = True
    return {
        "primary_tau": 0.7,
        "candidates": [
            _candidate("a", ratio={"estimate": 0.2, "interval": [0.1, 0.3]}, cost=1.5),
            {"label": "b", "run_name": "experimento-a-hosted-b", "status": "sin corrida"},
            flagged,
        ],
        "version_effect": {
            "status": "ok",
            "label": "qwen3:8b@0.7.3",
            "run_name": "experimento-a-base-0-7-3",
            **_block(ratio={"estimate": 1.1, "interval": [0.9, 1.3]}, cost=None, shift=-0.18),
        },
        "bridge": None,
    }


def test_formatting_uses_the_spanish_decimal_comma() -> None:
    assert format_es(0.3081, 2) == "0,31"
    assert format_es(-0.05, 2, signed=True) == "-0,05"
    assert format_es(0.2, 2, signed=True) == "+0,20"
    assert format_interval(0.31, (0.25, 0.37)) == "0,31 [0,25; 0,37]"
    assert format_interval(0.2, (0.1, 0.3), signed=True) == "+0,20 [+0,10; +0,30]"


def test_baseline_figures_read_the_pooled_curve_entry() -> None:
    figures = baseline_figures(_informe(), 0.70)
    assert figures["recall"] == {"estimate": 0.31, "interval": (0.25, 0.37)}
    assert figures["precision"]["estimate"] == 0.15
    assert figures["n_meetings"] == 44


def test_baseline_figures_of_an_unknown_tau_is_an_error() -> None:
    with pytest.raises(ValueError, match=r"0\.95"):
        baseline_figures(_informe(), 0.95)


def test_models_frame_lists_the_six_configured_models() -> None:
    frame = models_frame(load_hosted_config())
    assert len(frame) == 6
    assert frame["Etiqueta"].iloc[0] == "openai-small"
    assert {"Laboratorio", "Modelo", "Etiqueta"} <= set(frame.columns)


def _write_manifest(root: Path, name: str, status: str, pairs: dict[str, str]) -> None:
    run_dir = root / name
    run_dir.mkdir(parents=True)
    body = {
        "status": status,
        "pairs": {
            key: {"series": key.split("/")[0], "run": int(key.split("/")[1]), "status": st}
            for key, st in pairs.items()
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(body))


def test_run_status_distinguishes_none_pilot_partial_and_complete(tmp_path: Path) -> None:
    config = load_hosted_config()
    runs = config.runs_per_model
    _write_manifest(tmp_path, "experimento-a-piloto-openai-small", "ok", {"ES2002/0": "ok"})
    _write_manifest(
        tmp_path,
        "experimento-a-hosted-openai-large",
        "ok",
        {f"{s}/{r}": "ok" for s in SERIES for r in range(runs)},
    )
    _write_manifest(
        tmp_path,
        "experimento-a-hosted-google-small",
        "running",
        {"ES2002/0": "ok", "ES2002/1": "running"},
    )

    rows = {r["label"]: r for r in run_status(config, runs_root=tmp_path, evaluation_series=SERIES)}

    assert rows["anthropic-small"]["estado"] == "sin corrida"
    assert rows["openai-small"]["estado"] == "piloto"
    assert rows["openai-small"]["series"] == "ES2002"
    assert rows["openai-large"]["estado"] == "completa"
    assert rows["openai-large"]["series"] == "ES2002, ES2003"
    assert rows["google-small"]["estado"] == "parcial"
    assert rows["google-small"]["corridas"] == "ES2002: 1"


def test_bridge_state_is_pending_until_the_run_is_complete(tmp_path: Path) -> None:
    config = load_hosted_config()
    assert bridge_state(config, runs_root=tmp_path)["state"] == "pendiente"

    _write_manifest(tmp_path, config.bridge.run_name, "running", {"ES2002/0": "running"})
    assert bridge_state(config, runs_root=tmp_path)["state"] == "en curso"

    (tmp_path / config.bridge.run_name / "manifest.json").write_text(
        json.dumps({"status": "ok", "pairs": {"ES2002/0": {"series": "ES2002", "run": 0}}})
    )
    assert bridge_state(config, runs_root=tmp_path)["state"] == "en curso"  # no records yet

    (tmp_path / config.bridge.run_name / "extracciones.jsonl").write_text("{}\n")
    assert bridge_state(config, runs_root=tmp_path)["state"] == "lista"


def test_bridge_state_reports_a_failed_run(tmp_path: Path) -> None:
    config = load_hosted_config()
    _write_manifest(tmp_path, config.bridge.run_name, "failed", {"ES2002/0": "failed"})
    assert bridge_state(config, runs_root=tmp_path)["state"] == "fallida"


def test_bridge_frame_has_one_row_per_series_and_metric() -> None:
    bridge = {
        "tau": 0.7,
        "all_inside": False,
        "series": {
            "ES2002": {
                "bridge": {"precision": 0.2, "recall": 0.4, "f1": 0.27},
                "formal_range": {
                    "precision": [0.1, 0.3],
                    "recall": [0.1, 0.3],
                    "f1": [0.1, 0.3],
                },
                "n_formal_runs": 3,
                "outside_metrics": ["recall"],
                "inside": False,
            }
        },
    }
    frame = bridge_frame(bridge)
    assert list(frame["Métrica"]) == ["precision", "recall", "f1"]
    recall = frame[frame["Métrica"] == "recall"].iloc[0]
    assert recall["Puente"] == "0,40"
    assert recall["Rango formal"] == "0,10 a 0,30"
    assert recall["Dentro"] == "no"


def test_quality_table_skips_labels_without_runs() -> None:
    table = quality_table(_payload(), "0.70")
    assert list(table["Modelo"]) == ["a", "c"]
    row = table.iloc[0]
    assert row["Recall"] == "0,50"
    assert row["Δ Recall"] == "+0,20 [+0,10; +0,30]"
    assert row["Veredicto"] == "mejora"
    assert row["Recall sube, precision cae"] == "no"
    assert table.iloc[1]["Recall sube, precision cae"] == "sí"


def test_forest_rows_hold_estimate_interval_and_skip_missing_data() -> None:
    recall = recall_forest_rows(_payload())
    assert [r["label"] for r in recall] == ["a", "c"]
    assert recall[0] == {
        "label": "a",
        "estimate": 0.20,
        "low": 0.10,
        "high": 0.30,
        "verdict": "mejora",
    }
    time = time_forest_rows(_payload())
    assert [r["label"] for r in time] == ["a"]  # "c" has no time ratio
    assert time[0]["estimate"] == 0.2 and time[0]["verdict"] == "más rápido"


def test_operation_table_shows_time_completeness_decisions_and_cost() -> None:
    table = operation_table(_payload())
    assert list(table["Modelo"]) == ["a", "c"]
    first, second = table.iloc[0], table.iloc[1]
    assert first["Mediana por reunión (s)"] == "60"
    assert first["Línea base (s)"] == "300"
    assert first["Razón de tiempos"] == "0,20 [0,10; 0,30]"
    assert first["Tiempo"] == "más rápido"
    assert first["Reuniones con extracción"] == "3 de 4 (75 %)"
    assert first["Decisiones por reunión"] == "2,5"
    assert first["Costo (USD)"] == "1,50"
    assert second["Razón de tiempos"] == "sin datos"
    assert second["Costo (USD)"] == "pendiente"  # no price yet: never shown as 0


def test_operation_table_shows_tokens_extraction_status_and_the_lower_bound() -> None:
    payload = _payload()
    payload["candidates"][0]["vs_formal"] = _block(
        ratio={"estimate": 0.2, "interval": [0.1, 0.3]}, cost=1.5, lower_bound=True
    )
    first = operation_table(payload).iloc[0]
    assert first["Costo (USD)"] == "≥ 1,50"
    assert first["Tokens de entrada"] == "1.234.567"
    assert first["Tokens totales"] == "1.500.000"
    assert first["Sin extracción"] == "1 failed"
    assert first["Costo mediano por reunión (USD)"] == "≥ 0,15"


def test_empty_payload_gives_empty_tables() -> None:
    payload: dict[str, Any] = {
        "primary_tau": 0.7,
        "candidates": [],
        "version_effect": None,
        "bridge": None,
    }
    assert quality_table(payload, "0.70").empty
    assert version_effect_table(payload).empty
    assert operation_table(payload).empty
    assert recall_forest_rows(payload) == []


def test_tables_accept_a_baseline_selector() -> None:
    formal = recall_forest_rows(_payload(), baseline="formal")
    local = recall_forest_rows(_payload(), baseline="local")
    assert formal[0]["estimate"] == pytest.approx(0.20)
    assert local[0]["estimate"] == pytest.approx(0.15)
    assert quality_table(_payload(), "0.70", baseline="local").iloc[0]["Δ Recall"] == (
        "+0,15 [+0,10; +0,30]"
    )
    assert [r["label"] for r in time_forest_rows(_payload(), baseline="local")] == ["a"]
    assert list(operation_table(_payload(), baseline="local")["Modelo"]) == ["a", "c"]


def test_a_baseline_block_without_a_run_is_skipped() -> None:
    payload = _payload()
    payload["candidates"][0]["vs_local"] = {"status": "sin corrida", "baseline_run_name": "x"}
    assert [r["label"] for r in recall_forest_rows(payload, baseline="local")] == ["c"]
    assert list(quality_table(payload, "0.70", baseline="local")["Modelo"]) == ["c"]
    payload["candidates"][0].pop("vs_local")
    assert [r["label"] for r in recall_forest_rows(payload, baseline="local")] == ["c"]


def test_version_effect_table_shows_the_local_baseline_against_the_formal_run() -> None:
    table = version_effect_table(_payload())

    assert len(table) == 1
    row = table.iloc[0]
    assert row["Comparación"] == "qwen3:8b en 0.7.3 contra qwen3:8b formal (efecto de versión)"
    assert row["Δ Recall"] == "+0,02 [+0,10; +0,30]"
    assert row["Precision"] == "0,30"


def test_version_effect_table_is_empty_while_the_local_run_is_missing() -> None:
    payload = _payload()
    payload["version_effect"] = {"status": "sin corrida", "run_name": "x"}
    assert version_effect_table(payload).empty


def test_local_baseline_state_reports_progress(tmp_path: Path) -> None:
    config = load_hosted_config()
    series = [f"ES{i:04d}" for i in range(11)]
    assert (
        local_baseline_state(config, runs_root=tmp_path, evaluation_series=series)["state"]
        == "pendiente"
    )

    _write_manifest(
        tmp_path,
        config.local_baseline.run_name,
        "running",
        {"ES2002/0": "ok", "ES2002/1": "running"},
    )
    running = local_baseline_state(config, runs_root=tmp_path, evaluation_series=series)
    assert running["state"] == "en curso"
    assert "1 de 33" in running["detail"]

    done = {f"ES{i:04d}/{r}": "ok" for i in range(11) for r in range(3)}
    (tmp_path / config.local_baseline.run_name / "manifest.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "pairs": {
                    k: {"series": k.split("/")[0], "run": int(k.split("/")[1]), "status": v}
                    for k, v in done.items()
                },
            }
        )
    )
    (tmp_path / config.local_baseline.run_name / "extracciones.jsonl").write_text("{}\n")
    ready = local_baseline_state(config, runs_root=tmp_path, evaluation_series=series)
    assert ready["state"] == "lista"
