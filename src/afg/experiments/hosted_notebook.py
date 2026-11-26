"""Tables and figure data of notebook 33, the results of the hosted extension (ADR 0026).

Every number the notebook shows is produced here (or in :mod:`afg.experiments.hosted_comparison`)
and tested; the notebook only calls these functions and displays or plots the result. Nothing
here calls a model: the functions read stored run folders and the payload of
:func:`~afg.experiments.hosted_comparison.build_comparison`.

Text meant for a reader (column names, states, verdicts) is Spanish, with a decimal comma.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from afg.experiments.hosted_comparison import METRICS, NO_RUN
from afg.experiments.hosted_extraction import HostedConfig, hosted_run_name

__all__ = [
    "baseline_figures",
    "bridge_frame",
    "bridge_state",
    "format_es",
    "format_interval",
    "local_baseline_state",
    "models_frame",
    "operation_table",
    "quality_table",
    "recall_forest_rows",
    "run_status",
    "time_forest_rows",
    "version_effect_table",
]

LABELS = {"openai": "OpenAI", "anthropic": "Anthropic", "google": "Google"}


def format_es(value: float, digits: int = 2, *, signed: bool = False) -> str:
    """``value`` with ``digits`` decimals and a decimal comma (``signed``: always show the sign)."""
    text = f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"
    return text.replace(".", ",")


def format_interval(
    estimate: float, interval: Sequence[float], digits: int = 2, *, signed: bool = False
) -> str:
    """``estimate [low; high]`` in Spanish format."""
    low, high = (format_es(v, digits, signed=signed) for v in interval)
    return f"{format_es(estimate, digits, signed=signed)} [{low}; {high}]"


def baseline_figures(informe: Mapping[str, Any], tau: float) -> dict[str, Any]:
    """Pooled precision, recall and F1 (with their 95 % intervals) of a stored ``informe.json``."""
    for entry in informe["curve"]:
        if abs(float(entry["tau"]) - tau) < 1e-9:
            pooled = entry["origin_meetings"]["pooled"]
            figures: dict[str, Any] = {
                name: {
                    "estimate": float(pooled[name]),
                    "interval": tuple(float(v) for v in pooled["intervals"][name]),
                }
                for name in METRICS
            }
            figures["n_meetings"] = int(pooled["n_clusters"])
            return figures
    raise ValueError(f"The report has no curve entry for tau {tau}.")


def models_frame(config: HostedConfig) -> pd.DataFrame:
    """The configured paid models, one row each."""
    return pd.DataFrame(
        [
            {
                "Etiqueta": spec.label,
                "Laboratorio": LABELS.get(spec.provider, spec.provider),
                "Modelo": spec.model,
                "Punto de acceso": spec.base_url,
            }
            for spec in config.models.values()
        ]
    )


# --- state of the runs ------------------------------------------------------------------------


def _read_manifest(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _ok_runs(manifest: Mapping[str, Any]) -> dict[str, int]:
    """Finished repetitions per series, from the pairs of a run manifest."""
    counts: dict[str, int] = {}
    for pair in (manifest.get("pairs") or {}).values():
        if pair.get("status") == "ok":
            counts[pair["series"]] = counts.get(pair["series"], 0) + 1
    return dict(sorted(counts.items()))


def run_status(
    config: HostedConfig, *, runs_root: Path, evaluation_series: Sequence[str]
) -> list[dict[str, str]]:
    """Per model label: ``sin corrida``, ``piloto``, ``parcial`` or ``completa``.

    A full run is ``completa`` when every evaluation series has ``runs_per_model`` finished
    repetitions; a full run folder short of that is ``parcial``. A label with only a pilot
    folder is ``piloto``.
    """
    rows: list[dict[str, str]] = []
    for label in config.models:
        full = _read_manifest(runs_root / hosted_run_name(label))
        pilot = _read_manifest(runs_root / hosted_run_name(label, pilot=True))
        manifest, state = (full, "") if full is not None else (pilot, "piloto")
        if manifest is None:
            rows.append({"label": label, "estado": NO_RUN, "series": "-", "corridas": "-"})
            continue
        counts = _ok_runs(manifest)
        if full is not None:
            done = all(counts.get(s, 0) >= config.runs_per_model for s in evaluation_series)
            state = "completa" if done else "parcial"
        rows.append(
            {
                "label": label,
                "estado": state,
                "series": ", ".join(counts) or "-",
                "corridas": ", ".join(f"{s}: {n}" for s, n in counts.items()) or "-",
            }
        )
    return rows


def bridge_state(config: HostedConfig, *, runs_root: Path) -> dict[str, str]:
    """State of the continuity run: ``pendiente``, ``en curso``, ``fallida`` or ``lista``."""
    run_dir = runs_root / config.bridge.run_name
    manifest = _read_manifest(run_dir)
    if manifest is None:
        return {"state": "pendiente", "detail": "La corrida del puente todavía no existe."}
    status = manifest.get("status")
    if status == "failed":
        return {"state": "fallida", "detail": "La corrida del puente terminó con error."}
    if status != "ok" or not (run_dir / "extracciones.jsonl").is_file():
        return {"state": "en curso", "detail": "La corrida del puente aún no termina."}
    return {"state": "lista", "detail": "La corrida del puente terminó."}


def local_baseline_state(
    config: HostedConfig, *, runs_root: Path, evaluation_series: Sequence[str]
) -> dict[str, str]:
    """State of the secondary baseline run: ``pendiente``, ``en curso``, ``fallida`` or ``lista``.

    ``en curso`` says how many of the ``series x runs`` pairs have finished.
    """
    spec = config.local_baseline
    run_dir = runs_root / spec.run_name
    manifest = _read_manifest(run_dir)
    if manifest is None:
        return {"state": "pendiente", "detail": "La segunda línea base todavía no existe."}
    if manifest.get("status") == "failed":
        return {"state": "fallida", "detail": "La segunda línea base terminó con error."}
    if manifest.get("status") != "ok" or not (run_dir / "extracciones.jsonl").is_file():
        done = sum(_ok_runs(manifest).values())
        expected = len(evaluation_series) * spec.runs
        return {
            "state": "en curso",
            "detail": f"La segunda línea base lleva {done} de {expected} pares terminados.",
        }
    return {"state": "lista", "detail": "La segunda línea base terminó."}


# --- tables and figure data -------------------------------------------------------------------


def bridge_frame(bridge: Mapping[str, Any]) -> pd.DataFrame:
    """One row per series and metric: the bridge value against the range of the formal runs."""
    rows: list[dict[str, str]] = []
    for series_id, item in bridge["series"].items():
        if item.get("inside") is None:
            rows.append(
                {
                    "Serie": series_id,
                    "Métrica": "-",
                    "Puente": "-",
                    "Rango formal": item["note"],
                    "Dentro": "-",
                }
            )
            continue
        for name in METRICS:
            low, high = item["formal_range"][name]
            rows.append(
                {
                    "Serie": series_id,
                    "Métrica": name,
                    "Puente": format_es(item["bridge"][name]),
                    "Rango formal": f"{format_es(low)} a {format_es(high)}",
                    "Dentro": "no" if name in item["outside_metrics"] else "sí",
                }
            )
    return pd.DataFrame(rows)


def _ok_candidates(
    payload: Mapping[str, Any], baseline: str = "formal"
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """``(candidate, block)`` of every candidate whose comparison with ``baseline`` exists.

    ``baseline`` is ``formal`` or ``local``; a candidate without a run, or without that
    baseline's block (not requested or ``sin corrida``), is skipped.
    """
    pairs = []
    for item in payload["candidates"]:
        block = item.get(f"vs_{baseline}") if item["status"] == "ok" else None
        if block is not None and block["status"] == "ok":
            pairs.append((item, block))
    return pairs


def _tau_key(tau: float) -> str:
    return f"{tau:.2f}"


def quality_table(
    payload: Mapping[str, Any], tau_key: str, baseline: str = "formal"
) -> pd.DataFrame:
    """Extraction quality of every compared model at one tau, against one baseline.

    Labels without a run, or without that baseline's comparison, are skipped.
    """
    rows = []
    for item, block in _ok_candidates(payload, baseline):
        entry = block["taus"][tau_key]
        row: dict[str, str] = {
            "Modelo": item["label"],
            "Series": str(block["n_series"]),
            "Reuniones": str(block["n_meetings"]),
            "Precision": format_es(entry["candidate"]["precision"]),
            "Recall": format_es(entry["candidate"]["recall"]),
            "F1": format_es(entry["candidate"]["f1"]),
        }
        for name, title in (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1")):
            diff = entry["diff"][name]
            row[f"Δ {title}"] = format_interval(diff["estimate"], diff["interval"], signed=True)
        row["Veredicto"] = entry["verdict"]
        flag = entry.get("recall_up_precision_drop")
        row["Recall sube, precision cae"] = "n/d" if flag is None else "sí" if flag else "no"
        rows.append(row)
    return pd.DataFrame(rows, columns=_QUALITY_COLUMNS)


_QUALITY_COLUMNS = [
    "Modelo", "Series", "Reuniones", "Precision", "Recall", "F1",
    "Δ Precision", "Δ Recall", "Δ F1", "Veredicto", "Recall sube, precision cae",
]  # fmt: skip


def recall_forest_rows(
    payload: Mapping[str, Any], baseline: str = "formal"
) -> list[dict[str, Any]]:
    """Data of the forest plot: recall difference and interval at the primary tau per model."""
    key = _tau_key(float(payload["primary_tau"]))
    rows = []
    for item, block in _ok_candidates(payload, baseline):
        entry = block["taus"][key]
        diff = entry["diff"]["recall"]
        rows.append(
            {
                "label": item["label"],
                "estimate": diff["estimate"],
                "low": diff["interval"][0],
                "high": diff["interval"][1],
                "verdict": entry["verdict"],
            }
        )
    return rows


def time_forest_rows(payload: Mapping[str, Any], baseline: str = "formal") -> list[dict[str, Any]]:
    """Data of the time-ratio plot: ratio and interval per model; models without a ratio skip."""
    rows = []
    for item, block in _ok_candidates(payload, baseline):
        time = block["operation"]["time"]
        if time["ratio"] is None:
            continue
        rows.append(
            {
                "label": item["label"],
                "estimate": time["ratio"]["estimate"],
                "low": time["ratio"]["interval"][0],
                "high": time["ratio"]["interval"][1],
                "verdict": time["verdict"],
            }
        )
    return rows


def _seconds(value: float | None) -> str:
    return "sin datos" if value is None else f"{value:.0f}"


def operation_table(payload: Mapping[str, Any], baseline: str = "formal") -> pd.DataFrame:
    """Operation indicators (ADR 0026, decision 8) of every compared model against a baseline."""
    rows = []
    for item, block in _ok_candidates(payload, baseline):
        operation = block["operation"]
        time, done = operation["time"], operation["completeness"]["candidate"]
        ratio = time["ratio"]
        decisions = operation["decisions_per_meeting"]["candidate"]["mean"]
        cost = operation["cost_usd"]
        rows.append(
            {
                "Modelo": item["label"],
                "Mediana por reunión (s)": _seconds(time["candidate_median_s"]),
                "Línea base (s)": _seconds(time["baseline_median_s"]),
                "Razón de tiempos": (
                    "sin datos"
                    if ratio is None
                    else format_interval(ratio["estimate"], ratio["interval"])
                ),
                "Tiempo": time["verdict"],
                "Extracciones completas": (
                    "sin datos"
                    if done["share"] is None
                    else f"{done['complete']} de {done['expected']} "
                    f"({format_es(100 * done['share'], 0)} %)"
                ),
                "Decisiones por reunión": (
                    "sin datos" if decisions is None else format_es(decisions, 1)
                ),
                "Costo (USD)": "sin registrar" if cost is None else format_es(cost),
            }
        )
    return pd.DataFrame(rows, columns=_OPERATION_COLUMNS)


_OPERATION_COLUMNS = [
    "Modelo", "Mediana por reunión (s)", "Línea base (s)", "Razón de tiempos", "Tiempo",
    "Extracciones completas", "Decisiones por reunión", "Costo (USD)",
]  # fmt: skip


VERSION_EFFECT_TEXT = "qwen3:8b en 0.7.2 contra qwen3:8b formal (efecto de versión)"


def version_effect_table(payload: Mapping[str, Any], tau_key: str | None = None) -> pd.DataFrame:
    """Local baseline (``qwen3:8b`` on OpenKOS 0.7.2) against the formal run, at one tau.

    Empty while the local baseline run is missing. It is not a paid model and does not count in
    the Bonferroni family: it only shows how much of a difference the OpenKOS version makes.
    """
    effect = payload.get("version_effect")
    if effect is None or effect["status"] != "ok":
        return pd.DataFrame(columns=_VERSION_COLUMNS)
    entry = effect["taus"][tau_key or _tau_key(float(payload["primary_tau"]))]
    row: dict[str, str] = {
        "Comparación": VERSION_EFFECT_TEXT,
        "Series": str(effect["n_series"]),
        "Reuniones": str(effect["n_meetings"]),
        "Precision": format_es(entry["candidate"]["precision"]),
        "Recall": format_es(entry["candidate"]["recall"]),
        "F1": format_es(entry["candidate"]["f1"]),
    }
    for name, title in (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1")):
        diff = entry["diff"][name]
        row[f"Δ {title}"] = format_interval(diff["estimate"], diff["interval"], signed=True)
    return pd.DataFrame([row], columns=_VERSION_COLUMNS)


_VERSION_COLUMNS = [
    "Comparación", "Series", "Reuniones", "Precision", "Recall", "F1",
    "Δ Precision", "Δ Recall", "Δ F1",
]  # fmt: skip
