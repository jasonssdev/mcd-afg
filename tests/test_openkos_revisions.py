"""Tests for the reader of ``.openkos/findings.db`` (``openkos revisions``, OpenKOS 0.7.0)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from afg.domain.relation import RelationType
from afg.extraction.openkos.commands import CommandResult
from afg.extraction.openkos.revisions import (
    EXPECTED_COLUMNS,
    FindingsSchemaError,
    direction_of,
    read_revision_findings,
    run_revisions,
)
from afg.extraction.openkos.workspace import OpenKosCommandError
from tests.openkos_findings import REVISION_FINDINGS_SQL, Row, write_findings_db

A, B = "decisions/alpha", "decisions/beta"


def test_expected_columns_are_the_ones_of_openkos_0_7_0() -> None:
    assert EXPECTED_COLUMNS == (
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


@pytest.mark.parametrize(
    ("verdict", "relation"),
    [
        ("reverses", RelationType.REVIERTE),
        ("refines", RelationType.REFINA),
        ("reaffirms", RelationType.REAFIRMA),
        ("unrelated", RelationType.NO_RELACIONADA),
    ],
)
def test_verdict_maps_to_relation_type(
    tmp_path: Path, verdict: str, relation: RelationType
) -> None:
    write_findings_db(tmp_path, [Row((A, B), verdict)])

    [finding] = read_revision_findings(tmp_path).relations

    assert finding.relation is relation
    assert finding.verdict == verdict
    assert finding.decision_ids == (A, B)
    assert finding.confidence == pytest.approx(0.9)


def test_direction_comes_from_the_dates_later_is_the_source(tmp_path: Path) -> None:
    write_findings_db(
        tmp_path, [Row((A, B), "refines", dates=("2004-11-23T11:00", "2004-11-23T09:00"))]
    )

    [finding] = read_revision_findings(tmp_path).relations

    assert finding.source_decision_id == A  # alpha has the later date
    assert finding.target_decision_id == B
    assert finding.direction_reason == "dated"


def test_direction_unknown_keeps_reason(tmp_path: Path) -> None:
    write_findings_db(
        tmp_path,
        [Row((A, B), "refines", dates=(None, "2004-11-23T09:00"), states=("missing", "dated"))],
    )

    [finding] = read_revision_findings(tmp_path).relations

    assert finding.source_decision_id is None
    assert finding.target_decision_id is None
    assert finding.direction_reason == "missing"


def test_pairs_that_are_not_decisions_are_skipped_and_counted(tmp_path: Path) -> None:
    write_findings_db(tmp_path, [Row((A, B), "refines"), Row((A, "concepts/x"), "refines")])

    result = read_revision_findings(tmp_path)

    assert len(result.relations) == 1
    assert result.skipped_non_decision == 1


def test_no_findings_is_an_empty_result(tmp_path: Path) -> None:
    write_findings_db(tmp_path, [])

    result = read_revision_findings(tmp_path)

    assert result.relations == ()
    assert result.skipped_non_decision == 0


def test_the_latest_row_of_a_pair_wins(tmp_path: Path) -> None:
    write_findings_db(tmp_path, [Row((A, B), "refines"), Row((A, B), "reverses")])

    [finding] = read_revision_findings(tmp_path).relations

    assert finding.verdict == "reverses"


def test_reading_does_not_modify_the_database(tmp_path: Path) -> None:
    path = write_findings_db(tmp_path, [Row((A, B), "refines")])
    before = path.read_bytes()

    read_revision_findings(tmp_path)

    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == ["findings.db"]


def test_missing_database_names_the_remedy(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="openkos revisions"):
        read_revision_findings(tmp_path)


def test_missing_table_is_a_schema_error(tmp_path: Path) -> None:
    path = tmp_path / ".openkos" / "findings.db"
    path.parent.mkdir()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE other (x TEXT)")
    conn.close()

    with pytest.raises(FindingsSchemaError, match="revision_findings"):
        read_revision_findings(tmp_path)


def test_missing_column_is_named(tmp_path: Path) -> None:
    sql = REVISION_FINDINGS_SQL.replace("    date_0 TEXT,\n", "")
    write_findings_db(tmp_path, [], create_sql=sql)

    with pytest.raises(FindingsSchemaError, match=r"missing.*date_0"):
        read_revision_findings(tmp_path)


def test_extra_column_is_named(tmp_path: Path) -> None:
    sql = REVISION_FINDINGS_SQL.replace(
        "created_at TEXT NOT NULL", "created_at TEXT NOT NULL, holder TEXT"
    )
    write_findings_db(tmp_path, [], create_sql=sql)

    with pytest.raises(FindingsSchemaError, match=r"unexpected.*holder"):
        read_revision_findings(tmp_path)


def test_unknown_verdict_is_a_schema_error(tmp_path: Path) -> None:
    write_findings_db(tmp_path, [Row((A, B), "supersedes")])

    with pytest.raises(FindingsSchemaError, match="supersedes"):
        read_revision_findings(tmp_path)


# --- direction rule (openkos/resolution/decision_revision.py:113-158) -----------------------


def test_direction_of_dated_pair_picks_the_later_date() -> None:
    later, earlier, reason = direction_of(
        A, "dated", "2004-11-23T09:00", B, "dated", "2004-11-23T10:00"
    )
    assert (later, earlier, reason) == (B, A, "dated")


def test_direction_of_equal_dates_is_unknown() -> None:
    result = direction_of(A, "dated", "2004-11-23T09:00", B, "dated", "2004-11-23T09:00")
    assert result == (None, None, "equal")


def test_date_only_and_date_time_on_the_same_day_are_equal() -> None:
    result = direction_of(A, "dated", "2004-11-23", B, "dated", "2004-11-23T10:00")
    assert result == (None, None, "equal")


def test_date_only_side_compares_by_day() -> None:
    later, _, reason = direction_of(A, "dated", "2004-11-22", B, "dated", "2004-11-23T01:00")
    assert (later, reason) == (B, "dated")


@pytest.mark.parametrize("state", ["missing", "multiple", "none-reached"])
def test_first_side_not_dated_reports_its_own_state(state: str) -> None:
    result = direction_of(A, state, None, B, "missing", None)
    assert result == (None, None, state)


def test_second_side_not_dated_reports_the_second_state() -> None:
    result = direction_of(A, "dated", "2004-11-23", B, "multiple", None)
    assert result == (None, None, "multiple")


def test_dated_state_without_a_date_is_unknown_missing() -> None:
    result = direction_of(A, "dated", None, B, "dated", "2004-11-23")
    assert result == (None, None, "missing")


# --- running the command ---------------------------------------------------------------------


class _Runner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []

    def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
        self.calls.append((tuple(args), cwd))
        return CommandResult(self.returncode, "", "boom" if self.returncode else "", 0.1)


def test_run_revisions_calls_auto_all_in_the_workspace(tmp_path: Path) -> None:
    runner = _Runner()

    run_revisions(runner, "openkos", tmp_path)

    assert runner.calls == [(("openkos", "revisions", "--auto", "--all"), tmp_path)]


def test_run_revisions_failure_raises_with_the_stderr(tmp_path: Path) -> None:
    with pytest.raises(OpenKosCommandError, match="boom"):
        run_revisions(_Runner(returncode=2), "openkos", tmp_path)
