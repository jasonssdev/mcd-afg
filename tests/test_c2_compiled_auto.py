"""Tests for condition C2 (``openkos query`` over the workspaces of an Experiment A run)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from afg.conditions.base import Condition
from afg.conditions.c2_compiled_auto import (
    CompiledAutoCondition,
    CompiledAutoTrace,
    WorkspaceNotFoundError,
)
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.experiments.runner import _jsonable
from afg.extraction.openkos.capabilities import MissingCapabilitiesError
from afg.extraction.openkos.query import QueryRejectedError
from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.extraction.openkos_adapter import project_relative
from afg.shared.paths import PROJECT_ROOT
from tests.openkos_bundle import (
    concept_file,
    decision_file,
    write_bundle_file,
    write_decision,
    write_meeting,
)
from tests.openkos_query import QueryRunner, query_report

MEETINGS = ("ES2015a", "ES2015b", "ES2015c", "ES2015d")
SETTINGS = OpenKosRunSettings("openkos", "qwen3:8b", "bge-m3", base_seed=42, temperature=0.1)
RUN_NAME = "es2015-test"
SOURCE_QUOTE = "we're going with the kinetic battery"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, Path]:
    """Transcripts of four meetings and the bundle of ``run-1`` with one mappable decision."""
    transcripts = tmp_path / "transcripts"
    write_meeting(
        transcripts,
        "ES2015a",
        [
            ("PM", "Hello.", ("a.1",)),
            ("ME", SOURCE_QUOTE + " today", ("a.2", "a.3")),
            ("UI", "Elks have big antlers.", ("a.4",)),
        ],
    )
    for meeting in MEETINGS[1:]:
        write_meeting(transcripts, meeting, [("PM", "Nothing here.", (f"{meeting}.1",))])
    base = tmp_path / "workspaces"
    workspace = base / RUN_NAME / "ES2015" / "run-1"
    write_decision(
        workspace / "bundle",
        "battery",
        decision_file(
            title="Kinetic battery",
            subject="remote control battery",
            value="The remote will use a kinetic battery.",
            quotes=[("es2015a", SOURCE_QUOTE)],
        ),
    )
    bundle = workspace / "bundle"
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
    write_bundle_file(
        bundle,
        "events",
        "lost",
        concept_file(
            title="Lost",
            description="Nothing matches.",
            turns=["PM: Never said in the meeting."],
            provenance=["es2015a"],
            type_="Event",
        ),
    )
    write_decision(
        bundle,
        "orphan",
        decision_file(
            title="Orphan",
            subject="colour",
            value="The remote is red.",
            quotes=[("es2015a", "this quote is not in the transcript")],
        ),
    )
    return {"transcripts": transcripts, "base": base, "workspace": workspace}


def make(env: dict[str, Path], runner: QueryRunner, run: int = 1) -> CompiledAutoCondition:
    condition = CompiledAutoCondition(
        runner=runner,
        settings=SETTINGS,
        extraction_run=RUN_NAME,
        base_dir=env["base"],
        transcripts_dir=env["transcripts"],
        limit=5,
    )
    return condition.with_seed(SETTINGS.seed_for(run))


def question(text: str = "Which battery?", series: str = "ES2015") -> Question:
    return Question(
        id="ES2015.q001", series_id=series, stratum=QuestionStratum.E1_POINT_FACT, text=text
    )


def test_is_a_condition_named_c2(env: dict[str, Path]) -> None:
    condition = make(env, QueryRunner())
    assert isinstance(condition, Condition) and condition.condition_id == "C2"


def test_queries_the_workspace_of_the_run_with_limit_five(env: dict[str, Path]) -> None:
    runner = QueryRunner([query_report(llm={**query_report()["llm"], "seed": 43})])
    make(env, runner, run=1).answer(question())  # run 1 expects seed 43
    ((argv, cwd),) = runner.queries()
    assert argv == ("openkos", "query", "Which battery?", "--json", "--limit", "5")
    assert cwd == env["workspace"]


def test_answered_maps_cited_concepts_to_evidence_spans(env: dict[str, Path]) -> None:
    runner = QueryRunner([_seeded(43)])
    answer, trace = make(env, runner).answer_with_trace(question())
    assert answer.condition == "C2" and answer.abstained is False
    assert answer.text == "A kinetic battery."
    assert answer.cited_evidence == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.2", "a.3")),
    )
    assert trace.cited_acts == {"decisions/battery": {"ES2015a": ("a.2", "a.3")}}
    assert trace.unmapped_cited == ()


def _cite(*concept_ids: str) -> dict[str, object]:
    citations = [
        {"concept_id": concept_id, "title": concept_id, "excerpted": True}
        for concept_id in concept_ids
    ]
    return _seeded(43, citations=citations)


def test_cited_non_decision_concept_is_mapped_from_its_excerpt(env: dict[str, Path]) -> None:
    answer, trace = make(env, QueryRunner([_cite("concepts/elks")])).answer_with_trace(question())
    assert answer.cited_evidence == (EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.4",)),)
    assert trace.cited_acts == {"concepts/elks": {"ES2015a": ("a.4",)}}
    assert trace.unmapped_cited == ()


def test_spans_of_several_cited_concepts_are_deduplicated_in_order(env: dict[str, Path]) -> None:
    runner = QueryRunner([_cite("concepts/elks", "decisions/battery", "concepts/elks")])
    answer, _ = make(env, runner).answer_with_trace(question())
    assert answer.cited_evidence == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.4",)),
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.2", "a.3")),
    )


def test_unmapped_citations_carry_an_explicit_reason(env: dict[str, Path]) -> None:
    runner = QueryRunner(
        [
            _cite(
                "sources/es2015a",
                "events/lost",
                "decisions/orphan",
                "concepts/not-in-the-bundle",
            )
        ]
    )
    answer, trace = make(env, runner).answer_with_trace(question())
    assert answer.cited_evidence == () and trace.cited_acts == {}
    assert [(u.concept_id, u.reason) for u in trace.unmapped_cited] == [
        ("sources/es2015a", "source_full_transcript"),
        ("events/lost", "no_located_excerpt"),
        ("decisions/orphan", "decision_without_evidence"),
        ("concepts/not-in-the-bundle", "unknown_concept"),
    ]


def test_trace_with_unmapped_citations_serialises_as_runner_does(env: dict[str, Path]) -> None:
    _, trace = make(env, QueryRunner([_cite("sources/es2015a")])).answer_with_trace(question())
    assert _jsonable(trace)["unmapped_cited"] == [
        {"concept_id": "sources/es2015a", "reason": "source_full_transcript"}
    ]


@pytest.mark.parametrize(
    ("outcome", "text_fragment"),
    [("no_match", "No matching concepts"), ("no_answer_in_context", "none of them answers")],
)
def test_non_answered_outcomes_abstain_without_citations(
    env: dict[str, Path], outcome: str, text_fragment: str
) -> None:
    report = _seeded(43, outcome=outcome, answer=None, citations=[])
    answer, trace = make(env, QueryRunner([report])).answer_with_trace(question())
    assert answer.abstained is True and answer.cited_evidence == ()
    assert text_fragment in answer.text
    assert trace.outcome == outcome


def test_trace_carries_the_whole_report_and_serialises(env: dict[str, Path]) -> None:
    _, trace = make(env, QueryRunner([_seeded(43)])).answer_with_trace(question())
    assert isinstance(trace, CompiledAutoTrace)
    data = json.loads(json.dumps(asdict(trace), default=str))
    for key in (
        "outcome", "question", "limit", "answer", "withheld", "sufficiency", "attribution",
        "context_blocks", "omitted", "retrieved", "citations", "counts", "llm", "prompts",
        "openkos_version", "workspace", "run", "cited_acts", "unmapped_cited",
    ):  # fmt: skip
        assert key in data, key
    assert data["workspace"] == str(env["workspace"])  # outside the project root: as given
    assert data["run"] == 1 and data["llm"]["seed"] == 43
    assert data["context_blocks"][0]["concept_id"] == "decisions/battery"


def test_trace_workspace_is_project_relative_inside_the_project() -> None:
    assert project_relative(PROJECT_ROOT / "data" / "x") == "data/x"


def test_concept_map_is_built_once_per_workspace(env: dict[str, Path]) -> None:
    runner = QueryRunner([_seeded(43)])
    condition = make(env, runner)
    condition.answer(question())
    for path in (env["workspace"] / "bundle").glob("*/*.md"):
        path.unlink()  # a second read of the bundle would now find nothing
    answer = condition.answer(question("Again?"))
    assert len(answer.cited_evidence) == 1


def test_capabilities_are_probed_once_and_shared_by_with_seed(env: dict[str, Path]) -> None:
    runner = QueryRunner([_seeded(43)])
    condition = make(env, runner)
    condition.answer(question())
    condition.answer(question("Another?"))
    condition.with_seed(SETTINGS.seed_for(1)).answer(question("Third?"))
    probes = [c for c in runner.calls if c[0][1:] == ("query", "--help")]
    assert len(probes) == 1


def test_missing_query_json_capability_is_refused(env: dict[str, Path]) -> None:
    runner = QueryRunner(query_help="Usage: openkos query QUESTION\n  --limit INTEGER\n")
    with pytest.raises(MissingCapabilitiesError, match="query --json"):
        make(env, runner).answer(question())
    assert runner.queries() == []


@pytest.mark.parametrize("field", ["temperature", "seed"])
def test_null_temperature_or_seed_raises(env: dict[str, Path], field: str) -> None:
    report = _seeded(43)
    report["llm"][field] = None
    with pytest.raises(QueryRejectedError, match=field):
        make(env, QueryRunner([report])).answer(question())


def test_seed_that_is_not_the_runs_raises(env: dict[str, Path]) -> None:
    with pytest.raises(QueryRejectedError, match="seed 42, expected 43"):
        make(env, QueryRunner([_seeded(42)]), run=1).answer(question())


def test_withheld_raises(env: dict[str, Path]) -> None:
    with pytest.raises(QueryRejectedError, match="withheld"):
        make(env, QueryRunner([_seeded(43, withheld=1)])).answer(question())


def test_missing_workspace_for_the_series_or_run_is_a_clear_error(env: dict[str, Path]) -> None:
    runner = QueryRunner([_seeded(44)])
    with pytest.raises(WorkspaceNotFoundError, match="run-2"):
        make(env, runner, run=2).answer(question())
    with pytest.raises(WorkspaceNotFoundError, match="ES2016"):
        make(env, runner).answer(question(series="ES2016"))
    assert runner.queries() == []


def test_answering_without_a_run_is_an_error(env: dict[str, Path]) -> None:
    condition = CompiledAutoCondition(
        runner=QueryRunner(),
        settings=SETTINGS,
        extraction_run=RUN_NAME,
        base_dir=env["base"],
        transcripts_dir=env["transcripts"],
    )
    with pytest.raises(ValueError, match="with_seed"):
        condition.answer(question())


def test_seed_below_the_base_seed_is_refused(env: dict[str, Path]) -> None:
    with pytest.raises(ValueError, match="base seed"):
        make(env, QueryRunner()).with_seed(SETTINGS.base_seed - 1)


def _seeded(seed: int, **overrides: object) -> dict[str, object]:
    report = query_report(**overrides)
    report["llm"] = {**report["llm"], "seed": seed}  # type: ignore[dict-item]
    return report


def test_temperature_other_than_configured_raises(env: dict[str, Path]) -> None:
    report = _seeded(43)
    report["llm"]["temperature"] = 0.9
    with pytest.raises(QueryRejectedError, match="temperature"):
        make(env, QueryRunner([report])).answer(question())
