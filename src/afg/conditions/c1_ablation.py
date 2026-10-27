"""Retrieval-channel ablation for C1 on development data (ADR 0005).

C1 retrieves with BM25 and dense search fused by RRF (``c1_retrieval``), but its tuning
(``c1_tuning``) only explored that hybrid mode. This module measures what each channel
contributes: ``bm25`` alone, ``dense`` alone and ``hybrid`` (C1), all at the pinned C1
parameters (``[retrieval.c1]``) and over the same questions. It reuses
:func:`afg.conditions.c1_tuning.evaluate_grid`, so the figures (evidence recall, delivered
recall, first-hit ranks) are exactly the ones ``afg c1 tune`` reports; nothing generative
is involved.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from afg.conditions.c1_retrieval import RETRIEVAL_MODES, Embedder
from afg.conditions.c1_tuning import (
    ConfigResult,
    PinnedC1Params,
    TuningConfig,
    TuningQuestion,
    evaluate_grid,
    questions_with_any_delivered_hit,
    questions_with_any_hit,
    result_to_json,
)
from afg.shared.paths import REPORTS_DIR, TRANSCRIPTS_DIR

ABLATION_PATH: Path = REPORTS_DIR / "c1-tuning" / "ablacion-recuperacion.json"


@dataclass(frozen=True, slots=True)
class ModeResult:
    """Metrics of one retrieval mode at the pinned parameters."""

    mode: str
    result: ConfigResult


def evaluate_modes(
    questions: Sequence[TuningQuestion],
    meeting_ids: Sequence[str],
    params: PinnedC1Params,
    config: TuningConfig,
    embedder: Embedder,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    *,
    modes: Sequence[str] = RETRIEVAL_MODES,
) -> list[ModeResult]:
    """Measure each of ``modes`` at ``params``; ``config`` supplies the character budget.

    Raises:
        ValueError: if a mode is unknown or there are no questions.
    """
    unknown = [m for m in modes if m not in RETRIEVAL_MODES]
    if unknown:
        raise ValueError(f"Unknown retrieval mode(s) {unknown}; expected {RETRIEVAL_MODES}.")
    point = replace(
        config,
        max_chars=(params.max_chars,),
        overlap_turns=(params.overlap_turns,),
        k=(params.k,),
    )
    return [
        ModeResult(
            mode,
            evaluate_grid(questions, meeting_ids, point, embedder, transcripts_dir, mode=mode)[0],
        )
        for mode in modes
    ]


def save_ablation_results(
    path: Path,
    results: Sequence[ModeResult],
    *,
    params: PinnedC1Params,
    config: TuningConfig,
    n_questions: int,
    git_commit: str | None,
) -> None:
    """Write the ablation as JSON (UTF-8, LF), creating the folder."""
    payload = {
        "git_commit": git_commit,
        "n_questions": n_questions,
        "config": {"series": list(config.series), "char_budget": config.char_budget},
        "params": {
            "max_chars": params.max_chars,
            "overlap_turns": params.overlap_turns,
            "k": params.k,
        },
        "modes": [
            {
                "mode": r.mode,
                **result_to_json(r.result),
                "questions_with_any_hit": questions_with_any_hit(r.result),
                "questions_with_any_delivered_hit": questions_with_any_delivered_hit(r.result),
            }
            for r in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
