"""Paired comparison of the hosted extractors against the formal baseline (ADR 0026).

Reads stored Experiment A run folders (``reports/experiment-a/<run>/`` plus the OpenKOS
workspace manifests under ``data/interim/openkos/<run>/``) and compares a candidate with the
baseline ``qwen3:8b`` run over the series the candidate covers.

Primary question (decision 7): does the candidate recall more of the reference decisions? Each
system is scored with :func:`~afg.evaluation.scoring.score_series` (scope ``origin_meetings``,
gold in English, the same similarity as ``a-report``); the hits are tallied per meeting and
averaged over the repetitions of a series. A *paired* meeting-cluster bootstrap then resamples
the same meetings for both systems and takes the percentile interval of the candidate minus
baseline differences in pooled precision, recall and F1, at the Bonferroni level
``1 - family_alpha / n_models``.

Secondary operation indicators (decision 8): ingest time per meeting (paired bootstrap of the
log ratio), the share of meetings with an exact extraction (ingest exit 0 and no
``extraction_status`` in the source, with a count per status), extracted decisions per meeting,
and the tokens of each ingest with the cost they imply at the prices of the configuration (a
lower bound when a call did not report).

The similarity is injected, so nothing here needs Ollama.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from afg.domain.decision import Decision
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import SimilarityFn, score_series
from afg.experiments.extraction_runs import ExtractionRun, load_extraction_runs
from afg.experiments.hosted_cost import MeetingTokens, summarize_cost, summarize_tokens
from afg.experiments.hosted_extraction import (
    ComparisonSpec,
    HostedConfig,
    ModelPrice,
    hosted_run_name,
)
from afg.extraction.openkos.bundle_reader import EXTRACTION_STATUSES, read_extraction_status
from afg.extraction.openkos.event_dates import POSITION_LETTERS
from afg.extraction.openkos.tokens import TokenUsage

__all__ = [
    "BASELINE_CHOICES",
    "VERSION_EFFECT_LABEL",
    "DiffInterval",
    "MeetingCounts",
    "PairedResult",
    "RunData",
    "bridge_check",
    "build_comparison",
    "compare_to_baseline",
    "ingest_time_summary",
    "load_run_data",
    "meeting_counts",
    "paired_bootstrap",
    "verdict_for",
    "write_comparison",
]

ReferenceOf = Callable[[str], Sequence[ReferenceDecision]]
METRICS = ("precision", "recall", "f1")
NO_RUN = "sin corrida"
UNDETERMINED = "sin diferencia demostrada"


@dataclass(frozen=True, slots=True)
class MeetingCounts:
    """Hits and totals of one meeting, averaged over the repetitions of its series.

    ``hits_p``/``n_p``: extracted decisions of the meeting that matched / that were scored.
    ``hits_r``/``n_r``: reference decisions of the meeting that were covered / that exist.
    """

    hits_p: float
    n_p: float
    hits_r: float
    n_r: float


@dataclass(frozen=True, slots=True)
class DiffInterval:
    estimate: float
    interval: tuple[float, float]


@dataclass(frozen=True, slots=True)
class PairedResult:
    """Point estimates of both systems and the paired differences (candidate - baseline)."""

    baseline: Mapping[str, float]
    candidate: Mapping[str, float]
    precision: DiffInterval
    recall: DiffInterval
    f1: DiffInterval
    n_meetings: int


@dataclass(frozen=True, slots=True)
class RunData:
    """A stored run: its extractions, manifest and the folder of its OpenKOS workspaces."""

    name: str
    runs: tuple[ExtractionRun, ...]
    manifest: Mapping[str, Any]
    workspace_root: Path


def load_run_data(run_dir: Path, workspace_root: Path) -> RunData:
    """Read ``manifest.json`` and ``extracciones.jsonl`` of ``run_dir``."""
    runs = load_extraction_runs([run_dir])
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return RunData(run_dir.name, tuple(runs), manifest, workspace_root)


def _declared_pairs(data: RunData) -> dict[str, Mapping[str, Any]]:
    return dict(data.manifest.get("pairs") or {})


def _configured_runs(data: RunData) -> dict[str, int]:
    """Series -> number of runs the batch was configured with (its manifest), else observed."""
    observed: dict[str, int] = {}
    for r in data.runs:
        series_id = r.record["series_id"]
        observed[series_id] = max(observed.get(series_id, 0), r.run + 1)
    for pair in _declared_pairs(data).values():
        series_id = str(pair["series"])
        observed[series_id] = max(observed.get(series_id, 0), int(pair["run"]) + 1)
    series_ids = data.manifest.get("series_ids")
    runs = data.manifest.get("runs")
    if series_ids and isinstance(runs, int):
        return {str(s): runs for s in series_ids}
    return observed


def _series_of(data: RunData) -> list[str]:
    return sorted(_configured_runs(data))


def _pair_status(data: RunData, series_id: str, run: int) -> str | None:
    pair = _declared_pairs(data).get(f"{series_id}/{run}")
    return None if pair is None else str(pair.get("status"))


def _ok_runs(data: RunData) -> list[ExtractionRun]:
    """The stored runs of pairs that finished: a failed or unconfigured pair is not extraction."""
    configured = _configured_runs(data)
    declared = _declared_pairs(data)
    return [
        r
        for r in data.runs
        if r.run < configured.get(r.record["series_id"], 0)
        and (not declared or _pair_status(data, r.record["series_id"], r.run) == "ok")
    ]


def _coverage(data: RunData, series: Collection[str]) -> dict[str, Any]:
    """Configured vs finished runs of ``series`` (a failed or missing run is a failure)."""
    configured = _configured_runs(data)
    ok_pairs = {(r.record["series_id"], r.run) for r in _ok_runs(data)}
    expected = sum(configured.get(s, 0) for s in series)
    ok = sum(1 for pair in ok_pairs if pair[0] in series)
    with_failures = sorted(
        s for s in series if sum(1 for pair in ok_pairs if pair[0] == s) < configured.get(s, 0)
    )
    return {
        "runs_expected": expected,
        "runs_ok": ok,
        "runs_failed": expected - ok,
        "series_with_failures": with_failures,
    }


# --- precision / recall / F1 -----------------------------------------------------------------


def _f1(precision: float, recall: float) -> float:
    total = precision + recall
    return 2 * precision * recall / total if total else 0.0


def _figures(totals: Sequence[float]) -> dict[str, float]:
    hits_p, n_p, hits_r, n_r = totals
    precision = hits_p / n_p if n_p else 0.0
    recall = hits_r / n_r if n_r else 0.0
    return {"precision": precision, "recall": recall, "f1": _f1(precision, recall)}


def _tally(score: Any, sums: dict[str, list[float]], meetings: set[str]) -> None:
    for meeting, hit in zip(score.predicted_meetings, score.predicted_hits, strict=True):
        sums[meeting][0] += int(hit)
        sums[meeting][1] += 1
        meetings.add(meeting)
    for meeting, hit in zip(score.reference_meetings, score.reference_hits, strict=True):
        sums[meeting][2] += int(hit)
        sums[meeting][3] += 1
        meetings.add(meeting)


def meeting_counts(
    runs: Sequence[ExtractionRun],
    *,
    reference_of: ReferenceOf,
    similarity: SimilarityFn,
    tau: float,
    series: Collection[str] | None = None,
    expected_runs: Mapping[str, int] | None = None,
) -> dict[str, MeetingCounts]:
    """Per-meeting counts at ``tau`` (scope ``origin_meetings``), averaged over the runs.

    With ``expected_runs`` (series -> configured runs) the average is over the configured runs:
    a run that is absent counts as an empty extraction (every reference decision missed).
    """
    selected = [r for r in runs if series is None or r.record["series_id"] in series]
    references: dict[str, Sequence[ReferenceDecision]] = {}
    sums: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    runs_of: dict[str, int] = defaultdict(int)
    meetings_of: dict[str, set[str]] = defaultdict(set)
    for item in selected:
        series_id = item.record["series_id"]
        if series_id not in references:
            references[series_id] = reference_of(series_id)
        score = score_series(
            series_id,
            references[series_id],
            [Decision(**d) for d in item.decisions],
            similarity,
            tau=tau,
            alignment_scope="origin_meetings",
        )
        runs_of[series_id] += 1
        _tally(score, sums, meetings_of[series_id])
    for series_id, expected in (expected_runs or {}).items():
        if series is not None and series_id not in series:
            continue
        if series_id not in references:
            references[series_id] = reference_of(series_id)
        for _ in range(max(0, expected - runs_of[series_id])):
            empty = score_series(
                series_id,
                references[series_id],
                [],
                similarity,
                tau=tau,
                alignment_scope="origin_meetings",
            )
            runs_of[series_id] += 1
            _tally(empty, sums, meetings_of[series_id])
    divisor = {m: runs_of[s] for s, ms in meetings_of.items() for m in ms}
    return {m: MeetingCounts(*(v / divisor[m] for v in vals)) for m, vals in sums.items()}


def _percentiles(values: np.ndarray, level: float) -> tuple[float, float]:
    ordered = np.sort(values)
    n = len(ordered)
    alpha = 1.0 - level
    return (
        float(ordered[max(0, int(alpha / 2 * n))]),
        float(ordered[min(n - 1, int((1 - alpha / 2) * n))]),
    )


def _as_array(counts: Mapping[str, MeetingCounts], meetings: Sequence[str]) -> np.ndarray:
    zero = MeetingCounts(0.0, 0.0, 0.0, 0.0)
    return np.array(
        [[c.hits_p, c.n_p, c.hits_r, c.n_r] for c in (counts.get(m, zero) for m in meetings)],
        dtype=float,
    )


def _ratio_columns(totals: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precision, recall and F1 of each row of ``totals`` (a zero denominator gives 0)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        precision = np.where(totals[:, 1] > 0, totals[:, 0] / totals[:, 1], 0.0)
        recall = np.where(totals[:, 3] > 0, totals[:, 2] / totals[:, 3], 0.0)
        denominator = precision + recall
        f1 = np.where(denominator > 0, 2 * precision * recall / denominator, 0.0)
    return precision, recall, f1


def paired_bootstrap(
    baseline: Mapping[str, MeetingCounts],
    candidate: Mapping[str, MeetingCounts],
    *,
    resamples: int,
    seed: int,
    level: float,
) -> PairedResult:
    """Paired cluster bootstrap over meetings of the candidate - baseline differences.

    Every resample draws the same meetings for both systems (a meeting a system lacks counts as
    zero). Deterministic for ``seed``.
    """
    meetings = sorted(set(baseline) | set(candidate))
    if not meetings:
        raise ValueError("There are no meetings to compare.")
    base_array, cand_array = _as_array(baseline, meetings), _as_array(candidate, meetings)
    draws = np.random.default_rng(seed).integers(0, len(meetings), size=(resamples, len(meetings)))
    base_boot = _ratio_columns(base_array[draws].sum(axis=1))
    cand_boot = _ratio_columns(cand_array[draws].sum(axis=1))
    base_point = _figures(base_array.sum(axis=0).tolist())
    cand_point = _figures(cand_array.sum(axis=0).tolist())
    diffs = {
        name: DiffInterval(
            estimate=cand_point[name] - base_point[name],
            interval=_percentiles(cand_boot[i] - base_boot[i], level),
        )
        for i, name in enumerate(METRICS)
    }
    return PairedResult(
        baseline=base_point,
        candidate=cand_point,
        precision=diffs["precision"],
        recall=diffs["recall"],
        f1=diffs["f1"],
        n_meetings=len(meetings),
    )


def verdict_for(
    recall_interval: tuple[float, float],
    precision_interval: tuple[float, float],
    *,
    precision_margin: float,
) -> str:
    """ADR 0026, decision 7: ``mejora``, ``empeora`` or ``sin diferencia demostrada``."""
    if recall_interval[0] > 0 and precision_interval[0] >= precision_margin:
        return "mejora"
    if recall_interval[1] < 0:
        return "empeora"
    return UNDETERMINED


# --- operation indicators (ADR 0026, decision 8) ----------------------------------------------


def _run_pairs(data: RunData, series: Collection[str]) -> list[tuple[str, int]]:
    """Every ``(series, run)`` the run was configured with or attempted, failed ones included."""
    found = {(str(p["series"]), int(p["run"])) for p in _declared_pairs(data).values()}
    found |= {(r.record["series_id"], r.run) for r in data.runs}
    for series_id, runs in _configured_runs(data).items():
        found |= {(series_id, run) for run in range(runs)}
    return sorted(pair for pair in found if pair[0] in series)


def _ingest_meeting(argv: Sequence[str]) -> str | None:
    if len(argv) >= 3 and argv[1] == "ingest" and not argv[2].startswith("-"):
        return Path(argv[2]).stem
    return None


@dataclass(frozen=True, slots=True)
class _IngestProfile:
    seconds: dict[str, float]  # meeting -> ingest seconds averaged over its finished ingests
    complete: int  # meetings with extraction: exit 0, not the failed meeting, no extraction_status
    expected: int
    statuses: dict[str, int]  # extraction_status value -> meetings (the four keys, 0 when absent)
    tokens: list[MeetingTokens]  # one per (series, run, meeting) with a ``tokens:`` record


def _ingest_profile(data: RunData, series: Collection[str]) -> _IngestProfile:
    per_meeting: dict[str, list[float]] = defaultdict(list)
    complete = expected = 0
    statuses = dict.fromkeys(EXTRACTION_STATUSES, 0)
    tokens: list[MeetingTokens] = []
    for series_id, run in _run_pairs(data, series):
        path = data.workspace_root / series_id / f"run-{run}.manifest.json"
        if not path.is_file() and _pair_status(data, series_id, run) == "ok":
            raise FileNotFoundError(
                f"The run {data.name} reports {series_id}/{run} as ok but its workspace "
                f"manifest {path} is missing."
            )
        manifest: dict[str, Any] = (
            json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        )
        meetings = manifest.get("meetings") or [f"{series_id}{x}" for x in POSITION_LETTERS]
        failed_meeting = manifest.get("failed_meeting")
        seconds: dict[str, float] = defaultdict(float)
        finished: set[str] = set()
        run_tokens: dict[str, MeetingTokens] = {}
        for command in manifest.get("commands", []):
            meeting = _ingest_meeting(command.get("argv", []))
            if meeting is None:
                continue
            seconds[meeting] += float(command.get("duration_s", 0.0))
            if command.get("tokens") is not None:  # billed also when the ingest failed
                run_tokens.setdefault(meeting, MeetingTokens()).add(
                    TokenUsage.from_dict(command["tokens"])
                )
            if command.get("returncode", 0) == 0 and meeting != failed_meeting:
                finished.add(meeting)
        tokens.extend(run_tokens.values())
        bundle = data.workspace_root / series_id / f"run-{run}" / "bundle"
        for meeting in meetings:
            expected += 1
            if meeting in finished:
                per_meeting[meeting].append(seconds[meeting])
                # Exit 0 is not enough: a failed extraction exits 0 and leaves a status behind.
                status = read_extraction_status(bundle, meeting)
                if status is None:
                    complete += 1
                else:
                    statuses[status] = statuses.get(status, 0) + 1
    return _IngestProfile(
        {m: statistics.fmean(v) for m, v in per_meeting.items()},
        complete,
        expected,
        statuses,
        tokens,
    )


def ingest_time_summary(data: RunData, series: Collection[str] | None = None) -> dict[str, Any]:
    """Median ingest seconds per meeting and how many meetings finished (descriptive)."""
    selected = series if series is not None else _series_of(data)
    profile = _ingest_profile(data, selected)
    return {
        "median_s": statistics.median(profile.seconds.values()) if profile.seconds else None,
        "n_meetings": len(profile.seconds),
        "complete": profile.complete,
        "expected": profile.expected,
    }


def _time_ratio(
    baseline: Mapping[str, float],
    candidate: Mapping[str, float],
    *,
    resamples: int,
    seed: int,
    level: float,
) -> dict[str, Any]:
    shared = sorted(
        m for m in set(baseline) & set(candidate) if baseline[m] > 0 and candidate[m] > 0
    )
    result: dict[str, Any] = {
        "baseline_median_s": statistics.median(baseline.values()) if baseline else None,
        "candidate_median_s": statistics.median(candidate.values()) if candidate else None,
        "n_meetings": len(shared),
        "per_meeting_s": {m: {"baseline": baseline[m], "candidate": candidate[m]} for m in shared},
    }
    if not shared:
        return {**result, "ratio": None, "verdict": "sin datos"}
    logs = np.log(np.array([candidate[m] / baseline[m] for m in shared]))
    draws = np.random.default_rng(seed).integers(0, len(shared), size=(resamples, len(shared)))
    low, high = _percentiles(logs[draws].mean(axis=1), level)
    interval = (math.exp(low), math.exp(high))
    verdict = "más rápido" if interval[1] < 1 else "más lento" if interval[0] > 1 else UNDETERMINED
    return {
        **result,
        "ratio": {"estimate": math.exp(float(logs.mean())), "interval": list(interval)},
        "verdict": verdict,
    }


def _decisions_per_meeting(data: RunData, series: Collection[str]) -> dict[str, float | None]:
    per_meeting: dict[str, list[int]] = defaultdict(list)
    for item in data.runs:
        if item.record["series_id"] not in series:
            continue
        counts: dict[str, int] = defaultdict(int)
        for decision in item.decisions:
            if decision.get("status") == "accepted":
                counts[decision["meeting_id"]] += 1
        for letter in POSITION_LETTERS:
            meeting = f"{item.record['series_id']}{letter}"
            per_meeting[meeting].append(counts[meeting])
    averaged = [statistics.fmean(v) for v in per_meeting.values()]
    return {
        "mean": statistics.fmean(averaged) if averaged else None,
        "median": statistics.median(averaged) if averaged else None,
    }


def _completeness(profile: _IngestProfile) -> dict[str, Any]:
    share = profile.complete / profile.expected if profile.expected else None
    return {"complete": profile.complete, "expected": profile.expected, "share": share}


# --- comparison -------------------------------------------------------------------------------


def _tau_key(tau: float) -> str:
    return f"{tau:.2f}"


def compare_to_baseline(
    baseline: RunData,
    candidate: RunData,
    *,
    reference_of: ReferenceOf,
    similarity: SimilarityFn,
    spec: ComparisonSpec,
    n_models: int,
    price: ModelPrice | None = None,
    dashboard_usd: float | None = None,
) -> dict[str, Any]:
    """Compare ``candidate`` with ``baseline`` over the series the candidate covers.

    ``price`` (USD per million tokens) turns the candidate's token records into a cost; without
    it the cost is pending. ``dashboard_usd`` is the optional hand-read provider figure, kept
    only as a cross-check.
    """
    series = _series_of(candidate)
    baseline_runs = _configured_runs(baseline)
    candidate_runs = _configured_runs(candidate)
    missing = [s for s in series if s not in baseline_runs]
    if missing:
        raise ValueError(f"The baseline run has no runs of {', '.join(missing)}.")
    level = 1 - spec.family_alpha / n_models
    taus: dict[str, Any] = {}
    n_meetings = 0
    for tau in (spec.tau, *spec.sensitivity_taus):
        paired = paired_bootstrap(
            meeting_counts(
                _ok_runs(baseline),
                reference_of=reference_of,
                similarity=similarity,
                tau=tau,
                series=series,
                expected_runs=baseline_runs,
            ),
            meeting_counts(
                _ok_runs(candidate),
                reference_of=reference_of,
                similarity=similarity,
                tau=tau,
                series=series,
                expected_runs=candidate_runs,
            ),
            resamples=spec.bootstrap_resamples,
            seed=spec.bootstrap_seed,
            level=level,
        )
        n_meetings = paired.n_meetings
        taus[_tau_key(tau)] = {
            "tau": tau,
            "baseline": dict(paired.baseline),
            "candidate": dict(paired.candidate),
            "diff": {
                name: {"estimate": d.estimate, "interval": list(d.interval)}
                for name, d in (
                    ("precision", paired.precision),
                    ("recall", paired.recall),
                    ("f1", paired.f1),
                )
            },
            "verdict": verdict_for(
                paired.recall.interval,
                paired.precision.interval,
                precision_margin=spec.precision_margin,
            ),
            "recall_up_precision_drop": paired.recall.interval[0] > 0
            and paired.precision.interval[0] < spec.precision_margin,
        }
    base_profile = _ingest_profile(baseline, series)
    cand_profile = _ingest_profile(candidate, series)
    cost = summarize_cost(cand_profile.tokens, price)
    ok_candidate = _ok_runs(candidate)
    runs_per_series = {
        s: len({r.run for r in ok_candidate if r.record["series_id"] == s}) for s in series
    }
    return {
        "run_name": candidate.name,
        "baseline_run_name": baseline.name,
        "series_covered": series,
        "n_series": len(series),
        "n_meetings": n_meetings,
        "runs_per_series": runs_per_series,
        **_coverage(candidate, series),
        "scope_note": (
            f"La comparación cubre solo las series de la corrida candidata ({', '.join(series)}); "
            "la línea base se restringe a esas mismas series."
        ),
        "baseline": {"series": series},
        "n_models": n_models,
        "family_alpha": spec.family_alpha,
        "interval_level": level,
        "resamples": spec.bootstrap_resamples,
        "seed": spec.bootstrap_seed,
        "primary_tau": spec.tau,
        "precision_margin": spec.precision_margin,
        "taus": taus,
        "verdict": taus[_tau_key(spec.tau)]["verdict"],
        "operation": {
            "time": _time_ratio(
                base_profile.seconds,
                cand_profile.seconds,
                resamples=spec.bootstrap_resamples,
                seed=spec.bootstrap_seed,
                level=level,
            ),
            "completeness": {
                "baseline": _completeness(base_profile),
                "candidate": _completeness(cand_profile),
            },
            "extraction_status": {
                "baseline": dict(base_profile.statuses),
                "candidate": dict(cand_profile.statuses),
            },
            "decisions_per_meeting": {
                "baseline": _decisions_per_meeting(baseline, series),
                "candidate": _decisions_per_meeting(candidate, series),
            },
            "tokens": {
                "baseline": summarize_tokens(base_profile.tokens),
                "candidate": summarize_tokens(cand_profile.tokens),
            },
            "cost": cost,
            "cost_usd": cost["total_usd"],
            "dashboard_usd": dashboard_usd,
        },
    }


# --- bridge -----------------------------------------------------------------------------------


def _run_figures(
    data: RunData, reference_of: ReferenceOf, similarity: SimilarityFn, tau: float
) -> dict[str, list[dict[str, float]]]:
    """Per series, the precision / recall / F1 of each of its runs."""
    figures: dict[str, list[dict[str, float]]] = defaultdict(list)
    for item in data.runs:
        series_id = item.record["series_id"]
        score = score_series(
            series_id,
            reference_of(series_id),
            [Decision(**d) for d in item.decisions],
            similarity,
            tau=tau,
            alignment_scope="origin_meetings",
        )
        figures[series_id].append(
            {"precision": score.precision, "recall": score.recall, "f1": score.f1}
        )
    return figures


def bridge_check(
    *,
    bridge: RunData,
    formal: RunData,
    reference_of: ReferenceOf,
    similarity: SimilarityFn,
    tau: float,
) -> dict[str, Any]:
    """Whether the bridge run falls inside the min-max range of the formal runs, per series."""
    bridge_figures = _run_figures(bridge, reference_of, similarity, tau)
    formal_figures = _run_figures(formal, reference_of, similarity, tau)
    series: dict[str, Any] = {}
    for series_id, runs in sorted(bridge_figures.items()):
        reference_runs = formal_figures.get(series_id)
        if not reference_runs:
            series[series_id] = {"inside": None, "note": "la corrida formal no tiene esta serie"}
            continue
        value = {m: statistics.fmean(r[m] for r in runs) for m in METRICS}
        spread = {
            m: [min(r[m] for r in reference_runs), max(r[m] for r in reference_runs)]
            for m in METRICS
        }
        outside = [m for m in METRICS if not spread[m][0] <= value[m] <= spread[m][1]]
        series[series_id] = {
            "bridge": value,
            "formal_range": spread,
            "n_formal_runs": len(reference_runs),
            "outside_metrics": outside,
            "inside": not outside,
        }
    verdicts = [s["inside"] for s in series.values()]
    return {
        "tau": tau,
        "series": series,
        "all_inside": bool(verdicts) and all(v is True for v in verdicts),
    }


# --- orchestration and files ------------------------------------------------------------------


BASELINE_CHOICES = ("formal", "local", "both")
VERSION_EFFECT_LABEL = "qwen3:8b@0.7.3"


def build_comparison(
    *,
    config: HostedConfig,
    labels: Sequence[str],
    include_bridge: bool,
    pilot: bool,
    runs_root: Path,
    workspaces_root: Path,
    reference_of: ReferenceOf,
    similarity: SimilarityFn,
    baseline: str = "both",
) -> dict[str, Any]:
    """The whole comparison: every label's candidate (``sin corrida`` if its folder is absent).

    Each candidate holds one comparison block per selected baseline: ``vs_formal`` (the frozen
    formal run, the primary baseline) and ``vs_local`` (the secondary baseline, ``qwen3:8b`` on
    OpenKOS 0.7.3; ``sin corrida`` while its run is missing). The secondary baseline itself is
    compared with the formal one as ``version_effect`` (not part of the Bonferroni family).
    """
    if baseline not in BASELINE_CHOICES:
        raise ValueError(
            f"baseline must be one of {', '.join(BASELINE_CHOICES)}; got {baseline!r}."
        )

    def load(name: str) -> RunData | None:
        run_dir = runs_root / name
        complete = (run_dir / "manifest.json").is_file() and (
            run_dir / "extracciones.jsonl"
        ).is_file()
        return load_run_data(run_dir, workspaces_root / name) if complete else None

    formal = load(config.baseline_run_name)
    if formal is None:
        raise FileNotFoundError(f"The baseline run {config.baseline_run_name} is not stored.")
    local_name = config.local_baseline.run_name
    local = load(local_name)

    def compare(
        base: RunData,
        data: RunData,
        price: ModelPrice | None = None,
        dashboard: float | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "ok",
            **compare_to_baseline(
                base,
                data,
                reference_of=reference_of,
                similarity=similarity,
                spec=config.comparison,
                n_models=len(config.models),
                price=price,
                dashboard_usd=dashboard,
            ),
        }

    candidates: list[dict[str, Any]] = []
    for label in labels:
        name = hosted_run_name(label, pilot=pilot)
        data = load(name)
        if data is None:
            candidates.append({"label": label, "run_name": name, "status": NO_RUN})
            continue
        spec = config.models[label]
        stored = data.manifest.get("openkos") or {}
        price = config.prices.get(label)
        dashboard = config.dashboard_usd.get(label)
        item: dict[str, Any] = {
            "label": label,
            "run_name": name,
            "provider": data.manifest.get("provider") or spec.provider,
            "model": stored.get("generative_model") or spec.model,
            "base_url": stored.get("base_url") or spec.base_url,
            "status": "ok",
        }
        if baseline in ("formal", "both"):
            item["vs_formal"] = compare(formal, data, price, dashboard)
        if baseline in ("local", "both"):
            item["vs_local"] = (
                {"status": NO_RUN, "baseline_run_name": local_name}
                if local is None
                else compare(local, data, price, dashboard)
            )
        candidates.append(item)
    version_effect: dict[str, Any] | None = None
    if baseline != "formal":
        version_effect = (
            {"status": NO_RUN, "run_name": local_name}
            if local is None
            else {
                "label": VERSION_EFFECT_LABEL,
                "model": config.local_baseline.model,
                "run_name": local_name,
                **compare(formal, local),
            }
        )
    payload: dict[str, Any] = {
        "adr": "0026",
        "descriptive": True,
        "baseline": baseline,
        "baseline_run_name": config.baseline_run_name,
        "local_baseline_run_name": local_name,
        "primary_tau": config.comparison.tau,
        "n_models": len(config.models),
        "candidates": candidates,
        "version_effect": version_effect,
        "bridge": None,
    }
    if include_bridge:
        bridge = load(config.bridge.run_name)
        payload["bridge"] = (
            {"run_name": config.bridge.run_name, "status": NO_RUN}
            if bridge is None
            else {
                "run_name": config.bridge.run_name,
                "status": "ok",
                **bridge_check(
                    bridge=bridge,
                    formal=formal,
                    reference_of=reference_of,
                    similarity=similarity,
                    tau=config.comparison.tau,
                ),
            }
        )
    return payload


CSV_COLUMNS = (
    "label", "model", "run_name", "baseline", "status", "series", "n_meetings", "tau",
    "baseline_precision", "baseline_recall", "baseline_f1",
    "candidate_precision", "candidate_recall", "candidate_f1",
    "diff_precision", "diff_precision_low", "diff_precision_high",
    "diff_recall", "diff_recall_low", "diff_recall_high",
    "diff_f1", "diff_f1_low", "diff_f1_high",
    "verdict", "recall_up_precision_drop",
    "time_ratio", "time_ratio_low", "time_ratio_high", "time_verdict",
    "complete_share", "decisions_per_meeting",
    "tokens_prompt", "tokens_total", "cost_status", "cost_usd", "cost_lower_bound",
    "cost_median_per_meeting_usd", "dashboard_usd",
)  # fmt: skip


def _block_rows(head: Mapping[str, Any], block: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The CSV rows (one per tau) of one comparison block."""
    operation = block["operation"]
    ratio = operation["time"]["ratio"] or {"estimate": None, "interval": [None, None]}
    tokens = operation["tokens"]["candidate"]
    rows: list[dict[str, Any]] = []
    for entry in block["taus"].values():
        diff = entry["diff"]
        row: dict[str, Any] = {
            **head,
            "series": ",".join(block["series_covered"]),
            "n_meetings": block["n_meetings"],
            "tau": entry["tau"],
            "verdict": entry["verdict"],
            "recall_up_precision_drop": entry.get("recall_up_precision_drop"),
            "time_ratio": ratio["estimate"],
            "time_ratio_low": ratio["interval"][0],
            "time_ratio_high": ratio["interval"][1],
            "time_verdict": operation["time"]["verdict"],
            "complete_share": operation["completeness"]["candidate"]["share"],
            "decisions_per_meeting": operation["decisions_per_meeting"]["candidate"]["mean"],
            "tokens_prompt": (tokens or {}).get("prompt"),
            "tokens_total": (tokens or {}).get("total"),
            "cost_status": operation["cost"]["status"],
            "cost_usd": operation["cost_usd"],
            "cost_lower_bound": operation["cost"]["lower_bound"],
            "cost_median_per_meeting_usd": operation["cost"]["median_per_meeting_usd"],
            "dashboard_usd": operation["dashboard_usd"],
        }
        for name in METRICS:
            row[f"baseline_{name}"] = entry["baseline"][name]
            row[f"candidate_{name}"] = entry["candidate"][name]
            row[f"diff_{name}"] = diff[name]["estimate"]
            row[f"diff_{name}_low"] = diff[name]["interval"][0]
            row[f"diff_{name}_high"] = diff[name]["interval"][1]
        rows.append(row)
    return rows


def comparison_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One CSV row per candidate, baseline and tau; a missing run gets a single row.

    The ``baseline`` column is ``formal`` or ``local``. A candidate with a run but without the
    local baseline run gets one ``sin corrida`` row for ``local``. The version effect (local
    baseline against formal) follows as a row labelled ``qwen3:8b@0.7.3``.
    """
    rows: list[dict[str, Any]] = []
    for item in payload["candidates"]:
        head = {
            "label": item["label"],
            "model": item.get("model"),
            "run_name": item["run_name"],
            "status": item["status"],
        }
        if item["status"] != "ok":
            rows.append(head)
            continue
        for name in ("formal", "local"):
            block = item.get(f"vs_{name}")
            if block is None:
                continue
            labelled = {**head, "baseline": name, "status": block["status"]}
            if block["status"] != "ok":
                rows.append(labelled)
            else:
                rows.extend(_block_rows(labelled, block))
    effect = payload.get("version_effect")
    if effect is not None:
        head = {
            "label": effect.get("label", VERSION_EFFECT_LABEL),
            "model": effect.get("model"),
            "run_name": effect["run_name"],
            "baseline": "formal",
            "status": effect["status"],
        }
        rows.extend(_block_rows(head, effect) if effect["status"] == "ok" else [head])
    return rows


def write_comparison(payload: Mapping[str, Any], out_dir: Path) -> tuple[Path, Path]:
    """Write ``comparacion.json`` and ``comparacion.csv`` into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "comparacion.json"
    csv_path = out_dir / "comparacion.csv"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(comparison_rows(payload))
    return json_path, csv_path
