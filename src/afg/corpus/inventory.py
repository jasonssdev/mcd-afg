"""Paso cero: completeness and count verification, before the design is committed.

Thesis section 5.0 requires, before anything else is built: (a) verifying the six
configured series are complete and their files are readable, (b) counting distinct
decisions, and (c) counting candidate cross-meeting links. This module is the first thing
the harness must be able to run against a real corpus download, and it is the most
important module in this repository for exactly that reason -- everything downstream
(OE1's gold set, the alignment protocol, the question bank) depends on the numbers it
reports.

VERIFIED at paso cero (2026-09-20), by hand, against the extracted corpus at
``data/raw/ami/``:

- The abstractive-summary DECISIONS count is the number of ``<sentence>`` children of the
  ``<decisions>`` element in ``abstractive/<meeting>.abssumm.xml`` -- NOT the count of
  elements whose local tag contains "decision" (that matches the ``<decisions>`` container
  itself and returns 1). This is the Hsueh & Moore operationalization the thesis reuses
  (section 5.0 / OE1).
- The DDS-layer segment count is the number of ``<decision>`` elements in
  ``decision/manual/<meeting>.decision.xml``.
- ``external`` and ``recap`` are optional boolean attributes (value ``"true"``) on those
  ``<decision>`` elements. They are counted SEPARATELY, never summed -- see
  ``MeetingInventory.external_flag_count`` for why.
- All tags in these files are namespaced (``{http://nite.sourceforge.net/}...``); matching
  is done on the local tag name via ``afg.corpus.nxt.iter_elements``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from afg.corpus.layers import AnnotationLayer, discover_layer_files, discover_meetings_with_layer
from afg.corpus.nxt import NxtParseError, iter_elements, parse_xml
from afg.shared.config import load_corpus_config
from afg.shared.csvio import open_csv_writer
from afg.shared.logging import get_logger
from afg.shared.paths import TABLES_DIR

logger = get_logger(__name__)

INVENTORY_CSV_NAME = "paso_cero_inventory.csv"

# The AMI scenario design's kick-off meeting letter (thesis section 5.0 / config
# corpus.phases -- that letter->phase mapping itself is still an unverified ASSUMPTION,
# but "a" as the first meeting of every series is used structurally by this module too,
# via ``cfg["corpus"]["series"]["meeting_letters"][0]``).
_KICKOFF_LETTER_INDEX = 0


class CorpusNotDownloadedError(RuntimeError):
    """Raised when ``ami_root`` does not exist or contains no recognizable annotations."""

    def __init__(self, ami_root: Path) -> None:
        super().__init__(
            f"AMI corpus not found at {ami_root}. This is expected before paso cero has "
            "been run. Download the manual annotations first:\n"
            "  uv run afg corpus download\n"
            "then re-run:\n"
            "  uv run afg corpus inventory"
        )
        self.ami_root = ami_root


class MeetingInventory(BaseModel):
    """Per-meeting completeness and parse status."""

    meeting_id: str
    is_kickoff: bool = Field(
        default=False,
        description="Whether this is the first ('a') meeting of its series -- no prior "
        "meeting exists, so an 'external' flag here cannot be a cross-meeting link.",
    )
    present: bool = Field(description="Whether any annotation file for this meeting was found.")
    layers_present: tuple[str, ...] = Field(default_factory=tuple)
    parse_errors: tuple[str, ...] = Field(
        default_factory=tuple, description="One entry per file that failed to parse."
    )
    abstractive_decision_sentences: int = Field(
        default=0,
        description="Count of <sentence> children of <decisions> in the abssumm file "
        "(Hsueh & Moore operationalization, thesis section 5.0 / OE1).",
    )
    dds_segment_count: int = Field(
        default=0, description="Count of <decision> elements in the DDS layer file."
    )
    # external and recap are kept SEPARATE, never summed into one column: thesis section
    # 1.6 is explicit that 'external' conflates "decision from a previous meeting" with
    # "requirement injected by the scenario", while 'recap' specifically marks revisiting
    # a previous decision. Summing them destroys the distinction the whole E3 stratum
    # depends on.
    external_flag_count: int = Field(
        default=0, description="Count of DDS <decision> elements with external=\"true\"."
    )
    recap_flag_count: int = Field(
        default=0, description="Count of DDS <decision> elements with recap=\"true\"."
    )

    @property
    def is_readable(self) -> bool:
        return self.present and not self.parse_errors

    @property
    def kickoff_external_flags(self) -> int:
        """External flags on this meeting that cannot be cross-meeting links.

        Only meaningful when ``is_kickoff`` is true: the kick-off meeting of a series has
        no predecessor, so any 'external' flag there is necessarily something other than a
        link to a prior meeting's decision (thesis section 1.6).
        """
        return self.external_flag_count if self.is_kickoff else 0


class SeriesInventory(BaseModel):
    """Per-series completeness, aggregated from its meetings."""

    series_id: str
    meetings: tuple[MeetingInventory, ...]

    @property
    def is_complete(self) -> bool:
        return len(self.meetings) == 4 and all(m.present for m in self.meetings)

    @property
    def all_readable(self) -> bool:
        return all(m.is_readable for m in self.meetings)

    @property
    def total_abstractive_decisions(self) -> int:
        return sum(m.abstractive_decision_sentences for m in self.meetings)

    @property
    def total_dds_segments(self) -> int:
        return sum(m.dds_segment_count for m in self.meetings)

    @property
    def total_external_flags(self) -> int:
        return sum(m.external_flag_count for m in self.meetings)

    @property
    def total_recap_flags(self) -> int:
        return sum(m.recap_flag_count for m in self.meetings)

    @property
    def kickoff_external_flags(self) -> int:
        return sum(m.kickoff_external_flags for m in self.meetings)


class CorpusInventory(BaseModel):
    """Full paso-cero report."""

    ami_root: Path
    series: tuple[SeriesInventory, ...]
    dds_meeting_count: int = Field(
        description="Number of meetings found with the Decision Discussion Segmentation "
        "layer, expected to be 47 (thesis section 5.0)."
    )

    @property
    def all_series_complete(self) -> bool:
        return all(s.is_complete for s in self.series)

    @property
    def total_abstractive_decisions(self) -> int:
        return sum(s.total_abstractive_decisions for s in self.series)

    @property
    def total_dds_segments(self) -> int:
        return sum(s.total_dds_segments for s in self.series)

    @property
    def total_external_flags(self) -> int:
        return sum(s.total_external_flags for s in self.series)

    @property
    def total_recap_flags(self) -> int:
        return sum(s.total_recap_flags for s in self.series)

    @property
    def kickoff_external_flags(self) -> int:
        return sum(s.kickoff_external_flags for s in self.series)

    @property
    def candidate_cross_meeting_links(self) -> int:
        """Lower-bound hint of cross-meeting decision links, derived from AMI's own flags.

        = (external flags NOT on a kick-off meeting) + (recap flags).

        This is NOT the link count OE1 will establish: OE1 annotates relations between all
        cross-meeting decision pairs, including ones AMI's own annotators never flagged as
        external or recap. It is only a lower bound, useful for sanity-checking project
        viability before the real annotation pass (thesis section 7).
        """
        non_kickoff_external = self.total_external_flags - self.kickoff_external_flags
        return non_kickoff_external + self.total_recap_flags


def _count_abstractive_decision_sentences(path: Path) -> tuple[int, list[str]]:
    """Count <sentence> children of <decisions> in an abssumm file.

    VERIFIED at paso cero (2026-09-20): the root <nite:root> holds four section elements
    (abstract, actions, decisions, problems), each with <sentence> children carrying the
    text. Returns (count, parse_errors).
    """
    try:
        root = parse_xml(path)
    except NxtParseError as exc:
        return 0, [str(exc)]
    count = 0
    for decisions_el in iter_elements(root, "decisions"):
        for child in decisions_el:
            if isinstance(child.tag, str) and child.tag.split("}")[-1] == "sentence":
                count += 1
    return count, []


def _count_dds_segments_and_flags(path: Path) -> tuple[int, int, int, list[str]]:
    """Count <decision> elements in a DDS file, plus their external/recap flags.

    VERIFIED at paso cero (2026-09-20): the root holds <decision nite:id="..."> elements,
    with optional boolean attributes external="true" / recap="true". Returns
    (segment_count, external_count, recap_count, parse_errors).
    """
    try:
        root = parse_xml(path)
    except NxtParseError as exc:
        return 0, 0, 0, [str(exc)]
    segment_count = 0
    external_count = 0
    recap_count = 0
    for decision_el in iter_elements(root, "decision"):
        segment_count += 1
        if decision_el.get("external") == "true":
            external_count += 1
        if decision_el.get("recap") == "true":
            recap_count += 1
    return segment_count, external_count, recap_count, []


def corpus_is_present(ami_root: Path) -> bool:
    """Whether ``ami_root`` holds a real download, not just the tracked scaffold dir.

    ``data/raw/ami/`` ships a ``.gitkeep`` placeholder so the directory exists in a fresh
    checkout (thesis spec: keep the directory, gitignore its contents). Directory
    existence alone is therefore not evidence of a download -- this also requires at
    least one real file inside it.
    """
    if not ami_root.exists():
        return False
    return any(
        path.is_file() and path.name != ".gitkeep" and not path.name.startswith(".")
        for path in ami_root.rglob("*")
    )


def build_inventory(ami_root: Path) -> CorpusInventory:
    """Build the paso-cero inventory for the configured series.

    Raises:
        CorpusNotDownloadedError: if ``ami_root`` does not exist, or exists but holds
            nothing beyond the tracked ``.gitkeep`` placeholder.
    """
    if not corpus_is_present(ami_root):
        raise CorpusNotDownloadedError(ami_root)

    cfg = load_corpus_config()
    series_ids: list[str] = cfg["corpus"]["series"]["ids"]
    meeting_letters: list[str] = cfg["corpus"]["series"]["meeting_letters"]
    kickoff_letter = meeting_letters[_KICKOFF_LETTER_INDEX] if meeting_letters else None

    dds_meetings = discover_meetings_with_layer(
        ami_root, AnnotationLayer.DECISION_DISCUSSION_SEGMENTATION
    )

    series_reports: list[SeriesInventory] = []
    for series_id in series_ids:
        meeting_reports: list[MeetingInventory] = []
        for letter in meeting_letters:
            meeting_id = f"{series_id}{letter}"
            summary_files = [
                f
                for f in discover_layer_files(ami_root, AnnotationLayer.ABSTRACTIVE_SUMMARY)
                if f.meeting_id == meeting_id
            ]
            dds_files = [
                f
                for f in discover_layer_files(
                    ami_root, AnnotationLayer.DECISION_DISCUSSION_SEGMENTATION
                )
                if f.meeting_id == meeting_id
            ]
            present = bool(summary_files) or bool(dds_files) or meeting_id in dds_meetings

            layers_present: list[str] = []
            parse_errors: list[str] = []
            abstractive_count = 0
            dds_count = 0
            external_count = 0
            recap_count = 0

            for layer_file in summary_files:
                layers_present.append(AnnotationLayer.ABSTRACTIVE_SUMMARY.value)
                count, errors = _count_abstractive_decision_sentences(layer_file.path)
                abstractive_count += count
                parse_errors.extend(errors)

            for layer_file in dds_files:
                layers_present.append(AnnotationLayer.DECISION_DISCUSSION_SEGMENTATION.value)
                seg_count, ext_count, rec_count, errors = _count_dds_segments_and_flags(
                    layer_file.path
                )
                dds_count += seg_count
                external_count += ext_count
                recap_count += rec_count
                parse_errors.extend(errors)

            meeting_reports.append(
                MeetingInventory(
                    meeting_id=meeting_id,
                    is_kickoff=letter == kickoff_letter,
                    present=present,
                    layers_present=tuple(sorted(set(layers_present))),
                    parse_errors=tuple(parse_errors),
                    abstractive_decision_sentences=abstractive_count,
                    dds_segment_count=dds_count,
                    external_flag_count=external_count,
                    recap_flag_count=recap_count,
                )
            )

        series_reports.append(SeriesInventory(series_id=series_id, meetings=tuple(meeting_reports)))

    return CorpusInventory(
        ami_root=ami_root,
        series=tuple(series_reports),
        dds_meeting_count=len(dds_meetings),
    )


def render_table(inventory: CorpusInventory, console: Console | None = None) -> None:
    """Render the inventory as a Rich table to the console."""
    console = console or Console()
    table = Table(title="Paso cero -- corpus inventory")
    table.add_column("Series")
    table.add_column("Meeting")
    table.add_column("Present")
    table.add_column("Readable")
    table.add_column("Layers")
    table.add_column("AbsDec", justify="right")
    table.add_column("DDS", justify="right")
    table.add_column("Ext", justify="right")
    table.add_column("Recap", justify="right")

    for series in inventory.series:
        for meeting in series.meetings:
            table.add_row(
                series.series_id,
                meeting.meeting_id,
                "yes" if meeting.present else "no",
                "yes" if meeting.is_readable else "no",
                ", ".join(meeting.layers_present) or "-",
                str(meeting.abstractive_decision_sentences),
                str(meeting.dds_segment_count),
                str(meeting.external_flag_count),
                str(meeting.recap_flag_count),
            )

    console.print(table)
    console.print(
        f"DDS layer found on {inventory.dds_meeting_count} meetings "
        f"(expected 47, thesis section 5.0)."
    )
    console.print(f"Total abstractive-summary decisions: {inventory.total_abstractive_decisions}")
    console.print(f"Total DDS segments: {inventory.total_dds_segments}")
    console.print(
        f"Total external flags: {inventory.total_external_flags} "
        f"({inventory.kickoff_external_flags} on kick-off meetings, therefore unusable as "
        f"cross-meeting links)"
    )
    console.print(f"Total recap flags: {inventory.total_recap_flags}")
    console.print(
        f"Candidate cross-meeting links (lower-bound hint, NOT the OE1 link count): "
        f"{inventory.candidate_cross_meeting_links}"
    )
    if inventory.candidate_cross_meeting_links < 40:
        console.print(
            "[bold yellow]Warning:[/bold yellow] candidate cross-meeting links "
            f"({inventory.candidate_cross_meeting_links}) is below 40 -- per thesis "
            "section 7, the design must be widened BEFORE execution, not after."
        )
    console.print(f"All six series complete: {inventory.all_series_complete}")


def write_csv(inventory: CorpusInventory, out_dir: Path = TABLES_DIR) -> Path:
    """Write the per-meeting inventory to ``reports/tables/paso_cero_inventory.csv``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / INVENTORY_CSV_NAME
    with open_csv_writer(out_path) as writer:
        writer.writerow(
            [
                "series_id",
                "meeting_id",
                "present",
                "readable",
                "layers_present",
                "abstractive_decision_sentences",
                "dds_segment_count",
                "external_flag_count",
                "recap_flag_count",
                "parse_errors",
            ]
        )
        for series in inventory.series:
            for meeting in series.meetings:
                writer.writerow(
                    [
                        series.series_id,
                        meeting.meeting_id,
                        meeting.present,
                        meeting.is_readable,
                        "|".join(meeting.layers_present),
                        meeting.abstractive_decision_sentences,
                        meeting.dds_segment_count,
                        meeting.external_flag_count,
                        meeting.recap_flag_count,
                        "|".join(meeting.parse_errors),
                    ]
                )
    logger.info("Wrote paso cero inventory to %s", out_path)
    return out_path
