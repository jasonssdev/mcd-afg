"""Adapter from the OpenKOS instrument to :class:`~afg.extraction.protocol.ExtractionResult`.

Thesis section 5.9: the implementation runs on OpenKOS (local-first knowledge compilation
engine, Apache-2.0, same author, preexisting). Per ADR 0003 this is the only place that drives
OpenKOS, and per ADR 0006 it does so only through the command line, via an injectable
:class:`~afg.extraction.openkos.commands.CommandRunner`, so nothing here imports ``openkos`` or
needs it installed.

OpenKOS state is cumulative: the four meetings of a series are ingested in order into one
workspace. The unit of extraction is therefore the (series, run) pair, :meth:`extract_series`,
not one meeting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from afg.extraction.openkos.bundle_reader import (
    BundleDecisions,
    QuoteCounts,
    UnmappedDecision,
    read_decision_bundle,
)
from afg.extraction.openkos.commands import CommandRunner
from afg.extraction.openkos.event_dates import POSITION_LETTERS, attach_event_dates
from afg.extraction.openkos.workspace import (
    MeetingSource,
    OpenKosRunSettings,
    run_series_workspace,
    stage_meeting_body,
)
from afg.extraction.protocol import ExtractionResult, Extractor
from afg.shared.logging import get_logger
from afg.shared.paths import PROJECT_ROOT, TRANSCRIPTS_DIR

logger = get_logger(__name__)

BUNDLE_DIRNAME = "bundle"


def project_relative(path: Path) -> str:
    """``path`` relative to the project root (POSIX form), or as given when outside it."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


@dataclass(frozen=True, slots=True)
class SeriesExtraction:
    """One (series, run) extraction with what is needed to audit it."""

    series_id: str
    run: int
    result: ExtractionResult
    openkos_version: str | None
    workspace: Path
    manifest_path: Path
    quotes: QuoteCounts
    unmapped: tuple[UnmappedDecision, ...]

    def to_record(self) -> dict[str, Any]:
        """JSON-serializable form: one line of ``extracciones.jsonl`` of an Experiment A run."""
        return {
            "series_id": self.series_id,
            "run": self.run,
            "openkos_version": self.openkos_version,
            "workspace": project_relative(self.workspace),
            "manifest": project_relative(self.manifest_path),
            "n_decisions": len(self.result.decisions),
            "n_relations": len(self.result.relations),
            "quotes": asdict(self.quotes),
            "unmapped": [
                {
                    "concept_id": item.concept_id,
                    "meeting_ids": list(item.meeting_ids),
                    "reasons": list(item.reasons),
                }
                for item in self.unmapped
            ],
            "decisions": [decision.model_dump(mode="json") for decision in self.result.decisions],
        }


@dataclass(slots=True)
class OpenKosAdapter(Extractor):
    """Extractor backed by the ``openkos`` command line (thesis section 5.9 "instrument").

    Per thesis section 5.9, the boundary between instrument and contribution is explicit:
    OpenKOS provides ingestion, typed extraction with provenance, storage, and hybrid
    retrieval. This project's contribution is the reference set, the three-condition
    design, the alignment protocol, and the error-attribution measurement -- not the
    extraction engine itself.

    ``meetings_xml`` is the AMI ``meetings.xml``; when given, each meeting is ingested with its
    event date (ADR 0008).
    """

    runner: CommandRunner
    settings: OpenKosRunSettings
    base_dir: Path
    transcripts_dir: Path = TRANSCRIPTS_DIR
    meetings_xml: Path | None = None

    def _meeting_ids(self, series_id: str) -> list[str]:
        ids = [f"{series_id}{letter}" for letter in POSITION_LETTERS]
        missing = [m for m in ids if not (self.transcripts_dir / f"{m}.md").is_file()]
        if missing:
            raise FileNotFoundError(
                f"Frozen transcripts of {', '.join(missing)} not found in "
                f"{self.transcripts_dir}. Render them first (`uv run afg corpus transcripts`)."
            )
        return ids

    def extract_series(self, series_id: str, run: int) -> SeriesExtraction:
        """Build the workspace of ``(series_id, run)`` with OpenKOS and read its decisions.

        Raises:
            FileNotFoundError: a meeting of the series has no frozen transcript.
            afg.extraction.openkos.commands.OpenKosError: OpenKOS lacks a capability, a
                command failed, or the bundle does not have the expected layout.
        """
        meeting_ids = self._meeting_ids(series_id)
        staging = self.base_dir / series_id / f"run-{run}.sources"
        sources = [
            MeetingSource(m, stage_meeting_body(m, self.transcripts_dir, staging))
            for m in meeting_ids
        ]
        if self.meetings_xml is not None:
            sources = attach_event_dates(sources, self.meetings_xml, series_id)
        built = run_series_workspace(
            self.runner,
            series_id=series_id,
            run=run,
            base_dir=self.base_dir,
            settings=self.settings,
            sources=sources,
        )
        read: BundleDecisions = read_decision_bundle(
            built.workspace / BUNDLE_DIRNAME,
            series_id=series_id,
            meeting_ids=meeting_ids,
            transcripts_dir=self.transcripts_dir,
        )
        logger.info(
            "%s run %d: %d decisions, %d unmapped (OpenKOS %s).",
            series_id,
            run,
            len(read.decisions),
            len(read.unmapped),
            built.openkos_version,
        )
        return SeriesExtraction(
            series_id=series_id,
            run=run,
            result=ExtractionResult(decisions=read.decisions),
            openkos_version=built.openkos_version,
            workspace=built.workspace,
            manifest_path=built.manifest_path,
            quotes=read.quotes,
            unmapped=read.unmapped,
        )

    def extract(self, meeting_id: str, transcript: str) -> ExtractionResult:
        """Not supported: OpenKOS accumulates a series, so a single meeting is not a unit.

        Use :meth:`extract_series`.
        """
        raise NotImplementedError(
            "OpenKosAdapter extracts whole series, not single meetings: OpenKOS state is "
            "cumulative across the meetings of a series. Use OpenKosAdapter.extract_series."
        )
