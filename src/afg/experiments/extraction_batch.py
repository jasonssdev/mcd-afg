"""Experiment A over several series and runs under one run name (``afg experiment a-batch``).

The loop is unattended, so a failed ``(series, run)`` pair is recorded and the next one runs.
Everything lives in one ``reports/experiment-a/<run-name>/`` (``manifest.json`` plus
``extracciones.jsonl``, whose records keep their ``series_id``) and one workspace root
``data/interim/openkos/<run-name>/<SERIES>/run-<r>``, which is where C2 looks them up.

Repeating the run name resumes: pairs already ``ok`` are skipped and any other pair is redone
from a fresh workspace. The manifest keeps the single-series fields (``series`` as a
comma-joined string, ``runs`` per series, ``openkos``, ``created_at``/``updated_at``) so the
readers of ``afg experiment a`` reports keep working; the batch adds ``kind``, ``series_ids``
and ``pairs``.

Only integrity is reported (ADR 0005): counts and versions, never quality against the gold.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos_adapter import SeriesExtraction

__all__ = ["BatchConflictError", "SeriesExtractor", "batch_summary_lines", "run_batch"]

MANIFEST_FILENAME = "manifest.json"
RECORDS_FILENAME = "extracciones.jsonl"
BATCH_KIND = "batch"
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"


class BatchConflictError(Exception):
    """The run name exists and is not a batch this request can resume."""


class SeriesExtractor(Protocol):
    """What the loop needs from the OpenKOS adapter."""

    def extract_series(self, series_id: str, run: int) -> SeriesExtraction: ...


def _pair_key(series_id: str, run: int) -> str:
    return f"{series_id}/{run}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_resumable(run_dir: Path, series_ids: Sequence[str], runs: int) -> dict[str, Any]:
    """The manifest of an existing batch directory, checked against the request."""
    name = run_dir.name
    manifest_path = run_dir / MANIFEST_FILENAME
    manifest: dict[str, Any] = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    )
    if manifest.get("kind") != BATCH_KIND:
        raise BatchConflictError(
            f"{name} existe pero no es una corrida en lote (a-batch): no se reanuda ni se "
            "sobrescribe. Usa otro --run-name."
        )
    if set(manifest.get("series_ids", [])) != set(series_ids) or manifest.get("runs") != runs:
        raise BatchConflictError(
            f"{name} es un lote de {', '.join(manifest.get('series_ids', []))} con "
            f"{manifest.get('runs')} corrida(s) por serie; para reanudarlo se piden las mismas "
            "series y corridas. Usa otro --run-name para un lote distinto."
        )
    return manifest


def _prepare_resume(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Keep only the records of ``ok`` pairs (one each), dropping orphans of interrupted pairs."""
    records_path = run_dir / RECORDS_FILENAME
    if not records_path.is_file():
        return
    seen: set[str] = set()
    kept: list[str] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        key = _pair_key(record["series_id"], int(record["run"]))
        if manifest["pairs"].get(key, {}).get("status") == STATUS_OK and key not in seen:
            seen.add(key)
            kept.append(line)
    records_path.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")


def _remove_partial_pair(workspace_root: Path, series_id: str, run: int) -> None:
    """Delete the workspace, staging directory and OpenKOS manifest of one pair, nothing else."""
    base = workspace_root / series_id
    shutil.rmtree(base / f"run-{run}", ignore_errors=True)
    shutil.rmtree(base / f"run-{run}.sources", ignore_errors=True)
    (base / f"run-{run}.manifest.json").unlink(missing_ok=True)


def run_batch(
    adapter: SeriesExtractor,
    *,
    run_dir: Path,
    workspace_root: Path,
    series_ids: Sequence[str],
    runs: int,
    base_manifest: Mapping[str, Any],
    report: Callable[[str], None] = lambda _line: None,
) -> dict[str, Any]:
    """Extract every ``(series, run)`` pair, resuming ``run_dir`` when it is a matching batch.

    ``base_manifest`` carries the provenance fields of a new batch (as ``afg experiment a``
    writes them); it is ignored when resuming. Returns the final manifest.

    Raises:
        BatchConflictError: ``run_dir`` exists and is not a batch of these series and runs
            (checked before anything is written).
    """
    records_path = run_dir / RECORDS_FILENAME
    manifest_path = run_dir / MANIFEST_FILENAME
    if run_dir.exists():
        manifest = _load_resumable(run_dir, series_ids, runs)
        _prepare_resume(run_dir, manifest)
    else:
        manifest = {
            **base_manifest,
            "kind": BATCH_KIND,
            "series": ",".join(series_ids),
            "series_ids": list(series_ids),
            "runs": runs,
            "created_at": _now(),
            "pairs": {},
        }
        run_dir.mkdir(parents=True)

    def save() -> None:
        manifest["updated_at"] = _now()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    manifest["status"] = STATUS_RUNNING
    save()
    versions: list[str] = manifest["openkos"].setdefault("versions", [])
    for series_id in series_ids:
        for run in range(runs):
            key = _pair_key(series_id, run)
            if manifest["pairs"].get(key, {}).get("status") == STATUS_OK:
                report(f"{series_id} corrida {run}: ya completa, se omite.")
                continue
            _remove_partial_pair(workspace_root, series_id, run)
            entry: dict[str, Any] = {"series": series_id, "run": run, "status": STATUS_RUNNING}
            manifest["pairs"][key] = entry
            save()
            try:
                extraction = adapter.extract_series(series_id, run)
            except (OpenKosError, FileNotFoundError) as exc:
                entry.update(status=STATUS_FAILED, error=f"{type(exc).__name__}: {exc}")
                save()
                report(f"{series_id} corrida {run} fallida: {exc}")
                continue
            with records_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(extraction.to_record(), ensure_ascii=False) + "\n")
            entry.update(
                status=STATUS_OK,
                error=None,
                openkos_version=extraction.openkos_version,
                n_decisions=len(extraction.result.decisions),
                n_unmapped=len(extraction.unmapped),
                quotes_total=extraction.quotes.total,
                quotes_not_found=extraction.quotes.not_found,
            )
            if extraction.openkos_version and extraction.openkos_version not in versions:
                versions.append(extraction.openkos_version)
            save()
            report(
                f"{series_id} corrida {run}: {entry['n_decisions']} decisiones, "
                f"{entry['n_unmapped']} sin evidencia, {entry['quotes_not_found']} de "
                f"{entry['quotes_total']} citas no encontradas "
                f"(OpenKOS {extraction.openkos_version})."
            )
    failed = any(p["status"] != STATUS_OK for p in manifest["pairs"].values())
    manifest["status"] = STATUS_FAILED if failed else STATUS_OK
    save()
    return manifest


def _duration(seconds: float) -> str:
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {secs:02d} s"
    return f"{secs} s"


def batch_summary_lines(manifest: Mapping[str, Any], *, elapsed_seconds: float) -> list[str]:
    """Spanish integrity summary of a batch: counts and versions, never quality scores."""
    runs = int(manifest["runs"])
    pairs: Mapping[str, Mapping[str, Any]] = manifest["pairs"]
    lines = ["Resumen de integridad (sin puntajes: ADR 0005):"]
    for series_id in manifest["series_ids"]:
        entries = [pairs[k] for k in sorted(pairs) if pairs[k]["series"] == series_id]
        ok = [e for e in entries if e["status"] == STATUS_OK]
        failed = [e for e in entries if e["status"] == STATUS_FAILED]
        line = f"  {series_id}: {len(ok)} de {runs} corridas completas"
        if failed:
            line += f", {len(failed)} fallida(s)"
        lines.append(line)
        for e in sorted(ok, key=lambda item: item["run"]):
            lines.append(
                f"    corrida {e['run']}: {e['n_decisions']} decisiones, "
                f"{e['n_unmapped']} sin evidencia, {e['quotes_not_found']} de "
                f"{e['quotes_total']} citas no encontradas."
            )
        for e in sorted(failed, key=lambda item: item["run"]):
            lines.append(f"    corrida {e['run']} fallida: {e['error']}")
    versions = list(manifest["openkos"].get("versions", []))
    lines.append(f"Versiones de OpenKOS vistas: {', '.join(versions) or 'ninguna'}.")
    if len(versions) > 1:
        lines.append(
            "Aviso: más de una versión de OpenKOS en el mismo lote; las corridas no son "
            "comparables entre sí."
        )
    lines.append(f"Tiempo transcurrido: {_duration(elapsed_seconds)}.")
    return lines
