"""Tuning of C1 segmentation and of the common K on development data (ADR 0005).

The experiment fixes how many blocks (K) reach the answer prompt and how C1 cuts the
transcripts (``max_chars``, ``overlap_turns``). Both are chosen here, before any evaluation
series is touched, by measuring **evidence recall** and nothing generative: the fraction of
the dialogue acts that support the reference answer (``reference_evidence``) which are
contained in the K chunks retrieved for the question. A chunk contains the acts of the turns
it covers (``Chunk.dialogue_act_ids``).

The grid, the character budget and the tie margin live in ``[retrieval.tuning]`` of
``config/experiments.toml`` and are committed before any result is seen. The selection rule
(:func:`select_winner`) is a pure function of the results.

Cost: the index is built once per ``(max_chars, overlap_turns)`` and each question is
retrieved once with the largest K of the grid; the ranking for a smaller K is its prefix.
That holds only while the retriever's candidate pool is fixed, i.e. K <= ``MIN_POOL``
(``max(limit, MIN_POOL)`` candidates per channel); above that the pool grows with the limit
and the ranking can change, so the grid retrieves once per K instead.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.conditions.c1_chunking import Chunk, chunk_meetings
from afg.conditions.c1_retrieval import MIN_POOL, Embedder, HybridRetriever, configured_rrf_k
from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.shared.config import load_experiments_config
from afg.shared.paths import REPORTS_DIR, TRANSCRIPTS_DIR

RESULTS_PATH: Path = REPORTS_DIR / "c1-tuning" / "resultados.json"


class NoEligibleConfigError(ValueError):
    """Raised when no configuration fits the character budget."""


# --- metrics ---------------------------------------------------------------------------


def _acts(evidence: Sequence[EvidenceSpan]) -> set[tuple[str, str]]:
    return {(span.meeting_id, act) for span in evidence for act in span.dialogue_act_ids}


def evidence_recall(retrieved: Sequence[Chunk], evidence: Sequence[EvidenceSpan]) -> float:
    """Fraction of the reference dialogue acts contained in the union of ``retrieved``.

    Raises:
        ValueError: if ``evidence`` is empty (unanswerable questions are excluded upstream).
    """
    wanted = _acts(evidence)
    if not wanted:
        raise ValueError("evidence_recall needs reference evidence; E4 questions have none.")
    found = {(c.meeting_id, act) for c in retrieved for act in c.dialogue_act_ids}
    return len(wanted & found) / len(wanted)


def first_hit_rank(retrieved: Sequence[Chunk], evidence: Sequence[EvidenceSpan]) -> int | None:
    """1-based rank of the first chunk holding any reference act; ``None`` if none does."""
    wanted = _acts(evidence)
    for rank, c in enumerate(retrieved, start=1):
        if any((c.meeting_id, act) in wanted for act in c.dialogue_act_ids):
            return rank
    return None


# --- configuration ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TuningConfig:
    """The pre-registered grid and selection parameters (``[retrieval.tuning]``)."""

    series: tuple[str, ...]
    max_chars: tuple[int, ...]
    overlap_turns: tuple[int, ...]
    k: tuple[int, ...]
    char_budget: int
    tie_margin: float


def load_tuning_config(
    experiments: dict[str, Any] | None = None, development: frozenset[str] | None = None
) -> TuningConfig:
    """Read ``[retrieval.tuning]``, refusing any series outside the development split.

    Raises:
        ValueError: if a listed series is not a development series (ADR 0005) or a list is
            empty.
    """
    from afg.evaluation.judge_calibration_set import development_series

    section = (experiments or load_experiments_config())["retrieval"]["tuning"]
    allowed = development if development is not None else development_series()
    series = tuple(section["series"])
    outside = sorted(set(series) - allowed)
    if outside:
        raise ValueError(
            f"[retrieval.tuning].series lists {outside}, which are not development series "
            f"{sorted(allowed)} (ADR 0005): C1 is tuned on development data only."
        )
    config = TuningConfig(
        series=series,
        max_chars=tuple(int(v) for v in section["max_chars"]),
        overlap_turns=tuple(int(v) for v in section["overlap_turns"]),
        k=tuple(int(v) for v in section["k"]),
        char_budget=int(section["char_budget"]),
        tie_margin=float(section["tie_margin"]),
    )
    if not (config.series and config.max_chars and config.overlap_turns and config.k):
        raise ValueError("[retrieval.tuning] needs non-empty series, max_chars, overlap_turns, k.")
    return config


# --- questions -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TuningQuestion:
    question_id: str
    stratum: QuestionStratum
    question: str
    evidence: tuple[EvidenceSpan, ...]


def load_tuning_questions(path: Path, series: Sequence[str]) -> list[TuningQuestion]:
    """Answerable (E1-E3) questions of ``series`` from the calibration set, once each.

    The calibration set carries every question twice or more (one row per answer variant,
    ``<series>.<question>.<variant>``); the question id is the id without the variant.
    """
    from afg.evaluation.judge_calibration_set import load_calibration_items

    questions: dict[str, TuningQuestion] = {}
    for item in load_calibration_items(path):
        if item.series_id not in series or item.stratum is QuestionStratum.E4_UNANSWERABLE:
            continue
        question_id = item.id.rsplit(".", 1)[0]
        questions.setdefault(
            question_id,
            TuningQuestion(question_id, item.stratum, item.question, item.reference_evidence),
        )
    return list(questions.values())


def series_meetings(series: str, transcripts_dir: Path = TRANSCRIPTS_DIR) -> list[str]:
    """Meeting ids of ``series`` with a frozen transcript, sorted (D15: the whole series)."""
    ids = sorted(
        p.stem for p in transcripts_dir.glob(f"{series}?.jsonl") if len(p.stem) == len(series) + 1
    )
    if not ids:
        raise FileNotFoundError(
            f"No frozen transcripts for series {series} in {transcripts_dir}. "
            "Render them first (`uv run afg corpus transcripts`)."
        )
    return ids


# --- grid ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfigResult:
    """Recall of one ``(max_chars, overlap_turns, k)`` configuration."""

    max_chars: int
    overlap_turns: int
    k: int
    mean_recall: float
    recalls: dict[str, float]
    first_hit_ranks: dict[str, int | None]
    mean_context_chars: float
    n_chunks: int
    eligible: bool


ProgressFn = Callable[[int, int, int, int], None]
"""``(max_chars, overlap_turns, done, total)`` after each chunking configuration."""


def evaluate_grid(
    questions: Sequence[TuningQuestion],
    meeting_ids: Sequence[str],
    config: TuningConfig,
    embedder: Embedder,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    *,
    rrf_k: int | None = None,
    progress: ProgressFn | None = None,
) -> list[ConfigResult]:
    """Measure evidence recall for every ``(max_chars, overlap_turns, k)`` of the grid."""
    if not questions:
        raise ValueError("evaluate_grid needs at least one question (got no questions).")
    ks = sorted(set(config.k))
    # Top-K is a prefix of top-maxK only while the candidate pool is fixed (see module doc).
    prefix_stable = ks[-1] <= MIN_POOL
    fusion_k = rrf_k if rrf_k is not None else configured_rrf_k()
    pairs = [(m, o) for m in config.max_chars for o in config.overlap_turns]
    results: list[ConfigResult] = []
    for done, (max_chars, overlap) in enumerate(pairs, start=1):
        chunks = chunk_meetings(meeting_ids, max_chars, overlap, transcripts_dir)
        retriever = HybridRetriever(chunks, embedder, rrf_k=fusion_k)
        rankings: dict[str, dict[int, list[Chunk]]] = {}
        for q in questions:
            if prefix_stable:
                full = [h.chunk for h in retriever.retrieve(q.question, ks[-1])]
                rankings[q.question_id] = {k: full[:k] for k in ks}
            else:
                rankings[q.question_id] = {
                    k: [h.chunk for h in retriever.retrieve(q.question, k)] for k in ks
                }
        for k in ks:
            recalls = {
                q.question_id: evidence_recall(rankings[q.question_id][k], q.evidence)
                for q in questions
            }
            ranks = {
                q.question_id: first_hit_rank(rankings[q.question_id][k], q.evidence)
                for q in questions
            }
            context = [sum(len(c.text) for c in rankings[q.question_id][k]) for q in questions]
            results.append(
                ConfigResult(
                    max_chars=max_chars,
                    overlap_turns=overlap,
                    k=k,
                    mean_recall=sum(recalls.values()) / len(recalls),
                    recalls=recalls,
                    first_hit_ranks=ranks,
                    mean_context_chars=sum(context) / len(context),
                    n_chunks=len(chunks),
                    eligible=k * max_chars <= config.char_budget,
                )
            )
        if progress is not None:
            progress(max_chars, overlap, done, len(pairs))
    return results


# --- selection -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Selection:
    winner: ConfigResult
    best_recall: float
    near_ties: int
    reason: str


def select_winner(results: Sequence[ConfigResult], tie_margin: float) -> Selection:
    """The pre-registered rule: highest recall among eligible, ties by smaller cost.

    Among eligible configurations whose mean recall is within ``tie_margin`` (inclusive) of
    the best, the winner has the smaller ``k``, then smaller ``max_chars``, then smaller
    ``overlap_turns``.

    Raises:
        NoEligibleConfigError: if no configuration fits the character budget.
    """
    eligible = [r for r in results if r.eligible]
    if not eligible:
        raise NoEligibleConfigError(
            "No configuration fits the char_budget (k * max_chars <= char_budget); "
            "the pre-registered grid has no admissible point."
        )
    best = max(r.mean_recall for r in eligible)
    # Small epsilon so a gap of exactly tie_margin is not lost to float rounding.
    near = [r for r in eligible if best - r.mean_recall <= tie_margin + 1e-12]
    winner = min(near, key=lambda r: (r.k, r.max_chars, r.overlap_turns))
    reason = (
        f"best eligible mean recall {best:.3f}; {len(near)} eligible config(s) within "
        f"{tie_margin:g}; chose the smallest k, then max_chars, then overlap_turns "
        f"(recall {winner.mean_recall:.3f})."
    )
    return Selection(winner=winner, best_recall=best, near_ties=len(near), reason=reason)


# --- results file ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoredTuning:
    config: TuningConfig
    n_questions: int
    results: tuple[ConfigResult, ...]
    winner: ConfigResult
    reason: str


def _result_to_json(r: ConfigResult) -> dict[str, Any]:
    return {
        "max_chars": r.max_chars,
        "overlap_turns": r.overlap_turns,
        "k": r.k,
        "mean_recall": r.mean_recall,
        "recalls": r.recalls,
        "first_hit_ranks": r.first_hit_ranks,
        "mean_context_chars": r.mean_context_chars,
        "n_chunks": r.n_chunks,
        "eligible": r.eligible,
    }


def save_tuning_results(
    path: Path,
    results: Sequence[ConfigResult],
    selection: Selection,
    *,
    config: TuningConfig,
    n_questions: int,
) -> None:
    """Write the grid results and the decision as JSON (UTF-8, LF), creating the folder."""
    w = selection.winner
    payload = {
        "n_questions": n_questions,
        "config": {
            "series": list(config.series),
            "max_chars": list(config.max_chars),
            "overlap_turns": list(config.overlap_turns),
            "k": list(config.k),
            "char_budget": config.char_budget,
            "tie_margin": config.tie_margin,
        },
        "results": [_result_to_json(r) for r in results],
        "decision": {
            "max_chars": w.max_chars,
            "overlap_turns": w.overlap_turns,
            "k": w.k,
            "reason": selection.reason,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_tuning_results(path: Path) -> StoredTuning:
    """Read what :func:`save_tuning_results` wrote."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data["config"]
        config = TuningConfig(
            series=tuple(raw["series"]),
            max_chars=tuple(raw["max_chars"]),
            overlap_turns=tuple(raw["overlap_turns"]),
            k=tuple(raw["k"]),
            char_budget=int(raw["char_budget"]),
            tie_margin=float(raw["tie_margin"]),
        )
        results = tuple(ConfigResult(**r) for r in data["results"])
        d = data["decision"]
        winner = next(
            r
            for r in results
            if (r.max_chars, r.overlap_turns, r.k) == (d["max_chars"], d["overlap_turns"], d["k"])
        )
        return StoredTuning(config, int(data["n_questions"]), results, winner, str(d["reason"]))
    except (ValueError, KeyError, TypeError, StopIteration, OSError) as exc:
        raise ValueError(f"{path.name}: could not be read ({exc!r}).") from exc
