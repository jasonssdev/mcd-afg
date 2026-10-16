"""Tests for the reader of the non-decision concepts of an OpenKOS bundle.

Fixtures copy the layout of a real v0.5.5 bundle: concepts, events, projects and people carry
``provenance: [sources/<meeting>]`` and, after ``# title`` and the description, verbatim
``ROLE: text`` transcript turns separated by blank lines; ``sources/`` holds whole transcripts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.domain.decision import EvidenceSpan
from afg.extraction.openkos.bundle_reader import BundleFormatError, read_concept_bundle
from tests.openkos_bundle import concept_file, source_file, write_bundle_file, write_meeting

MEETINGS = ("ES2015a", "ES2015b", "ES2015c", "ES2015d")


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    write_meeting(
        directory,
        "ES2015a",
        [
            ("PM", "Welcome everybody.", ("a.1",)),
            ("UI", "I like the elk, really.", ("a.2", "a.3")),
            ("ID", "Mm.", ("a.4",)),
            ("PM", "Let us start the design.", ("a.5",)),
        ],
    )
    write_meeting(
        directory,
        "ES2015b",
        [
            ("PM", "Welcome back.", ("b.1",)),
            ("ME", "Think about young adults.", ("b.2",)),
            ("ID", "Mm.", ("b.3",)),
            ("UI", "Voice control is costly.", ("b.4", "b.5")),
            ("ID", "Mm.", ("b.6",)),
        ],
    )
    for meeting in ("ES2015c", "ES2015d"):
        write_meeting(directory, meeting, [("PM", "Nothing.", (f"{meeting}.1",))])
    return directory


def read(bundle: Path, transcripts: Path):  # type: ignore[no-untyped-def]
    return read_concept_bundle(bundle, meeting_ids=MEETINGS, transcripts_dir=transcripts)


def test_located_excerpt_becomes_a_span_with_the_union_of_dialogue_acts(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="Design ideas",
        description="A talk about ideas.",
        turns=["ME: Think about young adults.", "ID: Mm.", "UI: Voice control is costly."],
        provenance=["es2015b"],
    )
    write_bundle_file(bundle, "concepts", "design-ideas", text)
    result = read(bundle, transcripts)
    assert result.spans == {
        "concepts/design-ideas": (
            EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=("b.2", "b.3", "b.4", "b.5")),
        )
    }
    assert result.unmapped == ()
    assert result.excerpts.found == 1 and result.excerpts.not_found == 0


@pytest.mark.parametrize(
    ("folder", "type_"),
    [("events", "Event"), ("projects", "Project"), ("people", "Person"), ("concepts", "Concept")],
)
def test_every_non_decision_non_source_folder_is_read(
    tmp_path: Path, transcripts: Path, folder: str, type_: str
) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="T",
        description="D.",
        turns=["UI: I like the elk, really."],
        provenance=["es2015a"],
        type_=type_,
    )
    write_bundle_file(bundle, folder, "thing", text)
    result = read(bundle, transcripts)
    assert result.spans[f"{folder}/thing"] == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.2", "a.3")),
    )


def test_one_span_per_meeting_when_provenance_names_several(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="Both",
        description="Spans two meetings.",
        turns=["UI: I like the elk, really.", "UI: Voice control is costly."],
        provenance=["es2015a", "es2015b"],
    )
    write_bundle_file(bundle, "concepts", "both", text)
    result = read(bundle, transcripts)
    assert result.spans["concepts/both"] == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.2", "a.3")),
        EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=("b.4", "b.5")),
    )


def test_discontiguous_excerpts_fall_back_to_each_turn(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="Gaps",
        description="Not a contiguous window.",
        turns=["PM: Welcome everybody.", "PM: Let us start the design."],
        provenance=["es2015a"],
    )
    write_bundle_file(bundle, "concepts", "gaps", text)
    result = read(bundle, transcripts)
    assert result.spans["concepts/gaps"] == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.1", "a.5")),
    )
    assert result.excerpts.found == 2


def test_ambiguous_turn_is_not_assigned_to_the_first_occurrence(
    tmp_path: Path, transcripts: Path
) -> None:
    """``ID: Mm.`` is said twice in the meeting: never guess among occurrences."""
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="Gaps",
        description="One locatable turn and one ambiguous.",
        turns=["PM: Welcome back.", "ID: Mm.", "PM: Not in the transcript at all."],
        provenance=["es2015b"],
    )
    write_bundle_file(bundle, "concepts", "gaps", text)
    result = read(bundle, transcripts)
    assert result.spans["concepts/gaps"] == (
        EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=("b.1",)),
    )
    assert result.excerpts.found == 1
    assert result.excerpts.not_found == 1


def test_unlocatable_excerpts_are_counted_and_the_concept_is_unmapped(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="Lost",
        description="Nothing matches.",
        turns=["PM: A sentence that nobody said."],
        provenance=["es2015a"],
    )
    write_bundle_file(bundle, "events", "lost", text)
    result = read(bundle, transcripts)
    assert result.spans == {}
    assert [(u.concept_id, u.reasons) for u in result.unmapped] == [("events/lost", ("not_found",))]
    assert result.excerpts.total == 1 and result.excerpts.not_found == 1


def test_concept_without_excerpt_is_unmapped_with_a_reason(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(title="Bare", description="No turns.", turns=[], provenance=["es2015a"])
    write_bundle_file(bundle, "concepts", "bare", text)
    result = read(bundle, transcripts)
    assert [(u.concept_id, u.reasons) for u in result.unmapped] == [
        ("concepts/bare", ("no_excerpt",))
    ]


def test_sources_and_decisions_are_not_read(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    write_bundle_file(
        bundle, "sources", "es2015a", source_file("es2015a", "PM: Welcome everybody.")
    )
    write_bundle_file(
        bundle,
        "decisions",
        "d",
        concept_file(
            title="D",
            description="s: v",
            turns=["PM: Welcome everybody."],
            provenance=["es2015a"],
            type_="Decision",
        ),
    )
    result = read(bundle, transcripts)
    assert result.spans == {} and result.unmapped == () and result.excerpts.total == 0


def test_provenance_outside_the_series_is_a_format_error(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    text = concept_file(
        title="X", description="D.", turns=["PM: Welcome everybody."], provenance=["en2001a"]
    )
    write_bundle_file(bundle, "concepts", "x", text)
    with pytest.raises(BundleFormatError, match="not a meeting of the series"):
        read(bundle, transcripts)


def test_missing_folders_give_an_empty_result(tmp_path: Path, transcripts: Path) -> None:
    (tmp_path / "bundle").mkdir()
    result = read(tmp_path / "bundle", transcripts)
    assert result.spans == {} and result.unmapped == ()
