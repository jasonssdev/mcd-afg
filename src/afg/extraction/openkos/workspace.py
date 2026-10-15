"""Series-level OpenKOS workspace orchestration (version-agnostic, injectable).

OpenKOS state is cumulative: the meetings of a series (a, b, c, d) are ingested, in that
order, into ONE workspace, so the unit of orchestration is the (series, run) pair and each
pair gets a fresh workspace ``<base>/<series>/run-<r>/``. A manifest next to it
(``run-<r>.manifest.json``, outside the workspace so it never touches OpenKOS's own git
history) records the OpenKOS version, the settings, every command, its exit code and its
duration, also when the run fails.

Choices fixed here:

* What is ingested is the BODY of the frozen transcript (``ROLE: text`` turns) without its
  front matter (:func:`stage_meeting_body`): the body is what the turn character offsets
  index, and it is the text the C1 baseline sees too.
* ``--event-date`` is passed only when the caller knows the date of a meeting. The frozen
  transcripts do not carry it (it lives in the AMI ``meetings.xml``), so by default it is
  left out; :func:`~afg.extraction.openkos.event_dates.attach_event_dates` fills it for the
  four meetings of a series (ADR 0008) and the manifest records, per meeting, whether the
  time is real or synthetic.
* Generation seed of run ``r`` is ``base_seed + r``, as in the Experiment B runner.
* Exit codes of ``openkos ingest``: 0 ok, 1 refusal (fails), 3 drift (retried once).
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from afg.corpus.render import parse_front_matter
from afg.extraction.openkos.capabilities import (
    MissingCapabilitiesError,
    probe_capabilities,
    require_capabilities,
)
from afg.extraction.openkos.commands import CommandResult, CommandRunner, OpenKosError
from afg.shared.logging import get_logger

logger = get_logger(__name__)

EXIT_REFUSED = 1
EXIT_DRIFT = 3
DECISION_PASS_KEY = "transcript_decisions"
_TAIL_CHARS = 2000


class WorkspaceNotEmptyError(OpenKosError):
    """The target workspace directory already holds files; it is never reused."""


class OpenKosCommandError(OpenKosError):
    """An OpenKOS command exited with an unexpected status."""


class IngestRefusedError(OpenKosCommandError):
    """``openkos ingest`` refused a source (exit 1)."""


class IngestDriftError(OpenKosCommandError):
    """``openkos ingest`` reported drift (exit 3) again after one retry."""


@dataclass(frozen=True, slots=True)
class OpenKosRunSettings:
    """Run-independent configuration of the OpenKOS side of a series run."""

    executable: str
    generative_model: str
    embedding_model: str
    base_seed: int
    temperature: float

    def seed_for(self, run: int) -> int:
        """Generation seed of run ``run`` (Experiment B convention: base + run)."""
        return self.base_seed + run


@dataclass(frozen=True, slots=True)
class MeetingSource:
    """One file to ingest; ``event_date`` is ``YYYY-MM-DD[THH:MM[:SS]]`` or ``None``.

    ``time_source`` says where the clock time of ``event_date`` comes from (``"ami"`` for the
    recorded start time, ``"synthetic"`` for the order-preserving stand-in of
    :mod:`~afg.extraction.openkos.event_dates`); ``None`` when no date is passed.
    """

    meeting_id: str
    path: Path
    event_date: str | None = None
    time_source: str | None = None


@dataclass(frozen=True, slots=True)
class SeriesRunResult:
    """Where a successful run left its workspace and manifest."""

    workspace: Path
    manifest_path: Path
    openkos_version: str | None


@dataclass(slots=True)
class _Recorder:
    """Wraps a runner and keeps an auditable log of every command."""

    inner: CommandRunner
    log: list[dict[str, Any]] = field(default_factory=list)

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        result = self.inner.run(args, cwd=cwd)
        entry: dict[str, Any] = {
            "argv": list(args),
            "returncode": result.returncode,
            "duration_s": round(result.duration_s, 3),
        }
        if result.returncode != 0:
            entry["stderr_tail"] = result.stderr[-_TAIL_CHARS:]
        self.log.append(entry)
        return result


def stage_meeting_body(meeting_id: str, transcripts_dir: Path, dest_dir: Path) -> Path:
    """Write the body of a frozen transcript (front matter removed) and return its path."""
    markdown = (transcripts_dir / f"{meeting_id}.md").read_text(encoding="utf-8")
    _, body = parse_front_matter(markdown)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"{meeting_id}.md"
    target.write_text(body, encoding="utf-8")
    return target


def ensure_config_keys(text: str, values: Mapping[str, str]) -> str:
    """Set ``key: value`` lines in an ``openkos.yaml`` text.

    An active ``key:`` line is replaced, a commented ``# key:`` line (the template's
    documentation of a default) is replaced by an active one, and a key that appears
    nowhere is appended. A key is never duplicated.
    """
    lines = text.splitlines()
    for key, value in values.items():
        active = re.compile(rf"^{re.escape(key)}\s*:")
        commented = re.compile(rf"^#\s*{re.escape(key)}\s*:")
        index = next((i for i, line in enumerate(lines) if active.match(line)), None)
        if index is None:
            index = next((i for i, line in enumerate(lines) if commented.match(line)), None)
        if index is None:
            lines.append(f"{key}: {value}")
        else:
            lines[index] = f"{key}: {value}"
    return "\n".join(lines) + "\n"


def require_config_key(text: str, key: str, *, executable: str, version: str | None) -> None:
    """Raise if the generated ``openkos.yaml`` never mentions ``key`` (active or commented).

    The packaged template documents every key the version understands, so a missing key
    means the version predates the feature and a written line would be unknown to it.
    """
    if not re.search(rf"^\s*#?\s*{re.escape(key)}\s*:", text, re.MULTILINE):
        raise MissingCapabilitiesError((key,), executable=executable, version=version)


def _check_workspace_is_fresh(workspace: Path) -> None:
    if workspace.exists() and (not workspace.is_dir() or any(workspace.iterdir())):
        raise WorkspaceNotEmptyError(
            f"Workspace {workspace} is not an empty directory; a run never reuses state."
        )


def _ingest_args(executable: str, source: MeetingSource) -> list[str]:
    args = [executable, "ingest", str(source.path), "--auto"]
    if source.event_date is not None:
        args += ["--event-date", source.event_date]
    return args


def _ingest_one(
    recorder: _Recorder, executable: str, source: MeetingSource, workspace: Path
) -> None:
    args = _ingest_args(executable, source)
    result = recorder.run(args, cwd=workspace)
    if result.returncode == EXIT_DRIFT:
        logger.warning("Drift ingesting %s; retrying once.", source.meeting_id)
        result = recorder.run(args, cwd=workspace)
        if result.returncode == EXIT_DRIFT:
            raise IngestDriftError(f"Ingest of {source.meeting_id} drifted twice (exit 3).")
    if result.returncode == EXIT_REFUSED:
        raise IngestRefusedError(
            f"OpenKOS refused {source.meeting_id} (exit 1): {result.stderr[-_TAIL_CHARS:]}"
        )
    if result.returncode != 0:
        raise OpenKosCommandError(
            f"ingest of {source.meeting_id} exited {result.returncode}: "
            f"{result.stderr[-_TAIL_CHARS:]}"
        )


def run_series_workspace(
    runner: CommandRunner,
    *,
    series_id: str,
    run: int,
    base_dir: Path,
    settings: OpenKosRunSettings,
    sources: Sequence[MeetingSource],
) -> SeriesRunResult:
    """Build the workspace of one (series, run): init, configure, ingest a to d.

    Raises:
        WorkspaceNotEmptyError: the target directory holds files.
        MissingCapabilitiesError: the executable lacks what the run needs; nothing is
            created when this is detected by the probe.
        IngestRefusedError, IngestDriftError, OpenKosCommandError: a command failed; a
            manifest with ``status: failed`` is written before the error propagates.
    """
    workspace = base_dir / series_id / f"run-{run}"
    manifest_path = base_dir / series_id / f"run-{run}.manifest.json"
    _check_workspace_is_fresh(workspace)

    ordered = sorted(sources, key=lambda source: source.meeting_id)
    recorder = _Recorder(runner)
    capabilities = probe_capabilities(recorder, settings.executable)
    require_capabilities(
        capabilities, need_event_date=any(s.event_date is not None for s in ordered)
    )

    config_values = {
        DECISION_PASS_KEY: "true",
        "seed": str(settings.seed_for(run)),
        "temperature": str(settings.temperature),
        "review": "false",
    }
    manifest: dict[str, Any] = {
        "series_id": series_id,
        "run": run,
        "status": "running",
        "executable": settings.executable,
        "openkos_version": capabilities.version,
        "workspace": str(workspace),
        "settings": {
            "generative_model": settings.generative_model,
            "embedding_model": settings.embedding_model,
            "seed": settings.seed_for(run),
            "temperature": settings.temperature,
            "transcript_decisions": True,
        },
        "meetings": [source.meeting_id for source in ordered],
        "event_dates_passed": any(s.event_date is not None for s in ordered),
        "event_dates": [
            {
                "meeting_id": s.meeting_id,
                "event_date": s.event_date,
                "time_source": s.time_source,
            }
            for s in ordered
            if s.event_date is not None
        ],
        "failed_meeting": None,
        "error": None,
    }

    def write_manifest(status: str, error: BaseException | None = None) -> None:
        manifest["status"] = status
        manifest["error"] = None if error is None else f"{type(error).__name__}: {error}"
        manifest["commands"] = recorder.log
        manifest["total_duration_s"] = round(time.monotonic() - started, 3)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    started = time.monotonic()
    workspace.mkdir(parents=True, exist_ok=True)
    current: MeetingSource | None = None
    try:
        init = recorder.run(
            [
                settings.executable,
                "init",
                "--model",
                settings.generative_model,
                "--embedding-model",
                settings.embedding_model,
            ],
            cwd=workspace,
        )
        if init.returncode != 0:
            raise OpenKosCommandError(
                f"init exited {init.returncode}: {init.stderr[-_TAIL_CHARS:]}"
            )
        config_path = workspace / "openkos.yaml"
        template = config_path.read_text(encoding="utf-8")
        require_config_key(
            template,
            DECISION_PASS_KEY,
            executable=settings.executable,
            version=capabilities.version,
        )
        config_path.write_text(ensure_config_keys(template, config_values), encoding="utf-8")
        for current in ordered:
            _ingest_one(recorder, settings.executable, current, workspace)
    except OpenKosError as exc:
        if isinstance(exc, OpenKosCommandError) and current is not None:
            manifest["failed_meeting"] = current.meeting_id
        write_manifest("failed", exc)
        raise
    write_manifest("ok")
    return SeriesRunResult(workspace, manifest_path, capabilities.version)
