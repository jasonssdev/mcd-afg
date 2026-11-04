"""What a semantic (embedding) channel would add to the Task B lexical blocker (OE1).

The lexical blocker keeps a cross-meeting decision pair only when its overlap coefficient and
its shared-token count clear the operating point. Task C showed that it loses real relations
(``afg.annotation.recall``). This module measures, without changing the blocker, what a second
channel would buy and cost: pairs whose decision texts have a cosine similarity of at least
``t`` would be added to the candidates a human has to annotate.

It does not choose a threshold and does not recommend a path. It reports, for each ``t``:

* how many of the Task C false negatives the channel catches (benefit);
* how many of the kept relations it would also catch (overlap with the lexical channel);
* how many sampled rejected pairs labelled ``no_relacionada`` it would flag (false alarms);
* how many new pairs would need annotation, per series and in total (cost);
* the estimated recall of the union (lexical OR semantic).

## Union recall estimate

It uses the stratified logic of :func:`afg.annotation.recall.estimate_recall`. For each series
with a Task C sample, ``R`` is the rejected population, ``n`` the sample size, ``FN`` the sampled
false negatives and ``K`` the kept relations. The channel catches ``c`` of the ``FN``. Then

* estimated missed relations: ``sum(R * FN / n)`` (the lexical recall is ``K / (K + missed)``);
* estimated relations the channel recovers: ``sum(R * c / n)``;
* union recall: ``(K + recovered) / (K + recovered + residual)``, where the residual is the
  stratified estimate of ``FN - c`` (its Wilson bounds give the interval).

The interval reflects only the sampling uncertainty of the residual. It rests on a handful of
false negatives, and thresholds explored on the same false negatives are optimistic: the
threshold is selected on the evaluation sample.

## Layout

Everything but :func:`embed_texts` and the two label readers is pure. Embedding I/O goes through
the existing :class:`afg.conditions.c1_retrieval.OllamaEmbedder` (any object with ``embed``
works) and is cached on disk by the caller's choice of path (``data/interim/`` is gitignored).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.annotation.blocking import (
    _clears_operating_point,
    _decision_text,
    _scored_pairs,
)
from afg.annotation.recall import SeriesRecallCounts, estimate_recall
from afg.conditions.c1_retrieval import Embedder
from afg.domain.decision import Decision
from afg.domain.relation import RelationType
from afg.evaluation.metrics import wilson_interval
from afg.evaluation.relations import load_gold_pairs
from afg.shared.csvio import open_csv_reader
from afg.shared.paths import GOLD_RELATIONS_DIR

__all__ = [
    "DEFAULT_THRESHOLDS",
    "ChannelRow",
    "DiagnosisRow",
    "PairRecord",
    "cosine_similarity",
    "embed_texts",
    "evaluate_channel",
    "false_negative_diagnosis",
    "lexical_sensitivity",
    "read_gold_labels",
    "read_recall_sample_labels",
    "score_pairs",
    "threshold_grid",
    "threshold_table",
]

_NO_RELATION = RelationType.NO_RELACIONADA.value

PairKey = tuple[str, str]
"""``(earlier_decision_id, later_decision_id)``, the order the blocker and the CSVs use."""


def threshold_grid(start: float, stop: float, step: float) -> tuple[float, ...]:
    """Thresholds from ``start`` to ``stop`` inclusive in steps of ``step`` (no float drift)."""
    if step <= 0:
        raise ValueError("step must be positive.")
    n_steps = round((stop - start) / step)
    return tuple(round(start + i * step, 10) for i in range(n_steps + 1))


DEFAULT_THRESHOLDS: tuple[float, ...] = threshold_grid(0.50, 0.90, 0.05)


# --- records -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PairRecord:
    """One cross-meeting decision pair with its lexical score, cosine and human label.

    ``label`` is the gold relation for a lexical candidate, the Task C label for a sampled
    rejected pair, and ``None`` for a rejected pair that was not sampled.
    """

    series_id: str
    earlier_id: str
    later_id: str
    overlap_score: float
    shared_tokens: int
    cosine: float
    lexical_candidate: bool
    label: str | None

    @property
    def is_kept_relation(self) -> bool:
        """A lexical candidate a human labelled with a real relation."""
        return self.lexical_candidate and self.label not in (None, _NO_RELATION)

    @property
    def is_false_negative(self) -> bool:
        """A sampled rejected pair a human labelled with a real relation."""
        return not self.lexical_candidate and self.label not in (None, _NO_RELATION)

    @property
    def is_sampled_no_relation(self) -> bool:
        """A sampled rejected pair a human labelled ``no_relacionada``."""
        return not self.lexical_candidate and self.label == _NO_RELATION


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine of the angle between two vectors; ``0.0`` when either has zero norm."""
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} != {len(b)}.")
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm


def score_pairs(
    decisions: Sequence[Decision],
    vectors: Mapping[str, Sequence[float]],
    labels: Mapping[PairKey, str],
    *,
    threshold: float = 0.30,
    min_overlap_tokens: int = 2,
) -> list[PairRecord]:
    """Every cross-meeting pair of ``decisions`` with lexical score, cosine and label.

    ``vectors`` maps the blocker's decision text (``_decision_text``) to its embedding. The
    pair universe and the lexical flag come from the blocker itself, so the records partition
    exactly as :func:`afg.annotation.blocking.generate_candidates` and ``rejected_pairs`` do.

    Raises:
        KeyError: a decision text has no vector.
    """
    records: list[PairRecord] = []
    for earlier, later, score, shared in _scored_pairs(decisions):
        key = (earlier.id, later.id)
        records.append(
            PairRecord(
                series_id=earlier.series_id,
                earlier_id=earlier.id,
                later_id=later.id,
                overlap_score=score,
                shared_tokens=shared,
                cosine=cosine_similarity(
                    vectors[_decision_text(earlier)], vectors[_decision_text(later)]
                ),
                lexical_candidate=_clears_operating_point(
                    (earlier, later, score, shared),
                    threshold=threshold,
                    min_overlap_tokens=min_overlap_tokens,
                ),
                label=labels.get(key),
            )
        )
    return records


# --- one channel, one row ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChannelRow:
    """What one extra channel (a predicate over :class:`PairRecord`) catches and costs."""

    name: str
    parameter: float | None
    fn_caught: int
    fn_total: int
    kept_caught_all: int
    kept_total_all: int
    kept_caught_sampled: int
    kept_total_sampled: int
    false_alarms: int
    sampled_no_relation: int
    false_alarm_rate: float | None
    false_alarm_lower: float | None
    false_alarm_upper: float | None
    new_pairs: int
    new_pairs_by_series: Mapping[str, int]
    lexical_candidates: int
    candidates_total: int
    lexical_recall: float | None
    union_recall: float | None
    union_recall_lower: float | None
    union_recall_upper: float | None


def _series_counts(
    records: Sequence[PairRecord], caught: Callable[[PairRecord], bool] | None
) -> tuple[list[SeriesRecallCounts], dict[str, int]]:
    """Task C counts per sampled series; with ``caught``, the false negatives it leaves.

    Also returns, per series, how many sampled false negatives ``caught`` recovers.
    """
    by_series: dict[str, list[PairRecord]] = {}
    for record in records:
        by_series.setdefault(record.series_id, []).append(record)
    counts: list[SeriesRecallCounts] = []
    recovered: dict[str, int] = {}
    for series_id, items in by_series.items():
        rejected = [r for r in items if not r.lexical_candidate]
        sampled = [r for r in rejected if r.label is not None]
        if not sampled:
            continue
        false_negatives = [r for r in sampled if r.is_false_negative]
        n_caught = sum(1 for r in false_negatives if caught is not None and caught(r))
        recovered[series_id] = n_caught
        counts.append(
            SeriesRecallCounts(
                series_id=series_id,
                n_sampled=len(sampled),
                n_false_negative=len(false_negatives) - n_caught,
                rejected_population=len(rejected),
                kept_relations=sum(1 for r in items if r.is_kept_relation),
            )
        )
    return counts, recovered


def _union_estimate(
    records: Sequence[PairRecord], flag: Callable[[PairRecord], bool], confidence_level: float
) -> tuple[float | None, float | None, float | None, float | None]:
    """``(lexical recall, union recall, lower, upper)`` or all ``None`` without a sample."""
    base, _ = _series_counts(records, None)
    if not base:
        return None, None, None, None
    residual_counts, recovered = _series_counts(records, flag)
    lexical = estimate_recall(base, confidence_level=confidence_level)
    residual = estimate_recall(residual_counts, confidence_level=confidence_level)
    kept = sum(c.kept_relations for c in base)
    population = {c.series_id: c.rejected_population for c in base}
    sampled = {c.series_id: c.n_sampled for c in base}
    gained = sum(population[s] * n / sampled[s] for s, n in recovered.items())

    def union(missed: float) -> float:
        total = kept + gained + missed
        return (kept + gained) / total if total > 0 else 1.0

    return (
        lexical.recall,
        union(residual.missed),
        union(residual.missed_upper),
        union(residual.missed_lower),
    )


def evaluate_channel(
    records: Sequence[PairRecord],
    flag: Callable[[PairRecord], bool],
    *,
    name: str,
    parameter: float | None,
    confidence_level: float = 0.95,
) -> ChannelRow:
    """Benefit and cost of adding the pairs for which ``flag`` is true to the lexical candidates.

    ``flag`` is applied to lexically rejected pairs to count new pairs, false negatives caught
    and false alarms, and to lexical candidates to count kept relations it also catches.
    """
    rejected = [r for r in records if not r.lexical_candidate]
    sampled_series = {r.series_id for r in rejected if r.label is not None}
    false_negatives = [r for r in rejected if r.is_false_negative]
    no_relation = [r for r in rejected if r.is_sampled_no_relation]
    kept = [r for r in records if r.is_kept_relation]
    kept_sampled = [r for r in kept if r.series_id in sampled_series]
    false_alarms = sum(1 for r in no_relation if flag(r))
    if no_relation:
        ci = wilson_interval(false_alarms, len(no_relation), confidence_level)
        rate: float | None = ci.point_estimate
        lower: float | None = ci.lower
        upper: float | None = ci.upper
    else:
        rate = lower = upper = None
    new_by_series: dict[str, int] = dict.fromkeys(sorted({r.series_id for r in records}), 0)
    for series_id, n in Counter(r.series_id for r in rejected if flag(r)).items():
        new_by_series[series_id] = n
    new_pairs = sum(new_by_series.values())
    lexical_candidates = len(records) - len(rejected)
    lexical_recall, union, union_lower, union_upper = _union_estimate(
        records, flag, confidence_level
    )
    return ChannelRow(
        name=name,
        parameter=parameter,
        fn_caught=sum(1 for r in false_negatives if flag(r)),
        fn_total=len(false_negatives),
        kept_caught_all=sum(1 for r in kept if flag(r)),
        kept_total_all=len(kept),
        kept_caught_sampled=sum(1 for r in kept_sampled if flag(r)),
        kept_total_sampled=len(kept_sampled),
        false_alarms=false_alarms,
        sampled_no_relation=len(no_relation),
        false_alarm_rate=rate,
        false_alarm_lower=lower,
        false_alarm_upper=upper,
        new_pairs=new_pairs,
        new_pairs_by_series=new_by_series,
        lexical_candidates=lexical_candidates,
        candidates_total=lexical_candidates + new_pairs,
        lexical_recall=lexical_recall,
        union_recall=union,
        union_recall_lower=union_lower,
        union_recall_upper=union_upper,
    )


def _cosine_flag(threshold: float) -> Callable[[PairRecord], bool]:
    return lambda record: record.cosine >= threshold


def _lexical_flag(threshold: float, min_tokens: int) -> Callable[[PairRecord], bool]:
    return lambda record: record.overlap_score >= threshold and record.shared_tokens >= min_tokens


def threshold_table(
    records: Sequence[PairRecord],
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    *,
    confidence_level: float = 0.95,
) -> list[ChannelRow]:
    """One :class:`ChannelRow` per cosine threshold: the semantic channel is ``cosine >= t``."""
    return [
        evaluate_channel(
            records,
            _cosine_flag(t),
            name=f"cosine>={t:.2f}",
            parameter=t,
            confidence_level=confidence_level,
        )
        for t in thresholds
    ]


def lexical_sensitivity(
    records: Sequence[PairRecord],
    grid: Sequence[tuple[float, int]],
    *,
    confidence_level: float = 0.95,
) -> list[ChannelRow]:
    """The same measurement for looser lexical operating points ``(threshold, min tokens)``.

    A variant's pairs are those with ``overlap_score >= threshold`` and
    ``shared_tokens >= min_overlap_tokens``; the ones the default operating point rejected
    are the new pairs. Intended for variants looser than the default (0.30, 2).
    """
    return [
        evaluate_channel(
            records,
            _lexical_flag(threshold, min_tokens),
            name=f"overlap>={threshold:.2f}, tokens>={min_tokens}",
            parameter=threshold,
            confidence_level=confidence_level,
        )
        for threshold, min_tokens in grid
    ]


# --- diagnosis of the false negatives (aggregate and structural fields only) ---------------


@dataclass(frozen=True, slots=True)
class DiagnosisRow:
    """One false negative described by ids and numbers only (never by its text)."""

    series_id: str
    earlier_id: str
    later_id: str
    overlap_score: float
    shared_tokens: int
    overlap_class: str
    cosine: float
    cosine_rank_share: float


def false_negative_diagnosis(records: Sequence[PairRecord]) -> list[DiagnosisRow]:
    """Lexical score, shared tokens and cosine of every false negative.

    ``overlap_class`` is ``zero_overlap`` (no shared token) or ``partial_overlap`` (some, but
    below the operating point). ``cosine_rank_share`` is the share of the series' rejected
    pairs whose cosine is at least this pair's: how deep in the series' ranking it sits.
    """
    rows: list[DiagnosisRow] = []
    for record in records:
        if not record.is_false_negative:
            continue
        rejected = [
            r for r in records if r.series_id == record.series_id and not r.lexical_candidate
        ]
        at_least = sum(1 for r in rejected if r.cosine >= record.cosine)
        rows.append(
            DiagnosisRow(
                series_id=record.series_id,
                earlier_id=record.earlier_id,
                later_id=record.later_id,
                overlap_score=record.overlap_score,
                shared_tokens=record.shared_tokens,
                overlap_class="zero_overlap" if record.shared_tokens == 0 else "partial_overlap",
                cosine=record.cosine,
                cosine_rank_share=at_least / len(rejected),
            )
        )
    return rows


# --- embedding I/O and label readers -------------------------------------------------------


def _text_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_texts(
    texts: Sequence[str], embedder: Embedder, cache_path: Path, *, model: str
) -> dict[str, list[float]]:
    """Vector of every distinct text, embedding only what ``cache_path`` does not hold.

    The cache is a JSON file keyed by the SHA-256 of the text and tagged with ``model``; a
    cache written for another model is ignored and replaced. Nothing is written when there is
    nothing to embed.

    Raises:
        ValueError: the embedder returned a different number of vectors than texts.
    """
    unique = list(dict.fromkeys(texts))
    cached: dict[str, list[float]] = {}
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("model") == model:
            cached = {k: [float(x) for x in v] for k, v in payload["vectors"].items()}
    missing = [t for t in unique if _text_key(t) not in cached]
    if missing:
        fresh = embedder.embed(missing)
        if len(fresh) != len(missing):
            raise ValueError(f"Embedder returned {len(fresh)} vectors for {len(missing)} texts.")
        for text, vector in zip(missing, fresh, strict=True):
            cached[_text_key(text)] = [float(x) for x in vector]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"model": model, "vectors": cached}), encoding="utf-8")
    return {t: cached[_text_key(t)] for t in unique}


def read_recall_sample_labels(
    series_id: str, annotator: str, *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> dict[PairKey, str]:
    """Task C labels of ``<series>.recall-sample.<annotator>.csv`` (empty if the file is absent)."""
    path = relations_dir / f"{series_id}.recall-sample.{annotator}.csv"
    if not path.exists():
        return {}
    labels: dict[PairKey, str] = {}
    with open_csv_reader(path) as handle:
        for row in csv.DictReader(handle):
            relation = (row.get("relation") or "").strip()
            if relation:
                labels[(row["earlier_decision_id"], row["later_decision_id"])] = relation
    return labels


def read_gold_labels(
    series_id: str, *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> dict[PairKey, str]:
    """Gold relation of every labelled candidate pair (empty when the series has no gold file)."""
    try:
        pairs = load_gold_pairs(series_id, relations_dir=relations_dir)
    except FileNotFoundError:
        return {}
    return {(p.earlier_decision_id, p.later_decision_id): p.relation.value for p in pairs}
