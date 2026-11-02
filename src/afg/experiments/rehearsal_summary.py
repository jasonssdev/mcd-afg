"""Notebook-facing tables for the full-chain rehearsal on ES2015 (issue #255).

The rehearsal is a development run: every table it reads carries the mark
``desarrollo — no reportable`` and nothing here computes a statistic; the figures come from the
stored reports and tables written by the ``afg experiment`` commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from afg.experiments.analysis import H4_METRICS, H4_STRATUM, verdict_label

__all__ = [
    "correctness_frame",
    "load_development_json",
    "load_rehearsal_table",
    "steps_frame",
    "verdict_frame",
]

DEVELOPMENT = "development"
DEVELOPMENT_MARK = "desarrollo"

# (step, command, duration, result) as observed in the rehearsal of 2026-11-02, 1 run.
_STEPS: tuple[tuple[str, str, str, str], ...] = (
    (
        "1. Extracción de C2",
        "afg experiment a --series ES2015 --runs 1 --run-name ensayo-es2015",
        "25 min 47 s",
        "ok: 71 decisiones",
    ),
    (
        "2. Relaciones",
        "afg experiment a-relations --c2-extraction ensayo-es2015 --run-revisions",
        "2 min 52 s",
        "ok",
    ),
    (
        "3. Informe de A",
        "afg experiment a-report --c2-extraction ensayo-es2015 --descriptive",
        "10 s",
        "ok",
    ),
    (
        "4. Base de C3",
        "afg c3 build --c2-extraction ensayo-es2015 --series ES2015 --runs 1",
        "15 s",
        "ok: 27 decisiones de oro",
    ),
    (
        "5. Experimento B",
        "afg experiment b --conditions c0,c1,c2,c3 --c2-extraction ensayo-es2015 "
        "--run-name ensayo-b-es2015 --runs 1 --questions ES2015.preguntas.csv",
        "27 min 30 s",
        "ok: 84 registros, 0 errores",
    ),
    (
        "6a. Informe de B",
        "afg experiment b-report --run-name ensayo-b-es2015 --descriptive --questions ...",
        "2 s",
        "ok",
    ),
    (
        "6b. Hoja OE4",
        "afg experiment b-oe4-sheet --run-name ensayo-b-es2015",
        "1 s",
        "ok: 14 filas",
    ),
    (
        "6c. Muestra humana",
        "afg experiment b-sample --run-name ensayo-b-es2015",
        "1 s",
        "ok: 24 filas",
    ),
    (
        "6d. Resumen OE4 y acuerdo juez-humano",
        "afg experiment b-oe4-summary / b-human-check",
        "-",
        "omitido: requiere etiquetas humanas",
    ),
    (
        "7. Tablas finales",
        "afg experiment final-tables --name ensayo-es2015 --descriptive",
        "1 s",
        "ok: 6 tablas y 3 figuras",
    ),
)


def steps_frame() -> pd.DataFrame:
    """The rehearsal steps with their command, duration and result."""
    return pd.DataFrame(_STEPS, columns=["Paso", "Comando", "Duración", "Resultado"])


def load_development_json(path: Path) -> dict[str, Any]:
    """Read a stored report.

    Raises:
        ValueError: the report is not of the development partition (ADR 0005).
    """
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if data.get("partition") != DEVELOPMENT:
        raise ValueError(f"{path} is not a {DEVELOPMENT} report (ADR 0005).")
    return data


def load_rehearsal_table(path: Path) -> pd.DataFrame:
    """Read a table of ``reports/tables/`` and check it carries the development mark.

    Raises:
        ValueError: some row is not marked ``desarrollo — no reportable`` (ADR 0005).
    """
    frame = pd.read_csv(path)
    marks = frame["status"].astype(str)
    if not marks.str.contains(DEVELOPMENT_MARK).all():
        raise ValueError(f"{path} has rows without the 'desarrollo' mark (ADR 0005).")
    return frame


def correctness_frame(cells: pd.DataFrame) -> pd.DataFrame:
    """Correctness per condition (rows) and stratum (columns) as ``rate (questions)``."""
    shown = cells.assign(
        text=lambda f: [
            f"{rate:.2f}".replace(".", ",") + f" ({int(n)})"
            for rate, n in zip(f["correct"], f["questions"], strict=True)
        ]
    )
    return shown.pivot(index="condition", columns="stratum", values="text").rename_axis(
        index="Condición", columns="Estrato"
    )


def _signed(value: float) -> str:
    return f"{value:+.2f}".replace(".", ",")


def verdict_frame(analysis: dict[str, Any]) -> pd.DataFrame:
    """D16, H2 and H4 verdicts of an analysis, with the numbers and the sample behind each."""
    rows: list[dict[str, Any]] = []
    for c in analysis["comparisons"]:
        if c["descriptive"]:
            continue
        if c["primary"]:
            name = f"D16 ({c['condition_a']} - {c['condition_b']}, E3)"
        elif c["stratum"] == H4_STRATUM and c["metric"] in H4_METRICS:
            name = f"H4 {c['metric']} ({c['condition_a']} - {c['condition_b']})"
        else:
            continue
        rows.append(
            {
                "Hipótesis": name,
                "Preguntas": c["n_pairs"],
                "Diferencia": (
                    f"{_signed(c['difference'])} [{_signed(c['difference_lower'])}, "
                    f"{_signed(c['difference_upper'])}]"
                ),
                "Veredicto": verdict_label(c["criterion"]),
            }
        )
    h2 = analysis["h2"]
    if h2.get("difference") is not None:
        rows.append(
            {
                "Hipótesis": "H2 (brecha E3 - E1)",
                "Preguntas": f"E1 {h2['n_e1']}, E3 {h2['n_e3']}",
                "Diferencia": (
                    f"{_signed(h2['difference'])} [{_signed(h2['difference_lower'])}, "
                    f"{_signed(h2['difference_upper'])}]"
                ),
                "Veredicto": verdict_label(h2["verdict"]),
            }
        )
    return pd.DataFrame(rows, columns=["Hipótesis", "Preguntas", "Diferencia", "Veredicto"])
