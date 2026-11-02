"""Builder of an OpenKOS 0.7.0 ``.openkos/findings.db`` holding ``revision_findings``.

The ``CREATE TABLE`` statements are copied verbatim from
``openkos/state/revision_findings.py`` (``_CREATE_REVISION_FINDINGS_TABLE_SQL`` and
``_CREATE_REVISION_FINDING_DIGESTS_TABLE_SQL``, OpenKOS 0.7.0), so the schema test pins the exact
column list the reader depends on.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REVISION_FINDINGS_SQL = """
CREATE TABLE IF NOT EXISTS revision_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id_0 TEXT NOT NULL,
    pair_id_1 TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL,
    quote_0 TEXT,
    quote_1 TEXT,
    date_0 TEXT,
    date_1 TEXT,
    date_state_0 TEXT NOT NULL,
    date_state_1 TEXT NOT NULL,
    include_confidential INTEGER NOT NULL,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

DIGESTS_SQL = """
CREATE TABLE IF NOT EXISTS revision_finding_input_digests (
    finding_id INTEGER NOT NULL REFERENCES revision_findings(id),
    ordinal INTEGER NOT NULL,
    input_ref TEXT NOT NULL,
    digest TEXT NOT NULL
)
"""

_INSERT = """
INSERT INTO revision_findings
    (pair_id_0, pair_id_1, verdict, confidence, rationale, quote_0, quote_1, date_0, date_1,
     date_state_0, date_state_1, include_confidential, prompt_version, created_at)
VALUES (?, ?, ?, ?, 'because', NULL, NULL, ?, ?, ?, ?, 0, 'v1', '2026-11-01T00:00:00Z')
"""


@dataclass(frozen=True)
class Row:
    """One stored finding; ``ids`` must already be sorted, as OpenKOS stores them."""

    ids: tuple[str, str]
    verdict: str
    dates: tuple[str | None, str | None] = ("2004-11-23T09:00", "2004-11-23T10:00")
    states: tuple[str, str] = ("dated", "dated")
    confidence: float = 0.9


def write_findings_db(
    workspace: Path, rows: Sequence[Row] = (), *, create_sql: str = REVISION_FINDINGS_SQL
) -> Path:
    """Create ``<workspace>/.openkos/findings.db`` with ``rows`` in ``revision_findings``."""
    path = workspace / ".openkos" / "findings.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(create_sql)
        conn.execute(DIGESTS_SQL)
        if create_sql == REVISION_FINDINGS_SQL:
            for row in rows:
                conn.execute(
                    _INSERT,
                    (
                        row.ids[0],
                        row.ids[1],
                        row.verdict,
                        row.confidence,
                        row.dates[0],
                        row.dates[1],
                        row.states[0],
                        row.states[1],
                    ),
                )
    conn.close()
    return path
