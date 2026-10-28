"""Tests for ``afg.eda.figures`` (video-legible figures and PNG export)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from afg.eda.figures import (
    FIGURE_DPI,
    apply_style,
    plot_funnel,
    plot_grouped_bars,
    plot_hbars,
    plot_labeled_scatter,
    plot_level_sizes,
    plot_position_boxes,
    plot_rate_by_bin,
    plot_rate_lines,
    save_figure,
    video_style,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def _close_figures() -> None:
    yield
    plt.close("all")


class TestVideoStyle:
    def test_enlarges_fonts_inside_the_context_only(self) -> None:
        before = plt.rcParams["font.size"]
        with video_style():
            inside = plt.rcParams["font.size"]
        assert inside >= 16
        assert inside > before
        assert plt.rcParams["font.size"] == before


class TestSaveFigure:
    def test_writes_a_png_and_creates_missing_folders(self, tmp_path: Path) -> None:
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        target = tmp_path / "nested" / "dir" / "figura.png"
        out = save_figure(fig, target)
        assert out == target
        assert target.read_bytes().startswith(PNG_SIGNATURE)

    def test_same_figure_saved_twice_is_byte_identical(self, tmp_path: Path) -> None:
        fig, ax = plt.subplots()
        ax.bar(["a", "b"], [1, 2])
        first = save_figure(fig, tmp_path / "uno.png")
        second = save_figure(fig, tmp_path / "dos.png")
        assert first.read_bytes() == second.read_bytes()

    def test_default_dpi_is_150(self) -> None:
        assert FIGURE_DPI == 150

    def test_rejects_a_non_png_target(self, tmp_path: Path) -> None:
        fig, _ = plt.subplots()
        with pytest.raises(ValueError, match="png"):
            save_figure(fig, tmp_path / "figura.jpg")


class TestPlotLevelSizes:
    def test_one_bar_per_level_in_the_given_order(self) -> None:
        sizes = {"Serie": 14, "Reunión": 56, "Decisión": 343}
        fig = plot_level_sizes(sizes)
        assert isinstance(fig, Figure)
        ax = fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert labels == ["Serie", "Reunión", "Decisión"]
        assert [p.get_width() for p in ax.patches] == [14, 56, 343]

    def test_counts_are_written_next_to_the_bars_in_spanish_format(self) -> None:
        fig = plot_level_sizes({"Par": 3071, "Serie": 14})
        texts = {t.get_text() for t in fig.axes[0].texts}
        assert "3.071" in texts
        assert "14" in texts


class TestPlotRateByBin:
    def test_bars_are_percentages_with_labels(self) -> None:
        rates = pd.DataFrame(
            {"bin": ["a", "b"], "n": [50, 100], "n_true": [0, 5], "rate": [0.0, 0.05]}
        )
        fig = plot_rate_by_bin(rates, xlabel="x", ylabel="y")
        ax = fig.axes[0]
        assert [p.get_height() for p in ax.patches] == [0.0, 5.0]
        texts = {t.get_text() for t in ax.texts}
        assert "5,0 %" in texts
        assert "0,0 %" in texts


class TestPlotFunnel:
    STAGES: ClassVar[dict[str, int]] = {
        "Todos los pares": 1000,
        "Primer filtro": 200,
        "Filtro completo": 20,
    }

    def test_one_bar_per_stage_with_count_percentage_and_hours(self) -> None:
        fig = plot_funnel(
            self.STAGES,
            hours=[25.0, 5.0, 0.5],
            control_survives=[None, True, True],
            control_label="Control",
        )
        ax = fig.axes[0]
        assert [p.get_width() for p in ax.patches] == [1000, 200, 20]
        texts = " | ".join(t.get_text() for t in ax.texts)
        assert "1.000" in texts and "20,0 %" in texts and "2,0 %" in texts
        assert "25,0 h" in texts and "0,5 h" in texts

    def test_control_is_marked_only_on_stages_that_have_a_verdict(self) -> None:
        fig = plot_funnel(
            self.STAGES,
            hours=[25.0, 5.0, 0.5],
            control_survives=[None, True, False],
            control_label="Control",
        )
        texts = [t.get_text() for t in fig.axes[0].texts]
        assert sum("Control: se conserva" in t for t in texts) == 1
        assert sum("Control: se pierde" in t for t in texts) == 1

    def test_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError, match="one value per stage"):
            plot_funnel(
                self.STAGES, hours=[1.0], control_survives=[None, True, True], control_label="C"
            )


class TestPlotPositionBoxes:
    def test_one_box_per_position_with_median_labels(self) -> None:
        df = pd.DataFrame(
            {
                "position": list("aabbccdd"),
                "n_decisions": [3, 4, 7, 9, 6, 7, 6, 8],
            }
        )
        fig = plot_position_boxes(df, "n_decisions", ylabel="Decisiones")
        ax = fig.axes[0]
        assert [t.get_text() for t in ax.get_xticklabels()] == ["a", "b", "c", "d"]
        assert {t.get_text() for t in ax.texts} == {"3,5", "8,0", "6,5", "7,0"}


class TestPlotRateLines:
    def test_one_line_per_series_in_percent(self) -> None:
        table = pd.DataFrame(
            {"bin": ["1", "2", "3"], "solo": [0.4, 0.2, 0.1], "filtro": [0.02, 0.01, 0.0]}
        )
        fig = plot_rate_lines(
            table,
            {"Solo el coeficiente": "solo", "Filtro completo": "filtro"},
            xlabel="Tokens",
            ylabel="% que pasan",
        )
        ax = fig.axes[0]
        assert len(ax.lines) == 2
        assert list(ax.lines[0].get_ydata()) == pytest.approx([40.0, 20.0, 10.0])
        assert [t.get_text() for t in ax.get_legend().get_texts()] == [
            "Solo el coeficiente",
            "Filtro completo",
        ]


class TestApplyStyle:
    def test_sets_the_exploration_defaults_the_notebooks_share(self) -> None:
        with plt.rc_context():
            apply_style()
            assert tuple(plt.rcParams["figure.figsize"]) == (9, 4)
            assert plt.rcParams["figure.dpi"] == 110
            assert plt.rcParams["axes.grid"] is True
            assert plt.rcParams["grid.alpha"] == 0.3
            assert plt.rcParams["axes.spines.top"] is False
            assert plt.rcParams["axes.spines.right"] is False

    def test_is_idempotent(self) -> None:
        with plt.rc_context():
            apply_style()
            first = dict(plt.rcParams)
            apply_style()
            assert dict(plt.rcParams) == first


class TestPlotGroupedBars:
    def test_one_bar_per_group_and_category_with_values_written(self) -> None:
        fig = plot_grouped_bars(
            ["E1", "E2"],
            {"C0": [20.0, 0.0], "C1": [71.4, 100.0]},
            ylabel="% correctas",
        )
        ax = fig.axes[0]
        assert [p.get_height() for p in ax.patches] == [20.0, 0.0, 71.4, 100.0]
        texts = {t.get_text() for t in ax.texts}
        assert {"20", "0", "71,4", "100"} <= texts
        assert [t.get_text() for t in ax.get_xticklabels()] == ["E1", "E2"]
        assert {t.get_text() for t in ax.get_legend().get_texts()} == {"C0", "C1"}

    def test_decimals_fix_the_precision_of_every_bar_label(self) -> None:
        fig = plot_grouped_bars(["S1"], {"A": [0.289], "B": [0.5]}, ylabel="F1", decimals=3)
        assert {t.get_text() for t in fig.axes[0].texts} == {"0,289", "0,500"}

    def test_a_group_with_the_wrong_number_of_values_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="C1"):
            plot_grouped_bars(["E1", "E2"], {"C1": [1.0]}, ylabel="y")

    def test_missing_values_are_left_without_a_bar_label(self) -> None:
        fig = plot_grouped_bars(["E1", "E2"], {"C1": [50.0, float("nan")]}, ylabel="y")
        assert {t.get_text() for t in fig.axes[0].texts} == {"50"}


class TestPlotLabeledScatter:
    POINTS: ClassVar[list[tuple[str, float, float]]] = [
        ("qwen3:8b", 165.7, 0.289),
        ("qwen3.6:27b", 597.6, 0.470),
    ]

    def test_one_point_per_entry_with_its_label(self) -> None:
        fig = plot_labeled_scatter(self.POINTS, xlabel="s", ylabel="F1")
        ax = fig.axes[0]
        assert {t.get_text() for t in ax.texts} == {"qwen3:8b", "qwen3.6:27b"}
        assert len(ax.collections[0].get_offsets()) == 2

    def test_log_axis_is_optional(self) -> None:
        fig = plot_labeled_scatter(self.POINTS, xlabel="s", ylabel="F1", log_x=True)
        assert fig.axes[0].get_xscale() == "log"


class TestPlotHbars:
    def test_bars_in_the_given_order_with_annotations(self) -> None:
        fig = plot_hbars(
            {"respuesta": 10.0, "extracción": 600.0},
            annotations=["10 s", "600 s"],
            xlabel="s",
            log_x=True,
        )
        ax = fig.axes[0]
        assert [t.get_text() for t in ax.get_yticklabels()] == ["respuesta", "extracción"]
        assert [p.get_width() for p in ax.patches] == [10.0, 600.0]
        assert {"10 s", "600 s"} <= {t.get_text() for t in ax.texts}

    def test_annotations_must_match_the_bars(self) -> None:
        with pytest.raises(ValueError, match="annotations"):
            plot_hbars({"a": 1.0}, annotations=[], xlabel="x")
