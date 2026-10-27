"""Tests for the C1 retrieval-mode ablation. No network: fake embedders only."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.conditions.c1_ablation import evaluate_modes, load_ablation_results, save_ablation_results
from afg.conditions.c1_tuning import PinnedC1Params, evaluate_grid
from tests.test_c1_tuning import (
    LetterEmbedder,
    questions,
    small_config,
    transcripts,  # noqa: F401 - pytest fixture
)

PARAMS = PinnedC1Params(max_chars=40, overlap_turns=0, k=1)


class CountingEmbedder(LetterEmbedder):
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return super().embed(texts)


def test_one_result_per_mode_at_the_pinned_params(transcripts: Path) -> None:  # noqa: F811
    results = evaluate_modes(
        questions(), ["ES2015a"], PARAMS, small_config(), LetterEmbedder(), transcripts
    )
    assert [r.mode for r in results] == ["bm25", "dense", "hybrid"]
    for r in results:
        assert (r.result.max_chars, r.result.overlap_turns, r.result.k) == (40, 0, 1)
        assert set(r.result.recalls) == {"q1", "q2"}


def test_hybrid_mode_equals_the_tuning_grid_at_the_same_point(transcripts: Path) -> None:  # noqa: F811
    config = small_config(max_chars=(40,), overlap_turns=(0,), k=(1,))
    (grid,) = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    hybrid = next(
        r
        for r in evaluate_modes(
            questions(), ["ES2015a"], PARAMS, small_config(), LetterEmbedder(), transcripts
        )
        if r.mode == "hybrid"
    )
    assert hybrid.result == grid


def test_lexical_questions_are_found_by_bm25_at_rank_one(transcripts: Path) -> None:  # noqa: F811
    results = evaluate_modes(
        questions(), ["ES2015a"], PARAMS, small_config(), LetterEmbedder(), transcripts
    )
    bm25 = results[0].result
    assert bm25.first_hit_ranks == {"q1": 1, "q2": 1}
    assert bm25.mean_recall == 1.0


def test_bm25_mode_never_calls_the_embedder(transcripts: Path) -> None:  # noqa: F811
    embedder = CountingEmbedder()
    evaluate_modes(
        questions(), ["ES2015a"], PARAMS, small_config(), embedder, transcripts, modes=("bm25",)
    )
    assert embedder.calls == 0


def test_unknown_mode_is_rejected(transcripts: Path) -> None:  # noqa: F811
    with pytest.raises(ValueError, match="mode"):
        evaluate_modes(
            questions(),
            ["ES2015a"],
            PARAMS,
            small_config(),
            LetterEmbedder(),
            transcripts,
            modes=("sparse",),
        )


def test_evaluate_grid_mode_defaults_to_hybrid(transcripts: Path) -> None:  # noqa: F811
    config = small_config(max_chars=(40,), overlap_turns=(0,), k=(1,))
    default = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    explicit = evaluate_grid(
        questions(), ["ES2015a"], config, LetterEmbedder(), transcripts, mode="hybrid"
    )
    assert default == explicit


def test_results_file_carries_config_modes_and_commit(
    transcripts: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    results = evaluate_modes(
        questions(), ["ES2015a"], PARAMS, small_config(), LetterEmbedder(), transcripts
    )
    path = tmp_path / "out" / "ablacion.json"
    save_ablation_results(
        path, results, params=PARAMS, config=small_config(), n_questions=2, git_commit="abc123"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["git_commit"] == "abc123"
    assert data["n_questions"] == 2
    assert data["config"]["series"] == ["ES2015"]
    assert data["params"] == {"max_chars": 40, "overlap_turns": 0, "k": 1}
    assert [m["mode"] for m in data["modes"]] == ["bm25", "dense", "hybrid"]
    first = data["modes"][0]
    assert {"mean_recall", "mean_delivered_recall", "recalls", "delivered_recalls"} <= set(first)
    assert first["questions_with_any_hit"] == sum(
        1 for rank in first["first_hit_ranks"].values() if rank is not None
    )


def test_stored_ablation_is_read_back_with_its_modes_and_params(
    transcripts: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    results = evaluate_modes(
        questions(), ["ES2015a"], PARAMS, small_config(), LetterEmbedder(), transcripts
    )
    path = tmp_path / "ablacion.json"
    save_ablation_results(
        path, results, params=PARAMS, config=small_config(), n_questions=2, git_commit="abc123"
    )

    stored = load_ablation_results(path)

    assert stored.n_questions == 2
    assert stored.git_commit == "abc123"
    assert stored.params == PARAMS
    assert stored.modes == tuple(results)


def test_an_unreadable_ablation_file_is_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "ablacion.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"ablacion.json"):
        load_ablation_results(path)
