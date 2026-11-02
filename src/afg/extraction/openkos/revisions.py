"""Read the findings of ``openkos revisions`` (OpenKOS 0.7.0) as typed relations (ADR 0016).

``openkos revisions`` has no ``--json`` output. It judges candidate pairs of ``Decision``
concepts and persists each verdict in ``<workspace>/.openkos/findings.db``, table
``revision_findings`` (``openkos/state/revision_findings.py``,
``_CREATE_REVISION_FINDINGS_TABLE_SQL``).
This module opens that file read-only and refuses to read it unless the table has exactly the
columns of 0.7.0, so an upgrade that changes the layout fails loudly instead of misreading rows.
OpenKOS is pinned to ``==0.7.0`` (ADR 0006), which is what makes reading its store acceptable.

Verdicts (``RevisionVerdictValue``, ``resolution/decision_revision.py:496-499``) map to
:class:`~afg.domain.relation.RelationType` as ``reverses`` -> ``REVIERTE``, ``refines`` ->
``REFINA``, ``reaffirms`` -> ``REAFIRMA``, ``unrelated`` -> ``NO_RELACIONADA``. ``reverses``
covers both ``revierte`` and ``reemplaza`` of the annotation guide: the scorer merges them for
the principal figure (ADR 0016).

Direction is never stored (``revision_findings.py`` module docstring, ADR-0025 of OpenKOS). It is
recomputed from the stored dates with :func:`direction_of`, a copy of OpenKOS's own rule so the
later decision is the same one OpenKOS would name:

* ``resolution/decision_revision.py:113-158`` ``pair_direction``: the first side not ``dated``
  makes the direction unknown with that side's state as reason; then the second side; two equal
  dates are unknown with reason ``equal``; otherwise the holder is the id with the later date.
* ``event_dates.py:59-69`` ``at_common_precision``: two date-times compare as date-times, and if
  either side is date-only both compare as days.

No field of the judge's reply (rationale, quotes, confidence) ever decides direction.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from afg.domain.relation import RelationType
from afg.extraction.openkos.commands import CommandRunner
from afg.extraction.openkos.workspace import OpenKosCommandError

FINDINGS_RELATIVE_PATH = Path(".openkos") / "findings.db"
FINDINGS_TABLE = "revision_findings"
DECISION_ID_PREFIX = "decisions/"
_TAIL_CHARS = 400

EXPECTED_COLUMNS: tuple[str, ...] = (
    "id",
    "pair_id_0",
    "pair_id_1",
    "verdict",
    "confidence",
    "rationale",
    "quote_0",
    "quote_1",
    "date_0",
    "date_1",
    "date_state_0",
    "date_state_1",
    "include_confidential",
    "prompt_version",
    "created_at",
)
"""The columns of ``revision_findings`` in OpenKOS 0.7.0, in table order."""

VERDICT_TO_RELATION: dict[str, RelationType] = {
    "reverses": RelationType.REVIERTE,
    "refines": RelationType.REFINA,
    "reaffirms": RelationType.REAFIRMA,
    "unrelated": RelationType.NO_RELACIONADA,
}


class FindingsSchemaError(OpenKosCommandError):
    """``findings.db`` is not the layout OpenKOS 0.7.0 writes."""


@dataclass(frozen=True, slots=True)
class MachineRelation:
    """One judged pair of decisions.

    ``decision_ids`` are sorted (OpenKOS's own order). ``source_decision_id`` is the later
    decision and ``target_decision_id`` the earlier one, both ``None`` when the dates do not
    order the pair; ``direction_reason`` is ``dated`` or why not (``missing``, ``multiple``,
    ``none-reached``, ``equal``).
    """

    decision_ids: tuple[str, str]
    relation: RelationType
    verdict: str
    confidence: float
    source_decision_id: str | None
    target_decision_id: str | None
    direction_reason: str

    @property
    def is_link(self) -> bool:
        """A link is any verdict other than ``unrelated`` (``introduce`` is never produced)."""
        return self.relation is not RelationType.NO_RELACIONADA


@dataclass(frozen=True, slots=True)
class RevisionFindings:
    """The relations of one workspace and the pairs left out because they are not decisions."""

    relations: tuple[MachineRelation, ...]
    skipped_non_decision: int = 0


def _parse_when(text: str) -> date | datetime:
    """Parse ``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM[:SS]`` (``okf.format_event_when``)."""
    return datetime.fromisoformat(text) if "T" in text else date.fromisoformat(text)


def _day(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def direction_of(
    id_a: str,
    state_a: str,
    date_a: str | None,
    id_b: str,
    state_b: str,
    date_b: str | None,
) -> tuple[str | None, str | None, str]:
    """``(later id, earlier id, reason)`` of a pair, as OpenKOS's ``pair_direction`` computes it.

    ``id_a`` is the sorted-first id. A side whose state is ``dated`` but whose date is absent is
    treated as ``missing`` (the stored row is inconsistent; direction is not guessed).
    """
    for state, when in ((state_a, date_a), (state_b, date_b)):
        if state != "dated":
            return None, None, state
        if when is None:
            return None, None, "missing"
    value_a, value_b = _parse_when(date_a or ""), _parse_when(date_b or "")
    if not (isinstance(value_a, datetime) and isinstance(value_b, datetime)):
        value_a, value_b = _day(value_a), _day(value_b)
    if value_a == value_b:
        return None, None, "equal"
    return (id_b, id_a, "dated") if value_a < value_b else (id_a, id_b, "dated")


_Row = tuple[str, str, str, float, str | None, str | None, str, str]
"""The columns :func:`read_revision_findings` selects, in order."""


def _check_schema(conn: sqlite3.Connection, path: Path) -> None:
    columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({FINDINGS_TABLE})"))
    if not columns:
        raise FindingsSchemaError(
            f"{path}: no table {FINDINGS_TABLE!r}; run `openkos revisions --auto --all` first."
        )
    missing = [c for c in EXPECTED_COLUMNS if c not in columns]
    extra = [c for c in columns if c not in EXPECTED_COLUMNS]
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing columns: {', '.join(missing)}")
        if extra:
            parts.append(f"unexpected columns: {', '.join(extra)}")
        raise FindingsSchemaError(
            f"{path}: {FINDINGS_TABLE} is not the OpenKOS 0.7.0 layout ({'; '.join(parts)})."
        )


def read_revision_findings(workspace: Path) -> RevisionFindings:
    """Read ``<workspace>/.openkos/findings.db`` read-only into :class:`MachineRelation` s.

    Raises:
        FileNotFoundError: no ``findings.db`` (``openkos revisions`` was not run).
        FindingsSchemaError: the table is absent, its columns differ from 0.7.0, or a verdict
            is not one of the four OpenKOS defines.
    """
    path = workspace / FINDINGS_RELATIVE_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found; run `openkos revisions --auto --all` in {workspace} first."
        )
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        _check_schema(conn, path)
        rows: list[_Row] = conn.execute(
            "SELECT pair_id_0, pair_id_1, verdict, confidence, date_0, date_1, "
            f"date_state_0, date_state_1 FROM {FINDINGS_TABLE} ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    latest: dict[tuple[str, str], _Row] = {}
    for row in rows:
        latest[(row[0], row[1])] = row  # a re-judged pair replaces its earlier row
    relations: list[MachineRelation] = []
    skipped = 0
    for id_0, id_1, verdict, confidence, date_0, date_1, state_0, state_1 in latest.values():
        if verdict not in VERDICT_TO_RELATION:
            raise FindingsSchemaError(f"{path}: unknown verdict {verdict!r} for {id_0} / {id_1}.")
        if not (id_0.startswith(DECISION_ID_PREFIX) and id_1.startswith(DECISION_ID_PREFIX)):
            skipped += 1
            continue
        later, earlier, reason = direction_of(id_0, state_0, date_0, id_1, state_1, date_1)
        relations.append(
            MachineRelation(
                decision_ids=(id_0, id_1),
                relation=VERDICT_TO_RELATION[verdict],
                verdict=verdict,
                confidence=float(confidence),
                source_decision_id=later,
                target_decision_id=earlier,
                direction_reason=reason,
            )
        )
    return RevisionFindings(tuple(relations), skipped)


def run_revisions(runner: CommandRunner, executable: str, workspace: Path) -> None:
    """Run ``openkos revisions --auto --all`` in ``workspace`` (spends model calls).

    Raises:
        OpenKosCommandError: the command exited non-zero.
    """
    args: Sequence[str] = (executable, "revisions", "--auto", "--all")
    result = runner.run(args, cwd=workspace)
    if result.returncode != 0:
        raise OpenKosCommandError(
            f"revisions in {workspace} exited {result.returncode}: {result.stderr[-_TAIL_CHARS:]}"
        )
