"""Tests for the Experiment A batch loop. No OpenKOS: the adapter is a fake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.experiments.extraction_batch import (
    BatchConflictError,
    batch_summary_lines,
    run_batch,
)
from afg.extraction.openkos.bundle_reader import QuoteCounts, UnmappedDecision
from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos_adapter import SeriesExtraction
from afg.extraction.protocol import ExtractionResult


class FakeAdapter:
    def __init__(self, base_dir: Path, version: str = "0.5.5") -> None:
        self.base_dir = base_dir
        self.version = version
        self.fail: set[tuple[str, int]] = set()
        self.calls: list[tuple[str, int]] = []
        self.dirty_seen: list[bool] = []

    def extract_series(self, series_id: str, run: int) -> SeriesExtraction:
        self.calls.append((series_id, run))
        workspace = self.base_dir / series_id / f"run-{run}"
        self.dirty_seen.append(workspace.exists())
        workspace.mkdir(parents=True, exist_ok=True)
        if (series_id, run) in self.fail:
            raise OpenKosError(f"ingest de {series_id}b salió con 1")
        decision = Decision(
            id="decisions/kinetic",
            series_id=series_id,
            meeting_id=f"{series_id}a",
            decision_object="battery",
            content="Use a kinetic battery.",
            status=DecisionStatus.ACCEPTED,
            evidence=EvidenceSpan(meeting_id=f"{series_id}a", dialogue_act_ids=("a1",)),
        )
        return SeriesExtraction(
            series_id=series_id,
            run=run,
            result=ExtractionResult(decisions=(decision,)),
            openkos_version=self.version,
            workspace=workspace,
            manifest_path=self.base_dir / series_id / f"run-{run}.manifest.json",
            quotes=QuoteCounts(total=3, found=2, not_found=1),
            unmapped=(UnmappedDecision("decisions/ghost", (f"{series_id}b",), ("not_found",)),),
        )


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "out" / "lote", tmp_path / "ws" / "lote"


def _base() -> dict[str, object]:
    return {"schema_version": 1, "run_name": "lote", "openkos": {"versions": []}}


def _go(adapter: FakeAdapter, dirs: tuple[Path, Path], series=("ES2015", "IS1004"), runs=2):  # type: ignore[no-untyped-def]
    run_dir, workspace_root = dirs
    return run_batch(
        adapter,
        run_dir=run_dir,
        workspace_root=workspace_root,
        series_ids=list(series),
        runs=runs,
        base_manifest=_base(),
    )


def _records(run_dir: Path) -> list[dict[str, object]]:
    path = run_dir / "extracciones.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_runs_every_pair_in_one_directory_keeping_series_ids(dirs: tuple[Path, Path]) -> None:
    adapter = FakeAdapter(dirs[1])
    manifest = _go(adapter, dirs)

    assert adapter.calls == [("ES2015", 0), ("ES2015", 1), ("IS1004", 0), ("IS1004", 1)]
    assert [(r["series_id"], r["run"]) for r in _records(dirs[0])] == adapter.calls
    assert manifest["status"] == "ok"
    assert manifest["kind"] == "batch"
    assert manifest["series"] == "ES2015,IS1004"
    assert manifest["series_ids"] == ["ES2015", "IS1004"]
    assert manifest["runs"] == 2
    assert manifest["openkos"]["versions"] == ["0.5.5"]
    assert manifest["pairs"]["ES2015/1"]["status"] == "ok"
    assert json.loads((dirs[0] / "manifest.json").read_text()) == manifest


def test_a_failed_pair_is_recorded_and_the_batch_continues(dirs: tuple[Path, Path]) -> None:
    adapter = FakeAdapter(dirs[1])
    adapter.fail = {("ES2015", 0)}
    manifest = _go(adapter, dirs)

    assert len(adapter.calls) == 4
    assert manifest["status"] == "failed"
    failed = manifest["pairs"]["ES2015/0"]
    assert failed["status"] == "failed"
    assert "ingest de ES2015b" in failed["error"]
    assert [(r["series_id"], r["run"]) for r in _records(dirs[0])] == [
        ("ES2015", 1),
        ("IS1004", 0),
        ("IS1004", 1),
    ]


def test_missing_transcripts_count_as_a_failed_pair(dirs: tuple[Path, Path]) -> None:
    class Missing(FakeAdapter):
        def extract_series(self, series_id: str, run: int) -> SeriesExtraction:
            if series_id == "IS1004":
                raise FileNotFoundError("Frozen transcripts of IS1004a not found")
            return super().extract_series(series_id, run)

    manifest = _go(Missing(dirs[1]), dirs, runs=1)
    assert manifest["pairs"]["IS1004/0"]["status"] == "failed"
    assert manifest["pairs"]["ES2015/0"]["status"] == "ok"


def test_resume_skips_ok_pairs_and_redoes_failed_ones_from_a_fresh_workspace(
    dirs: tuple[Path, Path],
) -> None:
    adapter = FakeAdapter(dirs[1])
    adapter.fail = {("ES2015", 1)}
    _go(adapter, dirs)
    untouched = dirs[1] / "ES2015" / "run-0"
    (untouched / "keep.txt").write_text("x")
    (dirs[1] / "ES2015" / "run-1.sources").mkdir()
    (dirs[1] / "ES2015" / "run-1.sources" / "stale.md").write_text("x")

    adapter.fail = set()
    adapter.calls.clear()
    adapter.dirty_seen.clear()
    manifest = _go(adapter, dirs)

    assert adapter.calls == [("ES2015", 1)]
    assert adapter.dirty_seen == [False]  # partial workspace and staging were removed first
    assert not (dirs[1] / "ES2015" / "run-1.sources").exists()
    assert (untouched / "keep.txt").exists()
    assert manifest["status"] == "ok"
    pairs = [(r["series_id"], r["run"]) for r in _records(dirs[0])]
    assert sorted(pairs) == [("ES2015", 0), ("ES2015", 1), ("IS1004", 0), ("IS1004", 1)]
    assert len(pairs) == len(set(pairs))


def test_resume_drops_an_orphan_record_of_a_pair_that_never_reached_ok(
    dirs: tuple[Path, Path],
) -> None:
    adapter = FakeAdapter(dirs[1])
    _go(adapter, dirs, series=("ES2015",), runs=2)
    manifest_path = dirs[0] / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["pairs"]["ES2015/1"]["status"] = "running"  # interrupted after the record was written
    manifest["status"] = "running"
    manifest_path.write_text(json.dumps(manifest))

    adapter.calls.clear()
    _go(adapter, dirs, series=("ES2015",), runs=2)

    assert adapter.calls == [("ES2015", 1)]
    assert [(r["series_id"], r["run"]) for r in _records(dirs[0])] == [("ES2015", 0), ("ES2015", 1)]


def test_resume_refuses_a_single_series_run(dirs: tuple[Path, Path]) -> None:
    dirs[0].mkdir(parents=True)
    (dirs[0] / "manifest.json").write_text(json.dumps({"series": "ES2015", "runs": 1}))
    adapter = FakeAdapter(dirs[1])

    with pytest.raises(BatchConflictError, match="lote"):
        _go(adapter, dirs)
    assert adapter.calls == []


def test_resume_refuses_other_series_or_runs(dirs: tuple[Path, Path]) -> None:
    adapter = FakeAdapter(dirs[1])
    _go(adapter, dirs)
    adapter.calls.clear()

    with pytest.raises(BatchConflictError):
        _go(adapter, dirs, series=("ES2015", "TS3009"))
    with pytest.raises(BatchConflictError):
        _go(adapter, dirs, runs=3)
    assert adapter.calls == []


def test_a_directory_without_manifest_is_refused(dirs: tuple[Path, Path]) -> None:
    dirs[0].mkdir(parents=True)
    with pytest.raises(BatchConflictError):
        _go(FakeAdapter(dirs[1]), dirs)


def test_summary_has_integrity_figures_but_no_scores(dirs: tuple[Path, Path]) -> None:
    adapter = FakeAdapter(dirs[1])
    adapter.fail = {("IS1004", 1)}
    manifest = _go(adapter, dirs)
    text = "\n".join(batch_summary_lines(manifest, elapsed_seconds=3725))

    assert "ES2015: 2 de 2 corridas completas" in text
    assert "IS1004: 1 de 2 corridas completas, 1 fallida" in text
    assert "1 decisiones" in text
    assert "1 de 3 citas no encontradas" in text
    assert "1 sin evidencia" in text
    assert "Versiones de OpenKOS vistas: 0.5.5." in text
    assert "1 h 02 min" in text
    assert "F1" not in text and "precisión" not in text.lower()


def test_summary_warns_when_more_than_one_openkos_version_was_seen(
    dirs: tuple[Path, Path],
) -> None:
    adapter = FakeAdapter(dirs[1])
    _go(adapter, dirs, runs=1)
    adapter.version = "0.6.0"
    manifest = json.loads((dirs[0] / "manifest.json").read_text())
    manifest["pairs"]["IS1004/0"]["status"] = "running"
    (dirs[0] / "manifest.json").write_text(json.dumps(manifest))
    manifest = _go(adapter, dirs, runs=1)

    text = "\n".join(batch_summary_lines(manifest, elapsed_seconds=5))
    assert "0.5.5" in text and "0.6.0" in text
    assert "Aviso" in text
