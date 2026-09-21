"""Tests for freezing rendered transcripts to disk (thesis sections 5.3/5.4).

Synthetic fixtures reuse the two-speaker, four-turn meeting built by
``tests/test_transcripts.py`` (module-local copy here to keep this file
self-contained); the dialogue-act overlap computation additionally gets a purpose-built
synthetic case where segmentations disagree (one segment spans two dialogue acts, one
dialogue act spans two segments). A handful of behaviours are additionally checked
against the real download at ``data/raw/ami/``, restricted to two meetings so the suite
stays fast.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.corpus.render import (
    discover_meeting_ids,
    parse_front_matter,
    render_meeting_artifacts,
    render_meetings,
    renderer_revision,
    sha256_of_file,
    split_meeting_id,
    write_meeting_artifacts,
)
from afg.shared.paths import AMI_DIR

_CORPUS_AVAILABLE = (AMI_DIR / "words" / "IS1004d.A.words.xml").exists()

requires_corpus = pytest.mark.skipif(
    not _CORPUS_AVAILABLE, reason="AMI corpus not downloaded at data/raw/ami/"
)

_NITE_NS = 'xmlns:nite="http://nite.sourceforge.net/"'


def _write_words_file(path: Path, body: str) -> None:
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_segments_file(path: Path, segments: list[tuple[float, float, str]]) -> None:
    body = "\n".join(
        f'<segment nite:id="seg.{i}" channel="0" transcriber_start="{start}" '
        f'transcriber_end="{end}">\n   <nite:child href="{href}"/>\n</segment>'
        for i, (start, end, href) in enumerate(segments)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_dialogue_acts_file(path: Path, acts: list[tuple[str, str]]) -> None:
    body = "\n".join(
        f'<dact nite:id="{act_id}">\n'
        f'   <nite:pointer role="da-aspect" href="da-types.xml#id(ami_da_1)"/>\n'
        f'   <nite:child href="{words_href}"/>\n'
        f"</dact>"
        for act_id, words_href in acts
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_meetings_file(path: Path, observation: str, speakers: list[tuple[str, str]]) -> None:
    """``speakers`` is a list of ``(nxt_agent, role_code)`` pairs."""
    speaker_els = "\n".join(
        f'      <speaker nite:id="{observation}_{i}" nxt_agent="{agent}" role="{role}" '
        f'global_name="P{i}"/>'
        for i, (agent, role) in enumerate(speakers)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n'
        f'   <meeting nite:id="meet_1" type="scenario" observation="{observation}">\n'
        f"{speaker_els}\n"
        f"   </meeting>\n</nite:root>\n"
    )


def _build_synthetic_meeting(ami_root: Path) -> None:
    """Two-speaker, four-turn synthetic meeting, mirroring the fixture used in
    ``tests/test_transcripts.py``."""
    (ami_root / "words").mkdir(parents=True, exist_ok=True)
    (ami_root / "segments").mkdir(parents=True, exist_ok=True)
    (ami_root / "dialogueActs").mkdir(parents=True, exist_ok=True)
    (ami_root / "corpusResources").mkdir(parents=True, exist_ok=True)

    _write_words_file(
        ami_root / "words" / "MEET1.A.words.xml",
        '<w nite:id="MEET1.A.words1" starttime="0.0" endtime="0.5">Hello</w>\n'
        '<w nite:id="MEET1.A.words2" starttime="0.5" endtime="1.0">everyone</w>\n'
        '<w nite:id="MEET1.A.words3" starttime="2.0" endtime="2.3">How</w>\n'
        '<w nite:id="MEET1.A.words4" starttime="2.3" endtime="2.6">are</w>\n'
        '<w nite:id="MEET1.A.words5" starttime="2.6" endtime="3.0">you</w>\n'
        '<w nite:id="MEET1.A.words6" starttime="3.0" endtime="3.0" punc="true">?</w>',
    )
    _write_words_file(
        ami_root / "words" / "MEET1.B.words.xml",
        '<w nite:id="MEET1.B.words1" starttime="1.0" endtime="1.3">Hi</w>\n'
        '<w nite:id="MEET1.B.words2" starttime="1.3" endtime="2.0">there</w>\n'
        '<w nite:id="MEET1.B.words3" starttime="3.0" endtime="3.3">Fine</w>\n'
        '<w nite:id="MEET1.B.words4" starttime="3.3" endtime="4.0">thanks</w>',
    )

    _write_segments_file(
        ami_root / "segments" / "MEET1.A.segments.xml",
        [
            (0.0, 1.0, "MEET1.A.words.xml#id(MEET1.A.words1)..id(MEET1.A.words2)"),
            (2.0, 3.0, "MEET1.A.words.xml#id(MEET1.A.words3)..id(MEET1.A.words6)"),
        ],
    )
    _write_segments_file(
        ami_root / "segments" / "MEET1.B.segments.xml",
        [
            (1.0, 2.0, "MEET1.B.words.xml#id(MEET1.B.words1)..id(MEET1.B.words2)"),
            (3.0, 4.0, "MEET1.B.words.xml#id(MEET1.B.words3)..id(MEET1.B.words4)"),
        ],
    )

    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / "MEET1.A.dialog-act.xml",
        [
            ("MEET1.A.dialog-act.1", "MEET1.A.words.xml#id(MEET1.A.words1)..id(MEET1.A.words2)"),
            ("MEET1.A.dialog-act.2", "MEET1.A.words.xml#id(MEET1.A.words3)..id(MEET1.A.words6)"),
        ],
    )
    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / "MEET1.B.dialog-act.xml",
        [
            ("MEET1.B.dialog-act.1", "MEET1.B.words.xml#id(MEET1.B.words1)..id(MEET1.B.words2)"),
            ("MEET1.B.dialog-act.2", "MEET1.B.words.xml#id(MEET1.B.words3)..id(MEET1.B.words4)"),
        ],
    )

    _write_meetings_file(
        ami_root / "corpusResources" / "meetings.xml",
        "MEET1",
        [("A", "PM"), ("B", "ME")],
    )


def _build_overlap_disagreement_meeting(ami_root: Path) -> None:
    """One speaker, five words. Segments (turn boundaries) and dialogue acts (analytic
    boundaries) disagree about where to cut: one segment spans two dialogue acts, and one
    dialogue act spans two segments -- the many-to-many case the manifest's
    ``dialogue_act_ids`` field exists for."""
    (ami_root / "words").mkdir(parents=True, exist_ok=True)
    (ami_root / "segments").mkdir(parents=True, exist_ok=True)
    (ami_root / "dialogueActs").mkdir(parents=True, exist_ok=True)
    (ami_root / "corpusResources").mkdir(parents=True, exist_ok=True)

    _write_words_file(
        ami_root / "words" / "OVER1.A.words.xml",
        '<w nite:id="OVER1.A.words1" starttime="0.0" endtime="0.5">One</w>\n'
        '<w nite:id="OVER1.A.words2" starttime="0.5" endtime="1.0">two</w>\n'
        '<w nite:id="OVER1.A.words3" starttime="1.0" endtime="1.5">three</w>\n'
        '<w nite:id="OVER1.A.words4" starttime="1.5" endtime="2.0">four</w>\n'
        '<w nite:id="OVER1.A.words5" starttime="2.0" endtime="2.5">five</w>',
    )

    # Segment 0 spans words 1..3 (covers dialogue acts 1 and 2, which split at word 2).
    # Segment 1 spans words 4..5 (covers dialogue act 2's tail and dialogue act 3).
    _write_segments_file(
        ami_root / "segments" / "OVER1.A.segments.xml",
        [
            (0.0, 1.5, "OVER1.A.words.xml#id(OVER1.A.words1)..id(OVER1.A.words3)"),
            (1.5, 2.5, "OVER1.A.words.xml#id(OVER1.A.words4)..id(OVER1.A.words5)"),
        ],
    )

    # Dialogue act 1: words 1..2. Dialogue act 2: words 3..4 (spans across the segment
    # boundary between segment 0 and segment 1). Dialogue act 3: word 5.
    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / "OVER1.A.dialog-act.xml",
        [
            ("OVER1.A.dialog-act.1", "OVER1.A.words.xml#id(OVER1.A.words1)..id(OVER1.A.words2)"),
            ("OVER1.A.dialog-act.2", "OVER1.A.words.xml#id(OVER1.A.words3)..id(OVER1.A.words4)"),
            ("OVER1.A.dialog-act.3", "OVER1.A.words.xml#id(OVER1.A.words5)"),
        ],
    )

    _write_meetings_file(
        ami_root / "corpusResources" / "meetings.xml",
        "OVER1",
        [("A", "PM")],
    )


def _build_words_segments_dialogue_acts(ami_root: Path, meeting_id: str) -> None:
    """Minimal one-word, one-speaker fixture for an arbitrary ``meeting_id`` -- used where
    the exact transcript content does not matter and only the meeting id's shape
    (series/letter splitting, discovery, filtering) is under test. Deliberately skips
    ``corpusResources/meetings.xml``: role labels are not exercised here and
    ``speaker_role_labels`` degrades to the ``nxt_agent`` letter by design."""
    (ami_root / "words").mkdir(parents=True, exist_ok=True)
    (ami_root / "segments").mkdir(parents=True, exist_ok=True)
    (ami_root / "dialogueActs").mkdir(parents=True, exist_ok=True)

    _write_words_file(
        ami_root / "words" / f"{meeting_id}.A.words.xml",
        f'<w nite:id="{meeting_id}.A.words1" starttime="0.0" endtime="0.5">Hello</w>',
    )
    _write_segments_file(
        ami_root / "segments" / f"{meeting_id}.A.segments.xml",
        [(0.0, 0.5, f"{meeting_id}.A.words.xml#id({meeting_id}.A.words1)")],
    )
    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / f"{meeting_id}.A.dialog-act.xml",
        [(f"{meeting_id}.A.dialog-act.1", f"{meeting_id}.A.words.xml#id({meeting_id}.A.words1)")],
    )


class TestRenderMeetingArtifacts:
    def test_front_matter_round_trips_expected_keys(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "MEET1", revision="deadbee")
        assert artifacts is not None
        fields, body = parse_front_matter(artifacts.markdown)
        assert fields["meeting_id"] == "MEET1"
        # "MEET1" does not match the real AMI id shape ([A-Z]{2}\d{4}[a-e]?) -- it
        # exercises split_meeting_id's graceful-degradation path: the whole id becomes its
        # own series and the letter is empty (see TestSplitMeetingId for the direct unit
        # tests of that function).
        assert fields["series"] == "MEET1"
        assert fields["letter"] == ""
        assert fields["renderer"] == "afg.corpus.render@deadbee"
        assert fields["speakers"] == {"A": "PM", "B": "ME"}
        assert fields["turns"] == "4"
        assert fields["characters"] == str(len(body))
        assert body == "PM: Hello everyone\n\nME: Hi there\n\nPM: How are you?\n\nME: Fine thanks"

    def test_label_has_no_markdown_emphasis(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "MEET1", revision="deadbee")
        assert artifacts is not None
        _, body = parse_front_matter(artifacts.markdown)
        assert "**PM:**" not in body
        assert "PM: Hello everyone" in body

    def test_char_offsets_round_trip_to_text_for_every_turn(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "MEET1", revision="deadbee")
        assert artifacts is not None
        _, body = parse_front_matter(artifacts.markdown)
        assert len(artifacts.jsonl_lines) == 4
        for line in artifacts.jsonl_lines:
            record = json.loads(line)
            assert body[record["char_start"] : record["char_end"]] == record["text"]

    def test_missing_meeting_returns_none(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        assert render_meeting_artifacts(tmp_path, "DOES-NOT-EXIST", revision="deadbee") is None

    def test_front_matter_keeps_letter_key_empty_when_no_session_letter(
        self, tmp_path: Path
    ) -> None:
        """A real AMI shape with no session letter (e.g. IB4001) still gets a ``letter:``
        front-matter key, just with an empty value -- parsing stays uniform."""
        _build_words_segments_dialogue_acts(tmp_path, "IB4001")
        artifacts = render_meeting_artifacts(tmp_path, "IB4001", revision="deadbee")
        assert artifacts is not None
        fields, _ = parse_front_matter(artifacts.markdown)
        assert fields["series"] == "IB4001"
        assert fields["letter"] == ""
        assert "letter:" in artifacts.markdown


class TestDialogueActOverlap:
    """One segment spans two dialogue acts; one dialogue act spans two segments."""

    def test_first_segment_overlaps_first_two_dialogue_acts(self, tmp_path: Path) -> None:
        _build_overlap_disagreement_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "OVER1", revision="deadbee")
        assert artifacts is not None
        records = [json.loads(line) for line in artifacts.jsonl_lines]
        assert records[0]["text"] == "One two three"
        assert records[0]["dialogue_act_ids"] == [
            "OVER1.A.dialog-act.1",
            "OVER1.A.dialog-act.2",
        ]

    def test_second_segment_overlaps_last_two_dialogue_acts(self, tmp_path: Path) -> None:
        _build_overlap_disagreement_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "OVER1", revision="deadbee")
        assert artifacts is not None
        records = [json.loads(line) for line in artifacts.jsonl_lines]
        assert records[1]["text"] == "four five"
        assert records[1]["dialogue_act_ids"] == [
            "OVER1.A.dialog-act.2",
            "OVER1.A.dialog-act.3",
        ]


class TestDeterminism:
    def test_two_renders_of_the_same_corpus_are_byte_identical(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        out_a = tmp_path / "out_a"
        out_b = tmp_path / "out_b"
        result_a = render_meetings(tmp_path, ["MEET1"], out_a, manifest_dir=tmp_path / "reports_a")
        result_b = render_meetings(tmp_path, ["MEET1"], out_b, manifest_dir=tmp_path / "reports_b")

        assert (out_a / "MEET1.md").read_bytes() == (out_b / "MEET1.md").read_bytes()
        assert (out_a / "MEET1.jsonl").read_bytes() == (out_b / "MEET1.jsonl").read_bytes()
        assert result_a.total_turns == result_b.total_turns
        assert result_a.total_characters == result_b.total_characters
        assert (
            result_a.manifest_path.read_text().splitlines()[1]
            == result_b.manifest_path.read_text().splitlines()[1]
        )


class TestRenderMeetings:
    def test_writes_md_and_jsonl_per_meeting(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        out_dir = tmp_path / "out"
        result = render_meetings(tmp_path, ["MEET1"], out_dir, manifest_dir=tmp_path / "reports")
        assert (out_dir / "MEET1.md").exists()
        assert (out_dir / "MEET1.jsonl").exists()
        assert result.total_turns == 4
        assert result.meeting_ids == ("MEET1",)

    def test_manifest_has_one_row_per_rendered_meeting_with_matching_hashes(
        self, tmp_path: Path
    ) -> None:
        _build_synthetic_meeting(tmp_path)
        out_dir = tmp_path / "out"
        manifest_dir = tmp_path / "reports"
        result = render_meetings(tmp_path, ["MEET1"], out_dir, manifest_dir=manifest_dir)

        manifest_lines = result.manifest_path.read_text().splitlines()
        assert len(manifest_lines) == 2  # header + 1 row

        header = manifest_lines[0].split(",")
        row = manifest_lines[1].split(",")
        row_dict = dict(zip(header, row, strict=True))
        assert row_dict["meeting_id"] == "MEET1"
        assert row_dict["sha256_md"] == sha256_of_file(out_dir / "MEET1.md")
        assert row_dict["sha256_jsonl"] == sha256_of_file(out_dir / "MEET1.jsonl")

    def test_meeting_with_no_renderable_turns_is_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "words").mkdir(parents=True)
        (tmp_path / "words" / "EMPTY.A.words.xml").write_text(
            f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
            f'<nite:root nite:id="root" {_NITE_NS}></nite:root>\n'
        )
        out_dir = tmp_path / "out"
        result = render_meetings(tmp_path, ["EMPTY"], out_dir, manifest_dir=tmp_path / "reports")
        assert result.meeting_ids == ()
        assert result.total_turns == 0


class TestDiscoverMeetingIds:
    def test_discovers_every_meeting_under_words(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        assert discover_meeting_ids(tmp_path) == ["MEET1"]

    def test_filters_by_series(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        assert discover_meeting_ids(tmp_path, series_filter=["OTHER"]) == []
        # "MEET1" has no session letter under the real AMI id shape, so it is its own
        # series (see split_meeting_id) -- filtering by "MEET" (the old, wrong,
        # meeting_id[:-1] series) must NOT match it.
        assert discover_meeting_ids(tmp_path, series_filter=["MEET"]) == []
        assert discover_meeting_ids(tmp_path, series_filter=["MEET1"]) == ["MEET1"]


class TestSplitMeetingId:
    @pytest.mark.parametrize(
        ("meeting_id", "expected"),
        [
            ("ES2002a", ("ES2002", "a")),
            ("IS1004d", ("IS1004", "d")),
            ("EN2001a", ("EN2001", "a")),
            ("TS3005a", ("TS3005", "a")),
            ("IB4001", ("IB4001", "")),
            ("IB4010", ("IB4010", "")),
            ("IN1001", ("IN1001", "")),
        ],
    )
    def test_splits_real_ami_id_shapes(self, meeting_id: str, expected: tuple[str, str]) -> None:
        assert split_meeting_id(meeting_id) == expected

    def test_malformed_id_degrades_without_raising(self) -> None:
        assert split_meeting_id("not-a-real-meeting-id") == ("not-a-real-meeting-id", "")

    def test_empty_id_degrades_without_raising(self) -> None:
        assert split_meeting_id("") == ("", "")


class TestIbSeriesRegression:
    """Regression guard for the exact damage found in the committed manifest: the naive
    ``meeting_id[:-1]``/``meeting_id[-1]`` split shredded IB4001..IB4005 into a fabricated
    series "IB400" and merged IB4010 into that same fabricated series, because both
    truncate to "IB400"."""

    def test_ib4010_is_not_grouped_with_ib4001(self, tmp_path: Path) -> None:
        _build_words_segments_dialogue_acts(tmp_path, "IB4001")
        _build_words_segments_dialogue_acts(tmp_path, "IB4010")

        artifacts_4001 = render_meeting_artifacts(tmp_path, "IB4001", revision="deadbee")
        artifacts_4010 = render_meeting_artifacts(tmp_path, "IB4010", revision="deadbee")

        assert artifacts_4001 is not None
        assert artifacts_4010 is not None
        assert artifacts_4001.series == "IB4001"
        assert artifacts_4010.series == "IB4010"
        assert artifacts_4001.series != artifacts_4010.series

    def test_series_filter_selects_ib4001_only(self, tmp_path: Path) -> None:
        _build_words_segments_dialogue_acts(tmp_path, "IB4001")
        _build_words_segments_dialogue_acts(tmp_path, "IB4010")

        assert discover_meeting_ids(tmp_path, series_filter=["IB4001"]) == ["IB4001"]


class TestRendererRevision:
    def test_degrades_to_unknown_when_git_is_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise OSError("git not found")

        monkeypatch.setattr("afg.corpus.render.subprocess.run", _raise)
        assert renderer_revision() == "unknown"

    def test_returns_a_short_hash_when_git_succeeds(self) -> None:
        revision = renderer_revision()
        assert revision != ""

    def test_dirty_check_is_scoped_to_the_rendering_source_paths(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A regression guard for the provenance field's meaning.

        An unscoped ``git status --porcelain`` also reports untracked and unrelated files,
        so the manifest would mark every render after the first one ``-dirty`` just because
        the previous render rewrote the manifest. The field answers "which code produced
        this text", so the status call must be limited to the rendering sources.
        """
        seen: list[list[str]] = []

        def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            stdout = "deadbee\n" if "log" in cmd else ""
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

        monkeypatch.setattr("afg.corpus.render.subprocess.run", _fake_run)
        assert renderer_revision() == "deadbee"

        for verb in ("log", "status"):
            cmd = next(c for c in seen if verb in c)
            assert "--" in cmd, f"the {verb} call must be path-scoped"
            scoped = cmd[cmd.index("--") + 1 :]
            assert scoped, f"the {verb} call must name the paths it checks"
            assert all(path.startswith("src/afg/") for path in scoped)

    def test_revision_is_the_last_render_source_commit_not_head(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stamping HEAD is circular: committing the manifest moves HEAD, which rewrites
        the front matter, which changes every sha256_md in that same manifest."""
        seen: list[list[str]] = []

        def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbee\n", stderr="")

        monkeypatch.setattr("afg.corpus.render.subprocess.run", _fake_run)
        renderer_revision()
        assert not any("rev-parse" in cmd for cmd in seen)
        assert any("log" in cmd for cmd in seen)

    def test_pins_an_explicit_abbrev_length(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """core.abbrev defaults to "auto" and scales the hash length with the repository's
        object count. Without an explicit --abbrev, the same commit would stamp a longer
        hash once the repo crosses that threshold, changing every renderer: front-matter
        line -- and therefore every sha256_md -- with no code or corpus change."""
        seen: list[list[str]] = []

        def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            seen.append(cmd)
            stdout = "deadbeefcafe\n" if "log" in cmd else ""
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

        monkeypatch.setattr("afg.corpus.render.subprocess.run", _fake_run)
        assert renderer_revision() == "deadbeefcafe"

        log_cmd = next(c for c in seen if "log" in c)
        assert "--abbrev=12" in log_cmd


class TestManifestLineEndings:
    def test_manifest_is_written_with_lf_not_crlf(self, tmp_path: Path) -> None:
        """csv.writer defaults to CRLF; git normalizes it to LF on commit, so the file on
        disk would never match the one checked out and every render would show a spurious
        diff -- destroying the very reproducibility evidence the manifest provides."""
        _build_synthetic_meeting(tmp_path)
        result = render_meetings(
            tmp_path, ["MEET1"], tmp_path / "out", manifest_dir=tmp_path / "tables"
        )
        raw = result.manifest_path.read_bytes()
        assert b"\r\n" not in raw
        assert raw.count(b"\n") == 2  # header + 1 row


class TestManifestMerge:
    """A filtered render merges into whatever manifest already exists at the target
    location rather than replacing it wholesale -- the exact defect that let a
    ``--series`` render silently truncate a 171-row manifest down to a handful."""

    def test_second_render_of_one_meeting_preserves_the_other_meetings_row(
        self, tmp_path: Path
    ) -> None:
        ami_root = tmp_path / "ami"
        _build_synthetic_meeting(ami_root)
        _build_words_segments_dialogue_acts(ami_root, "IB4001")

        out_dir = tmp_path / "out"
        manifest_dir = tmp_path / "reports"

        first = render_meetings(ami_root, ["MEET1", "IB4001"], out_dir, manifest_dir=manifest_dir)
        first_rows = {
            line.split(",")[0]: line for line in first.manifest_path.read_text().splitlines()[1:]
        }
        assert set(first_rows) == {"MEET1", "IB4001"}

        # Render ONLY IB4001 again, into the same location.
        second = render_meetings(ami_root, ["IB4001"], out_dir, manifest_dir=manifest_dir)
        second_rows = {
            line.split(",")[0]: line for line in second.manifest_path.read_text().splitlines()[1:]
        }

        assert set(second_rows) == {"MEET1", "IB4001"}
        # MEET1 was NOT rendered this time -- its row must survive verbatim, not vanish.
        assert second_rows["MEET1"] == first_rows["MEET1"]
        # IB4001 WAS rendered this time -- its row comes from this invocation.
        assert "IB4001" in second_rows


class TestWriteMeetingArtifacts:
    def test_force_refusal_is_a_caller_concern_not_a_write_error(self, tmp_path: Path) -> None:
        """write_meeting_artifacts always writes; --force refusal is enforced by the CLI
        layer against the output directory, exercised in TestCliForceRefusal below."""
        _build_synthetic_meeting(tmp_path)
        artifacts = render_meeting_artifacts(tmp_path, "MEET1", revision="deadbee")
        assert artifacts is not None
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        md_path, jsonl_path = write_meeting_artifacts(artifacts, out_dir)
        assert md_path.exists()
        assert jsonl_path.exists()


class TestCliForceRefusal:
    """``afg corpus transcripts`` must refuse to overwrite a non-empty output directory
    without --force -- transcripts are meant to be frozen before annotation starts."""

    def test_refuses_a_non_empty_output_dir_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ami_root = tmp_path / "ami"
        _build_synthetic_meeting(ami_root)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "stale.md").write_text("leftover from a previous freeze")

        monkeypatch.setattr(afg_cli, "AMI_DIR", ami_root)
        runner = CliRunner()
        result = runner.invoke(afg_cli.app, ["corpus", "transcripts", "--out", str(out_dir)])

        assert result.exit_code == 1
        assert (out_dir / "stale.md").read_text() == "leftover from a previous freeze"
        assert not (out_dir / "MEET1.md").exists()

    def test_force_overwrites_a_non_empty_output_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ami_root = tmp_path / "ami"
        _build_synthetic_meeting(ami_root)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "stale.md").write_text("leftover from a previous freeze")

        monkeypatch.setattr(afg_cli, "AMI_DIR", ami_root)
        monkeypatch.setattr(afg_cli, "TABLES_DIR", tmp_path / "reports")
        runner = CliRunner()
        result = runner.invoke(
            afg_cli.app, ["corpus", "transcripts", "--out", str(out_dir), "--force"]
        )

        assert result.exit_code == 0, result.output
        assert (out_dir / "MEET1.md").exists()


class TestCliScratchManifestIsolation:
    """A render to a non-canonical --out must not touch the tracked manifest at all
    (Finding 2, rule 1) -- only a render into the canonical transcripts directory may
    write reports/tables/transcripts_manifest.csv."""

    def test_custom_out_does_not_touch_the_tracked_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ami_root = tmp_path / "ami"
        _build_synthetic_meeting(ami_root)

        tracked_tables_dir = tmp_path / "reports"
        tracked_tables_dir.mkdir()
        tracked_manifest = tracked_tables_dir / "transcripts_manifest.csv"
        tracked_manifest.write_text("sentinel: must stay untouched\n")

        out_dir = tmp_path / "scratch"

        monkeypatch.setattr(afg_cli, "AMI_DIR", ami_root)
        monkeypatch.setattr(afg_cli, "TABLES_DIR", tracked_tables_dir)
        runner = CliRunner()
        result = runner.invoke(
            afg_cli.app, ["corpus", "transcripts", "--out", str(out_dir), "--force"]
        )

        assert result.exit_code == 0, result.output
        assert tracked_manifest.read_text() == "sentinel: must stay untouched\n"
        assert (out_dir / "transcripts_manifest.csv").exists()


@requires_corpus
class TestCorpusBackedRendering:
    """Regression tests against the real download, restricted to two meetings so the
    suite stays fast."""

    def test_renders_two_real_meetings(self, tmp_path: Path) -> None:
        result = render_meetings(
            AMI_DIR,
            ["IS1004d", "ES2015a"],
            tmp_path / "out",
            manifest_dir=tmp_path / "reports",
        )
        assert result.meeting_ids == ("ES2015a", "IS1004d")
        assert result.total_turns > 0

    def test_dialogue_act_ids_reference_real_summlink_style_ids(self, tmp_path: Path) -> None:
        result = render_meetings(
            AMI_DIR, ["IS1004d"], tmp_path / "out", manifest_dir=tmp_path / "reports"
        )
        assert result.total_turns > 0
        jsonl_path = tmp_path / "out" / "IS1004d.jsonl"
        found_nonempty = False
        for line in jsonl_path.read_text().splitlines():
            record = json.loads(line)
            if record["dialogue_act_ids"]:
                found_nonempty = True
                assert all("IS1004d" in act_id for act_id in record["dialogue_act_ids"])
        assert found_nonempty
