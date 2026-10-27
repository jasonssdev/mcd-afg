"""Consolidated cost and latency table of the models the thesis uses (notebook ``19``).

Every row is read from a stored result -- the records and manifests of the Experiment B
runs, the model screen of OpenKOS's decision pass, the judge calibration and the tau judge
run -- and never measured here: no model is called. A row is one *role* (answer generator,
judge, extraction) of one *model* doing one *activity*, with the number of units it covers
(calls, runs), the mean and total wall-clock seconds, and a ratio against a baseline model
where the comparison makes sense.

The seconds are wall-clock on the machine that produced each result; they are comparable
inside one source and only indicative across sources (different loads, different machines).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from afg.evaluation.judge_calibration_results import StoredCalibration
from afg.experiments.model_screen import FAILURE_FLOOR, MARGIN_FLOOR, VOLUME_FACTOR

COLUMNS: tuple[str, ...] = (
    "role",
    "model",
    "activity",
    "units",
    "mean_seconds",
    "total_seconds",
    "ratio",
    "detail",
    "source",
)


@dataclass(frozen=True, slots=True)
class CostRow:
    """One role/model/activity line of the cost table."""

    role: str
    """``answer``, ``judge`` or ``extraction``."""
    model: str
    activity: str
    units: int
    """Calls or runs the row covers."""
    mean_seconds: float
    """Mean wall-clock seconds per unit."""
    total_seconds: float
    ratio: float | None = None
    """Mean seconds over the baseline's, when the row is part of a comparison."""
    detail: str = ""
    source: str = ""


def answer_and_judge_costs(
    records: Iterable[Mapping[str, Any]], *, label: str, source: str = ""
) -> list[CostRow]:
    """Answer rows (one per condition) and one judge row from Experiment B records.

    Records without a timing (an error before the call) are not counted. ``label`` names the
    run in the ``activity`` column.
    """
    answers: dict[str, list[float]] = {}
    models: dict[str, str] = {}
    judge_times: list[float] = []
    judge_model = ""
    for record in records:
        condition = str(record["condition"])
        if record.get("answer_seconds") is not None:
            answers.setdefault(condition, []).append(float(record["answer_seconds"]))
            models[condition] = str(record["generative_model"])
        if record.get("judge_seconds") is not None:
            judge_times.append(float(record["judge_seconds"]))
            judge_model = str((record.get("judge") or {}).get("model", ""))
    rows = [
        CostRow(
            "answer",
            models[condition],
            f"{label} / {condition}",
            len(times),
            sum(times) / len(times),
            sum(times),
            source=source,
        )
        for condition, times in sorted(answers.items())
    ]
    if judge_times:
        rows.append(
            CostRow(
                "judge",
                judge_model,
                label,
                len(judge_times),
                sum(judge_times) / len(judge_times),
                sum(judge_times),
                source=source,
            )
        )
    return rows


def screen_costs(
    scored: Mapping[str, Mapping[str, Any]], *, phase: str, baseline: str, source: str = ""
) -> list[CostRow]:
    """One extraction row per model and series of an OpenKOS model screen (``scored.json``).

    ``ratio`` divides the mean seconds per run by the ``baseline`` model's on the same series
    (``None`` when the baseline is absent for that series).
    """
    mean_by: dict[tuple[str, str], float] = {}
    for entry in scored.values():
        times = entry["wall_s_per_run"]
        mean_by[(str(entry["model"]), str(entry["series"]))] = sum(times) / len(times)
    rows = []
    for entry in scored.values():
        model, series = str(entry["model"]), str(entry["series"])
        times = entry["wall_s_per_run"]
        base = mean_by.get((baseline, series))
        mean = mean_by[(model, series)]
        rows.append(
            CostRow(
                "extraction",
                model,
                f"{phase} {series}",
                len(times),
                mean,
                float(sum(times)),
                ratio=mean / base if base else None,
                detail=(
                    f"{entry['decisions_per_meeting_mean']:.1f} decisiones/reunión; "
                    f"fallas {entry['failed_meeting_runs']} de {entry['meeting_runs']}"
                ),
                source=source,
            )
        )
    return rows


def screen_quality(
    scored: Mapping[str, Mapping[str, Any]], *, tau: float, phase: str
) -> pd.DataFrame:
    """Quality and cost of every model and series of a screen at one similarity threshold.

    One row per ``model|series`` entry with the mean recall, precision and F1 (and the F1
    range over the runs) at ``tau``, next to the mean seconds per run, the decisions per
    meeting and the failed meeting-runs. The quality is the one stored in ``scored.json``
    (it equals the thesis's own score, notebook 15).

    Raises:
        ValueError: if ``tau`` is not on an entry's curve.
    """
    rows = []
    for entry in scored.values():
        point = next((p for p in entry["curve"] if abs(p["tau"] - tau) < 1e-9), None)
        if point is None:
            raise ValueError(
                f"tau={tau} is not on the curve of {entry['model']}|{entry['series']}."
            )
        times = entry["wall_s_per_run"]
        rows.append(
            {
                "model": entry["model"],
                "series": entry["series"],
                "phase": phase,
                "runs": len(times),
                "recall": point["recall"]["mean"],
                "precision": point["precision"]["mean"],
                "f1": point["f1"]["mean"],
                "f1_min": point["f1"]["min"],
                "f1_max": point["f1"]["max"],
                "seconds_per_run": sum(times) / len(times),
                "decisions_per_meeting": entry["decisions_per_meeting_mean"],
                "failed_meeting_runs": entry["failed_meeting_runs"],
                "meeting_runs": entry["meeting_runs"],
            }
        )
    return pd.DataFrame(rows)


def screen_by_model(quality: pd.DataFrame) -> pd.DataFrame:
    """Average :func:`screen_quality` over the series, one row per model (input order)."""
    numeric = [
        "recall",
        "precision",
        "f1",
        "seconds_per_run",
        "decisions_per_meeting",
        "failed_meeting_runs",
        "meeting_runs",
    ]
    return quality.groupby("model", sort=False)[numeric].mean()


def screen_rule(quality: pd.DataFrame, *, baseline: str) -> pd.DataFrame:
    """The pre-registered selection rule of the model screen, from stored quality rows.

    Same four conditions as :func:`afg.experiments.model_screen.selection_rule` (margin,
    no recall loss, failures, volume), but computed from the frame of :func:`screen_quality`
    so a notebook can apply it with no model server. One row per candidate and series; the
    ``baseline`` model is not a candidate. A test checks this reproduces the stored screen.
    """
    base = quality[quality["model"] == baseline].set_index("series")
    rows = []
    for _, cand in quality[quality["model"] != baseline].iterrows():
        ref = base.loc[cand["series"]]
        spread = max(cand["f1_max"] - cand["f1_min"], ref["f1_max"] - ref["f1_min"])
        needed = max(MARGIN_FLOOR, spread)
        d_f1 = cand["f1"] - ref["f1"]
        row = {
            "candidate": cand["model"],
            "series": cand["series"],
            "d_f1": d_f1,
            "spread": spread,
            "needed": needed,
            "margin_ok": bool(d_f1 >= needed),
            "recall_ok": bool(cand["recall"] >= ref["recall"]),
            "failures_ok": bool(
                cand["failed_meeting_runs"] <= max(FAILURE_FLOOR, ref["failed_meeting_runs"])
            ),
            "volume_ok": bool(
                cand["decisions_per_meeting"] <= VOLUME_FACTOR * ref["decisions_per_meeting"]
            ),
        }
        row["passes"] = all(row[c] for c in ("margin_ok", "recall_ok", "failures_ok", "volume_ok"))
        rows.append(row)
    return pd.DataFrame(rows)


def screen_winner(rule: pd.DataFrame) -> str | None:
    """The candidate that passes on every series with the largest mean F1 gain, else ``None``."""
    if rule.empty:
        return None
    passing = rule.groupby("candidate", sort=False).agg(
        passes=("passes", "all"), mean_gain=("d_f1", "mean")
    )
    passing = passing[passing["passes"]]
    return None if passing.empty else str(passing["mean_gain"].idxmax())


def judge_calibration_costs(stored: StoredCalibration, *, source: str = "") -> list[CostRow]:
    """One judge row per calibration candidate: mean seconds per call over its calls."""
    return [
        CostRow(
            "judge",
            c.model,
            f"calibración ({stored.n_items} ítems)",
            c.calls,
            c.latency_seconds,
            c.latency_seconds * c.calls,
            detail=f"fallas {c.failures} de {c.calls}",
            source=source,
        )
        for c in stored.candidates
    ]


def tau_judge_cost(meta: Mapping[str, Any], *, source: str = "") -> CostRow:
    """The judge row of the tau calibration (``run.json``): total seconds over its pairs."""
    n = int(meta["n_pairs"])
    total = float(meta["judge_seconds_total"])
    return CostRow(
        "judge",
        str(meta["judge_model"]),
        "juicio de pares para τ",
        n,
        total / n,
        total,
        source=source,
    )


def extraction_manifest_cost(
    manifest: Mapping[str, Any], *, label: str, source: str = ""
) -> CostRow:
    """The full OpenKOS extraction of one series, from a run manifest's timestamps.

    The duration spans every run of the folder, so ``mean_seconds`` divides it by the number of
    series-runs: ``runs``, times the series of an ``a-batch`` manifest (``series_ids``).

    Raises:
        ValueError: if the manifest has no ``created_at``/``updated_at`` pair.
    """
    if not manifest.get("created_at") or not manifest.get("updated_at"):
        raise ValueError(f"{label}: the manifest needs created_at and updated_at.")
    start = datetime.fromisoformat(str(manifest["created_at"]))
    end = datetime.fromisoformat(str(manifest["updated_at"]))
    total = (end - start).total_seconds()
    runs = int(manifest.get("runs") or 1) * max(1, len(manifest.get("series_ids") or ()))
    openkos = manifest.get("openkos") or {}
    versions = ", ".join(str(v) for v in openkos.get("versions", []))
    return CostRow(
        "extraction",
        str(openkos.get("generative_model", "")),
        f"OpenKOS completo {manifest.get('series', '')} ({label})",
        runs,
        total / runs,
        total,
        detail=f"OpenKOS {versions}" if versions else "",
        source=source,
    )


def cost_frame(rows: Sequence[CostRow]) -> pd.DataFrame:
    """The rows as a frame with the stable :data:`COLUMNS`."""
    return pd.DataFrame(
        [
            {
                "role": r.role,
                "model": r.model,
                "activity": r.activity,
                "units": r.units,
                "mean_seconds": r.mean_seconds,
                "total_seconds": r.total_seconds,
                "ratio": r.ratio,
                "detail": r.detail,
                "source": r.source,
            }
            for r in rows
        ],
        columns=list(COLUMNS),
    )
