"""Tests for the relation report of Experiment A (workspaces + findings + gold -> JSON)."""

from __future__ import annotations

from pathlib import Path

from afg.domain.relation import RelationType
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.relations import GoldPair
from afg.experiments.relations_report import discover_runs, score_workspaces
from afg.extraction.openkos.commands import CommandResult
from tests.openkos_findings import Row, write_findings_db
from tests.relations_workspace import (
    ALPHA,
    BETA,
    reference_decision,
    text_similarity,
    write_transcripts,
    write_workspace,
)

A, B = "decisions/alpha", "decisions/beta"


def _reference() -> tuple[ReferenceDecision, ...]:
    return (
        reference_decision("ES2015a.d01", "ES2015a", *ALPHA),
        reference_decision("ES2015b.d01", "ES2015b", *BETA),
    )


def _gold() -> tuple[GoldPair, ...]:
    return (GoldPair("ES2015a.d01", "ES2015b.d01", RelationType.REFINA, True),)


def _score(tmp_path: Path, **overrides):  # type: ignore[no-untyped-def]
    write_transcripts(tmp_path / "transcripts")
    args = {
        "run_name": "lote",
        "workspace_root": tmp_path / "ws",
        "series_ids": ["ES2015"],
        "reference_of": lambda s: _reference(),
        "gold_of": lambda s: _gold(),
        "similarity": text_similarity,
        "tau": 0.70,
        "transcripts_dir": tmp_path / "transcripts",
    }
    args.update(overrides)
    return score_workspaces(**args)


def test_discover_runs_orders_numerically_and_ignores_other_folders(tmp_path: Path) -> None:
    for name in ("run-10", "run-2", "run-0"):
        (tmp_path / name / "bundle").mkdir(parents=True)
    (tmp_path / "run-1").mkdir()  # no bundle: not a workspace
    (tmp_path / "notes").mkdir()
    (tmp_path / "run-3.manifest.json").write_text("{}")

    assert [run for run, _ in discover_runs(tmp_path)] == [0, 2, 10]


def test_scores_a_workspace_against_the_gold(tmp_path: Path) -> None:
    write_workspace(tmp_path / "ws", findings=[Row((A, B), "refines")])

    report = _score(tmp_path)

    [entry] = report["entries"]
    assert (entry["series"], entry["run"]) == ("ES2015", 0)
    assert entry["alignment"] == {"machine_decisions": 2, "gold_decisions": 2, "aligned": 2}
    assert entry["findings"] == {
        "n_relations": 1,
        "by_verdict": {"refines": 1},
        "skipped_non_decision": 0,
    }
    assert entry["score"]["existence_end_to_end"]["tp"] == 1
    assert report["pooled"]["existence_end_to_end"]["recall"]["rate"] == 1.0
    assert report["pooled"]["direction_principal"]["end_to_end"]["rate"] == 1.0
    assert report["tau"] == 0.70
    assert report["run_name"] == "lote"
    assert report["partition"] == "development"


def test_unaligned_decisions_are_missed_end_to_end(tmp_path: Path) -> None:
    write_workspace(tmp_path / "ws", findings=[Row((A, B), "refines")])
    reference = (
        reference_decision("ES2015a.d01", "ES2015a", "other object", "Something else entirely."),
        reference_decision("ES2015b.d01", "ES2015b", *BETA),
    )

    report = _score(tmp_path, reference_of=lambda s: reference)

    [entry] = report["entries"]
    assert entry["alignment"]["aligned"] == 1
    assert entry["score"]["existence_end_to_end"]["recall"]["rate"] == 0.0
    assert entry["score"]["existence_conditional"]["recall"]["trials"] == 0


def test_run_revisions_runs_before_reading(tmp_path: Path) -> None:
    workspace = write_workspace(tmp_path / "ws", findings=None)
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    class Runner:
        def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
            calls.append((tuple(args), cwd))
            write_findings_db(workspace, [Row((A, B), "reaffirms")])
            return CommandResult(0, "", "", 0.1)

    report = _score(tmp_path, runner=Runner(), executable="openkos", run_revisions_first=True)

    assert calls == [(("openkos", "revisions", "--auto", "--all"), workspace)]
    assert report["entries"][0]["findings"]["by_verdict"] == {"reaffirms": 1}


def test_without_the_flag_revisions_are_not_run(tmp_path: Path) -> None:
    write_workspace(tmp_path / "ws", findings=[Row((A, B), "refines")])

    class Runner:
        def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
            raise AssertionError("must not run OpenKOS")

    _score(tmp_path, runner=Runner(), executable="openkos")


def test_a_workspace_without_findings_is_an_error_entry_not_a_crash(tmp_path: Path) -> None:
    write_workspace(tmp_path / "ws", run=0, findings=None)
    write_workspace(tmp_path / "ws", run=1, findings=[Row((A, B), "refines")])

    report = _score(tmp_path)

    first, second = report["entries"]
    assert "openkos revisions" in first["error"]
    assert "score" not in first
    assert second["score"]["existence_end_to_end"]["tp"] == 1
    assert report["pooled"]["n_gold_links"] == 1  # only the run that could be read
    assert report["n_errors"] == 1


def test_no_workspaces_gives_an_empty_report(tmp_path: Path) -> None:
    report = _score(tmp_path)

    assert report["entries"] == []
    assert report["pooled"]["n_gold_pairs"] == 0
