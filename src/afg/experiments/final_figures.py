"""PNG figures of the final report, drawn from the tables of :mod:`afg.experiments.final_tables`.

One figure per question the report answers: Experiment A headline, Experiment B correctness by
condition and stratum, answer/judge latency, and OE4 stage shares. Colours are colour-blind safe
(Okabe-Ito). A stamped (development) figure carries the stamp in its title and as a footer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from afg.experiments.final_tables import FinalTables

_COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00")
_DPI = 130


def _save(fig: Figure, path: Path, *, title: str, stamp: str | None) -> Path:
    fig.suptitle(f"{title} — {stamp}" if stamp else title, fontsize=10)
    if stamp:
        fig.text(0.5, 0.01, stamp, ha="center", color="#B00020", fontsize=9)
    fig.tight_layout(rect=(0, 0.04 if stamp else 0, 1, 0.95))
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def _errors(frame: pd.DataFrame, value: str) -> list[list[float]]:
    return [
        (frame[value] - frame[f"{value}_lower"]).tolist(),
        (frame[f"{value}_upper"] - frame[value]).tolist(),
    ]


def _a_headline(table: pd.DataFrame, path: Path, stamp: str | None) -> Path:
    data = table[table["scope"] == "origin_meetings"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = [f"τ {t:.2f}" for t in data["tau"]]
    width = 0.25
    for i, name in enumerate(("precision", "recall", "f1")):
        xs = [x + (i - 1) * width for x in range(len(data))]
        ax.errorbar(
            xs,
            data[name],
            yerr=_errors(data, name),
            fmt="o",
            capsize=3,
            color=_COLORS[i],
            label=name.capitalize() if name != "f1" else "F1",
        )
    ax.set_xticks(range(len(data)), labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Valor (IC 95 % por reunión)")
    ax.legend(frameon=False, ncol=3, loc="upper right")
    return _save(fig, path, title="Experimento A: P, R y F1 por τ", stamp=stamp)


def _b_correct(table: pd.DataFrame, path: Path, stamp: str | None) -> Path:
    # A condition in two runs would draw twice; the first run wins.
    data = table[table["correct"].notna()].drop_duplicates(["condition", "stratum"])
    strata = list(dict.fromkeys(data["stratum"]))
    conditions = sorted(set(data["condition"]))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    width = 0.8 / max(1, len(conditions))
    for i, condition in enumerate(conditions):
        sub = (
            data[data["condition"] == condition]
            .set_index("stratum")
            .reindex(strata)
            .dropna(subset=["correct"])
        )
        xs = [strata.index(s) + (i - (len(conditions) - 1) / 2) * width for s in sub.index]
        ax.errorbar(
            xs,
            sub["correct"],
            yerr=_errors(sub, "correct"),
            fmt="o",
            capsize=3,
            color=_COLORS[i % len(_COLORS)],
            label=condition,
        )
    ax.set_xticks(range(len(strata)), strata, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Respuesta correcta (IC 95 % por pregunta)")
    ax.legend(frameon=False, title="Condición")
    return _save(fig, path, title="Experimento B: corrección por condición y estrato", stamp=stamp)


def _cost(table: pd.DataFrame, path: Path, stamp: str | None) -> Path:
    data = table[table["role"].isin(["answer", "judge"])]
    fig, ax = plt.subplots(figsize=(8, 0.6 * max(3, len(data)) + 1))
    colors = [_COLORS[0] if r == "answer" else _COLORS[1] for r in data["role"]]
    labels = [f"{a} ({r})" for a, r in zip(data["activity"], data["role"], strict=True)]
    ax.barh(range(len(data)), data["mean_seconds"], color=colors)
    ax.set_yticks(range(len(data)), labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Segundos por consulta (promedio, tiempo de pared)")
    return _save(fig, path, title="Latencia de respuesta y de juez por condición", stamp=stamp)


def _oe4(table: pd.DataFrame, path: Path, stamp: str | None) -> Path:
    wide = table.pivot_table(index="condition", columns="stage", values="share", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7, 0.7 * max(2, len(wide)) + 1.5))
    left = pd.Series(0.0, index=wide.index)
    for i, stage in enumerate(wide.columns):
        ax.barh(
            wide.index,
            wide[stage].fillna(0),
            left=left,
            color=_COLORS[i % len(_COLORS)],
            label=stage,
        )
        left = left + wide[stage].fillna(0)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Parte de las fallas")
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    return _save(fig, path, title="OE4: etapa de las fallas", stamp=stamp)


def draw_all(final: FinalTables, name: str, figures_dir: Path) -> list[Path]:
    """Every figure whose table is present and non-empty; returns the PNG paths written."""
    from afg.experiments.final_tables import STAMP

    stamp = STAMP if final.stamped else None
    tables = final.tables
    jobs = (
        ("a-headline", "a-headline", _a_headline),
        ("b-cells", "b-correct", _b_correct),
        ("cost-latency", "cost-latency", _cost),
        ("oe4-stages", "oe4-stages", _oe4),
    )
    paths = []
    for key, stem, draw in jobs:
        frame = tables.get(key)
        if frame is not None and not frame.empty:
            paths.append(draw(frame, figures_dir / f"{name}-{stem}.png", stamp))
    return paths
