"""Raw results of the judge calibration, stored for the notebook (issue #82).

``afg judge calibration-run`` is slow (it calls every candidate model on every item, in both
orders and with every seed), so the notebook does not run it: it loads the file written here.
Numbers are only copied from :class:`afg.evaluation.judge_calibration_runner.CalibrationResult`,
never recomputed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.evaluation.judge_calibration_runner import CalibrationResult
from afg.shared.paths import REPORTS_DIR

RESULTS_PATH: Path = REPORTS_DIR / "judge-calibration" / "resultados.json"


class CalibrationResultsError(ValueError):
    """Raised when the stored results cannot be read."""


@dataclass(frozen=True, slots=True)
class StoredCandidate:
    model: str
    kappa: float
    kappa_lower: float
    kappa_upper: float
    position_consistency: float
    seed_consistency: float
    e4_accuracy: float
    json_valid_rate: float
    verbosity_flip_rate: float
    latency_seconds: float
    evidence_kappa: float | None
    calls: int
    failures: int


@dataclass(frozen=True, slots=True)
class StoredCalibration:
    n_items: int
    candidates: tuple[StoredCandidate, ...]
    outcome: str
    selected: str | None
    failures: dict[str, tuple[str, ...]]


def save_calibration_results(path: Path, result: CalibrationResult, *, n_items: int) -> None:
    """Write ``result`` as JSON (UTF-8, LF), creating the folder."""
    payload: dict[str, Any] = {
        "n_items": n_items,
        "candidates": [
            {
                "model": run.metrics.model,
                "kappa": run.metrics.kappa_correct.point_estimate,
                "kappa_lower": run.metrics.kappa_correct.lower,
                "kappa_upper": run.metrics.kappa_correct.upper,
                "position_consistency": run.metrics.position_consistency,
                "seed_consistency": run.metrics.seed_consistency,
                "e4_accuracy": run.metrics.e4_accuracy,
                "json_valid_rate": run.metrics.json_valid_rate,
                "verbosity_flip_rate": run.metrics.verbosity_flip_rate,
                "latency_seconds": run.metrics.latency_seconds,
                "evidence_kappa": run.evidence_supported.kappa if run.evidence_supported else None,
                "calls": run.calls,
                "failures": run.failures,
            }
            for run in result.runs
        ],
        "decision": {
            "outcome": result.decision.outcome,
            "selected": result.decision.selected,
            "failures": {model: list(f) for model, f in result.decision.failures.items()},
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_calibration_results(path: Path) -> StoredCalibration:
    """Read what :func:`save_calibration_results` wrote."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        decision = data["decision"]
        return StoredCalibration(
            n_items=int(data["n_items"]),
            candidates=tuple(StoredCandidate(**c) for c in data["candidates"]),
            outcome=str(decision["outcome"]),
            selected=decision["selected"],
            failures={m: tuple(f) for m, f in decision["failures"].items()},
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise CalibrationResultsError(f"{path.name}: no se pudo leer ({exc}).") from exc
