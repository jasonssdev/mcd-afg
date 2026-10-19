"""The OpenKOS decision-pass model screen, read with the thesis's own scorer.

OpenKOS screened four local generation models for its transcript decision pass on the two
adjudicated development series, ES2015 and TS3009 (pre-registration
``evals/transcript_decisions/PREREGISTRATION-model-screen.md`` in the OpenKOS repository).
Its harness stored every run as ``runs-pass-*.json`` (copied to
``reports/experiment-a/model-screen-openkos/``) and scored them with a copy of this
project's alignment metric. This module re-scores those runs with the thesis's code
(:func:`afg.evaluation.scoring.score_series`, primary ``origin_meetings`` scope, ADR 0011)
and applies the pre-registered selection rule, so a notebook can show both sides.

## What a run is

One ``(model, series, run)``: the four meeting-runs of a series in one repetition. Each
stored item becomes an extracted :class:`~afg.domain.decision.Decision` with ``subject`` as
its decision object and ``value`` as its content (the pass's subject is the thesis's
object). Every item is ``ACCEPTED``: the pass emits only decisions. A failed meeting-run
contributes the items it kept (none when every window failed), as on the OpenKOS side.

The pass stores evidence as quotes, not dialogue-act ids, and precision, recall and F1 do
not read the evidence; so each decision carries one synthetic act id
(``<meeting>#pass-<n>``) to satisfy :class:`~afg.domain.decision.EvidenceSpan`. Role
stratification is therefore NOT available for these runs.

## Partition

Only development series are accepted (ADR 0005); a run of an evaluation series is refused
when loaded, before anything is scored.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Final, Literal

import numpy as np
import pandas as pd

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import (
    IntervalSettings,
    SimilarityFn,
    pair_text,
    pool_scores,
    score_series,
)
from afg.shared.csvio import read_rows

__all__ = [
    "CurvePoint",
    "PassRun",
    "RuleCheck",
    "advances",
    "ceiling_pairs",
    "ceiling_summary",
    "curve_frame",
    "curve_summary",
    "guardrails_frame",
    "language_counts",
    "language_of",
    "load_openkos_scores",
    "load_pass_runs",
    "mean_min_max",
    "openkos_agreement",
    "paired_similarity",
    "relabel_series",
    "reproduction_frame",
    "score_curve",
    "selection_rule",
    "verdict_frame",
]

Language = Literal["en", "es", "unknown"]

SELECTION_TAU: Final = 0.60
"""The threshold of the pre-registered selection statistic (mean per-run F1)."""
MARGIN_FLOOR: Final = 0.05
"""Condition 1: a candidate must beat the baseline by at least this much F1 ..."""
FAILURE_FLOOR: Final = 2
"""Condition 3: ... fail at most ``max(FAILURE_FLOOR, baseline failures)`` meeting-runs ..."""
VOLUME_FACTOR: Final = 1.10
"""Condition 4: ... and emit at most this factor of the baseline's decisions per meeting."""


@dataclass(frozen=True, slots=True)
class PassRun:
    """One repetition of the decision pass of one model over one series."""

    model: str
    series: str
    run: int
    decisions: tuple[Decision, ...]
    meetings: tuple[str, ...]
    failures: tuple[tuple[str, str], ...]
    wall_s: float

    @property
    def failed_meeting_runs(self) -> int:
        return len(self.failures)

    @property
    def decisions_per_meeting(self) -> float:
        return len(self.decisions) / len(self.meetings) if self.meetings else 0.0


def _require_development(
    series: str, partition_of: Callable[[str], str] | None, where: str
) -> None:
    """Refuse a series that is not a development series (ADR 0005); ``where`` prefixes it."""
    if partition_of is None:
        from afg.experiments.runner import configured_partition_of

        partition_of = configured_partition_of()
    if partition_of(series) != "development":
        raise ValueError(f"{where}: series {series} is not a development series (ADR 0005).")


def load_pass_runs(
    paths: Iterable[Path], *, partition_of: Callable[[str], str] | None = None
) -> list[PassRun]:
    """Read ``runs-pass-*.json`` files into one :class:`PassRun` per (model, series, run).

    Raises:
        ValueError: a file is not of the ``pass`` arm; a record is of a series whose
            partition is not ``development``; a record lacks ``items`` or an item lacks
            ``subject`` or ``value``; or a ``(model, series, run, meeting)`` key appears
            more than once (within a file or across the files), which would merge runs.
    """
    if partition_of is None:
        from afg.experiments.runner import configured_partition_of

        partition_of = configured_partition_of()
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, int, str]] = set()
    for path in paths:
        name = Path(path).name
        stored = json.loads(Path(path).read_text(encoding="utf-8"))
        if stored.get("arm") != "pass":
            raise ValueError(f"{name}: only the pass arm stores subject and value.")
        model = str(stored["model"])
        for record in stored["records"]:
            series = str(record["series"])
            _require_development(series, partition_of, name)
            meeting = str(record["meeting"])
            key = (model, series, int(record["run"]), meeting)
            if key in seen:
                raise ValueError(
                    f"{name}: {model} run {key[2]} of {meeting} is repeated; "
                    "refusing to merge two records of the same meeting-run."
                )
            seen.add(key)
            if "items" not in record:
                raise ValueError(f"{name}: the record of {meeting} (run {key[2]}) has no items.")
            for item in record["items"]:
                missing = [f for f in ("subject", "value") if f not in item]
                if missing:
                    raise ValueError(
                        f"{name}: an item of {meeting} (run {key[2]}) lacks {', '.join(missing)}."
                    )
            grouped[(model, series, int(record["run"]))].append(record)

    runs = []
    for (model, series, run), records in sorted(grouped.items()):
        records = sorted(records, key=lambda r: str(r["meeting"]))
        decisions: list[Decision] = []
        for record in records:
            meeting = str(record["meeting"])
            for item in record["items"]:
                n = len(decisions)
                decisions.append(
                    Decision(
                        id=f"{model}/{series}/r{run}/{n}",
                        series_id=series,
                        meeting_id=meeting,
                        decision_object=str(item["subject"]),
                        content=str(item["value"]),
                        status=DecisionStatus.ACCEPTED,
                        evidence=EvidenceSpan(
                            meeting_id=meeting, dialogue_act_ids=(f"{meeting}#pass-{n}",)
                        ),
                    )
                )
        runs.append(
            PassRun(
                model=model,
                series=series,
                run=run,
                decisions=tuple(decisions),
                meetings=tuple(str(r["meeting"]) for r in records),
                failures=tuple(
                    (str(r["meeting"]), str(r["failure"])) for r in records if r.get("failure")
                ),
                wall_s=float(sum(float(r.get("wall_s") or 0.0) for r in records)),
            )
        )
    return runs


def relabel_series(
    run: PassRun, series: str, *, partition_of: Callable[[str], str] | None = None
) -> PassRun:
    """The same run attributed to ``series``, keeping each meeting's letter (a->a, b->b ...).

    This is the cross-series null control: one team's output scored against another
    team's reference. The texts are untouched; only the meeting labels move.

    Raises:
        ValueError: the run's series or ``series`` is not a development series (ADR 0005).
    """
    _require_development(run.series, partition_of, "relabel_series")
    _require_development(series, partition_of, "relabel_series")

    def move(meeting: str) -> str:
        return f"{series}{meeting[len(run.series) :]}"

    decisions = tuple(
        d.model_copy(
            update={
                "series_id": series,
                "meeting_id": move(d.meeting_id),
                "evidence": EvidenceSpan(
                    meeting_id=move(d.meeting_id), dialogue_act_ids=d.evidence.dialogue_act_ids
                ),
            }
        )
        for d in run.decisions
    )
    return replace(
        run,
        series=series,
        decisions=decisions,
        meetings=tuple(move(m) for m in run.meetings),
        failures=tuple((move(m), f) for m, f in run.failures),
    )


# --- language -------------------------------------------------------------------------------

_WORD = re.compile(r"[^\W\d_]+")
_SPANISH: Final = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "que",
        "en",
        "un",
        "una",
        "con",
        "por",
        "para",
        "se",
        "al",
        "lo",
        "es",
        "son",
        "como",
        "su",
        "sus",
        "y",
        "o",
        "pero",
        "más",
        "no",
        "sobre",
        "este",
        "esta",
        "usar",
        "tener",
    ]
)
_ENGLISH: Final = frozenset(
    [
        "the",
        "of",
        "to",
        "and",
        "a",
        "in",
        "is",
        "will",
        "be",
        "with",
        "for",
        "on",
        "that",
        "it",
        "as",
        "are",
        "this",
        "by",
        "use",
        "have",
        "we",
        "they",
        "should",
        "from",
    ]
)


def language_of(text: str) -> Language:
    """``en``, ``es`` or ``unknown`` by stopword counts (the OpenKOS harness's rule)."""
    words = [w.casefold() for w in _WORD.findall(text)]
    es = sum(w in _SPANISH for w in words)
    en = sum(w in _ENGLISH for w in words)
    if es == en:
        return "unknown"
    return "es" if es > en else "en"


def language_counts(runs: Iterable[PassRun]) -> dict[str, int]:
    """How many extracted ``object: content`` texts read as English, Spanish or neither."""
    counts = Counter(
        language_of(pair_text(d.decision_object, d.content)) for r in runs for d in r.decisions
    )
    return {lang: counts.get(lang, 0) for lang in ("en", "es", "unknown")}


# --- scoring --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CurvePoint:
    """The thesis score of one run at one threshold."""

    model: str
    series: str
    run: int
    tau: float
    tp: int
    n_predicted: int
    n_reference: int
    precision: float
    recall: float
    f1: float


def score_curve(
    runs: Iterable[PassRun],
    references: Mapping[str, Sequence[ReferenceDecision]],
    similarity: SimilarityFn,
    *,
    taus: Sequence[float],
) -> list[CurvePoint]:
    """Score every run at every ``tau`` with :func:`~afg.evaluation.scoring.score_series`."""
    points = []
    for run in runs:
        reference = references[run.series]
        for tau in taus:
            s = score_series(run.series, reference, run.decisions, similarity, tau=tau)
            points.append(
                CurvePoint(
                    model=run.model,
                    series=run.series,
                    run=run.run,
                    tau=float(tau),
                    tp=s.tp,
                    n_predicted=s.tp + s.fp,
                    n_reference=s.tp + s.fn,
                    precision=s.precision,
                    recall=s.recall,
                    f1=s.f1,
                )
            )
    return points


def curve_frame(points: Iterable[CurvePoint]) -> pd.DataFrame:
    """One row per (model, series, run, tau)."""
    return pd.DataFrame([asdict(p) for p in points])


def curve_summary(points: Iterable[CurvePoint]) -> pd.DataFrame:
    """Per (model, series, tau): runs, mean/min/max recall, precision and F1, TP per run."""
    grouped: dict[tuple[str, str, float], list[CurvePoint]] = defaultdict(list)
    for p in points:
        grouped[(p.model, p.series, round(p.tau, 10))].append(p)
    rows = []
    for (model, series, tau), group in sorted(grouped.items()):
        group = sorted(group, key=lambda p: p.run)
        row: dict[str, Any] = {"model": model, "series": series, "tau": tau, "runs": len(group)}
        for metric in ("recall", "precision", "f1"):
            values = [getattr(p, metric) for p in group]
            row[f"{metric}_mean"] = statistics.fmean(values)
            row[f"{metric}_min"] = min(values)
            row[f"{metric}_max"] = max(values)
        row["tp"] = [p.tp for p in group]
        rows.append(row)
    return pd.DataFrame(rows)


def paired_similarity(
    similarity: SimilarityFn, left: Sequence[str], right: Sequence[str]
) -> list[float]:
    """``similarity(left[i], right[i])`` for each ``i`` (the diagonal of the matrix)."""
    if len(left) != len(right):
        raise ValueError("paired_similarity needs two lists of the same length.")
    if not left:
        return []
    return [float(v) for v in np.diag(np.asarray(similarity(left, right), dtype=float))]


def ceiling_pairs(path: Path) -> list[tuple[str, str]]:
    """``(English AMI sentence, Spanish "object: content")`` of each reference decision.

    Rows with ``final_status == "decision"`` and a non-blank ``sentence_text`` (the
    abstractive sentence the decision was annotated from), as the OpenKOS diagnostic reads
    them. Embedding the two sides measures how similar a faithful English rendering of a
    decision can be to its Spanish reference text.
    """
    return [
        (
            row["sentence_text"].strip(),
            pair_text(row["final_object"].strip(), row["final_content"].strip()),
        )
        for row in read_rows(Path(path))
        if row.get("final_status", "").strip() == "decision"
        and row.get("sentence_text", "").strip()
    ]


# --- guardrails and the selection rule -------------------------------------------------------


def guardrails_frame(runs: Iterable[PassRun]) -> pd.DataFrame:
    """Per (model, series): runs, failed meeting-runs of the total, decisions per meeting
    (mean over runs), seconds per run (mean) and the language of the extracted texts."""
    grouped: dict[tuple[str, str], list[PassRun]] = defaultdict(list)
    for run in runs:
        grouped[(run.model, run.series)].append(run)
    rows = []
    for (model, series), group in sorted(grouped.items()):
        languages = language_counts(group)
        rows.append(
            {
                "model": model,
                "series": series,
                "runs": len(group),
                "failed_meeting_runs": sum(r.failed_meeting_runs for r in group),
                "meeting_runs": sum(len(r.meetings) for r in group),
                "decisions_per_meeting": statistics.fmean(r.decisions_per_meeting for r in group),
                "seconds_per_run": statistics.fmean(r.wall_s for r in group),
                "language_en": languages["en"],
                "language_es": languages["es"],
                "language_unknown": languages["unknown"],
            }
        )
    return pd.DataFrame(rows)


@dataclass(frozen=True, slots=True)
class RuleCheck:
    """The four pre-registered conditions for one candidate on one series."""

    candidate: str
    baseline: str
    series: str
    tau: float
    f1_candidate: float
    f1_baseline: float
    d_f1: float
    spread: float
    margin_needed: float
    margin_ok: bool
    recall_candidate: float
    recall_baseline: float
    recall_ok: bool
    failures_candidate: int
    failures_baseline: int
    failures_ok: bool
    volume_candidate: float
    volume_baseline: float
    volume_ok: bool

    @property
    def volume_cap(self) -> float:
        """Condition 4's ceiling: the baseline's decisions per meeting times 1.10."""
        return VOLUME_FACTOR * self.volume_baseline

    @property
    def passed(self) -> bool:
        return self.margin_ok and self.recall_ok and self.failures_ok and self.volume_ok


def selection_rule(
    points: Iterable[CurvePoint],
    runs: Iterable[PassRun],
    *,
    candidate: str,
    baseline: str,
    series: Sequence[str] = ("ES2015", "TS3009"),
    tau: float = SELECTION_TAU,
    partition_of: Callable[[str], str] | None = None,
) -> list[RuleCheck]:
    """Apply the pre-registered rule to ``candidate`` against ``baseline``, per series.

    1. margin: ``dF1 >= max(0.05, S)``, with ``dF1`` the difference of mean per-run F1 at
       ``tau`` and ``S`` the larger of the two models' per-run F1 min-max ranges;
    2. no recall loss: mean recall at ``tau`` of the candidate >= the baseline's;
    3. failures: failed meeting-runs <= ``max(2, baseline's)``;
    4. volume: mean decisions per meeting <= 1.10 x the baseline's.

    Raises:
        ValueError: a series checked is not a development series (ADR 0005), or there are
            no scores for the candidate or the baseline on one.
    """
    for s in series:
        _require_development(s, partition_of, "selection_rule")
    at_tau = [p for p in points if abs(p.tau - tau) < 1e-9]
    run_list = list(runs)

    def f1s(model: str, s: str) -> list[float]:
        return [p.f1 for p in at_tau if p.model == model and p.series == s]

    def recall(model: str, s: str) -> float:
        return statistics.fmean(p.recall for p in at_tau if p.model == model and p.series == s)

    def of(model: str, s: str) -> list[PassRun]:
        return [r for r in run_list if r.model == model and r.series == s]

    checks = []
    for s in series:
        fc, fb = f1s(candidate, s), f1s(baseline, s)
        if not fc or not fb:
            raise ValueError(f"No scores at tau {tau} for {candidate} or {baseline} on {s}.")
        d_f1 = statistics.fmean(fc) - statistics.fmean(fb)
        spread = max(max(fc) - min(fc), max(fb) - min(fb))
        needed = max(MARGIN_FLOOR, spread)
        rc, rb = recall(candidate, s), recall(baseline, s)
        fail_c = sum(r.failed_meeting_runs for r in of(candidate, s))
        fail_b = sum(r.failed_meeting_runs for r in of(baseline, s))
        vol_c = statistics.fmean(r.decisions_per_meeting for r in of(candidate, s))
        vol_b = statistics.fmean(r.decisions_per_meeting for r in of(baseline, s))
        checks.append(
            RuleCheck(
                candidate=candidate,
                baseline=baseline,
                series=s,
                tau=tau,
                f1_candidate=statistics.fmean(fc),
                f1_baseline=statistics.fmean(fb),
                d_f1=d_f1,
                spread=spread,
                margin_needed=needed,
                margin_ok=d_f1 >= needed,
                recall_candidate=rc,
                recall_baseline=rb,
                recall_ok=rc >= rb,
                failures_candidate=fail_c,
                failures_baseline=fail_b,
                failures_ok=fail_c <= max(FAILURE_FLOOR, fail_b),
                volume_candidate=vol_c,
                volume_baseline=vol_b,
                volume_ok=vol_c <= VOLUME_FACTOR * vol_b,
            )
        )
    return checks


def advances(checks: Sequence[RuleCheck]) -> bool:
    """A candidate advances only when every condition holds on every series checked."""
    return bool(checks) and all(c.passed for c in checks)


def verdict_frame(checks_by_candidate: Mapping[str, Sequence[RuleCheck]]) -> pd.DataFrame:
    """Per candidate: whether it advances and its mean dF1 over the series, best first."""
    rows = [
        {
            "candidate": candidate,
            "advances": advances(checks),
            "d_f1_mean": statistics.fmean(c.d_f1 for c in checks),
        }
        for candidate, checks in checks_by_candidate.items()
    ]
    return (
        pd.DataFrame(rows, columns=["candidate", "advances", "d_f1_mean"])
        .sort_values("d_f1_mean", ascending=False)
        .reset_index(drop=True)
    )


def mean_min_max(values: Sequence[float]) -> tuple[float, float, float]:
    """``(mean, min, max)`` of ``values``; refuses an empty list."""
    if not values:
        raise ValueError("mean_min_max is undefined for an empty list.")
    return statistics.fmean(values), min(values), max(values)


def ceiling_summary(
    similarities: Mapping[str, Sequence[float]], *, thresholds: Sequence[float]
) -> pd.DataFrame:
    """Per series: n, median, min, max of the similarities and the count at or above each
    threshold (columns ``count_ge_<threshold>``, two decimals)."""
    rows = {}
    for series, values in similarities.items():
        row: dict[str, Any] = {
            "n": len(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
        for t in thresholds:
            row[f"count_ge_{t:.2f}"] = sum(1 for v in values if v >= t)
        rows[series] = row
    return pd.DataFrame.from_dict(rows, orient="index")


def reproduction_frame(
    reference: Sequence[ReferenceDecision],
    runs: Sequence[Sequence[Decision]],
    similarity: SimilarityFn,
    *,
    taus: Sequence[float],
    openkos_pooled: Mapping[float, Mapping[str, Any]],
    settings: IntervalSettings,
    series: str = "ES2015",
    partition_of: Callable[[str], str] | None = None,
) -> pd.DataFrame:
    """The thesis scorer's pooled result over ``runs`` at each ``tau`` next to OpenKOS's copy.

    ``openkos_pooled`` maps ``round(tau, 2)`` to the copy's pooled ``{"tp", "recall", ...}``.
    One row per ``tau``: TP per run, pooled TP, the copy's pooled TP, extracted and
    reference counts, recall (thesis and copy) and pooled F1.
    """
    rows = []
    for tau in taus:
        scores = [score_series(series, reference, ds, similarity, tau=tau) for ds in runs]
        pooled = pool_scores(scores, settings=settings, partition_of=partition_of)
        theirs = openkos_pooled[round(tau, 2)]
        rows.append(
            {
                "tau": tau,
                "tp_per_run": [s.tp for s in scores],
                "tp_pooled": pooled.tp,
                "tp_pooled_openkos": theirs["tp"],
                "n_extracted": pooled.tp + pooled.fp,
                "n_reference": pooled.tp + pooled.fn,
                "recall": pooled.recall,
                "recall_openkos": theirs["recall"],
                "f1": pooled.f1,
            }
        )
    return pd.DataFrame(rows)


# --- the OpenKOS side -----------------------------------------------------------------------


def load_openkos_scores(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """The OpenKOS harness's ``scored.json``, keyed by ``(model, series)``.

    Its entries carry what only the OpenKOS harness computes (the evidence-overlap
    ``harness_recall``) and its own copy of the thesis curve, for comparison.
    """
    stored = json.loads(Path(path).read_text(encoding="utf-8"))
    return {(str(e["model"]), str(e["series"])): e for e in stored.values()}


def openkos_agreement(
    points: Iterable[CurvePoint], entries: Mapping[tuple[str, str], Mapping[str, Any]]
) -> pd.DataFrame:
    """Per (model, series, tau): TP per run from the thesis scorer next to the OpenKOS copy's."""
    grouped: dict[tuple[str, str, float], list[CurvePoint]] = defaultdict(list)
    for p in points:
        grouped[(p.model, p.series, round(p.tau, 10))].append(p)
    rows = []
    for (model, series, tau), group in sorted(grouped.items()):
        entry = entries.get((model, series))
        if entry is None:
            continue
        theirs = next((c for c in entry["curve"] if abs(float(c["tau"]) - tau) < 1e-9), None)
        if theirs is None:
            continue
        ours = [p.tp for p in sorted(group, key=lambda p: p.run)]
        other = [int(v) for v in theirs["tp"]]
        rows.append(
            {
                "model": model,
                "series": series,
                "tau": tau,
                "tp_thesis": ours,
                "tp_openkos": other,
                "equal": ours == other,
                "tp_difference": sum(ours) - sum(other),
            }
        )
    return pd.DataFrame(rows)
