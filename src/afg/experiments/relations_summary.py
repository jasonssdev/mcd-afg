"""Notebook-facing tables for the relation report of Experiment A (``relaciones.json``, ADR 0016).

``afg experiment a-relations`` writes one ``relaciones.json`` per extraction run. This module
only reads that file and arranges its figures into tables; it scores nothing (the scoring is in
:mod:`afg.evaluation.relations`). Column labels are Spanish because a person reads them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

__all__ = [
    "accuracy_frame",
    "existence_frame",
    "format_proportion",
    "load_relation_report",
    "run_frame",
]

DEVELOPMENT = "development"
POOLED_LABEL = "conjunto"
_SCOPE_LABELS = {
    "existence_end_to_end": "extremo a extremo",
    "existence_conditional": "condicionada",
}
_ACCURACY_ROWS = (
    ("Tipo (principal)", "type_principal"),
    ("Tipo (estricta)", "type_strict"),
    ("Dirección (principal)", "direction_principal"),
    ("Dirección (desconocida excluida)", "direction_unknown_excluded"),
)
_ACCURACY_COLUMNS = (
    ("Extremo a extremo", "end_to_end"),
    ("Condicionada", "conditional"),
    ("Entre detectados", "among_detected"),
)


def load_relation_report(path: Path) -> dict[str, Any]:
    """Read a ``relaciones.json``.

    Raises:
        ValueError: the report is not of the development partition (ADR 0005).
    """
    report: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if report.get("partition") != DEVELOPMENT:
        raise ValueError(f"{path} is not a {DEVELOPMENT} report (ADR 0005).")
    return report


def _percent(value: float) -> str:
    return f"{value * 100:.1f}".replace(".", ",")


def format_proportion(proportion: Mapping[str, Any]) -> str:
    """``k/n (rate %) [lower; upper]`` with Wilson bounds in percent, or ``sin casos``."""
    if not proportion["trials"]:
        return "sin casos"
    return (
        f"{proportion['successes']}/{proportion['trials']} "
        f"({_percent(proportion['rate'])} %) "
        f"[{_percent(proportion['lower'])}; {_percent(proportion['upper'])}]"
    )


def _scored_entries(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [e for e in report["entries"] if "error" not in e]


def run_frame(report: Mapping[str, Any]) -> pd.DataFrame:
    """One row per scored run: alignment, gold links and machine links by verdict."""
    rows = []
    for entry in _scored_entries(report):
        verdicts = entry["findings"]["by_verdict"]
        score = entry["score"]
        rows.append(
            {
                "Serie": entry["series"],
                "Corrida": f"run-{entry['run']}",
                "Decisiones de la máquina": entry["alignment"]["machine_decisions"],
                "Decisiones de oro": entry["alignment"]["gold_decisions"],
                "Decisiones alineadas": entry["alignment"]["aligned"],
                "Enlaces de oro": score["n_gold_links"],
                "Enlaces de oro alineados": score["n_gold_links_aligned"],
                "Enlaces de la máquina": score["n_machine_links"],
                "reafirma": verdicts.get("reaffirms", 0),
                "refina": verdicts.get("refines", 0),
                "revierte o reemplaza": verdicts.get("reverses", 0),
                "sin relación": verdicts.get("unrelated", 0),
                "Enlaces con ambas decisiones alineadas": score["n_machine_links_aligned"],
            }
        )
    return pd.DataFrame(rows)


def existence_frame(report: Mapping[str, Any]) -> pd.DataFrame:
    """Link existence per run and pooled, in both scopes (end to end and conditional)."""
    labelled = [(f"run-{e['run']}", e["score"]) for e in _scored_entries(report)]
    labelled.append((POOLED_LABEL, report["pooled"]))
    rows = []
    for key, scope in _SCOPE_LABELS.items():
        for label, score in labelled:
            existence = score[key]
            f1 = existence["f1"]
            rows.append(
                {
                    "Ámbito": scope,
                    "Corrida": label,
                    "TP": existence["tp"],
                    "FP": existence["fp"],
                    "FN": existence["fn"],
                    "Precisión": format_proportion(existence["precision"]),
                    "Recall": format_proportion(existence["recall"]),
                    "F1": "no definido" if f1 is None else f"{f1:.3f}".replace(".", ","),
                    "FP sin par candidato": existence["fp_breakdown"]["not_candidate"],
                    "FP con decisión sin alinear": existence["fp_breakdown"]["unaligned"],
                }
            )
    return pd.DataFrame(rows)


def accuracy_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """Type and direction accuracy (principal and sensitivity) over the three denominators."""
    data = {
        row_label: [format_proportion(score[key][view]) for _, view in _ACCURACY_COLUMNS]
        for row_label, key in _ACCURACY_ROWS
    }
    return pd.DataFrame.from_dict(
        data, orient="index", columns=[label for label, _ in _ACCURACY_COLUMNS]
    )
