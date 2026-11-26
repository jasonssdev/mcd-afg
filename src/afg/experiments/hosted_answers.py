"""Answer comparison of the hosted extractors against C1 (ADR 0026, amendments 3 and 4).

For each paid model, Experiment B ran C2 alone over the workspaces derived from the model's
extraction (``afg experiment b-derive``). This module compares those answers with the formal
run, reading only the stored records of ``reports/experiment-b/<run>/``:

* **Primary** (fourth amendment): the paired difference "C2 with that extractor minus C1 of the
  current infrastructure" (Ollama 0.40.16, ``experimento-b-c1-ollama-0-40-16``) in the correctness
  of E3, computed by the existing analysis (:func:`afg.experiments.analysis.analyze_runs`, the D16
  bootstrap of ADR 0010: runs averaged per question, questions resampled) at the Bonferroni level
  ``1 - family_alpha / n_models``. The verdict reads the interval against 0: *supera a C1*
  (entirely above), *no se distingue de C1* (contains 0) or *queda bajo C1* (entirely below).
* **Secondary**: the same difference against C1 formal, against C2 formal and against C2 over the
  0.7.3 baseline (to attribute an improvement to the model and not to the OpenKOS version), and,
  per stratum and in total, correctness, abstention, ``evidence_supported``, ``citation_correct``,
  ``outdated_among_answered`` (H4) and ``answer_seconds`` beside the reference.
* **Infrastructure effect**: "C1 current minus C1 formal" per stratum and in E3, at the nominal 95 %
  level (it is not part of the Bonferroni family): how much the change of Ollama moved C1 alone.

A run that does not exist yet, or has no C2 records, is reported as ``pendiente``. The comparison
is descriptive: the figures of C1 and C2 formal were seen before the amendment (decision 6), so it
does not replace the D16 criterion of the formal run. Nothing here calls a model, and the payload
carries figures only, never answers, rationales or decision texts (ADR 0005).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from afg.evaluation.scoring import IntervalSettings
from afg.experiments.analysis import (
    ALL_STRATA,
    PRIMARY_METRIC,
    PRIMARY_STRATUM,
    AnalysisReport,
    CellSummary,
    MinQuestions,
    RateEstimate,
    analyze_runs,
)

__all__ = [
    "ABOVE",
    "BELOW",
    "INDISTINGUISHABLE",
    "AnswerComparisonSpec",
    "answer_comparison_rows",
    "answer_run_name",
    "build_answer_comparison",
    "verdict_for",
    "write_answer_comparison",
]

ABOVE = "supera a"
INDISTINGUISHABLE = "no se distingue de"
BELOW = "queda bajo"
PENDING = "pendiente"
NO_RUN = "sin corrida"
C1_FORMAL = "C1 formal"
C1_NOW = "C1 actual"
NOMINAL_LEVEL = 0.95
C2_FORMAL = "C2 formal"
C2_BASE = "C2 de la línea base 0.7.3"
BASELINE_KEY = "baseline_0_7_3"
SUBJECT, REFERENCE = "C2", "C1"
"""Condition ids the existing analysis compares as ``C2`` against ``C1``; both sides are
relabelled to them, so the primary comparison is the very one :func:`analyze_runs` flags."""
CELL_METRICS = ("correct", "evidence_supported", "citation_correct", "outdated_among_answered")
PAIRED_METRICS = ("correct", "evidence_supported")
INFRASTRUCTURE_ROW = "infraestructura"
CSV_COLUMNS = (
    "model",
    "comparison",
    "reference",
    "status",
    "reason",
    "stratum",
    "metric",
    "n_pairs",
    "difference",
    "lower",
    "upper",
    "verdict",
    "sample_sufficient",
)

Record = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AnswerComparisonSpec:
    """Parameters of the comparison (ADR 0026, amendment 3, decision 2)."""

    models: tuple[str, ...]
    """Labels of the paid models: the Bonferroni family and the run folders."""
    family_alpha: float
    interval: IntervalSettings
    """Resamples and seed of the bootstrap; the confidence level is replaced by Bonferroni's."""
    min_questions: MinQuestions
    formal_run: str = "experimento-b-formal"
    base_run: str = "experimento-b-base-0-7-3"
    c1_run: str = "experimento-b-c1-ollama-0-40-16"
    """C1 control with the extension's infrastructure (fourth amendment, decision 2)."""
    min_runs: int = 3

    @property
    def level(self) -> float:
        return 1 - self.family_alpha / len(self.models)


def answer_run_name(label: str) -> str:
    """Experiment B run folder of a model: ``experimento-b-hosted-<label>``."""
    return f"experimento-b-hosted-{label}"


def verdict_for(lower: float, upper: float, reference: str) -> str:
    """Wording of the amendment: the interval of the difference against 0, naming the reference."""
    if lower > 0.0:
        return f"{ABOVE} {reference}"
    if upper < 0.0:
        return f"{BELOW} {reference}"
    return f"{INDISTINGUISHABLE} {reference}"


def _stratum(record: Record) -> str:
    return str(record["stratum"]).split("_", 1)[0]


def _of(records: Sequence[Record] | None, condition: str) -> list[Record]:
    return [r for r in records or () if str(r["condition"]) == condition]


def _latest(records: Sequence[Record]) -> list[Record]:
    latest: dict[tuple[str, int], Record] = {}
    for record in records:
        latest[(str(record["question_id"]), int(record["run"]))] = record
    return list(latest.values())


def _estimate(estimate: RateEstimate | None) -> dict[str, Any] | None:
    if estimate is None:
        return None
    return {
        "point": estimate.point,
        "lower": estimate.lower,
        "upper": estimate.upper,
        "n_questions": estimate.n_questions,
    }


def _side(cell: CellSummary | None, records: Sequence[Record], stratum: str) -> dict[str, Any]:
    """Metrics of one side of a stratum: the cell's rates plus abstention and answer time."""
    kept = [
        r
        for r in _latest(records)
        if r.get("error") is None and (stratum == ALL_STRATA or _stratum(r) == stratum)
    ]
    abstained = [bool((r.get("answer") or {}).get("abstained")) for r in kept]
    seconds = [float(r["answer_seconds"]) for r in kept if r.get("answer_seconds") is not None]
    out: dict[str, Any] = {"records": len(kept)}
    for metric in CELL_METRICS:
        if cell is not None and metric in cell.metrics:
            out[metric] = _estimate(cell.metrics[metric])
    out["abstention_rate"] = sum(abstained) / len(abstained) if abstained else None
    out["answer_seconds"] = sum(seconds) / len(seconds) if seconds else None
    return out


def _difference(report: AnalysisReport, stratum: str, metric: str) -> dict[str, Any] | None:
    for c in report.comparisons:
        if (c.condition_a, c.condition_b, c.stratum, c.metric) == (
            SUBJECT,
            REFERENCE,
            stratum,
            metric,
        ):
            return {
                "stratum": stratum,
                "metric": metric,
                "n_pairs": c.n_pairs,
                "difference": c.difference,
                "lower": c.difference_lower,
                "upper": c.difference_upper,
                "sample_sufficient": c.sample_sufficient,
            }
    return None


def _questions(records: Sequence[Record]) -> int:
    return len({str(r["question_id"]) for r in records if r.get("error") is None})


def _pair(
    subject: Sequence[Record],
    reference: Sequence[Record],
    *,
    reference_label: str,
    spec: AnswerComparisonSpec,
    with_warnings: bool,
    level: float | None = None,
) -> dict[str, Any]:
    """The paired comparison of ``subject`` against ``reference`` records.

    ``level`` replaces the Bonferroni confidence level (the infrastructure effect uses 95 %).
    """
    merged = [{**r, "condition": SUBJECT} for r in subject] + [
        {**r, "condition": REFERENCE} for r in reference
    ]
    report = analyze_runs(
        merged,
        settings=replace(spec.interval, confidence_level=spec.level if level is None else level),
        min_questions=spec.min_questions,
        min_runs=spec.min_runs,
    )
    cells = {(c.condition, c.stratum): c for c in report.cells}
    strata = [*sorted({c.stratum for c in report.cells} - {ALL_STRATA}), ALL_STRATA]
    rows = []
    for stratum in strata:
        differences = {m: _difference(report, stratum, m) for m in PAIRED_METRICS}
        rows.append(
            {
                "stratum": stratum,
                "subject": _side(cells.get((SUBJECT, stratum)), subject, stratum),
                "reference": _side(cells.get((REFERENCE, stratum)), reference, stratum),
                "differences": {
                    m: {**d, "verdict": verdict_for(d["lower"], d["upper"], reference_label)}
                    for m, d in differences.items()
                    if d is not None
                },
            }
        )
    primary = _difference(report, PRIMARY_STRATUM, PRIMARY_METRIC)
    comparison: dict[str, Any]
    if primary is None:
        comparison = {"status": PENDING, "reason": "sin preguntas pareadas en E3"}
    else:
        comparison = {
            "status": "ok",
            "reference": reference_label,
            **primary,
            "verdict": verdict_for(primary["lower"], primary["upper"], reference_label),
        }
    warnings: list[str] = []
    if with_warnings:
        warnings.extend(report.warnings)
        n_subject, n_reference = _questions(subject), _questions(reference)
        if n_subject < n_reference:
            warnings.append(
                f"La corrida cubre {n_subject} de las {n_reference} preguntas de la referencia."
            )
    return {"comparison": comparison, "strata": rows, "warnings": warnings}


def _model_entry(
    label: str,
    run: str,
    records_by_run: Mapping[str, Sequence[Record] | None],
    spec: AnswerComparisonSpec,
) -> dict[str, Any]:
    subject = _of(records_by_run.get(run), SUBJECT)
    if not subject:
        has_run = records_by_run.get(run)
        return {
            "run": run,
            "status": PENDING,
            "reason": "sin registros de C2" if has_run else NO_RUN,
        }
    c1 = _of(records_by_run.get(spec.c1_run), REFERENCE)
    if not c1:
        return {
            "run": run,
            "status": PENDING,
            "reason": f"sin la corrida de C1 con la infraestructura actual ({spec.c1_run})",
        }
    primary = _pair(subject, c1, reference_label=C1_NOW, spec=spec, with_warnings=True)
    secondary: dict[str, Any] = {}
    for key, source, condition, reference_label in (
        ("vs_c1_formal", spec.formal_run, REFERENCE, C1_FORMAL),
        ("vs_c2_formal", spec.formal_run, SUBJECT, C2_FORMAL),
        ("vs_c2_base_0_7_3", spec.base_run, SUBJECT, C2_BASE),
    ):
        reference = _of(records_by_run.get(source), condition)
        if not reference:
            secondary[key] = {"status": PENDING, "reason": NO_RUN}
            continue
        pair = _pair(
            subject, reference, reference_label=reference_label, spec=spec, with_warnings=False
        )
        secondary[key] = {**pair["comparison"], "strata": pair["strata"]}
    return {
        "run": run,
        "status": "ok",
        "primary": primary["comparison"],
        "secondary": secondary,
        "strata": primary["strata"],
        "warnings": primary["warnings"],
    }


def _infrastructure_effect(
    records_by_run: Mapping[str, Sequence[Record] | None], spec: AnswerComparisonSpec
) -> dict[str, Any]:
    """C1 of the current infrastructure minus C1 formal, per stratum, at the nominal level."""
    runs = {"current": spec.c1_run, "formal": spec.formal_run}
    current = _of(records_by_run.get(spec.c1_run), REFERENCE)
    formal = _of(records_by_run.get(spec.formal_run), REFERENCE)
    if not current or not formal:
        missing = [runs[k] for k, found in (("current", current), ("formal", formal)) if not found]
        return {
            "status": PENDING,
            "reason": f"sin C1 en {', '.join(missing)}",
            "runs": runs,
            "level": NOMINAL_LEVEL,
        }
    pair = _pair(
        current,
        formal,
        reference_label=C1_FORMAL,
        spec=spec,
        with_warnings=False,
        level=NOMINAL_LEVEL,
    )
    effect: dict[str, Any] = {
        "status": pair["comparison"]["status"],
        "runs": runs,
        "level": NOMINAL_LEVEL,
        "comparison": pair["comparison"],
        "strata": pair["strata"],
    }
    if effect["status"] != "ok":
        effect["reason"] = pair["comparison"]["reason"]
    return effect


def build_answer_comparison(
    records_by_run: Mapping[str, Sequence[Record] | None],
    spec: AnswerComparisonSpec,
    *,
    only: Sequence[str] | None = None,
) -> dict[str, Any]:
    """The comparison payload (JSON-ready) from the stored records of each Experiment B run.

    ``records_by_run`` maps a run folder name to its latest records, ``None`` (or empty) when the
    run does not exist yet. It must hold ``spec.c1_run`` (C1 of the current infrastructure),
    ``spec.formal_run`` (C1 and C2 formal), ``spec.base_run`` (the 0.7.3 baseline) and
    ``answer_run_name(label)`` for every model reported. ``only`` limits the models reported;
    the Bonferroni family stays the whole of ``spec.models``.

    Raises:
        ValueError: ``only`` names a label that is not in ``spec.models``.
        afg.evaluation.scoring.DevelopmentResultError: a run holds development-series records.
    """
    labels = tuple(spec.models if only is None else only)
    unknown = [label for label in labels if label not in spec.models]
    if unknown:
        raise ValueError(f"Unknown model label(s): {', '.join(unknown)}.")
    return {
        "adr": "0026",
        "amendment": 4,
        "descriptive": True,
        "reference": C1_NOW,
        "family": {
            "alpha": spec.family_alpha,
            "n_models": len(spec.models),
            "level": spec.level,
        },
        "bootstrap": {
            "n_resamples": spec.interval.n_resamples,
            "seed": spec.interval.seed,
            "confidence_level": spec.level,
        },
        "runs": {
            "c1_actual": spec.c1_run,
            "formal": spec.formal_run,
            "baseline_0_7_3": spec.base_run,
        },
        "infrastructure_effect": _infrastructure_effect(records_by_run, spec),
        "models": {
            label: _model_entry(label, answer_run_name(label), records_by_run, spec)
            for label in labels
        },
        BASELINE_KEY: _model_entry(BASELINE_KEY, spec.base_run, records_by_run, spec),
    }


def answer_comparison_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One CSV row per model and comparison (primary and secondary), pending ones included."""
    rows: list[dict[str, Any]] = []
    entries = {**payload["models"], BASELINE_KEY: payload[BASELINE_KEY]}
    for model, entry in entries.items():
        if entry["status"] != "ok":
            rows.append(
                {
                    "model": model,
                    "comparison": "primary",
                    "status": PENDING,
                    "reason": entry["reason"],
                }
            )
            continue
        for name, comparison in (("primary", entry["primary"]), *entry["secondary"].items()):
            rows.append(
                {
                    "model": model,
                    "comparison": name,
                    "reason": comparison.get("reason", ""),
                    **{k: comparison.get(k, "") for k in CSV_COLUMNS[2:] if k != "reason"},
                }
            )
    effect = payload["infrastructure_effect"]
    comparison = effect.get("comparison", {})
    rows.append(
        {
            "model": INFRASTRUCTURE_ROW,
            "comparison": "infrastructure_effect",
            "reason": effect.get("reason") or comparison.get("reason", ""),
            **{k: comparison.get(k, "") for k in CSV_COLUMNS[2:] if k != "reason"},
            "status": effect["status"],
        }
    )
    return rows


def write_answer_comparison(payload: Mapping[str, Any], out_dir: Path) -> tuple[Path, Path]:
    """Write ``respuestas-comparacion.json`` and ``.csv`` into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "respuestas-comparacion.json"
    csv_path = out_dir / "respuestas-comparacion.csv"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(answer_comparison_rows(payload))
    return json_path, csv_path
