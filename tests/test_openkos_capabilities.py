"""Tests for the OpenKOS capability probe."""

from __future__ import annotations

import pytest

from afg.extraction.openkos.capabilities import (
    Capabilities,
    MissingCapabilitiesError,
    parse_version,
    probe_capabilities,
    require_capabilities,
)
from tests.openkos_fake import FakeRunner


def test_parse_version_reads_the_openkos_banner() -> None:
    assert parse_version("openkos 0.6.0\n") == "0.6.0"
    assert parse_version("openkos 0.6.0rc1") == "0.6.0rc1"


def test_parse_version_returns_none_when_unrecognized() -> None:
    assert parse_version("") is None
    assert parse_version("something else entirely") is None


def test_probe_reports_capabilities_from_help_text() -> None:
    runner = FakeRunner()
    caps = probe_capabilities(runner, "openkos")
    assert caps == Capabilities(
        executable="openkos",
        version="0.6.0",
        ingest_auto=True,
        ingest_event_date=True,
        query_json=True,
    )
    assert runner.subcommands() == [("--version",), ("ingest", "--help"), ("query", "--help")]


def test_probe_uses_the_configured_executable() -> None:
    runner = FakeRunner()
    probe_capabilities(runner, "/opt/openkos/bin/openkos")
    assert all(argv[0] == "/opt/openkos/bin/openkos" for argv, _ in runner.calls)


def test_probe_detects_missing_flags() -> None:
    runner = FakeRunner(
        ingest_help="Usage: openkos ingest SOURCE\n  --auto\n",
        query_help="Usage: openkos query Q\n",
    )
    caps = probe_capabilities(runner, "openkos")
    assert caps.ingest_auto and not caps.ingest_event_date and not caps.query_json


def test_require_lists_every_missing_capability() -> None:
    caps = Capabilities(
        executable="openkos",
        version="0.5.2",
        ingest_auto=False,
        ingest_event_date=False,
        query_json=False,
    )
    with pytest.raises(MissingCapabilitiesError) as excinfo:
        require_capabilities(caps)
    assert excinfo.value.missing == ("ingest --auto", "query --json")
    assert "0.5.2" in str(excinfo.value)
    assert "ingest --auto" in str(excinfo.value)


def test_require_event_date_only_when_requested() -> None:
    caps = Capabilities(
        executable="openkos",
        version="0.6.0",
        ingest_auto=True,
        ingest_event_date=False,
        query_json=True,
    )
    require_capabilities(caps)
    with pytest.raises(MissingCapabilitiesError) as excinfo:
        require_capabilities(caps, need_event_date=True)
    assert excinfo.value.missing == ("ingest --event-date",)


def test_unparsable_version_is_recorded_as_unknown_not_assumed() -> None:
    runner = FakeRunner(version_output="garbled")
    caps = probe_capabilities(runner, "openkos")
    assert caps.version is None
    with pytest.raises(MissingCapabilitiesError) as excinfo:
        require_capabilities(caps)
    assert excinfo.value.missing == ("version",)


def test_missing_executable_is_a_clear_error() -> None:
    class _Absent:
        def run(self, args, *, cwd=None):  # type: ignore[no-untyped-def]
            raise FileNotFoundError(args[0])

    with pytest.raises(MissingCapabilitiesError) as excinfo:
        probe_capabilities(_Absent(), "nope")
    assert excinfo.value.missing == ("executable",)
