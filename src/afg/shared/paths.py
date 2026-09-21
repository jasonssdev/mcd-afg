"""Project paths, typed.

Port of the legacy ``utils/paths.py`` (conda / flat-layout project), rewritten for the
``src/afg`` package layout and made domain-aware: directory names describe what they hold
in this project's vocabulary (gold decisions, gold relations, questions) rather than only
generic data-science layers.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# --- top-level ---------------------------------------------------------------------
CONFIG_DIR: Path = PROJECT_ROOT / "config"
BIBLIOGRAPHY_DIR: Path = PROJECT_ROOT / "bibliography"
DATA_DIR: Path = PROJECT_ROOT / "data"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
ENV_PATH: Path = PROJECT_ROOT / ".env"

# --- data/ ---------------------------------------------------------------------------
RAW_DIR: Path = DATA_DIR / "raw"
AMI_DIR: Path = RAW_DIR / "ami"
INTERIM_DIR: Path = DATA_DIR / "interim"
TRANSCRIPTS_DIR: Path = INTERIM_DIR / "transcripts"
PROCESSED_DIR: Path = DATA_DIR / "processed"
GOLD_DECISIONS_DIR: Path = PROCESSED_DIR / "decisions"
GOLD_RELATIONS_DIR: Path = PROCESSED_DIR / "relations"
QUESTIONS_DIR: Path = PROCESSED_DIR / "questions"
EXTERNAL_DIR: Path = DATA_DIR / "external"

# --- reports/ --------------------------------------------------------------------------
FIGURES_DIR: Path = REPORTS_DIR / "figures"
TABLES_DIR: Path = REPORTS_DIR / "tables"

# Directories that this project writes to at runtime. Anything not writable (config/,
# bibliography/ source files, docs/) is deliberately excluded: those are
# authored by hand, not generated.
_WRITABLE_DIRS: tuple[Path, ...] = (
    RAW_DIR,
    AMI_DIR,
    INTERIM_DIR,
    TRANSCRIPTS_DIR,
    PROCESSED_DIR,
    GOLD_DECISIONS_DIR,
    GOLD_RELATIONS_DIR,
    QUESTIONS_DIR,
    EXTERNAL_DIR,
    FIGURES_DIR,
    TABLES_DIR,
)


def ensure_dirs() -> None:
    """Create every writable project directory if it does not already exist.

    Safe to call repeatedly (idempotent). Does not create ``CONFIG_DIR``,
    ``BIBLIOGRAPHY_DIR``, or ``DOCS_DIR`` -- those are authored, version-controlled content
    and their absence should surface as an error, not be silently papered over.
    """
    for directory in _WRITABLE_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
