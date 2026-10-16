"""Tests for the ``openkos query --json`` wrapper (schema v1). No OpenKOS: scripted runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.extraction.openkos.commands import OpenKosError
from afg.extraction.openkos.query import (
    QueryFailedError,
    QueryOutputError,
    QueryRejectedError,
    QuerySchemaError,
    parse_query_report,
    require_reproducible,
    run_query,
)
from tests.openkos_query import QueryRunner, query_report


def test_builds_the_exact_arguments_and_runs_in_the_workspace(tmp_path: Path) -> None:
    runner = QueryRunner()
    run_query(runner, "openkos", tmp_path, "Which battery?", limit=5)
    ((argv, cwd),) = runner.queries()
    assert argv == ("openkos", "query", "Which battery?", "--json", "--limit", "5")
    assert cwd == tmp_path
    for forbidden in ("--allow-unattributed", "--include-confidential", "--save", "--auto"):
        assert forbidden not in argv


def test_parses_every_field_of_schema_v1(tmp_path: Path) -> None:
    report = run_query(QueryRunner(), "openkos", tmp_path, "q", limit=5)
    assert report.outcome == "answered" and report.answer == "A kinetic battery."
    assert report.openkos_version == "0.5.5" and report.limit == 5 and report.withheld == 0
    assert report.sufficiency.enabled and report.sufficiency.raw_reply == "YES"
    assert report.attribution.status == "reported" and report.attribution.used_indices == (1,)
    assert report.context_blocks[0].concept_id == "decisions/battery"
    assert report.omitted[0].reason == "context_budget"
    assert report.retrieved[0].dense_rank is None and report.retrieved[0].fts_rank == 1
    assert report.citations[0].concept_id == "decisions/battery"
    assert report.counts.fused == 2
    assert report.llm.seed == 42 and report.llm.temperature == 0.1
    assert report.prompts.user_sha256 == "u"


def test_non_json_output_is_an_error() -> None:
    with pytest.raises(QueryOutputError, match="JSON"):
        parse_query_report("not json at all")


def test_non_zero_exit_without_json_is_a_failure(tmp_path: Path) -> None:
    runner = QueryRunner(reports=[""], query_code=2, query_stderr="boom: no workspace")
    with pytest.raises(QueryFailedError, match="boom"):
        run_query(runner, "openkos", tmp_path, "q", limit=5)


def test_non_zero_exit_with_json_still_reads_the_outcome(tmp_path: Path) -> None:
    refusal = query_report(outcome="no_match", answer=None, citations=[])
    runner = QueryRunner(reports=[refusal], query_code=1)
    assert run_query(runner, "openkos", tmp_path, "q", limit=5).outcome == "no_match"


def test_wrong_schema_version_is_rejected() -> None:
    with pytest.raises(QuerySchemaError, match="schema_version"):
        parse_query_report(json.dumps(query_report(schema_version=2)))


def test_missing_key_and_unknown_outcome_are_schema_errors() -> None:
    broken = query_report()
    del broken["llm"]
    with pytest.raises(QuerySchemaError, match="llm"):
        parse_query_report(json.dumps(broken))
    with pytest.raises(QuerySchemaError, match="outcome"):
        parse_query_report(json.dumps(query_report(outcome="maybe")))


def test_answered_without_text_is_a_schema_error() -> None:
    with pytest.raises(QuerySchemaError, match="answer"):
        parse_query_report(json.dumps(query_report(answer=None)))


def test_all_failures_are_openkos_errors() -> None:
    for error in (QueryFailedError, QueryOutputError, QueryRejectedError, QuerySchemaError):
        assert issubclass(error, OpenKosError)


def _llm(**changes: object) -> str:
    base = query_report()["llm"]
    return json.dumps(query_report(llm={**base, **changes}))


def test_reproducible_report_passes() -> None:
    require_reproducible(parse_query_report(_llm()), expected_seed=42, expected_temperature=0.1)


@pytest.mark.parametrize("field", ["temperature", "seed"])
def test_null_temperature_or_seed_is_rejected(field: str) -> None:
    with pytest.raises(QueryRejectedError, match=field):
        require_reproducible(
            parse_query_report(_llm(**{field: None})), expected_seed=42, expected_temperature=0.1
        )


def test_unexpected_seed_is_rejected() -> None:
    with pytest.raises(QueryRejectedError, match="seed"):
        require_reproducible(
            parse_query_report(_llm(seed=43)), expected_seed=42, expected_temperature=0.1
        )


def test_withheld_outcome_or_count_is_rejected() -> None:
    withheld = parse_query_report(json.dumps(query_report(outcome="withheld", answer=None)))
    with pytest.raises(QueryRejectedError, match="withheld"):
        require_reproducible(withheld, expected_seed=42, expected_temperature=0.1)
    counted = parse_query_report(json.dumps(query_report(withheld=2)))
    with pytest.raises(QueryRejectedError, match="withheld"):
        require_reproducible(counted, expected_seed=42, expected_temperature=0.1)


def test_temperature_other_than_configured_is_rejected() -> None:
    with pytest.raises(QueryRejectedError, match="temperature"):
        require_reproducible(
            parse_query_report(_llm(temperature=0.7)), expected_seed=42, expected_temperature=0.1
        )


def test_temperature_is_compared_as_a_float_not_by_text() -> None:
    near = 0.1 + 1e-12
    require_reproducible(
        parse_query_report(_llm(temperature=near)), expected_seed=42, expected_temperature=0.1
    )
