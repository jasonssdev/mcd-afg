"""Audit the bibliography: coverage per thesis section, unreviewed preprints, missing and
duplicate DOIs.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from afg.bibliography.library import BibEntry, load_library
from afg.shared.csvio import open_csv_writer
from afg.shared.logging import get_logger
from afg.shared.paths import TABLES_DIR

logger = get_logger(__name__)

AUDIT_CSV_NAME = "bibliography_audit.csv"

EXPECTED_SECTIONS = tuple(f"section-8-{i}" for i in range(1, 8))


class BibliographyAudit(BaseModel):
    """Coverage and quality report over the bibliography."""

    total_entries: int
    entries_per_section: dict[str, int]
    sections_with_no_entries: tuple[str, ...]
    preprint_keys: tuple[str, ...]
    missing_doi_keys: tuple[str, ...]
    duplicate_doi_groups: tuple[tuple[str, tuple[str, ...]], ...]


def audit_library(entries: list[BibEntry]) -> BibliographyAudit:
    """Compute coverage and quality checks over a loaded bibliography."""
    section_counts: Counter[str] = Counter()
    for entry in entries:
        for section in entry.sections:
            section_counts[section] += 1

    sections_with_no_entries = tuple(s for s in EXPECTED_SECTIONS if section_counts.get(s, 0) == 0)

    preprint_keys = tuple(e.key for e in entries if e.is_preprint)
    missing_doi_keys = tuple(e.key for e in entries if not e.doi)

    doi_to_keys: dict[str, list[str]] = {}
    for entry in entries:
        if entry.doi:
            doi_to_keys.setdefault(entry.doi, []).append(entry.key)
    duplicate_doi_groups = tuple(
        (doi, tuple(keys)) for doi, keys in sorted(doi_to_keys.items()) if len(keys) > 1
    )

    return BibliographyAudit(
        total_entries=len(entries),
        entries_per_section={s: section_counts.get(s, 0) for s in EXPECTED_SECTIONS},
        sections_with_no_entries=sections_with_no_entries,
        preprint_keys=preprint_keys,
        missing_doi_keys=missing_doi_keys,
        duplicate_doi_groups=duplicate_doi_groups,
    )


def render_table(audit: BibliographyAudit, console: Console | None = None) -> None:
    console = console or Console()

    section_table = Table(title="Bibliography coverage per thesis section")
    section_table.add_column("Section")
    section_table.add_column("Entries", justify="right")
    for section, count in audit.entries_per_section.items():
        section_table.add_row(section, str(count))
    console.print(section_table)

    console.print(f"Total entries: {audit.total_entries}")
    preprints = ", ".join(audit.preprint_keys) or "none"
    console.print(f"Preprints (not peer reviewed): {len(audit.preprint_keys)} -- {preprints}")
    missing_doi = ", ".join(audit.missing_doi_keys) or "none"
    console.print(f"Missing DOI: {len(audit.missing_doi_keys)} -- {missing_doi}")
    if audit.duplicate_doi_groups:
        console.print("[bold red]Duplicate DOIs found:[/bold red]")
        for doi, keys in audit.duplicate_doi_groups:
            console.print(f"  {doi}: {', '.join(keys)}")
    else:
        console.print("Duplicate DOIs: none")


def write_csv(audit: BibliographyAudit, out_dir: Path = TABLES_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / AUDIT_CSV_NAME
    with open_csv_writer(out_path) as writer:
        writer.writerow(["section", "entry_count"])
        for section, count in audit.entries_per_section.items():
            writer.writerow([section, count])
        writer.writerow([])
        writer.writerow(["metric", "value"])
        writer.writerow(["total_entries", audit.total_entries])
        writer.writerow(["preprint_count", len(audit.preprint_keys)])
        writer.writerow(["missing_doi_count", len(audit.missing_doi_keys)])
        writer.writerow(["duplicate_doi_group_count", len(audit.duplicate_doi_groups)])
    logger.info("Wrote bibliography audit to %s", out_path)
    return out_path


def run_audit() -> BibliographyAudit:
    """Load the library and compute the audit -- convenience wrapper for the CLI."""
    return audit_library(load_library())
