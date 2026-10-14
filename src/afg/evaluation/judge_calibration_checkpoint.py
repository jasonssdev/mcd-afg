"""Per-candidate checkpoints of the judge calibration (issue #82).

A candidate run takes tens of minutes, so each finished candidate is written to its own file
at once and a rerun skips it. A stored result is only reused when its key matches: the key is
a hash of everything the result depends on (the labeled items and the excerpts the judge reads,
the thresholds, the model tag, its reasoning setting, the generator and the judge prompt), so a
changed label, prompt or threshold can never be answered with a stale result.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from afg.domain.question import format_reference_evidence
from afg.evaluation.judge import judge_system_prompt
from afg.evaluation.judge_calibration import (
    CalibrationThresholds,
    CandidateMetrics,
    FieldAgreement,
)
from afg.evaluation.judge_calibration_runner import CandidateRun
from afg.evaluation.judge_calibration_set import CalibrationItem
from afg.evaluation.metrics import BootstrapCI


def calibration_key(
    *,
    items: Sequence[CalibrationItem],
    excerpts: Mapping[str, str],
    thresholds: CalibrationThresholds,
    model: str,
    generative_model: str,
    think: bool | str | None,
) -> str:
    """Hash of everything a candidate's result depends on; item order does not matter."""
    payload: dict[str, Any] = {
        "items": sorted(
            (
                {
                    "id": item.id,
                    "stratum": item.stratum.value,
                    "question": item.question,
                    "reference_answer": item.reference_answer,
                    "reference_evidence": format_reference_evidence(item.reference_evidence),
                    "answer_text": item.answer_text,
                    "answer_abstained": item.answer_abstained,
                    "correct": item.correct,
                    "evidence_supported": item.evidence_supported,
                    "excerpt": excerpts[item.id],
                }
                for item in items
            ),
            key=lambda row: str(row["id"]),
        ),
        "thresholds": asdict(thresholds),
        "model": model,
        "generative_model": generative_model,
        "think": think,
        "prompt": judge_system_prompt(),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _file_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model) + ".json"


class CandidateCheckpoints:
    """Stores one JSON file per candidate under ``directory``, guarded by a key."""

    def __init__(self, directory: Path, *, key_for: Callable[[str], str]) -> None:
        self._directory = directory
        self._key_for = key_for

    def save(self, model: str, run: CandidateRun) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": model,
            "key": self._key_for(model),
            "metrics": asdict(run.metrics),
            "evidence_supported": asdict(run.evidence_supported)
            if run.evidence_supported
            else None,
            "calls": run.calls,
            "failures": run.failures,
        }
        path = self._directory / _file_name(model)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def load(self, model: str) -> CandidateRun | None:
        """The stored run, or ``None`` when absent, unreadable or made for other inputs."""
        path = self._directory / _file_name(model)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data["key"] != self._key_for(model) or data["model"] != model:
                return None
            metrics = dict(data["metrics"])
            metrics["kappa_correct"] = BootstrapCI(**metrics["kappa_correct"])
            evidence = data["evidence_supported"]
            return CandidateRun(
                metrics=CandidateMetrics(**metrics),
                evidence_supported=FieldAgreement(**evidence) if evidence else None,
                calls=int(data["calls"]),
                failures=int(data["failures"]),
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None
