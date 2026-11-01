"""Tests for the C3 builder: a C2 workspace with its decisions replaced by the gold reference."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from afg.domain.decision import EvidenceSpan
from afg.evaluation.reference import ReferenceDecision, ReferenceSet
from afg.extraction.openkos.bundle_reader import read_decision_bundle
from afg.extraction.openkos.gold_bundle import (
    GOLD_GENERATOR,
    GoldRelation,
    GoldWorkspaceExistsError,
    build_gold_workspace,
    load_gold_relations,
)
from afg.extraction.openkos.workspace import OpenKosCommandError
from afg.extraction.openkos_adapter import BUNDLE_DIRNAME
from tests.openkos_bundle import concept_file, decision_file, write_bundle_file, write_meeting
from tests.openkos_fake import FakeRunner

MEETINGS = ("ES2015a", "ES2015b", "ES2015c", "ES2015d")
INDEX = (
    "---\nokf_version: '0.2'\n---\n\n# Concepts\n\n"
    "* [Elks](/concepts/elks.md) - About elks.\n\n"
    "# Decisions\n\n* [Old](/decisions/old.md) - old: Old one\n\n"
    "# Directory Update Log\n\n## 2026-10-27\n\n* **Ingest**: Extracted.\n"
)


def _reference(
    decision_id: str,
    meeting: str,
    acts: tuple[str, ...] | None,
    *,
    obj: str = "battery",
    content: str = "use a kinetic battery",
) -> ReferenceDecision:
    return ReferenceDecision(
        decision_id=decision_id,
        series_id="ES2015",
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=acts) if acts else None,
        evidence_method="sentence_id" if acts else "none",
        role=None,
    )


@pytest.fixture
def env(tmp_path: Path) -> dict[str, Path]:
    transcripts = tmp_path / "transcripts"
    write_meeting(
        transcripts,
        "ES2015a",
        [
            ("PM", "Hello.", ("a.1",)),
            ("ME", "we're going with the kinetic battery today", ("a.2", "a.3")),
            ("UI", "Elks have big antlers.", ("a.4",)),
            ("PM", "Fine.", ("a.5",)),
            ("ME", "Mm-hmm.", ("a.6",)),
            ("ME", "Mm-hmm.", ("a.7",)),
        ],
    )
    write_meeting(transcripts, "ES2015b", [("PM", "Agreed on the battery.", ("b.1",))])
    for meeting in MEETINGS[2:]:
        write_meeting(transcripts, meeting, [("PM", "Nothing here.", (f"{meeting}.1",))])
    c2 = tmp_path / "c2" / "run-compiled" / "ES2015" / "run-1"
    bundle = c2 / "bundle"
    write_bundle_file(
        bundle,
        "decisions",
        "old",
        decision_file(title="Old", subject="old", value="Old one", quotes=[("es2015a", "Hello.")]),
    )
    write_bundle_file(
        bundle,
        "concepts",
        "elks",
        concept_file(
            title="Elks",
            description="About elks.",
            turns=["UI: Elks have big antlers."],
            provenance=["es2015a"],
        ),
    )
    (bundle / "sources").mkdir()
    (bundle / "sources" / "es2015a.md").write_text("source a\n", encoding="utf-8")
    (bundle / "index.md").write_text(INDEX, encoding="utf-8")
    (c2 / "openkos.yaml").write_text("model: qwen3:8b\nseed: 43\ntemperature: 0.1\n")
    (c2 / "raw").mkdir()
    (c2 / "raw" / "ES2015a.md").write_text("raw a\n", encoding="utf-8")
    (c2 / ".openkos").mkdir()
    (c2 / ".openkos" / "fts.db").write_text("stale index", encoding="utf-8")
    return {"transcripts": transcripts, "c2": c2, "target": tmp_path / "c3" / "ES2015" / "run-1"}


def _reference_set() -> ReferenceSet:
    return ReferenceSet(
        series_id="ES2015",
        decisions=(
            _reference("ES2015a.d01", "ES2015a", ("a.2", "a.3")),
            _reference("ES2015a.d02", "ES2015a", ("a.4", "a.5"), obj="elks", content="no elks"),
            _reference("ES2015b.d01", "ES2015b", ("b.1",), content="kinetic battery agreed"),
            _reference("ES2015b.d02", "ES2015b", None),
            _reference("ES2015a.d03", "ES2015a", ("zz.9",)),
            _reference("ES2015a.d04", "ES2015a", ("a.4", "a.6"), obj="split"),
        ),
    )


RELATIONS = (
    GoldRelation("ES2015a.d01", "ES2015b.d01", "reafirma"),
    GoldRelation("ES2015a.d02", "ES2015b.d02", "refina"),
)


def _build(env: dict[str, Path], runner: FakeRunner | None = None, **kwargs):  # type: ignore[no-untyped-def]
    return build_gold_workspace(
        series_id="ES2015",
        c2_run="compiled",
        run=1,
        c2_workspace=env["c2"],
        target=env["target"],
        reference=_reference_set(),
        relations=RELATIONS,
        runner=runner or FakeRunner(),
        executable="openkos",
        transcripts_dir=env["transcripts"],
        generated_at="2026-10-28T10:00:00Z",
        **kwargs,
    )


def test_copies_everything_but_decisions_and_the_index(env: dict[str, Path]) -> None:
    _build(env)
    target = env["target"]

    assert (target / "openkos.yaml").read_bytes() == (env["c2"] / "openkos.yaml").read_bytes()
    assert (target / "raw" / "ES2015a.md").is_file()
    assert (target / BUNDLE_DIRNAME / "concepts" / "elks.md").is_file()
    assert (target / BUNDLE_DIRNAME / "sources" / "es2015a.md").is_file()
    assert not (target / BUNDLE_DIRNAME / "decisions" / "old.md").exists()
    assert not (target / ".openkos" / "fts.db").exists()
    assert (env["c2"] / BUNDLE_DIRNAME / "decisions" / "old.md").is_file()  # C2 untouched


def test_gold_decisions_round_trip_through_the_bundle_reader(env: dict[str, Path]) -> None:
    _build(env)

    read = read_decision_bundle(
        env["target"] / BUNDLE_DIRNAME,
        series_id="ES2015",
        meeting_ids=MEETINGS,
        transcripts_dir=env["transcripts"],
    )

    by_id = {d.id: d for d in read.decisions}
    assert sorted(by_id) == [
        "decisions/es2015a-d01",
        "decisions/es2015a-d02",
        "decisions/es2015a-d04",
        "decisions/es2015b-d01",
    ]
    assert not read.unmapped
    first = by_id["decisions/es2015a-d01"]
    assert (first.decision_object, first.content) == ("battery", "use a kinetic battery")
    assert first.meeting_id == "ES2015a"
    assert first.evidence.dialogue_act_ids == ("a.2", "a.3")
    # Evidence spanning two consecutive turns survives as one quote.
    assert by_id["decisions/es2015a-d02"].evidence.dialogue_act_ids == ("a.4", "a.5")
    assert by_id["decisions/es2015b-d01"].evidence.dialogue_act_ids == ("b.1",)


def test_decision_files_are_stamped_as_gold(env: dict[str, Path]) -> None:
    _build(env)
    text = (env["target"] / "bundle" / "decisions" / "es2015b-d01.md").read_text("utf-8")
    metadata = yaml.safe_load(text.split("---\n")[1])

    assert metadata["type"] == "Decision"
    assert metadata["generated"] == {"at": "2026-10-28T10:00:00Z", "by": GOLD_GENERATOR}
    assert metadata["provenance"] == ["sources/es2015b"]
    assert metadata["sources"] == [{"id": "sources/es2015b", "resource": "/sources/es2015b.md"}]
    assert metadata["description"] == "battery: kinetic battery agreed"


def test_accepted_relations_become_links_in_both_decisions(env: dict[str, Path]) -> None:
    result = _build(env)
    decisions = env["target"] / "bundle" / "decisions"
    later = (decisions / "es2015b-d01.md").read_text("utf-8")
    earlier = (decisions / "es2015a-d01.md").read_text("utf-8")

    assert "[battery: use a kinetic battery](/decisions/es2015a-d01.md) — reaffirms" in later
    assert "(/decisions/es2015b-d01.md) — reaffirmed by" in earlier
    assert result.relations_written == 1
    assert result.relations_dropped == ("ES2015a.d02>ES2015b.d02",)
    assert "refines" not in (decisions / "es2015a-d02.md").read_text("utf-8")


def test_index_lists_the_gold_decisions_and_keeps_the_rest(env: dict[str, Path]) -> None:
    _build(env)
    index = (env["target"] / "bundle" / "index.md").read_text("utf-8")

    assert "/decisions/old.md" not in index
    assert "(/decisions/es2015b-d01.md) - battery: kinetic battery agreed" in index
    assert "[Elks](/concepts/elks.md)" in index
    assert "# Directory Update Log" in index
    assert index.index("# Decisions") < index.index("es2015b-d01") < index.index("# Directory")


def test_manifest_reports_what_was_written_and_dropped(env: dict[str, Path]) -> None:
    result = _build(env)
    manifest = json.loads((env["target"] / "c3-manifest.json").read_text("utf-8"))

    assert result.manifest_path == env["target"] / "c3-manifest.json"
    assert manifest["series_id"] == "ES2015"
    assert manifest["c2_run"] == "compiled" and manifest["run"] == 1
    assert manifest["decisions_written"] == 4
    assert manifest["dropped"] == [
        {"id": "ES2015b.d02", "reason": "no_evidence"},
        {"id": "ES2015a.d03", "reason": "evidence_not_in_transcript"},
    ]
    assert manifest["relations_written"] == 1
    assert manifest["openkos_version"] == "0.6.0"
    assert manifest["c2_workspace"].endswith("run-compiled/ES2015/run-1")
    assert manifest["generated_by"] == GOLD_GENERATOR


def test_evidence_that_comes_back_partial_is_listed(env: dict[str, Path]) -> None:
    result = _build(env)

    # d01 and d02 come back as whole turns, which is complete. d04 has non-consecutive
    # turns (a.4 and a.6): only the first run survives, and the rest is reported.
    assert result.evidence_partial == ("ES2015a.d04",)


def test_acts_finer_than_a_turn_are_widened_to_the_turn_without_being_partial(
    env: dict[str, Path],
) -> None:
    single = ReferenceSet("ES2015", (_reference("ES2015a.d01", "ES2015a", ("a.2",)),))
    result = build_gold_workspace(
        series_id="ES2015",
        c2_run="compiled",
        run=1,
        c2_workspace=env["c2"],
        target=env["target"],
        reference=single,
        relations=(),
        runner=FakeRunner(),
        executable="openkos",
        transcripts_dir=env["transcripts"],
    )

    read = read_decision_bundle(
        env["target"] / BUNDLE_DIRNAME,
        series_id="ES2015",
        meeting_ids=MEETINGS,
        transcripts_dir=env["transcripts"],
    )
    assert result.evidence_partial == ()
    assert read.decisions[0].evidence.dialogue_act_ids == ("a.2", "a.3")


def test_reindexes_after_writing_the_bundle(env: dict[str, Path]) -> None:
    runner = FakeRunner()
    _build(env, runner)

    reindex = [(argv, cwd) for argv, cwd in runner.calls if argv[1:2] == ("reindex",)]
    assert reindex == [(("openkos", "reindex", "--force"), env["target"])]


def test_failed_reindex_is_an_error(env: dict[str, Path]) -> None:
    with pytest.raises(OpenKosCommandError, match="reindex"):
        _build(env, FakeRunner(reindex_code=1))


def test_refuses_to_overwrite_unless_asked(env: dict[str, Path]) -> None:
    _build(env)
    (env["target"] / "marker").write_text("x", encoding="utf-8")

    with pytest.raises(GoldWorkspaceExistsError):
        _build(env)
    assert (env["target"] / "marker").exists()

    _build(env, overwrite=True)
    assert not (env["target"] / "marker").exists()


def test_missing_c2_bundle_is_an_error(env: dict[str, Path], tmp_path: Path) -> None:
    env["c2"] = tmp_path / "nowhere"
    with pytest.raises(FileNotFoundError, match="nowhere"):
        _build(env)
    assert not env["target"].exists()


def _relations_csv(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["pair_id,earlier_decision_id,later_decision_id,final_relation,final_direction_ok"]
    lines += [f"p{i},{a},{b},{rel},{ok}" for i, (a, b, rel, ok) in enumerate(rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_gold_relations_keeps_only_accepted_pairs(tmp_path: Path) -> None:
    _relations_csv(
        tmp_path / "ES2015.candidates.adjudicated.csv",
        [
            ("ES2015a.d01", "ES2015b.d01", "refina", "si"),
            ("ES2015a.d02", "ES2015b.d02", "no_relacionada", "si"),
            ("ES2015a.d03", "ES2015b.d03", "reafirma", "no"),
            ("ES2015a.d04", "ES2015b.d04", "", ""),
        ],
    )

    assert load_gold_relations("ES2015", relations_dir=tmp_path) == (
        GoldRelation("ES2015a.d01", "ES2015b.d01", "refina"),
    )


def test_load_gold_relations_without_a_file_is_empty(tmp_path: Path) -> None:
    assert load_gold_relations("ES2015", relations_dir=tmp_path) == ()
