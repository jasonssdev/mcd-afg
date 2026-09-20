"""Load and normalize ``bibliography/refs.bib``."""

from __future__ import annotations

from pathlib import Path

import bibtexparser
from pydantic import BaseModel, ConfigDict, Field

from afg.shared.paths import BIBLIOGRAPHY_DIR

REFS_BIB_PATH = BIBLIOGRAPHY_DIR / "refs.bib"


class BibEntry(BaseModel):
    """A normalized BibTeX entry."""

    model_config = ConfigDict(frozen=True)

    key: str
    entry_type: str
    title: str = ""
    year: str = ""
    doi: str | None = None
    keywords: tuple[str, ...] = Field(default_factory=tuple)
    note: str | None = None

    @property
    def sections(self) -> tuple[str, ...]:
        """Thesis subsection keywords, e.g. ('section-8-1',)."""
        return tuple(k for k in self.keywords if k.startswith("section-8-"))

    @property
    def is_preprint(self) -> bool:
        return "preprint" in self.keywords or "not-peer-reviewed" in self.keywords


def _split_keywords(raw: str) -> tuple[str, ...]:
    return tuple(k.strip() for k in raw.split(",") if k.strip())


def load_library(path: Path = REFS_BIB_PATH) -> list[BibEntry]:
    """Parse ``refs.bib`` into a list of :class:`BibEntry`.

    Raises:
        FileNotFoundError: if ``path`` does not exist -- this project ships a seeded
            ``refs.bib`` under version control, so a missing file is a broken checkout,
            not a state to handle gracefully.
    """
    if not path.exists():
        raise FileNotFoundError(f"Bibliography file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        database = bibtexparser.load(fh)

    entries: list[BibEntry] = []
    for raw_entry in database.entries:
        entries.append(
            BibEntry(
                key=raw_entry.get("ID", ""),
                entry_type=raw_entry.get("ENTRYTYPE", ""),
                title=raw_entry.get("title", ""),
                year=raw_entry.get("year", ""),
                doi=raw_entry.get("doi") or None,
                keywords=_split_keywords(raw_entry.get("keywords", "")),
                note=raw_entry.get("note") or None,
            )
        )
    return entries
