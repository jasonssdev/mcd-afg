"""Final report tables and figures from stored outputs only (issue #243).

Everything here reads what earlier commands already wrote -- the Experiment A report
(``informe.json``), the Experiment B analysis (``analisis.json``), the run records and manifests,
and the OE4 summary (``oe4-resumen.json``) -- and arranges it as CSV and Markdown tables plus PNG
figures. It computes no statistic and calls no model: intervals, differences and verdicts are the
stored ones; the only arithmetic is means of stored wall-clock seconds and the break-even of
:mod:`afg.evaluation.amortization`.

Development outputs are never reportable (ADR 0005). With ``descriptive`` they are written anyway,
and every table row, Markdown file and figure carries :data:`STAMP`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from afg.evaluation.amortization import break_even_queries
from afg.evaluation.scoring import DevelopmentResultError
from afg.experiments.cost_table import (
    answer_and_judge_costs,
    cost_frame,
    extraction_manifest_cost,
)

if TYPE_CHECKING:
    from afg.domain.question import Question

STAMP = "desarrollo — no reportable"
STATUS_COLUMN = "status"
B_METRICS: tuple[str, ...] = (
    "correct",
    "evidence_supported",
    "abstention_correct",
    "citation_correct",
    "outdated_among_answered",
    "wrong_among_answered",
)
_SCOPES = ("origin_meetings", "series")
_RELATION_ROWS = (
    "type_principal",
    "type_strict",
    "direction_principal",
    "direction_unknown_excluded",
)
_RELATION_VIEWS = ("end_to_end", "conditional", "among_detected")
_PALETTE = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00")
_BASELINE = "C1"


@dataclass(frozen=True, slots=True)
class BRun:
    """One Experiment B run folder, read from disk: manifest, records, analysis and OE4."""

    name: str
    manifest: Mapping[str, Any]
    records: Sequence[Mapping[str, Any]]
    analysis: Mapping[str, Any]
    oe4: Mapping[str, Any] | None = None
    oe4_rule_failures: int | None = None
    """Incorrect C2 E1 answers the rule attributes to synthesis (left out of the sheet)."""


@dataclass(frozen=True, slots=True)
class FinalInputs:
    """The stored material of the report. ``a_manifests`` maps an A run name to its manifest."""

    a_report: Mapping[str, Any] | None
    b_runs: Sequence[BRun]
    a_manifests: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class FinalTables:
    tables: dict[str, pd.DataFrame]
    stamped: bool
    captions: dict[str, str] = field(default_factory=dict)


# --- tables -----------------------------------------------------------------------------------


def a_headline_table(report: Mapping[str, Any]) -> pd.DataFrame:
    """P/R/F1 with their cluster intervals at the principal tau and the sensitivities."""
    rows = []
    for entry in report["curve"]:
        if entry.get("role") is None:
            continue
        reading = "principal" if entry["role"] == "principal" else "sensibilidad"
        for scope in _SCOPES:
            pooled = entry[scope]["pooled"]
            row: dict[str, Any] = {"tau": entry["tau"], "reading": reading, "scope": scope}
            for name in ("precision", "recall", "f1"):
                low, high = pooled["intervals"][name]
                row |= {name: pooled[name], f"{name}_lower": low, f"{name}_upper": high}
            row |= {k: pooled[k] for k in ("tp", "fp", "fn", "n_clusters")}
            row["null_coverage"] = entry.get("null_coverage")
            rows.append(row)
    return pd.DataFrame(rows)


def a_relations_table(report: Mapping[str, Any]) -> pd.DataFrame:
    """Pooled relation results (existence, type and direction), one row per metric and view."""
    relations = report.get("relations")
    columns = ["metric", "view", "successes", "trials", "rate", "lower", "upper"]
    if not relations:
        return pd.DataFrame(columns=columns)
    pooled = relations["pooled"]
    rows = []
    for key in ("existence_end_to_end", "existence_conditional"):
        for view in ("precision", "recall"):
            rows.append({"metric": key, "view": view, **_proportion(pooled[key][view])})
    for key in _RELATION_ROWS:
        for view in _RELATION_VIEWS:
            rows.append({"metric": key, "view": view, **_proportion(pooled[key][view])})
    return pd.DataFrame(rows, columns=columns)


def _proportion(value: Mapping[str, Any]) -> dict[str, Any]:
    return {k: value[k] for k in ("successes", "trials", "rate", "lower", "upper")}


def b_cells_table(analyses: Sequence[tuple[str, Mapping[str, Any]]]) -> pd.DataFrame:
    """Condition x stratum cells: each metric with its interval, and the failure counts."""
    rows = []
    for run, analysis in analyses:
        for cell in analysis["cells"]:
            row: dict[str, Any] = {
                "run": run,
                "condition": cell["condition"],
                "stratum": cell["stratum"],
                "questions": cell["questions"],
                "records": cell["records"],
                "judge_failures": cell["judge_failures"],
                "errors": cell["errors"],
            }
            for metric in B_METRICS:
                est = (cell.get("metrics") or {}).get(metric)
                row[metric] = None if est is None else est["point"]
                row[f"{metric}_lower"] = None if est is None else est["lower"]
                row[f"{metric}_upper"] = None if est is None else est["upper"]
            rows.append(row)
    return pd.DataFrame(rows)


def b_paired_table(analyses: Sequence[tuple[str, Mapping[str, Any]]]) -> pd.DataFrame:
    """Stored paired comparisons (D16, secondary, H4 with its upper bound and the C0 ones)."""
    rows = []
    for run, analysis in analyses:
        for c in analysis["comparisons"]:
            rows.append(
                {
                    "run": run,
                    "primary": bool(c["primary"]),
                    "descriptive": bool(c.get("descriptive", False)),
                    "condition_a": c["condition_a"],
                    "condition_b": c["condition_b"],
                    "stratum": c["stratum"],
                    "metric": c["metric"],
                    "n_pairs": c["n_pairs"],
                    "difference": c["difference"],
                    "difference_lower": c["difference_lower"],
                    "difference_upper": c["difference_upper"],
                    "criterion": c["criterion"],
                    "nonoverlap_criterion": c["nonoverlap_criterion"],
                }
            )
    return pd.DataFrame(rows)


def cost_tables(
    runs: Sequence[BRun], a_manifests: Mapping[str, Mapping[str, Any]]
) -> dict[str, pd.DataFrame]:
    """Cost and latency per condition, and the amortized break-even against the baseline.

    Answer and judge rows come from each run's records; the extraction row of a run that used an
    Experiment A extraction (``c2_extraction``) from that run's manifest. The break-even compares
    the one-time compilation (the extraction span over its ``runs``) with the mean answer seconds
    of the structured condition and of C1, pooled over the runs of each condition. Tokens are not
    recorded by the runner, so no token column exists.
    """
    rows = []
    compile_by_condition: dict[str, float] = {}
    answers: dict[str, list[float]] = {}
    for run in runs:
        source = f"reports/experiment-b/{run.name}"
        rows += answer_and_judge_costs(run.records, label=run.name, source=source)
        for record in run.records:
            if record.get("answer_seconds") is not None:
                answers.setdefault(str(record["condition"]), []).append(
                    float(record["answer_seconds"])
                )
        a_name = run.manifest.get("c2_extraction")
        manifest = a_manifests.get(str(a_name)) if a_name else None
        if manifest is not None:
            row = extraction_manifest_cost(
                manifest, label=str(a_name), source=f"reports/experiment-a/{a_name}"
            )
            rows.append(row)
            compile_by_condition["C2"] = row.total_seconds / max(1, int(manifest.get("runs") or 1))
    return {
        "cost_latency": cost_frame(rows),
        "break_even": _break_even(compile_by_condition, answers),
    }


def _break_even(
    compile_by_condition: Mapping[str, float], answers: Mapping[str, list[float]]
) -> pd.DataFrame:
    columns = [
        "structured_condition",
        "compile_seconds",
        "structured_query_seconds",
        "rag_query_seconds",
        "break_even_queries",
        "reading",
    ]
    rows = []
    baseline = answers.get(_BASELINE)
    for condition, compile_seconds in sorted(compile_by_condition.items()):
        structured = answers.get(condition)
        if not baseline or not structured:
            continue
        rag_mean = sum(baseline) / len(baseline)
        own_mean = sum(structured) / len(structured)
        n = break_even_queries(compile_seconds, own_mean, rag_mean)
        rows.append(
            {
                "structured_condition": condition,
                "compile_seconds": compile_seconds,
                "structured_query_seconds": own_mean,
                "rag_query_seconds": rag_mean,
                "break_even_queries": n,
                "reading": (
                    f"{n:.0f} consultas"
                    if n is not None
                    else f"no existe: {condition} no es más barata por consulta que {_BASELINE}"
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


OE4_ALL = "todas"
OE4_LABELLED = "etiquetadas"
_OE4_REMAINDER_STAGE = "sintesis"


def oe4_table(
    summaries: Sequence[tuple[str, Mapping[str, Any]]],
    rule_failures: Mapping[str, int] | None = None,
) -> pd.DataFrame:
    """Share of the failures per OE4 stage, one row per run, condition, basis and stage.

    ``basis`` is ``etiquetadas`` for the failures a person labelled in the worksheet (the stored
    summary) and, when ``rule_failures`` (run name -> count) is given, ``todas`` for all the
    incorrect answers: the labelled ones plus the failures the rule attributes to synthesis, which
    the worksheet leaves out by design. Those add to the ``sintesis`` stage; no other count changes.
    """
    rows: list[dict[str, Any]] = []
    for run, summary in summaries:
        stages = {stage: int(cell["cases"]) for stage, cell in summary["stages"].items()}
        labelled = int(summary["n_failures"])
        bases = [(OE4_LABELLED, stages, labelled)]
        extra = (rule_failures or {}).get(run)
        if extra is not None:
            all_stages = dict(stages)
            all_stages[_OE4_REMAINDER_STAGE] = all_stages.get(_OE4_REMAINDER_STAGE, 0) + extra
            bases.insert(0, (OE4_ALL, all_stages, labelled + extra))
        for basis, counts, total in bases:
            for stage, cases in counts.items():
                rows.append(
                    {
                        "run": run,
                        "condition": summary["condition"],
                        "stage": stage,
                        "cases": cases,
                        "share": cases / total if total else 0.0,
                        "n_failures": total,
                        "basis": basis,
                    }
                )
    return pd.DataFrame(
        rows, columns=["run", "condition", "stage", "cases", "share", "n_failures", "basis"]
    )


# --- assembly ---------------------------------------------------------------------------------


def build_final_tables(inputs: FinalInputs, *, descriptive: bool) -> FinalTables:
    """All tables of the report.

    Raises:
        DevelopmentResultError: an input is not over the evaluation partition and ``descriptive``
            is false (ADR 0005).
    """
    unreportable = []
    if inputs.a_report is not None and not inputs.a_report.get("reportable"):
        unreportable.append(f"Experimento A ({inputs.a_report.get('run_name', '?')})")
    for run in inputs.b_runs:
        if run.manifest.get("partition") != "evaluation" or not run.analysis.get("reportable"):
            unreportable.append(f"Experimento B ({run.name})")
    if unreportable and not descriptive:
        raise DevelopmentResultError(
            f"{', '.join(unreportable)} no es de la partición de evaluación: solo esas "
            "corridas entran a las tablas del informe (ADR 0005)."
        )
    stamped = bool(unreportable)
    analyses = [(run.name, run.analysis) for run in inputs.b_runs]
    tables: dict[str, pd.DataFrame] = {}
    if inputs.a_report is not None:
        tables["a-headline"] = a_headline_table(inputs.a_report)
        tables["a-relations"] = a_relations_table(inputs.a_report)
    if inputs.b_runs:
        tables["b-cells"] = b_cells_table(analyses)
        tables["b-paired"] = b_paired_table(analyses)
        cost = cost_tables(inputs.b_runs, inputs.a_manifests)
        tables["cost-latency"] = cost["cost_latency"]
        tables["break-even"] = cost["break_even"]
        oe4 = [(r.name, r.oe4) for r in inputs.b_runs if r.oe4 is not None]
        if oe4:
            rule = {
                r.name: r.oe4_rule_failures
                for r in inputs.b_runs
                if r.oe4_rule_failures is not None
            }
            tables["oe4-stages"] = oe4_table(oe4, rule)
    if stamped:
        tables = {k: v.assign(**{STATUS_COLUMN: STAMP}) for k, v in tables.items()}
    return FinalTables(tables=tables, stamped=stamped)


# --- writing ----------------------------------------------------------------------------------


def _cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value).replace("|", "\\|")


def markdown_table(frame: pd.DataFrame, *, title: str, stamped: bool) -> str:
    """A GitHub-flavoured Markdown table, with the stamp above it when ``stamped``."""
    lines = [f"**{title}**", ""]
    if stamped:
        lines += [f"> **{STAMP}**", ""]
    columns = list(frame.columns)
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(" --- " for _ in columns) + "|")
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(_cell(row[c]) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def write_final_tables(
    final: FinalTables, name: str, *, tables_dir: Path, figures_dir: Path
) -> list[Path]:
    """Write ``<name>-<table>.csv``/``.md`` and the figures; returns the files written."""
    from afg.experiments import final_figures

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, frame in sorted(final.tables.items()):
        csv_path = tables_dir / f"{name}-{key}.csv"
        frame.to_csv(csv_path, index=False)
        md_path = tables_dir / f"{name}-{key}.md"
        md_path.write_text(
            markdown_table(frame, title=f"{name} / {key}", stamped=final.stamped),
            encoding="utf-8",
        )
        written += [csv_path, md_path]
    written += final_figures.draw_all(final, name, figures_dir)
    return written


# --- reading the stored outputs ---------------------------------------------------------------


def _stored_report(directory: Path, names: Sequence[str], command: str) -> Mapping[str, Any]:
    for name in names:
        if (directory / name).is_file():
            loaded: Mapping[str, Any] = json.loads((directory / name).read_text(encoding="utf-8"))
            return loaded
    raise FileNotFoundError(f"Falta {' o '.join(names)} en {directory}. Se genera con `{command}`.")


def load_final_inputs(
    *,
    a_run: str | None,
    b_runs: Sequence[str],
    a_dir: Path,
    b_dir: Path,
    descriptive: bool,
    questions: Mapping[str, Question] | None = None,
) -> FinalInputs:
    """Read the stored reports of the named runs; nothing is recomputed.

    The development file (``informe-descriptivo.json``, ``analisis-descriptivo.json``) is only
    looked for with ``descriptive``; otherwise only the reportable file counts. With ``questions``
    (the question bank by id) the C2 failures the OE4 rule attributes to synthesis are counted from
    the run records of every run that has an OE4 summary.

    Raises:
        FileNotFoundError: a stored report is missing (the message names the command to run).
    """
    from afg.experiments import c2_base_evidence
    from afg.experiments.runner import RECORDS_FILE, load_records

    a_report = None
    if a_run is not None:
        names = ["informe.json", *(["informe-descriptivo.json"] if descriptive else [])]
        a_report = _stored_report(
            a_dir / a_run, names, f"afg experiment a-report --c2-extraction {a_run}"
        )
    runs: list[BRun] = []
    a_manifests: dict[str, Mapping[str, Any]] = {}
    for name in b_runs:
        folder = b_dir / name
        names = ["analisis.json", *(["analisis-descriptivo.json"] if descriptive else [])]
        analysis = _stored_report(folder, names, f"afg experiment b-report --run-name {name}")
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        oe4_path = folder / "oe4-resumen.json"
        oe4 = json.loads(oe4_path.read_text(encoding="utf-8")) if oe4_path.is_file() else None
        records = load_records(folder / RECORDS_FILE, latest_only=True)
        rule_failures = (
            len(c2_base_evidence.rule_attributed_failures(records, questions))
            if oe4 is not None and questions is not None
            else None
        )
        runs.append(BRun(name, manifest, records, analysis, oe4, rule_failures))
        extraction = manifest.get("c2_extraction")
        if extraction and (a_dir / extraction / "manifest.json").is_file():
            a_manifests[str(extraction)] = json.loads(
                (a_dir / extraction / "manifest.json").read_text(encoding="utf-8")
            )
    return FinalInputs(a_report, runs, a_manifests)
