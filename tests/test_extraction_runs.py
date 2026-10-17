"""Tests for the analysis of exploratory OpenKOS extraction runs (synthetic fixtures)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from afg.evaluation.reference import ReferenceDecision, ReferenceSet
from afg.experiments.extraction_runs import (
    ExtractionRun,
    decisions_matching,
    decisions_per_meeting,
    load_extraction_runs,
    pairwise_overlap,
    provenance_table,
    reference_counts_per_meeting,
    reproducibility_check,
)


def _decision(meeting: str, content: str) -> dict[str, Any]:
    return {
        "id": f"decisions/{content.lower().replace(' ', '-')}",
        "series_id": "ES2015",
        "meeting_id": meeting,
        "decision_object": "thing",
        "content": content,
        "status": "accepted",
    }


def _record(run: int, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "series_id": "ES2015",
        "run": run,
        "openkos_version": "0.5.5",
        "n_decisions": len(decisions),
        "decisions": decisions,
    }


def _write_run_dir(base: Path, name: str, records: list[dict[str, Any]], *, seed: int = 42) -> Path:
    directory = base / name
    directory.mkdir(parents=True)
    manifest = {
        "run_name": name,
        "created_at": "2026-10-16T18:00:00+00:00",
        "updated_at": "2026-10-16T18:30:00+00:00",
        "git_commit": "abc123",
        "runs": len(records),
        "openkos": {
            "seed": seed,
            "versions": ["0.5.5"],
            "generative_model": "qwen3:8b",
            "generative_model_digest": "g" * 64,
            "embedding_model": "bge-m3",
            "embedding_model_digest": "e" * 64,
            "temperature": 0.1,
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    (directory / "extracciones.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return directory


@pytest.fixture
def runs(tmp_path: Path) -> list[ExtractionRun]:
    a = [_decision("ES2015a", "Use kinetic battery"), _decision("ES2015b", "Logo on remote")]
    b = [_decision("ES2015a", "Use kinetic battery"), _decision("ES2015b", "Use rubber case")]
    first = _write_run_dir(tmp_path, "r1", [_record(0, a)])
    second = _write_run_dir(tmp_path, "r3x", [_record(0, a), _record(1, b)])
    return load_extraction_runs([first, second])


def test_load_extraction_runs_reads_every_record_with_its_seed(
    runs: list[ExtractionRun],
) -> None:
    assert [(r.run_name, r.run, r.seed) for r in runs] == [
        ("r1", 0, 42),
        ("r3x", 0, 42),
        ("r3x", 1, 43),
    ]
    assert runs[0].label == "r1 / corrida 0"


def test_decisions_per_meeting_is_tidy_and_counts_zero_meetings(
    runs: list[ExtractionRun],
) -> None:
    table = decisions_per_meeting(runs, meeting_ids=["ES2015a", "ES2015b", "ES2015c"])

    assert list(table.columns) == ["run_name", "run", "seed", "meeting_id", "n_decisions"]
    assert len(table) == 9
    row = table[(table.run_name == "r3x") & (table.run == 1) & (table.meeting_id == "ES2015c")]
    assert row.n_decisions.item() == 0


def test_pairwise_overlap_counts_common_and_jaccard(runs: list[ExtractionRun]) -> None:
    table = pairwise_overlap(runs)

    assert len(table) == 3
    pair = table[(table.run_a == "r3x / corrida 0") & (table.run_b == "r3x / corrida 1")].iloc[0]
    assert (pair.n_a, pair.n_b, pair.common) == (2, 2, 1)
    assert pair.jaccard == pytest.approx(1 / 3)
    same = table[(table.run_a == "r1 / corrida 0") & (table.run_b == "r3x / corrida 0")].iloc[0]
    assert same.jaccard == 1.0


def test_pairwise_overlap_ignores_decisions_with_same_content_in_other_meeting(
    tmp_path: Path,
) -> None:
    one = [_decision("ES2015a", "Same text")]
    two = [_decision("ES2015b", "Same text")]
    loaded = load_extraction_runs(
        [_write_run_dir(tmp_path, "x", [_record(0, one), _record(1, two)])]
    )

    assert pairwise_overlap(loaded).common.item() == 0


def test_reproducibility_check_same_seed_identical(runs: list[ExtractionRun]) -> None:
    result = reproducibility_check(runs[0], runs[1])

    assert result.seed == 42
    assert result.identical is True
    assert result.n_decisions == (2, 2)


def test_reproducibility_check_detects_a_difference(tmp_path: Path) -> None:
    one = [_decision("ES2015a", "Use kinetic battery")]
    two = [_decision("ES2015a", "Use solar battery")]
    first = _write_run_dir(tmp_path, "p", [_record(0, one)])
    second = _write_run_dir(tmp_path, "q", [_record(0, two)])
    a, b = load_extraction_runs([first, second])

    assert reproducibility_check(a, b).identical is False


def test_reproducibility_check_refuses_different_seeds(runs: list[ExtractionRun]) -> None:
    with pytest.raises(ValueError, match="semilla"):
        reproducibility_check(runs[1], runs[2])


def test_reference_counts_per_meeting_counts_only_given_meetings() -> None:
    def ref(decision_id: str, meeting: str) -> ReferenceDecision:
        return ReferenceDecision(
            decision_id=decision_id,
            series_id="ES2015",
            meeting_id=meeting,
            decision_object="o",
            content="c",
            evidence=None,
            evidence_method="none",
            role=None,
        )

    reference = ReferenceSet(
        series_id="ES2015",
        decisions=(ref("d1", "ES2015a"), ref("d2", "ES2015a"), ref("d3", "ES2015c")),
    )

    counts = reference_counts_per_meeting(reference, ["ES2015a", "ES2015b", "ES2015c"])

    assert counts.to_dict() == {"ES2015a": 2, "ES2015b": 0, "ES2015c": 1}


def test_decisions_matching_filters_by_content_case_insensitively(
    runs: list[ExtractionRun],
) -> None:
    found = decisions_matching(runs[0], r"LOGO")

    assert list(found.columns) == ["meeting_id", "decision_object", "content"]
    assert found.content.tolist() == ["Logo on remote"]


def test_provenance_table_reports_versions_models_seed_and_duration(
    runs: list[ExtractionRun],
) -> None:
    table = provenance_table(runs)

    row = table.loc["r3x"]
    assert row["versión de OpenKOS"] == "0.5.5"
    assert row["semilla base"] == 42
    assert row["duración (min)"] == 30.0
    assert row["commit"] == "abc123"
    assert row["digest del modelo generativo"] == "g" * 12
    assert list(table.index) == ["r1", "r3x"]
