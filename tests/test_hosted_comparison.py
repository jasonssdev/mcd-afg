"""Tests for the paired comparison of hosted extractors against the baseline (ADR 0026).

Everything runs on fake run folders and a fake text similarity: no Ollama, no model.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.evaluation.reference import ReferenceDecision
from afg.experiments.hosted_comparison import (
    bridge_check,
    compare_to_baseline,
    load_run_data,
    meeting_counts,
    paired_bootstrap,
    verdict_for,
)
from afg.experiments.hosted_extraction import ComparisonSpec
from tests.relations_workspace import reference_decision, text_similarity

SPEC = ComparisonSpec(
    tau=0.70,
    sensitivity_taus=(0.75, 0.80),
    bootstrap_resamples=2000,
    bootstrap_seed=42,
    family_alpha=0.05,
    precision_margin=-0.05,
)
SERIES = ("ES2015", "IS1004")
LETTERS = "abcd"


def _text(meeting: str) -> tuple[str, str]:
    return (f"object {meeting}", f"content {meeting}")


def _reference(series: str) -> list[ReferenceDecision]:
    return [
        reference_decision(f"{series}{x}.d01", f"{series}{x}", *_text(f"{series}{x}"))
        for x in LETTERS
    ]


def _reference_of(series: str) -> Sequence[ReferenceDecision]:
    return _reference(series)


def _decision(
    series: str, meeting: str, text: tuple[str, str], index: int = 0
) -> dict[str, object]:
    return {
        "id": f"decisions/{meeting}-{index}",
        "series_id": series,
        "meeting_id": meeting,
        "decision_object": text[0],
        "content": text[1],
        "status": "accepted",
        "evidence": {"meeting_id": meeting, "dialogue_act_ids": ["x1"]},
        "annotator": None,
        "origin_meeting_ids": [],
    }


def _write_run(
    root: Path,
    name: str,
    found: dict[tuple[str, int], list[str]],
    *,
    spurious: int = 0,
    ingest_seconds: dict[str, float] | None = None,
    failed: dict[tuple[str, int], str] | None = None,
) -> Path:
    """A run folder: ``found`` maps ``(series, run)`` to the meetings whose gold it extracts."""
    run_dir = root / "out" / name
    run_dir.mkdir(parents=True)
    pairs: dict[str, dict[str, object]] = {}
    lines = []
    workspace_root = root / "ws" / name
    for (series, run), meetings in sorted(found.items()):
        decisions = [_decision(series, m, _text(m)) for m in meetings]
        decisions += [
            _decision(series, f"{series}a", (f"noise {i}", f"noise {i}"), index=i + 1)
            for i in range(spurious)
        ]
        lines.append(json.dumps({"series_id": series, "run": run, "decisions": decisions}))
        failed_meeting = (failed or {}).get((series, run))
        pairs[f"{series}/{run}"] = {
            "series": series,
            "run": run,
            "status": "failed" if failed_meeting else "ok",
        }
        commands: list[dict[str, object]] = [{"argv": ["openkos", "--version"], "duration_s": 0.1}]
        for letter in LETTERS:
            meeting = f"{series}{letter}"
            seconds = (ingest_seconds or {}).get(meeting, 10.0)
            code = 1 if meeting == failed_meeting else 0
            commands.append(
                {
                    "argv": [
                        "openkos",
                        "ingest",
                        f"/x/{name}/{series}/run-{run}.sources/{meeting}.md",
                        "--auto",
                    ],
                    "returncode": code,
                    "duration_s": seconds,
                }
            )
            if code:
                break
        manifest_path = workspace_root / series / f"run-{run}.manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "failed" if failed_meeting else "ok",
                    "failed_meeting": failed_meeting,
                    "meetings": [f"{series}{x}" for x in LETTERS],
                    "commands": commands,
                }
            )
        )
    (run_dir / "manifest.json").write_text(
        json.dumps({"kind": "batch", "pairs": pairs, "openkos": {"seed": None}})
    )
    (run_dir / "extracciones.jsonl").write_text("\n".join(lines) + "\n")
    return run_dir


def _all(meetings_of: dict[str, list[str]], runs: int = 2) -> dict[tuple[str, int], list[str]]:
    return {(s, r): list(ms) for s, ms in meetings_of.items() for r in range(runs)}


def _meetings(series: str, letters: str) -> list[str]:
    return [f"{series}{x}" for x in letters]


def _load(tmp_path: Path, name: str):  # type: ignore[no-untyped-def]
    return load_run_data(tmp_path / "out" / name, tmp_path / "ws" / name)


def _compare(tmp_path: Path, **kw):  # type: ignore[no-untyped-def]
    return compare_to_baseline(
        _load(tmp_path, "base"),
        _load(tmp_path, "cand"),
        reference_of=_reference_of,
        similarity=text_similarity,
        spec=SPEC,
        n_models=6,
        **kw,
    )


def test_meeting_counts_average_the_runs_of_a_series(tmp_path: Path) -> None:
    _write_run(
        tmp_path,
        "base",
        {("ES2015", 0): ["ES2015a"], ("ES2015", 1): []},
    )
    counts = meeting_counts(
        _load(tmp_path, "base").runs,
        reference_of=_reference_of,
        similarity=text_similarity,
        tau=0.70,
    )
    assert counts["ES2015a"].hits_r == pytest.approx(0.5)
    assert counts["ES2015a"].n_r == pytest.approx(1.0)
    assert counts["ES2015a"].hits_p == pytest.approx(0.5)
    assert counts["ES2015a"].n_p == pytest.approx(0.5)
    assert counts["ES2015b"].n_r == pytest.approx(1.0)
    assert counts["ES2015b"].hits_r == 0


def test_identical_systems_show_no_difference(tmp_path: Path) -> None:
    found = _all({s: _meetings(s, "ab") for s in SERIES})
    _write_run(tmp_path, "base", found)
    _write_run(tmp_path, "cand", found)

    result = _compare(tmp_path)

    primary = result["taus"]["0.70"]
    assert primary["diff"]["recall"]["estimate"] == 0
    assert primary["diff"]["recall"]["interval"] == [0, 0]
    assert result["verdict"] == "sin diferencia demostrada"


def test_a_clearly_better_candidate_is_an_improvement(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({s: _meetings(s, "a") for s in SERIES}))
    _write_run(tmp_path, "cand", _all({s: _meetings(s, "abcd") for s in SERIES}))

    result = _compare(tmp_path)

    recall = result["taus"]["0.70"]["diff"]["recall"]
    assert recall["interval"][0] > 0
    assert result["verdict"] == "mejora"
    assert result["series_covered"] == ["ES2015", "IS1004"]
    assert result["n_meetings"] == 8
    assert result["interval_level"] == pytest.approx(1 - 0.05 / 6)
    assert result["n_models"] == 6


def test_a_worse_candidate_is_reported_as_worse(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({s: _meetings(s, "abcd") for s in SERIES}))
    _write_run(tmp_path, "cand", _all({s: _meetings(s, "a") for s in SERIES}))

    assert _compare(tmp_path)["verdict"] == "empeora"


def test_more_recall_with_much_less_precision_is_not_an_improvement(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({s: _meetings(s, "a") for s in SERIES}))
    _write_run(tmp_path, "cand", _all({s: _meetings(s, "abcd") for s in SERIES}), spurious=12)

    result = _compare(tmp_path)

    assert result["taus"]["0.70"]["diff"]["recall"]["interval"][0] > 0
    assert result["taus"]["0.70"]["diff"]["precision"]["interval"][0] < SPEC.precision_margin
    assert result["verdict"] == "sin diferencia demostrada"


def test_only_the_series_of_the_candidate_are_compared(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({s: _meetings(s, "a") for s in SERIES}))
    _write_run(tmp_path, "cand", _all({"ES2015": _meetings("ES2015", "abcd")}))

    result = _compare(tmp_path)

    assert result["series_covered"] == ["ES2015"]
    assert result["n_meetings"] == 4
    assert result["baseline"]["series"] == ["ES2015"]
    assert "ES2015" in result["scope_note"]


def test_the_bootstrap_is_deterministic_for_the_seed(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({s: _meetings(s, "ab") for s in SERIES}))
    _write_run(tmp_path, "cand", _all({s: _meetings(s, "abc") for s in SERIES}))
    assert _compare(tmp_path) == _compare(tmp_path)


def test_paired_bootstrap_uses_the_same_meetings_for_both_systems() -> None:
    # Two meetings: the systems are perfectly anti-correlated, so with *paired* resampling the
    # recall difference is always +-1 or 0, never anything else.
    from afg.experiments.hosted_comparison import MeetingCounts

    base = {"m1": MeetingCounts(1, 1, 1, 1), "m2": MeetingCounts(0, 1, 0, 1)}
    cand = {"m1": MeetingCounts(0, 1, 0, 1), "m2": MeetingCounts(1, 1, 1, 1)}
    result = paired_bootstrap(base, cand, resamples=500, seed=1, level=0.95)
    assert result.recall.interval[0] == -1.0 and result.recall.interval[1] == 1.0
    assert result.recall.estimate == 0.0


@pytest.mark.parametrize(
    ("recall_ci", "precision_ci", "expected"),
    [
        ((0.01, 0.2), (-0.05, 0.1), "mejora"),
        ((0.01, 0.2), (-0.0501, 0.1), "sin diferencia demostrada"),
        ((-0.1, -0.01), (0.0, 0.1), "empeora"),
        ((-0.1, 0.1), (0.0, 0.1), "sin diferencia demostrada"),
        ((0.0, 0.2), (0.0, 0.1), "sin diferencia demostrada"),
    ],
)
def test_the_verdict_follows_adr_decision_7(
    recall_ci: tuple[float, float], precision_ci: tuple[float, float], expected: str
) -> None:
    assert verdict_for(recall_ci, precision_ci, precision_margin=-0.05) == expected


# --- operation KPIs ---------------------------------------------------------------------------


def test_time_ratio_is_the_paired_geometric_ratio_with_a_verdict(tmp_path: Path) -> None:
    slow = {f"{s}{x}": 100.0 for s in SERIES for x in LETTERS}
    fast = {f"{s}{x}": 10.0 for s in SERIES for x in LETTERS}
    found = _all({s: _meetings(s, "ab") for s in SERIES})
    _write_run(tmp_path, "base", found, ingest_seconds=slow)
    _write_run(tmp_path, "cand", found, ingest_seconds=fast)

    time = _compare(tmp_path)["operation"]["time"]

    assert time["candidate_median_s"] == 10.0
    assert time["baseline_median_s"] == 100.0
    assert time["ratio"]["estimate"] == pytest.approx(0.1)
    assert time["ratio"]["interval"][1] < 1
    assert time["verdict"] == "más rápido"
    assert time["n_meetings"] == 8


def test_slower_and_undetermined_time_verdicts(tmp_path: Path) -> None:
    base = {f"{s}{x}": 10.0 for s in SERIES for x in LETTERS}
    slow = {f"{s}{x}": 40.0 for s in SERIES for x in LETTERS}
    found = _all({s: _meetings(s, "ab") for s in SERIES})
    _write_run(tmp_path, "base", found, ingest_seconds=base)
    _write_run(tmp_path, "cand", found, ingest_seconds=slow)
    assert _compare(tmp_path)["operation"]["time"]["verdict"] == "más lento"


def test_equal_times_are_not_a_demonstrated_difference(tmp_path: Path) -> None:
    found = _all({s: _meetings(s, "ab") for s in SERIES})
    _write_run(tmp_path, "base", found)
    _write_run(tmp_path, "cand", found)
    time = _compare(tmp_path)["operation"]["time"]
    assert time["ratio"]["estimate"] == pytest.approx(1.0)
    assert time["verdict"] == "sin diferencia demostrada"


def test_time_sums_every_ingest_command_of_a_meeting_and_ignores_other_commands(
    tmp_path: Path,
) -> None:
    found = _all({"ES2015": _meetings("ES2015", "a")}, runs=1)
    _write_run(tmp_path, "base", found, ingest_seconds={"ES2015a": 5.0})
    _write_run(tmp_path, "cand", found, ingest_seconds={"ES2015a": 5.0})
    manifest = tmp_path / "ws" / "cand" / "ES2015" / "run-0.manifest.json"
    data = json.loads(manifest.read_text())
    data["commands"].append(  # the drift retry of meeting a: its time counts too
        {
            "argv": ["openkos", "ingest", "/x/ES2015a.md", "--auto"],
            "returncode": 0,
            "duration_s": 7.0,
        }
    )
    manifest.write_text(json.dumps(data))

    time = _compare(tmp_path)["operation"]["time"]
    assert time["per_meeting_s"]["ES2015a"] == {"baseline": 5.0, "candidate": 12.0}
    assert time["per_meeting_s"]["ES2015b"] == {"baseline": 10.0, "candidate": 10.0}


def test_completeness_counts_meetings_whose_ingest_finished(tmp_path: Path) -> None:
    found = _all({"ES2015": _meetings("ES2015", "ab")}, runs=1)
    _write_run(tmp_path, "base", found)
    _write_run(tmp_path, "cand", found, failed={("ES2015", 0): "ES2015c"})

    operation = _compare(tmp_path)["operation"]

    assert operation["completeness"]["candidate"] == {"complete": 2, "expected": 4, "share": 0.5}
    assert operation["completeness"]["baseline"] == {"complete": 4, "expected": 4, "share": 1.0}


def test_extracted_decisions_per_meeting_are_descriptive(tmp_path: Path) -> None:
    _write_run(tmp_path, "base", _all({"ES2015": _meetings("ES2015", "a")}, runs=2))
    _write_run(tmp_path, "cand", _all({"ES2015": _meetings("ES2015", "abcd")}, runs=2))

    per_meeting = _compare(tmp_path)["operation"]["decisions_per_meeting"]

    assert per_meeting["baseline"]["mean"] == pytest.approx(0.25)
    assert per_meeting["candidate"]["mean"] == pytest.approx(1.0)


def test_cost_is_passed_through_when_given(tmp_path: Path) -> None:
    found = _all({"ES2015": _meetings("ES2015", "a")}, runs=1)
    _write_run(tmp_path, "base", found)
    _write_run(tmp_path, "cand", found)
    assert _compare(tmp_path, cost_usd=12.5)["operation"]["cost_usd"] == 12.5
    assert _compare(tmp_path)["operation"]["cost_usd"] is None


# --- bridge -----------------------------------------------------------------------------------


def test_bridge_inside_the_range_of_the_formal_runs(tmp_path: Path) -> None:
    formal = {
        ("ES2015", 0): ["ES2015a"],
        ("ES2015", 1): ["ES2015a", "ES2015b"],
        ("ES2015", 2): ["ES2015a", "ES2015b", "ES2015c"],
    }
    _write_run(tmp_path, "formal", formal)
    _write_run(tmp_path, "bridge", {("ES2015", 0): ["ES2015a", "ES2015b"]})

    result = bridge_check(
        bridge=_load(tmp_path, "bridge"),
        formal=_load(tmp_path, "formal"),
        reference_of=_reference_of,
        similarity=text_similarity,
        tau=0.70,
    )

    series = result["series"]["ES2015"]
    assert series["inside"] is True
    assert series["formal_range"]["recall"] == [0.25, 0.75]
    assert series["bridge"]["recall"] == 0.5
    assert result["all_inside"] is True


def test_bridge_outside_the_range_is_flagged(tmp_path: Path) -> None:
    formal = {("ES2015", r): ["ES2015a"] for r in range(3)}
    _write_run(tmp_path, "formal", formal)
    _write_run(tmp_path, "bridge", {("ES2015", 0): _meetings("ES2015", "abcd")})

    result = bridge_check(
        bridge=_load(tmp_path, "bridge"),
        formal=_load(tmp_path, "formal"),
        reference_of=_reference_of,
        similarity=text_similarity,
        tau=0.70,
    )

    assert result["series"]["ES2015"]["inside"] is False
    assert result["series"]["ES2015"]["outside_metrics"] == ["recall", "f1"]
    assert result["all_inside"] is False


# --- orchestration and files ------------------------------------------------------------------


def _build(tmp_path: Path, **kw):  # type: ignore[no-untyped-def]
    from afg.experiments.hosted_comparison import build_comparison
    from afg.experiments.hosted_extraction import load_hosted_config

    return build_comparison(
        config=kw.pop("config", load_hosted_config()),
        labels=kw.pop("labels", ["openai-small", "google-large"]),
        include_bridge=kw.pop("include_bridge", False),
        pilot=kw.pop("pilot", False),
        runs_root=tmp_path / "out",
        workspaces_root=tmp_path / "ws",
        reference_of=_reference_of,
        similarity=text_similarity,
    )


def test_build_comparison_skips_labels_without_a_run(tmp_path: Path) -> None:
    _write_run(tmp_path, "experimento-a-formal", _all({"ES2015": _meetings("ES2015", "a")}))
    _write_run(
        tmp_path,
        "experimento-a-hosted-openai-small",
        _all({"ES2015": _meetings("ES2015", "abcd")}),
    )

    payload = _build(tmp_path)

    by_label = {c["label"]: c for c in payload["candidates"]}
    assert by_label["openai-small"]["status"] == "ok"
    assert by_label["openai-small"]["provider"] == "openai"
    assert by_label["openai-small"]["n_models"] == 6
    assert by_label["google-large"] == {
        "label": "google-large",
        "run_name": "experimento-a-hosted-google-large",
        "status": "sin corrida",
    }
    assert payload["bridge"] is None


def test_build_comparison_reads_pilot_runs_and_the_bridge(tmp_path: Path) -> None:
    _write_run(tmp_path, "experimento-a-formal", {("ES2015", r): ["ES2015a"] for r in range(3)})
    _write_run(
        tmp_path, "experimento-a-piloto-openai-small", {("ES2015", 0): _meetings("ES2015", "abcd")}
    )
    _write_run(tmp_path, "experimento-a-puente-0-7-2", {("ES2015", 0): ["ES2015a"]})

    payload = _build(tmp_path, labels=["openai-small"], pilot=True, include_bridge=True)

    assert payload["candidates"][0]["run_name"] == "experimento-a-piloto-openai-small"
    assert payload["candidates"][0]["status"] == "ok"
    assert payload["bridge"]["all_inside"] is True


def test_a_missing_baseline_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    with pytest.raises(FileNotFoundError, match="experimento-a-formal"):
        _build(tmp_path)


def test_costs_come_from_the_config_table(tmp_path: Path) -> None:
    import dataclasses

    from afg.experiments.hosted_extraction import load_hosted_config

    config = dataclasses.replace(load_hosted_config(), costs_usd={"openai-small": 3.25})
    _write_run(tmp_path, "experimento-a-formal", _all({"ES2015": _meetings("ES2015", "a")}))
    _write_run(
        tmp_path, "experimento-a-hosted-openai-small", _all({"ES2015": _meetings("ES2015", "a")})
    )

    payload = _build(tmp_path, config=config, labels=["openai-small"])

    assert payload["candidates"][0]["operation"]["cost_usd"] == 3.25


def test_write_comparison_produces_json_and_a_csv_with_one_row_per_tau(tmp_path: Path) -> None:
    import csv

    from afg.experiments.hosted_comparison import write_comparison

    _write_run(tmp_path, "experimento-a-formal", _all({"ES2015": _meetings("ES2015", "a")}))
    _write_run(
        tmp_path, "experimento-a-hosted-openai-small", _all({"ES2015": _meetings("ES2015", "abcd")})
    )
    payload = _build(tmp_path)

    json_path, csv_path = write_comparison(payload, tmp_path / "cmp")

    assert json.loads(json_path.read_text())["candidates"][0]["label"] == "openai-small"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    ok = [r for r in rows if r["status"] == "ok"]
    assert [r["tau"] for r in ok] == ["0.7", "0.75", "0.8"]
    assert ok[0]["verdict"] in {"mejora", "empeora", "sin diferencia demostrada"}
    assert {r["status"] for r in rows} == {"ok", "sin corrida"}


def test_ingest_time_summary_gives_the_median_and_the_completeness(tmp_path: Path) -> None:
    from afg.experiments.hosted_comparison import ingest_time_summary

    _write_run(
        tmp_path,
        "base",
        _all({"ES2015": _meetings("ES2015", "abcd")}, runs=1),
        ingest_seconds={"ES2015a": 10.0, "ES2015b": 20.0, "ES2015c": 30.0, "ES2015d": 40.0},
    )

    summary = ingest_time_summary(_load(tmp_path, "base"))

    assert summary["median_s"] == 25.0
    assert summary["n_meetings"] == 4
    assert summary["complete"] == 4 and summary["expected"] == 4
