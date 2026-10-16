"""Video-legible figures for the AFG2 progress video (notebook ``11``).

The analysis lives elsewhere in :mod:`afg.eda`; this module only draws already-computed
tables with large fonts and exports them as PNG with a fixed resolution, so that a script can
embed the files. Every ``plot_*`` function returns a :class:`~matplotlib.figure.Figure` and
never shows or saves it. Call them inside ``with video_style():``.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from afg.eda.tables import format_thousands as _es

FIGURE_DPI = 150
_COLORS = ["#0173B2", "#DE8F05", "#029E73", "#D55E00"]  # colour-blind-safe (seaborn "colorblind")


def apply_style() -> None:
    """Set the matplotlib defaults of the exploration notebooks (screen-sized, light grid)."""
    plt.rcParams.update(
        {
            "figure.figsize": (9, 4),
            "figure.dpi": 110,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


@contextmanager
def video_style() -> Iterator[None]:
    """Matplotlib settings with large fonts and clean axes for a screen recording."""
    params: dict[str, Any] = {
        "font.size": 18,
        "axes.titlesize": 22,
        "axes.labelsize": 18,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16,
        "legend.fontsize": 16,
        "figure.figsize": (12, 6.75),
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
    }
    with plt.rc_context(cast("Any", params)):
        yield


def save_figure(fig: Figure, path: Path, *, dpi: int = FIGURE_DPI) -> Path:
    """Save ``fig`` as a deterministic PNG (no software/time metadata); create the folder."""
    path = Path(path)
    if path.suffix.lower() != ".png":
        raise ValueError(f"figures are exported as png, got {path.suffix!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, format="png", bbox_inches="tight", metadata={"Software": None})
    return path


def plot_level_sizes(sizes: Mapping[str, int], *, title: str = "") -> Figure:
    """Horizontal bars with the number of rows of each analysis level, on a log axis."""
    fig, ax = plt.subplots()
    labels = list(sizes)
    values = list(sizes.values())
    ax.barh(labels, values, color=_COLORS[0])
    ax.set_xscale("log")
    ax.invert_yaxis()
    ax.set_xlabel("Número de registros (escala logarítmica)")
    ax.grid(axis="y", visible=False)
    for y, value in enumerate(values):
        ax.text(value * 1.1, y, _es(value), va="center")
    ax.set_xlim(right=max(values) * 4)
    if title:
        ax.set_title(title, loc="left")
    return fig


def plot_rate_by_bin(rates: pd.DataFrame, *, xlabel: str, ylabel: str, title: str = "") -> Figure:
    """Bars of ``rate`` (as a percentage) per ``bin``; the table comes from ``rate_by_bin``."""
    fig, ax = plt.subplots()
    percent = rates["rate"] * 100
    ax.bar(rates["bin"].astype(str), percent, color=_COLORS[3])
    for x, value in enumerate(percent):
        ax.text(x, value, f"{_es(value, 1)} %", ha="center", va="bottom")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, percent.max() * 1.2 if percent.max() > 0 else 1)
    if title:
        ax.set_title(title, loc="left")
    return fig


def plot_rate_lines(
    table: pd.DataFrame,
    series: Mapping[str, str],
    *,
    xlabel: str,
    ylabel: str,
    title: str = "",
    x: str = "bin",
) -> Figure:
    """One line per entry of ``series`` (legend label -> rate column), in percent."""
    fig, ax = plt.subplots()
    for color, (label, column) in zip(_COLORS[3::-1], series.items(), strict=False):
        ax.plot(
            table[x].astype(str), table[column] * 100, marker="o", lw=3, color=color, label=label
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False)
    if title:
        ax.set_title(title, loc="left")
    return fig


def plot_funnel(
    stages: Mapping[str, int],
    *,
    hours: Sequence[float],
    control_survives: Sequence[bool | None],
    control_label: str,
    title: str = "",
) -> Figure:
    """Horizontal funnel: one bar per filtering stage, from the whole universe to the final set.

    Each bar is annotated with its count, its share of the first stage and the annotation
    ``hours`` it implies. ``control_survives`` holds, per stage, whether the control case
    (``control_label``) is still present (``True``/``False``) or ``None`` when the stage
    has no verdict (the unfiltered universe).
    """
    labels = list(stages)
    counts = list(stages.values())
    if len(hours) != len(labels) or len(control_survives) != len(labels):
        raise ValueError("hours and control_survives need one value per stage")
    fig, ax = plt.subplots()
    ax.barh(labels, counts, color=_COLORS[0], height=0.55)
    ax.invert_yaxis()
    ax.grid(visible=False)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    total = counts[0]
    pad = total * 0.015
    for y, (count, hrs, survives) in enumerate(zip(counts, hours, control_survives, strict=True)):
        ax.text(
            count + pad,
            y - 0.08,
            f"{_es(count)} pares ({_es(count / total * 100, 1)} %) · {_es(hrs, 1)} h",
            va="center",
            fontweight="bold",
        )
        if survives is not None:
            ax.text(
                count + pad,
                y + 0.24,
                f"{control_label}: {'se conserva' if survives else 'se pierde'}",
                va="center",
                fontsize=15,
                color=_COLORS[2] if survives else _COLORS[3],
            )
    ax.set_xlim(right=total * 1.9)
    if title:
        ax.set_title(title, loc="left")
    return fig


def plot_position_boxes(
    df: pd.DataFrame, value: str, *, ylabel: str, position: str = "position", title: str = ""
) -> Figure:
    """Box plot of ``value`` for each meeting position a-d, with the median written above."""
    order = ["a", "b", "c", "d"]
    fig, ax = plt.subplots()
    groups = [df.loc[df[position] == p, value].dropna() for p in order]
    ax.boxplot(
        groups,
        tick_labels=order,
        widths=0.5,
        patch_artist=True,
        boxprops={"facecolor": "#9CC5E0"},
        medianprops={"color": "black", "lw": 2.5},
    )
    top = max(g.max() for g in groups)
    for i, g in enumerate(groups, start=1):
        ax.text(i, g.max() + top * 0.03, _es(g.median(), 1), ha="center", va="bottom")
    ax.set_xlabel("Posición de la reunión en la serie")
    ax.set_ylabel(ylabel)
    ax.set_ylim(top=top * 1.15)
    if title:
        ax.set_title(title, loc="left")
    return fig
