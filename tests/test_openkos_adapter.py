"""Tests for ``OpenKosAdapter.extract_series`` (scripted OpenKOS, no network)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.domain.decision import DecisionStatus
from afg.extraction.openkos.bundle_reader import QuoteCounts
from afg.extraction.openkos.commands import CommandResult
from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.extraction.openkos_adapter import OpenKosAdapter, SeriesExtraction
from afg.extraction.protocol import ExtractionResult
from afg.shared.paths import PROJECT_ROOT
from tests.openkos_bundle import decision_file, write_decision, write_meeting
from tests.openkos_fake import FakeRunner

SETTINGS = OpenKosRunSettings(
    executable="openkos",
    generative_model="qwen3:8b",
    embedding_model="bge-m3",
    base_seed=42,
    temperature=0.1,
)
VALUE = "The remote control will use a kinetic battery, not a solar one."


class BundleWritingRunner(FakeRunner):
    """A FakeRunner whose ingest of the last meeting leaves a bundle behind, like OpenKOS."""

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        result = super().run(args, cwd=cwd)
        if args[1:2] == ["ingest"] and Path(args[2]).name == "ES2015d.md" and cwd is not None:
            write_decision(
                cwd / "bundle",
                "kinetic",
                decision_file(
                    title=VALUE.rstrip("."),
                    subject="remote control battery",
                    value=VALUE,
                    quotes=[
                        ("es2015a", "going with the kinetic battery"),
                        ("es2015d", "so kinetic it is"),
                    ],
                ),
            )
        return result


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    write_meeting(
        directory, "ES2015a", [("ID", "We're going with the kinetic battery.", ("a1", "a2"))]
    )
    write_meeting(directory, "ES2015b", [("PM", "Nothing.", ("b1",))])
    write_meeting(directory, "ES2015c", [("PM", "Nothing.", ("c1",))])
    write_meeting(directory, "ES2015d", [("PM", "So kinetic it is.", ("d1",))])
    return directory


def _adapter(tmp_path: Path, transcripts: Path, runner: FakeRunner, **kw) -> OpenKosAdapter:  # type: ignore[no-untyped-def]
    return OpenKosAdapter(
        runner=runner,
        settings=SETTINGS,
        base_dir=tmp_path / "ws",
        transcripts_dir=transcripts,
        **kw,
    )


def test_extract_series_returns_the_decisions_of_the_compiled_bundle(
    tmp_path: Path, transcripts: Path
) -> None:
    runner = BundleWritingRunner()
    extraction = _adapter(tmp_path, transcripts, runner).extract_series("ES2015", run=1)

    assert isinstance(extraction.result, ExtractionResult)
    [decision] = extraction.result.decisions
    assert decision.series_id == "ES2015"
    assert decision.origin_meeting_ids == ("ES2015a", "ES2015d")
    assert decision.status is DecisionStatus.ACCEPTED
    assert extraction.result.relations == ()
    assert extraction.series_id == "ES2015"
    assert extraction.run == 1
    assert extraction.openkos_version == "0.6.0"
    assert extraction.quotes.total == 2
    assert extraction.quotes.found == 2
    assert extraction.unmapped == ()
    assert extraction.workspace == tmp_path / "ws" / "ES2015" / "run-1"
    assert json.loads(extraction.manifest_path.read_text())["status"] == "ok"


def test_adapter_only_talks_to_openkos_through_the_injected_runner(
    tmp_path: Path, transcripts: Path
) -> None:
    runner = BundleWritingRunner()
    _adapter(tmp_path, transcripts, runner).extract_series("ES2015", run=0)

    assert {argv[0] for argv, _ in runner.calls} == {"openkos"}
    ingested = [
        Path(argv[2]).name
        for argv, _ in runner.calls
        if argv[1:2] == ("ingest",) and argv[2] != "--help"
    ]
    assert ingested == ["ES2015a.md", "ES2015b.md", "ES2015c.md", "ES2015d.md"]
    # ingestion reads the body staged outside the workspace, never the frozen transcript
    staged = [Path(a[2]) for a, _ in runner.calls if a[1:2] == ("ingest",) and a[2] != "--help"]
    assert all(path.parent == tmp_path / "ws" / "ES2015" / "run-0.sources" for path in staged)
    assert not staged[0].read_text().startswith("---")


def test_event_dates_are_passed_when_meetings_xml_is_given(
    tmp_path: Path, transcripts: Path
) -> None:
    xml = tmp_path / "meetings.xml"
    rows = "".join(
        f'<meeting observation="ES2015{letter}" dateOnly="{day}-11-2004"/>'
        for letter, day in zip("abcd", ("23", "24", "25", "26"), strict=True)
    )
    xml.write_text(f'<?xml version="1.0"?><meetings>{rows}</meetings>', encoding="utf-8")
    runner = BundleWritingRunner()

    _adapter(tmp_path, transcripts, runner, meetings_xml=xml).extract_series("ES2015", run=0)

    dates = [
        argv[argv.index("--event-date") + 1]
        for argv, _ in runner.calls
        if argv[1:2] == ("ingest",) and argv[2] != "--help"
    ]
    assert dates == [
        "2004-11-23T09:00",
        "2004-11-24T10:00",
        "2004-11-25T11:00",
        "2004-11-26T12:00",
    ]


def test_no_event_dates_without_meetings_xml(tmp_path: Path, transcripts: Path) -> None:
    runner = BundleWritingRunner()
    _adapter(tmp_path, transcripts, runner).extract_series("ES2015", run=0)
    assert all("--event-date" not in argv for argv, _ in runner.calls)


def test_a_series_without_a_frozen_meeting_is_refused_before_any_command(
    tmp_path: Path, transcripts: Path
) -> None:
    (transcripts / "ES2015c.md").unlink()
    runner = BundleWritingRunner()
    with pytest.raises(FileNotFoundError, match="ES2015c"):
        _adapter(tmp_path, transcripts, runner).extract_series("ES2015", run=0)
    assert runner.calls == []


def test_a_bundle_without_decisions_gives_an_empty_result(
    tmp_path: Path, transcripts: Path
) -> None:
    extraction = _adapter(tmp_path, transcripts, FakeRunner()).extract_series("ES2015", run=0)
    assert extraction.result.decisions == ()
    assert extraction.quotes.total == 0


def test_the_per_meeting_extractor_entry_point_explains_why_it_is_not_supported(
    tmp_path: Path, transcripts: Path
) -> None:
    adapter = _adapter(tmp_path, transcripts, FakeRunner())
    with pytest.raises(NotImplementedError, match="extract_series"):
        adapter.extract("ES2015a", "text")


def _extraction_at(workspace: Path, manifest: Path) -> SeriesExtraction:
    return SeriesExtraction(
        series_id="ES2015",
        run=0,
        result=ExtractionResult(decisions=()),
        openkos_version="0.5.5",
        workspace=workspace,
        manifest_path=manifest,
        quotes=QuoteCounts(),
        unmapped=(),
    )


def test_to_record_paths_are_relative_to_the_project_root() -> None:
    workspace = PROJECT_ROOT / "data" / "interim" / "openkos" / "ES2015" / "run-0"
    record = _extraction_at(workspace, workspace.parent / "run-0.manifest.json").to_record()

    assert record["workspace"] == "data/interim/openkos/ES2015/run-0"
    assert record["manifest"] == "data/interim/openkos/ES2015/run-0.manifest.json"


def test_to_record_keeps_paths_outside_the_project_root_as_given(tmp_path: Path) -> None:
    record = _extraction_at(tmp_path / "ws", tmp_path / "m.json").to_record()

    assert record["workspace"] == str(tmp_path / "ws")
    assert record["manifest"] == str(tmp_path / "m.json")
