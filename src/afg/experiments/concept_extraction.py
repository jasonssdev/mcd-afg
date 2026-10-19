"""The OpenKOS concept-extraction screens, read from their aggregated score files.

OpenKOS ran three pre-registered, model-free-to-read evaluations of its concept extraction
(the step that turns a transcript into the compiled base that condition C2 answers from):

- **#1557, the model screen.** Which local chat model should extract concepts. Rounds 1 and
  2 are stored as ``model-screen/r1.json`` and ``r2.json`` (with ``validity.json`` for the
  baseline checks), and the harness's own verdicts as ``model-screen/decisions/*.json``.
- **#1572, the per-rule drop ablation.** Which deterministic drop (loss point L7 of #1559)
  costs window lift: ``drop-ablation/drop_ablation.json``, plus the per-object audit classes
  in ``drop_ablation_classes.json`` (copied without the model-written titles and
  descriptions).
- **#1571, the selector-judge study.** How much of the selector judge's loss (L10) is the
  selection itself and how much is the extractor judging its own output: ``judge-study/
  judge_study.json``, the three arms (no judge, self judge, fixed judge) and the harness's
  verdict.
- **#1560, the Ask model screen.** Which local model should answer, run the sufficiency
  check and cite, over synthetic bundles only (no AMI material): ``ask-screen/round1.json``,
  ``round2.json`` and ``confirmation.json``, the harness's comparison reports (no generated
  text).
- **#1558, the window-size screen.** Which ``_CHUNK_TARGET`` the extractor should cut a
  source into: ``window-screen/w8b.json`` and ``window-screen/decisions/w8b.json``.

The copies live in ``reports/experiment-a/extraccion-conceptos-openkos/``. Nothing here calls
a model or embeds a text: every figure is read from those files, and the registered rules are
re-applied to them so a notebook can show that the harness's verdict follows from its numbers.

## The metric, in one paragraph

A gold sentence is one of AMI's human abstractive-summary sentences (``abstract``,
``decisions``, ``problems``); its ``summlink`` acts place it in the extraction window that
holds its evidence. ``soft_cov(G, U)`` is the mean, over gold sentences, of the best bge-m3
cosine against the produced ``"title: description"`` units. The **coverage lift** subtracts
the same coverage against a *foreign* meeting's gold (same letter, another team), so topical
resemblance that any meeting about a remote control would earn cancels out.

## Partition

Every meeting in these files must belong to a development series (ADR 0005); a file that
names any other meeting is refused when it is loaded.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pandas as pd

__all__ = [
    "ASK_ROLES",
    "ASK_SETS",
    "BASELINE_MODEL",
    "BASELINE_WINDOW",
    "FIXED_JUDGE",
    "JUDGE_ARMS",
    "SCREEN_MODELS",
    "STAGES",
    "WINDOW_ARMS",
    "ConceptScreens",
    "WindowForecast",
    "ask_halving",
    "ask_penalty_frame",
    "ask_role_frame",
    "ask_select",
    "ask_vetoes",
    "drop_class_counts",
    "drop_rule_frame",
    "exploratory_forecast",
    "g1_frame",
    "judge_labels",
    "judge_study_frame",
    "judge_verdict",
    "l7_attribution",
    "load_concept_screens",
    "per_meeting_deltas",
    "round_frame",
    "round_one_vetoes",
    "round_two_selection",
    "stage_frame",
    "trace_frame",
    "window_arm_frame",
    "window_selection",
    "window_stage_frame",
]

BASELINE_MODEL: Final = "qwen3:8b"
"""The shipped extraction model, the baseline of #1557 and the primary model of #1558."""

SCREEN_MODELS: Final = (
    "qwen3:8b",
    "qwen3.6:35b-a3b",
    "gemma4:26b-a4b",
    "qwen3:14b",
    "qwen3.6:27b",
)
"""The #1557 models in the registered round-1 order (baseline first)."""

STAGES: Final = ("raw", "dedup", "drops", "pre_ceiling", "ceiling", "judge", "final")
"""The recorded pipeline stages, in order (#1559's per-stage loss table)."""

BASELINE_WINDOW: Final = 4000
WINDOW_ARMS: Final = (4000, 6000, 8000, 12000)
"""The ``_CHUNK_TARGET`` arms of #1558, in characters."""

# Registered bars (PREREGISTRATION.md of #1557 and #1558).
_V1_MARGIN: Final = 0.02
_V1_ABSOLUTE: Final = 0.05
_V3_MARGIN: Final = 0.02
_V4_LOW: Final = 0.5
_V4_HIGH: Final = 1.5
_V5_MARGIN: Final = 0.10
_F_MARGIN: Final = 0.10
_G1_FLOOR: Final = -0.05


@dataclass(frozen=True)
class ConceptScreens:
    """The three OpenKOS screens as stored by their harnesses (parsed JSON, unmodified)."""

    round1: dict[str, Any]
    round2: dict[str, Any]
    validity: dict[str, Any]
    model_stage0: dict[str, Any]
    model_decisions: dict[str, dict[str, Any]]
    ablation: dict[str, Any]
    ablation_classes: list[dict[str, Any]]
    window: dict[str, Any]
    window_stage0: dict[str, Any]
    window_decision: dict[str, Any]
    judge_study: dict[str, Any]
    ask_rounds: dict[str, dict[str, Any]]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _meetings_in(screens: ConceptScreens) -> set[str]:
    meetings: set[str] = set()
    for score in (screens.round1, screens.round2, screens.validity):
        for per_model in score.get("per_window", {}).values():
            meetings |= set(per_model)
    for arm in screens.window["arms"].values():
        meetings |= set(arm.get("per_meeting", {}))
    meetings |= {row["meeting"] for row in screens.ablation_classes}
    return meetings


def load_concept_screens(
    root: Path, *, partition_of: Callable[[str], str] | None = None
) -> ConceptScreens:
    """Read the copied score and decision files under ``root``.

    Raises:
        FileNotFoundError: a registered file is missing.
        ValueError: a meeting outside the development series appears in any file, or a
            per-object audit row still carries model-written text.
    """
    if partition_of is None:
        from afg.experiments.runner import configured_partition_of

        partition_of = configured_partition_of()
    model = root / "model-screen"
    screens = ConceptScreens(
        round1=_read(model / "r1.json"),
        round2=_read(model / "r2.json"),
        validity=_read(model / "validity.json"),
        model_stage0=_read(model / "stage0.json"),
        model_decisions={p.stem: _read(p) for p in sorted((model / "decisions").glob("*.json"))},
        ablation=_read(root / "drop-ablation" / "drop_ablation.json"),
        ablation_classes=_read(root / "drop-ablation" / "drop_ablation_classes.json"),
        window=_read(root / "window-screen" / "w8b.json"),
        window_stage0=_read(root / "window-screen" / "stage0.json"),
        window_decision=_read(root / "window-screen" / "decisions" / "w8b.json"),
        judge_study=_read(root / "judge-study" / "judge_study.json"),
        ask_rounds={
            name: _read(root / "ask-screen" / f"{name}.json")
            for name in ("round1", "round2", "confirmation")
        },
    )
    for row in screens.ablation_classes:
        if {"title", "description"} & set(row):
            raise ValueError("drop_ablation_classes.json must not carry titles or descriptions")
    for meeting in sorted(_meetings_in(screens)):
        series = meeting[:-1]
        if partition_of(series) != "development":
            raise ValueError(
                f"load_concept_screens: meeting {meeting} is not in a development series "
                "(ADR 0005)."
            )
    return screens


# ---------------------------------------------------------------- #1557, the model screen


def _rate(counter: Mapping[str, Any]) -> float:
    den = counter["den"]
    return counter["num"] / den if den else 0.0


def round_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """One row per model of a #1557 round: the primary, its paired delta and every veto.

    ``dlift_*`` is the paired window-level delta (candidate minus baseline) with its 95%
    two-stage bootstrap interval; it is missing for the baseline.
    """
    rows = []
    for model, m in score["models"].items():
        dlift = m.get("dlift") or {}
        dmeet = m.get("dlift_meeting") or {}
        rows.append(
            {
                "model": model,
                "window_lift": m["window_lift_mean"],
                "dlift": dlift.get("point", math.nan),
                "dlift_low": dlift.get("low", math.nan),
                "dlift_high": dlift.get("high", math.nan),
                "meeting_lift": m["meeting_lift_mean"],
                "dlift_meeting": dmeet.get("point", math.nan),
                "dlift_meeting_low": dmeet.get("low", math.nan),
                "dlift_meeting_high": dmeet.get("high", math.nan),
                "failures": m["failures"]["num"],
                "windows": m["failures"]["den"],
                "failure_rate": _rate(m["failures"]),
                "objects_total": m["objects_total"],
                "meeting_runs": m["meeting_runs"],
                "objects_per_meeting": m["objects_per_meeting"],
                "verbatim_rate": _rate(m["verbatim"]),
                "wrong_language": m["prose"]["wrong_language"]["num"],
                "spanish_titles": m["prose"]["wrong_language"]["den"],
                "wrong_language_rate": _rate(m["prose"]["wrong_language"]),
                "median_window_s": m["median_window_s"],
                "s_per_meeting_run": m["mean_s_per_meeting_run"],
                "judged_out": m["counters"]["judged_out"],
                "participant_added": m["counters"]["participant_added"],
            }
        )
    order = {m: i for i, m in enumerate(SCREEN_MODELS)}
    frame = pd.DataFrame(rows)
    return frame.sort_values("model", key=lambda s: s.map(order)).reset_index(drop=True)


def _volume_bounds(baseline_objects: float) -> tuple[float, float]:
    return _V4_LOW * baseline_objects, _V4_HIGH * baseline_objects


def round_one_vetoes(frame: pd.DataFrame, *, baseline: str = BASELINE_MODEL) -> pd.DataFrame:
    """Re-apply #1557's round-1 rule to :func:`round_frame` output.

    A candidate is dropped when it fails V1 (failure rate above the baseline's + 0.02 or
    above 0.05), V3 (wrong-language share above the baseline's + 0.02), V4 (objects per
    meeting-run outside [0.5, 1.5] x the baseline's), V5 (verbatim share above the
    baseline's + 0.10), or when the upper bound of its paired lift delta is below 0. The
    survivors are ranked by point delta and the top ceil(k/2) kept.
    """
    base = frame.set_index("model").loc[baseline]
    low, high = _volume_bounds(base.objects_per_meeting)
    rows = []
    for r in frame[frame.model != baseline].itertuples():
        v1 = (
            r.failure_rate <= base.failure_rate + _V1_MARGIN + 1e-12
            and r.failure_rate <= _V1_ABSOLUTE
        )
        v3 = r.wrong_language_rate <= base.wrong_language_rate + _V3_MARGIN + 1e-12
        v4 = low - 1e-12 <= r.objects_per_meeting <= high + 1e-12
        v5 = r.verbatim_rate <= base.verbatim_rate + _V5_MARGIN + 1e-12
        ci = not r.dlift_high < 0
        rows.append(
            {
                "model": r.model,
                "V1": v1,
                "V3": v3,
                "V4": v4,
                "V5": v5,
                "CI upper >= 0": ci,
                "passes": v1 and v3 and v4 and v5 and ci,
                "dlift": r.dlift,
                "volume_low": low,
                "volume_high": high,
            }
        )
    out = pd.DataFrame(rows)
    keep = math.ceil(len(out) / 2)
    ranked = out[out.passes].sort_values("dlift", ascending=False).model.head(keep)
    out["kept"] = out.model.isin(set(ranked))
    return out


def g1_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """#1557's G1 guardrail: source-grounded precision judged by ``gpt-oss:20b``."""
    rows = []
    for model, g in score["g1"].items():
        d = g.get("dprecision") or {}
        rows.append(
            {
                "model": model,
                "supported": g["precision"]["num"],
                "labelled": g["precision"]["den"],
                "precision": _rate(g["precision"]),
                "partial": g["partial"],
                "unsupported": g["unsupported"],
                "dprecision": d.get("point", math.nan),
                "dprecision_low": d.get("low", math.nan),
                "dprecision_high": d.get("high", math.nan),
                "judge_coverage": g["judge_coverage_mean"],
            }
        )
    return pd.DataFrame(rows)


def round_two_selection(
    frame: pd.DataFrame, g1: pd.DataFrame, *, baseline: str = BASELINE_MODEL
) -> pd.DataFrame:
    """Re-apply #1557's selection: every veto, G1 lower bound >= -0.05, lift lower bound > 0."""
    base = frame.set_index("model").loc[baseline]
    low, high = _volume_bounds(base.objects_per_meeting)
    g = g1.set_index("model")
    rows = []
    for r in frame[frame.model != baseline].itertuples():
        checks = {
            "lift lower > 0": r.dlift_low > 0,
            "V1": r.failure_rate <= base.failure_rate + _V1_MARGIN + 1e-12
            and r.failure_rate <= _V1_ABSOLUTE,
            "V3": r.wrong_language_rate <= base.wrong_language_rate + _V3_MARGIN + 1e-12,
            "V4": low - 1e-12 <= r.objects_per_meeting <= high + 1e-12,
            "V5": r.verbatim_rate <= base.verbatim_rate + _V5_MARGIN + 1e-12,
            "G1 lower >= -0.05": g.loc[r.model].dprecision_low >= _G1_FLOOR,
        }
        rows.append(
            {"model": r.model, **checks, "selected": all(checks.values()), "volume": (low, high)}
        )
    return pd.DataFrame(rows)


def stage_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """Window lift and object count after each recorded stage, per model (#1559).

    ``change`` is the stage's window-lift change against the previous stage: that stage's
    loss when negative.
    """
    rows = []
    for model, m in score["models"].items():
        previous = None
        for stage in STAGES:
            lift = m["stage_window_lift"][stage]
            rows.append(
                {
                    "model": model,
                    "stage": stage,
                    "objects": m["stage_table"][stage]["units"],
                    "window_lift": lift,
                    "change": math.nan if previous is None else lift - previous,
                    "meeting_lift": m["stage_table"][stage]["lift"],
                }
            )
            previous = lift
    return pd.DataFrame(rows)


def trace_frame(decision: Mapping[str, Any], key: str = "model") -> pd.DataFrame:
    """The harness's own verdict trace (``decisions/*.json``) as a table."""
    return pd.DataFrame(
        [
            {key: t[key], "passed": t["passed"], "reasons": "; ".join(t["reasons"])}
            for t in decision["trace"]
        ]
    )


# ---------------------------------------------------------- #1572, the drop ablation


def drop_rule_frame(ablation: Mapping[str, Any], block: str = "primary") -> pd.DataFrame:
    """Per model and deterministic rule: the lift delta with the rule off and what it dropped.

    A positive ``delta`` means the rule costs window lift (turning it off restores lift).
    ``block`` is ``primary`` (round 1, n = 1) or ``secondary`` (runs 1 and 2).
    """
    rows = []
    for model, m in ablation[block].items():
        for rule, r in m["rules"].items():
            rows.append(
                {
                    "model": model,
                    "rule": rule,
                    "delta": r["delta"]["point"],
                    "delta_low": r["delta"]["low"],
                    "delta_high": r["delta"]["high"],
                    "dropped": r["dropped"],
                    "windows_emptied": r["windows_emptied"],
                    "false_positives": r["false_positives"],
                    "false_positive_delta": r["false_positive_delta"],
                }
            )
    return pd.DataFrame(rows)


def l7_attribution(ablation: Mapping[str, Any], block: str = "primary") -> pd.DataFrame:
    """The L7 loss per model and the share of it the framing drop restores.

    ``l7_change`` is the window-lift change across the deterministic-drops stage (negative is
    a loss). ``framing_share`` is the framing delta over the loss, defined only when the
    stage lost lift.
    """
    rows = []
    for model, m in ablation[block].items():
        loss = m["l7_loss"]
        framing = m["rules"]["framing"]["delta"]["point"]
        rows.append(
            {
                "model": model,
                "l7_change": -loss,
                "framing_delta": framing,
                "framing_share": framing / loss if loss > 0 else math.nan,
                "dedup_change": -m["l6_loss"],
                "ceiling_cut": m["caps"]["ceiling"]["objects_cut"],
                "backstop_cut": m["caps"]["backstop"]["objects_cut"],
                "invalid_records": len(m["invalid"]),
            }
        )
    return pd.DataFrame(rows)


def drop_class_counts(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Audit counts of every dropped object by rule, class (target or false positive) and type."""
    counts = Counter((r["rule"], r["class"], r["type"]) for r in rows)
    frame = pd.DataFrame(
        [{"rule": k[0], "class": k[1], "type": k[2], "objects": n} for k, n in counts.items()]
    )
    return frame.sort_values(["rule", "class", "objects"], ascending=[True, False, False])


# ---------------------------------------------------------- #1571, the selector judge

JUDGE_ARMS: Final = ("none", "self", "fixed")
"""#1571's arms: no judge, the extractor judging itself, and the fixed ``gemma4:26b-a4b``."""

FIXED_JUDGE: Final = "gemma4:26b-a4b"
"""The fixed judge of #1571; as an extractor it has the same model in both judge arms."""


def judge_study_frame(study: Mapping[str, Any], block: str = "primary") -> pd.DataFrame:
    """One row per extractor of #1571: lift and kept objects per arm, losses and coupling.

    A loss is the arm's window lift minus the no-judge lift (negative costs lift). The
    coupling is fixed minus self: positive means the fixed judge keeps more lift. Judge-arm
    values are means over the three seed indices.
    """
    rows = []
    for model, m in study[block].items():
        arms = m["arms"]
        row: dict[str, Any] = {"model": model, "meeting_runs": m["meeting_runs"]}
        for arm in JUDGE_ARMS:
            row[f"{arm}_lift"] = arms[arm]["lift"]
            row[f"{arm}_kept"] = arms[arm]["kept"]
        for arm in ("self", "fixed"):
            loss = arms[arm]["loss"]
            row[f"{arm}_loss"] = loss["point"]
            row[f"{arm}_loss_low"] = loss["low"]
            row[f"{arm}_loss_high"] = loss["high"]
            row[f"{arm}_judged_out"] = arms[arm]["judged_out"]
            row[f"{arm}_seed_lifts"] = tuple(
                arms[arm]["seed_lifts"][str(s)] for s in arms[arm]["seeds"]
            )
            row[f"{arm}_failed"] = arms[arm]["judge_failed"]
        coupling = m["deltas"]["coupling"]
        row["coupling"] = coupling["point"]
        row["coupling_low"] = coupling["low"]
        row["coupling_high"] = coupling["high"]
        rows.append(row)
    order = {m: i for i, m in enumerate(SCREEN_MODELS)}
    frame = pd.DataFrame(rows)
    return frame.sort_values("model", key=lambda s: s.map(order)).reset_index(drop=True)


def judge_labels(frame: pd.DataFrame, *, fixed_judge: str = FIXED_JUDGE) -> dict[str, str]:
    """#1571's per-extractor rule, for every extractor other than the fixed judge's model.

    ``coupling`` when the coupling interval's lower bound is above 0; else ``judge`` when
    the fixed-judge loss interval's upper bound is below 0; else ``unresolved``.
    """
    labels = {}
    for r in frame[frame.model != fixed_judge].itertuples():
        if r.coupling_low > 0:
            labels[r.model] = "coupling"
        elif r.fixed_loss_high < 0:
            labels[r.model] = "judge"
        else:
            labels[r.model] = "unresolved"
    return labels


def judge_verdict(labels: Mapping[str, str]) -> tuple[str, bool]:
    """#1571's overall verdict and whether a follow-up fix issue is due.

    ``coupling`` when 2 or more extractors are coupling-attributable; ``judge`` when 2 or
    more are judge-attributable and none is coupling-attributable; ``not_resolved``
    otherwise. A follow-up is due when any extractor is attributable either way.
    """
    counts = Counter(labels.values())
    if counts["coupling"] >= 2:
        verdict = "coupling"
    elif counts["judge"] >= 2 and counts["coupling"] == 0:
        verdict = "judge"
    else:
        verdict = "not_resolved"
    return verdict, counts["coupling"] + counts["judge"] > 0


# ------------------------------------------------------------ #1560, the Ask model screen

ASK_ROLES: Final = ("sufficiency", "answer", "citation")
"""The three Ask roles of #1560; answer and citation share one call."""

ASK_SETS: Final = ("es-es", "es-en", "es-built")
"""Spanish questions over a Spanish bundle, its English mirror, and a compiled English one."""

_ASK_FAILURE_KEY: Final = {
    "sufficiency": "suff_failure",
    "answer": "ans_failure",
    "citation": "ans_failure",
}
_ASK_LATENCY_KEY: Final = {
    "sufficiency": "suff_median_s",
    "answer": "ans_median_s",
    "citation": "ans_median_s",
}
_ASK_LATENCY_RATIO: Final = 2.0
_ASK_LANGUAGE_MARGIN: Final = 0.05
_ASK_COMPLIANCE_MARGIN: Final = 0.05
_ASK_MISS_MARGIN: Final = 0.02


def ask_vetoes(report: Mapping[str, Any], role: str, model: str) -> list[str]:
    """Re-apply #1560's vetoes for one candidate and role from a comparison report.

    V1 failures (<= baseline + 0.02 and <= 0.05), V2 median latency of the role's call
    (<= 2.0 x baseline, when measured), S1 grounded refusals (<= baseline) and S2 adjacent
    misses (<= baseline + 0.02) for sufficiency, V3 Spanish answers (>= baseline - 0.05) for
    answer, V4 ``USED:`` compliance (>= baseline - 0.05) for citation, and X1 (the ``es-en``
    per-set upper bound not below 0) for every role. M (memory) is a stage-0 gate and is not
    in the reports.
    """
    g = report["guardrails"][model]
    base = report["guardrails"][report["baseline"]]
    vetoes = []
    fail = _ASK_FAILURE_KEY[role]
    if g[fail] > base[fail] + _V1_MARGIN + 1e-12 or g[fail] > _V1_ABSOLUTE:
        vetoes.append("V1")
    lat = _ASK_LATENCY_KEY[role]
    if g[lat] is not None and base[lat] and g[lat] > _ASK_LATENCY_RATIO * base[lat]:
        vetoes.append("V2")
    if role == "sufficiency":
        if g["grounded_refused"] > base["grounded_refused"] + 1e-12:
            vetoes.append("S1")
        if g["adjacent_missed"] > base["adjacent_missed"] + _ASK_MISS_MARGIN + 1e-12:
            vetoes.append("S2")
    if role == "answer" and g["spanish_answers"] < base["spanish_answers"] - _ASK_LANGUAGE_MARGIN:
        vetoes.append("V3")
    if role == "citation" and g["compliance"] < base["compliance"] - _ASK_COMPLIANCE_MARGIN:
        vetoes.append("V4")
    es_en = report["roles"][role]["candidates"][model]["per_set"].get("es-en")
    if es_en is not None and es_en["hi"] < 0:
        vetoes.append("X1")
    return vetoes


def ask_role_frame(report: Mapping[str, Any], role: str) -> pd.DataFrame:
    """One row per candidate of a role: the pooled paired delta, per-set deltas and vetoes.

    ``vetoes`` are re-applied here (:func:`ask_vetoes`); ``harness_vetoes`` are the ids the
    harness wrote, for comparison.
    """
    block = report["roles"][role]
    rows = []
    for model, c in block["candidates"].items():
        d = c["delta"]
        row: dict[str, Any] = {
            "model": model,
            "baseline_mean": block["baseline_mean"],
            "n": d["n"],
            "delta": d["mean"],
            "delta_low": d["lo"],
            "delta_high": d["hi"],
        }
        for name in ASK_SETS:
            row[name] = c["per_set"][name]["mean"]
        row["vetoes"] = tuple(ask_vetoes(report, role, model))
        row["harness_vetoes"] = tuple(v.split()[0] for v in c["vetoes"])
        rows.append(row)
    return pd.DataFrame(rows)


def ask_halving(frame: pd.DataFrame) -> set[str]:
    """#1560's round-1 cut: drop vetoed candidates and those whose upper bound is below 0,
    then keep the top ceil(k/2) by point delta (k = candidates that entered), never fewer than
    2 when 2 are eligible."""
    eligible = frame[(frame.vetoes.map(len) == 0) & ~(frame.delta_high < 0)]
    keep = max(math.ceil(len(frame) / 2), min(2, len(eligible)))
    ranked = eligible.sort_values(["delta", "model"], ascending=[False, True])
    return set(ranked.model.head(keep))


def ask_select(frame: pd.DataFrame) -> str | None:
    """#1560's selection: the largest point delta whose lower bound is above 0 with no veto;
    a tie goes to the first model name. ``None`` when nothing qualifies."""
    eligible = frame[(frame.vetoes.map(len) == 0) & (frame.delta_low > 0)]
    if eligible.empty:
        return None
    return str(eligible.sort_values(["delta", "model"], ascending=[False, True]).model.iloc[0])


def ask_penalty_frame(report: Mapping[str, Any]) -> pd.DataFrame:
    """Each model's cross-lingual penalty (``es-en`` minus ``es-es``, paired) per role."""
    rows = []
    for model, roles in report["penalty"].items():
        for role, p in roles.items():
            rows.append(
                {
                    "model": model,
                    "role": role,
                    "n": p["n"],
                    "penalty": p["mean"],
                    "low": p["lo"],
                    "high": p["hi"],
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------- #1558, the window-size screen


def _arm_key(arm: int) -> str:
    return f"c{arm}"


def window_arm_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """One row per window-size arm of #1558 (primary model): primary, vetoes and reports."""
    runs = len(score["runs"])
    rows = []
    for arm in WINDOW_ARMS:
        a = score["arms"][_arm_key(arm)]
        d = a.get("dlift_meeting") or {}
        dc = a.get("dcoverage_meeting") or {}
        dp = a.get("dprecision") or {}
        rows.append(
            {
                "arm": arm,
                "da_windows": a["failures"]["den"] // runs,
                "dlift": d.get("point", math.nan),
                "dlift_low": d.get("low", math.nan),
                "dlift_high": d.get("high", math.nan),
                "meeting_lift": a["meeting_lift_mean"],
                "failed_chars_rate": _rate(a["failed_chars"]),
                "failed_windows": a["failures"]["num"],
                "window_runs": a["failures"]["den"],
                "objects_total": a["objects_total"],
                "objects_per_meeting": a["objects_per_meeting"],
                "verbatim_rate": _rate(a["verbatim"]),
                "wrong_language_rate": _rate(a["prose"]["wrong_language"]),
                "redundant_rate": _rate(a["redundant_final"]),
                "judge_coverage": a["judged"]["coverage_mean"],
                "dcoverage": dc.get("point", math.nan),
                "dcoverage_low": dc.get("low", math.nan),
                "dcoverage_high": dc.get("high", math.nan),
                "g1_precision": _rate(a["judged"]["precision"]),
                "dprecision": dp.get("point", math.nan),
                "dprecision_low": dp.get("low", math.nan),
                "dprecision_high": dp.get("high", math.nan),
                "medium10_recall": _rate(a["prose"]["subject_recall_exact"]),
                "medium10_windows": a["medium10_699"][0]["windows"],
                "median_window_s": a["median_window_s"],
                "s_per_meeting_run": a["mean_s_per_meeting_run"],
            }
        )
    return pd.DataFrame(rows)


def per_meeting_deltas(score: Mapping[str, Any]) -> pd.DataFrame:
    """Per meeting, each arm's run-mean meeting lift minus the 4,000 arm's."""
    base = score["arms"][_arm_key(BASELINE_WINDOW)]["per_meeting"]
    rows = []
    for arm in WINDOW_ARMS[1:]:
        per = score["arms"][_arm_key(arm)]["per_meeting"]
        for meeting in base:
            mean_arm = sum(per[meeting]) / len(per[meeting])
            mean_base = sum(base[meeting]) / len(base[meeting])
            rows.append({"arm": arm, "meeting": meeting, "delta": mean_arm - mean_base})
    return pd.DataFrame(rows).pivot(index="arm", columns="meeting", values="delta")


def window_selection(frame: pd.DataFrame) -> pd.DataFrame:
    """Re-apply #1558's selection rule to :func:`window_arm_frame` output.

    Each arm against the 4,000 arm: V1 (character-weighted failures <= base + 0.02 and
    <= 0.05), V3, V4 ([0.5, 1.5] x base volume), V5, F (redundant rate <= base + 0.10), and
    the 95% lower bound of the paired meeting-lift delta > 0.
    """
    base = frame.set_index("arm").loc[BASELINE_WINDOW]
    low, high = _volume_bounds(base.objects_per_meeting)
    rows = []
    for r in frame[frame.arm != BASELINE_WINDOW].itertuples():
        checks = {
            "lift lower > 0": r.dlift_low > 0,
            "V1": r.failed_chars_rate <= base.failed_chars_rate + _V1_MARGIN + 1e-12
            and r.failed_chars_rate <= _V1_ABSOLUTE,
            "V3": r.wrong_language_rate <= base.wrong_language_rate + _V3_MARGIN + 1e-12,
            "V4": low - 1e-12 <= r.objects_per_meeting <= high + 1e-12,
            "V5": r.verbatim_rate <= base.verbatim_rate + _V5_MARGIN + 1e-12,
            "F": r.redundant_rate <= base.redundant_rate + _F_MARGIN + 1e-12,
        }
        rows.append(
            {"arm": r.arm, **checks, "selected": all(checks.values()), "volume": (low, high)}
        )
    return pd.DataFrame(rows)


def window_stage_frame(score: Mapping[str, Any]) -> pd.DataFrame:
    """Meeting lift and object count after each stage, per window arm."""
    rows = []
    for arm in WINDOW_ARMS:
        table = score["arms"][_arm_key(arm)]["stage_table"]
        for stage in STAGES:
            rows.append(
                {
                    "arm": arm,
                    "stage": stage,
                    "objects": table[stage]["units"],
                    "meeting_lift": table[stage]["lift"],
                }
            )
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class WindowForecast:
    """#1558's registered forecast for the exploratory model's uncached work."""

    per_arm_s: dict[int, float]
    medium10_s: float
    stage0_s: float
    total_s: float
    budget_s: float

    @property
    def runs(self) -> bool:
        """The registered rule: the exploratory model runs only within its budget."""
        return self.total_s <= self.budget_s


def exploratory_forecast(
    stage0: Mapping[str, Any],
    *,
    model: str,
    da_seconds: float,
    medium10_seconds: float,
    median_4000_s: float,
    da_windows: Mapping[int, int],
    medium10_windows: Mapping[int, int],
    runs: int = 2,
    budget_h: float = 4.0,
    arms: Sequence[int] = (6000, 8000),
) -> WindowForecast:
    """Forecast, with the registered formula, the exploratory model's uncached model time.

    One DA run plus one ``medium-10`` run at arm N costs
    ``D x (W_N x t_N) / (41 x t_4000) + P x (M_N x t_N) / (4 x t_4000)``, with ``t_N`` the
    arm's stage-0 median window seconds, ``W_N`` and ``M_N`` the DA and ``medium-10``
    window counts. The total adds one ``medium-10`` run at 4,000 (seed 2, uncached) and the
    stage 0 already spent (load plus every timed window).
    """
    entries = stage0["models"][model]
    base_w = da_windows[BASELINE_WINDOW]
    base_m = medium10_windows[BASELINE_WINDOW]
    per_arm = {}
    for arm in arms:
        t = entries[_arm_key(arm)]["median_window_s"]
        one = da_seconds * da_windows[arm] * t / (base_w * median_4000_s) + (
            medium10_seconds * medium10_windows[arm] * t / (base_m * median_4000_s)
        )
        per_arm[arm] = runs * one
    loads = {entries[_arm_key(a)]["load_s"] for a in arms}
    stage0_s = sum(loads) + sum(sum(entries[_arm_key(a)]["window_s"]) for a in arms)
    total = sum(per_arm.values()) + medium10_seconds + stage0_s
    return WindowForecast(
        per_arm_s=per_arm,
        medium10_s=medium10_seconds,
        stage0_s=stage0_s,
        total_s=total,
        budget_s=budget_h * 3600,
    )
