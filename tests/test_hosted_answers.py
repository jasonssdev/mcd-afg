"""Tests for the answer comparison of the hosted extractors (ADR 0026, amendment 3).

Synthetic records only (ADR 0005): the stratum labels and the verdict flags are the sole content.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from afg.evaluation.scoring import IntervalSettings
from afg.experiments.hosted_answers import (
    ABOVE,
    BELOW,
    INDISTINGUISHABLE,
    AnswerComparisonSpec,
    answer_comparison_rows,
    answer_run_name,
    build_answer_comparison,
    verdict_for,
    write_answer_comparison,
)

FORMAL = "experimento-b-formal"
BASE = "experimento-b-base-0-7-3"
SPEC = AnswerComparisonSpec(
    models=("m-a", "m-b"),
    family_alpha=0.05,
    interval=IntervalSettings(n_resamples=400, confidence_level=0.95, seed=1),
    min_questions=3,
    formal_run=FORMAL,
    base_run=BASE,
)
QUESTIONS = [f"q{i}" for i in range(1, 9)]


def _record(
    qid: str,
    condition: str,
    run: int,
    correct: bool,
    *,
    stratum: str = "E3_evolution",
    abstained: bool = False,
    seconds: float = 2.0,
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "condition": condition,
        "run": run,
        "stratum": stratum,
        "partition": "evaluation",
        "schema_version": 2,
        "error": None,
        "judge_failure": None,
        "verdict": {"correct": correct, "evidence_supported": correct, "outdated": False},
        "answer": {"abstained": abstained},
        "citation_correct": correct,
        "answer_seconds": seconds,
    }


def _records(
    condition: str, correct_of: Any, *, runs: int = 3, prefix: str = "", **kw: Any
) -> list[dict[str, Any]]:
    return [
        _record(prefix + q, condition, r, correct_of(i), **kw)
        for i, q in enumerate(QUESTIONS)
        for r in range(runs)
    ]


def _formal() -> list[dict[str, Any]]:
    # C1 right on every question; C2 right on the first half only
    return _records("C1", lambda i: True) + _records("C2", lambda i: i < 4)


def test_run_names_follow_the_extraction_labels() -> None:
    assert answer_run_name("openai-small") == "experimento-b-hosted-openai-small"


@pytest.mark.parametrize(
    ("lower", "upper", "label"),
    [
        (0.01, 0.4, ABOVE),
        (-0.2, 0.2, INDISTINGUISHABLE),
        (0.0, 0.3, INDISTINGUISHABLE),  # touching zero is not clear of zero
        (-0.5, -0.01, BELOW),
    ],
)
def test_verdict_follows_the_interval_against_zero(lower: float, upper: float, label: str) -> None:
    assert verdict_for(lower, upper, "C1") == f"{label} C1"


def test_verdict_labels_are_the_ones_of_the_amendment() -> None:
    assert (ABOVE, INDISTINGUISHABLE, BELOW) == ("supera a", "no se distingue de", "queda bajo")
    assert verdict_for(0.1, 0.2, "C1") == "supera a C1"
    assert verdict_for(-0.1, 0.2, "C1") == "no se distingue de C1"
    assert verdict_for(-0.2, -0.1, "C1") == "queda bajo C1"


def _build(records: dict[str, Sequence[dict[str, Any]] | None]) -> dict[str, Any]:
    return build_answer_comparison(records, SPEC)


def test_a_model_above_c1_is_reported_with_the_bonferroni_level() -> None:
    # model run answers worse than C1 on the first half only: strictly below C1
    payload = _build(
        {FORMAL: _formal(), answer_run_name("m-a"): _records("C2", lambda i: i < 2), BASE: None}
    )
    assert payload["family"] == {"alpha": 0.05, "n_models": 2, "level": pytest.approx(1 - 0.05 / 2)}
    model = payload["models"]["m-a"]
    assert model["status"] == "ok"
    primary = model["primary"]
    assert (primary["stratum"], primary["metric"], primary["reference"]) == (
        "E3",
        "correct",
        "C1 formal",
    )
    assert primary["difference"] == pytest.approx(0.25 - 1.0)
    assert primary["n_pairs"] == 8
    assert primary["verdict"] == "queda bajo C1 formal"
    assert primary["upper"] < 0


def test_the_difference_is_the_paired_bootstrap_of_the_existing_analysis() -> None:
    from afg.experiments.analysis import analyze_runs

    subject = _records("C2", lambda i: i % 2 == 0)
    payload = _build({FORMAL: _formal(), answer_run_name("m-a"): subject})
    level = 1 - 0.05 / 2
    settings = IntervalSettings(n_resamples=400, confidence_level=level, seed=1)
    merged = _records("C1", lambda i: True) + [dict(r, condition="C2") for r in subject]
    expected = next(
        c for c in analyze_runs(merged, settings=settings, min_questions=3).comparisons if c.primary
    )
    primary = payload["models"]["m-a"]["primary"]
    assert (primary["difference"], primary["lower"], primary["upper"]) == (
        expected.difference,
        expected.difference_lower,
        expected.difference_upper,
    )


def test_pending_runs_are_reported_as_pendiente_without_failing() -> None:
    payload = _build({FORMAL: _formal()})
    for label in SPEC.models:
        assert payload["models"][label] == {
            "run": answer_run_name(label),
            "status": "pendiente",
            "reason": "sin corrida",
        }
    assert payload["baseline_0_7_3"]["status"] == "pendiente"


def test_missing_formal_run_marks_everything_pending() -> None:
    payload = _build({answer_run_name("m-a"): _records("C2", lambda i: True)})
    assert payload["models"]["m-a"]["status"] == "pendiente"
    assert "formal" in payload["models"]["m-a"]["reason"]


def test_a_run_without_c2_records_is_pending() -> None:
    payload = _build({FORMAL: _formal(), answer_run_name("m-a"): _records("C1", lambda i: True)})
    assert payload["models"]["m-a"]["status"] == "pendiente"
    assert "C2" in payload["models"]["m-a"]["reason"]


def test_secondary_comparisons_use_c2_formal_and_the_0_7_3_baseline() -> None:
    base = _records("C2", lambda i: i < 2)
    payload = _build(
        {FORMAL: _formal(), BASE: base, answer_run_name("m-a"): _records("C2", lambda i: i < 6)}
    )
    model = payload["models"]["m-a"]
    vs_formal, vs_base = model["secondary"]["vs_c2_formal"], model["secondary"]["vs_c2_base_0_7_3"]
    assert vs_formal["difference"] == pytest.approx(0.75 - 0.5)
    assert vs_base["difference"] == pytest.approx(0.75 - 0.25)
    assert vs_formal["reference"] == "C2 formal"
    assert vs_base["reference"] == "C2 de la línea base 0.7.3"
    assert payload["baseline_0_7_3"]["status"] == "ok"
    assert payload["baseline_0_7_3"]["primary"]["difference"] == pytest.approx(0.25 - 1.0)


def test_secondary_is_pending_when_its_reference_is_missing() -> None:
    payload = _build({FORMAL: _formal(), answer_run_name("m-a"): _records("C2", lambda i: True)})
    secondary = payload["models"]["m-a"]["secondary"]
    assert secondary["vs_c2_base_0_7_3"] == {"status": "pendiente", "reason": "sin corrida"}
    assert secondary["vs_c2_formal"]["status"] == "ok"


def test_strata_report_the_secondary_metrics_beside_the_reference() -> None:
    e1 = {"stratum": "E1_point_fact", "prefix": "e1-"}
    subject = _records("C2", lambda i: True, abstained=True, seconds=4.0, **e1)
    subject += _records("C2", lambda i: i < 4)
    formal = _formal() + _records("C1", lambda i: True, seconds=1.0, **e1)
    payload = _build({FORMAL: formal, answer_run_name("m-a"): subject})
    rows = {r["stratum"]: r for r in payload["models"]["m-a"]["strata"]}
    assert set(rows) == {"E1", "E3", "ALL"}
    e1 = rows["E1"]
    assert e1["subject"]["abstention_rate"] == 1.0 and e1["reference"]["abstention_rate"] == 0.0
    assert e1["subject"]["answer_seconds"] == pytest.approx(4.0)
    assert e1["reference"]["answer_seconds"] == pytest.approx(1.0)
    e3 = rows["E3"]
    assert e3["subject"]["correct"]["point"] == pytest.approx(0.5)
    for metric in ("correct", "evidence_supported", "citation_correct", "outdated_among_answered"):
        assert metric in e3["subject"]
    assert "outdated_among_answered" not in e1["subject"]  # H4 lives in E3 only


def test_a_short_stratum_is_flagged_not_silenced() -> None:
    short = [r for r in _formal() if r["question_id"] in {"q1", "q2"}]
    payload = _build(
        {FORMAL: short, answer_run_name("m-a"): [r for r in short if r["condition"] == "C2"]}
    )
    primary = payload["models"]["m-a"]["primary"]
    assert primary["sample_sufficient"] is False
    assert any("mínimo" in w for w in payload["models"]["m-a"]["warnings"])


def test_a_run_that_covers_fewer_questions_than_c1_warns() -> None:
    subject = [r for r in _records("C2", lambda i: True) if r["question_id"] != "q8"]
    payload = _build({FORMAL: _formal(), answer_run_name("m-a"): subject})
    warnings = payload["models"]["m-a"]["warnings"]
    assert any("7" in w and "8" in w for w in warnings)
    assert payload["models"]["m-a"]["primary"]["n_pairs"] == 7


def test_development_records_are_refused() -> None:
    from afg.evaluation.scoring import DevelopmentResultError

    dev = [dict(r, partition="development") for r in _formal()]
    with pytest.raises(DevelopmentResultError):
        _build(
            {
                FORMAL: dev,
                answer_run_name("m-a"): [
                    dict(r, partition="development") for r in _records("C2", lambda i: True)
                ],
            }
        )


def test_payload_never_carries_answer_or_decision_text() -> None:
    records = _formal()
    for record in records:
        record["answer"]["text"] = "SENSITIVE-ANSWER"
        record["verdict"]["rationale"] = "SENSITIVE-RATIONALE"
    payload = _build({FORMAL: records, answer_run_name("m-a"): _records("C2", lambda i: True)})
    assert "SENSITIVE" not in json.dumps(payload, ensure_ascii=False)


def test_rows_and_writer_emit_json_and_csv(tmp_path: Path) -> None:
    payload = _build(
        {FORMAL: _formal(), BASE: None, answer_run_name("m-a"): _records("C2", lambda i: i < 6)}
    )
    rows = answer_comparison_rows(payload)
    primaries = [r for r in rows if r["comparison"] == "primary" and r["status"] == "ok"]
    assert [r["model"] for r in primaries] == ["m-a"]
    assert any(r["status"] == "pendiente" and r["model"] == "m-b" for r in rows)
    json_path, csv_path = write_answer_comparison(payload, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["family"]["n_models"] == 2
    with csv_path.open(encoding="utf-8", newline="") as handle:
        loaded = list(csv.DictReader(handle))
    assert {r["model"] for r in loaded} >= {"m-a", "m-b"}


def test_only_limits_the_entries_but_keeps_the_family_size() -> None:
    payload = build_answer_comparison({FORMAL: _formal()}, SPEC, only=("m-b",))
    assert list(payload["models"]) == ["m-b"]
    assert payload["family"]["n_models"] == 2


def test_only_refuses_an_unknown_label() -> None:
    with pytest.raises(ValueError, match="zzz"):
        build_answer_comparison({}, SPEC, only=("zzz",))
