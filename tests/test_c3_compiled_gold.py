"""Tests for condition C3 (``openkos query`` over the gold workspaces of ``afg c3 build``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.conditions.base import Condition
from afg.conditions.c2_compiled_auto import WorkspaceNotFoundError
from afg.conditions.c3_compiled_gold import CompiledGoldCondition
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.extraction.openkos.query import QueryRejectedError
from afg.extraction.openkos.workspace import OpenKosRunSettings
from tests.openkos_bundle import decision_file, write_decision, write_meeting
from tests.openkos_query import QueryRunner, query_report

SETTINGS = OpenKosRunSettings("openkos", "qwen3:8b", "bge-m3", base_seed=42, temperature=0.1)
RUN_NAME = "es2015-test"
QUOTE = "we're going with the kinetic battery"


@pytest.fixture
def env(tmp_path: Path) -> dict[str, Path]:
    transcripts = tmp_path / "transcripts"
    write_meeting(transcripts, "ES2015a", [("ME", QUOTE + " today", ("a.2", "a.3"))])
    for meeting in ("ES2015b", "ES2015c", "ES2015d"):
        write_meeting(transcripts, meeting, [("PM", "Nothing.", (f"{meeting}.1",))])
    base = tmp_path / "c3"
    workspace = base / RUN_NAME / "ES2015" / "run-1"
    write_decision(
        workspace / "bundle",
        "es2015a-d01",
        decision_file(
            title="Kinetic battery",
            subject="battery",
            value="Use a kinetic battery.",
            quotes=[("es2015a", QUOTE)],
        ),
    )
    return {"transcripts": transcripts, "base": base, "workspace": workspace}


def make(env: dict[str, Path], runner: QueryRunner, run: int = 1) -> CompiledGoldCondition:
    condition = CompiledGoldCondition(
        runner=runner,
        settings=SETTINGS,
        extraction_run=RUN_NAME,
        base_dir=env["base"],
        transcripts_dir=env["transcripts"],
        limit=5,
    )
    return condition.with_seed(SETTINGS.seed_for(run))


def question() -> Question:
    return Question(
        id="ES2015.q001",
        series_id="ES2015",
        stratum=QuestionStratum.E1_POINT_FACT,
        text="Which battery?",
    )


def _seeded(seed: int, **overrides: object) -> dict[str, object]:
    report = query_report(**overrides)
    report["llm"] = {**report["llm"], "seed": seed}  # type: ignore[dict-item]
    return report


def test_is_a_condition_named_c3(env: dict[str, Path]) -> None:
    condition = make(env, QueryRunner())
    assert isinstance(condition, Condition) and condition.condition_id == "C3"
    assert isinstance(condition, CompiledGoldCondition)


def test_default_base_dir_is_the_c3_workspaces_dir() -> None:
    from afg.shared.paths import OPENKOS_C3_WORKSPACES_DIR

    condition = CompiledGoldCondition(
        runner=QueryRunner(), settings=SETTINGS, extraction_run=RUN_NAME
    )
    assert condition.base_dir == OPENKOS_C3_WORKSPACES_DIR


def test_queries_the_gold_workspace_and_maps_the_gold_decision(env: dict[str, Path]) -> None:
    citation = {"concept_id": "decisions/es2015a-d01", "title": "t", "excerpted": True}
    runner = QueryRunner([_seeded(43, citations=[citation])])

    answer, trace = make(env, runner).answer_with_trace(question())

    ((argv, cwd),) = runner.queries()
    assert argv == ("openkos", "query", "Which battery?", "--json", "--limit", "5")
    assert cwd == env["workspace"]
    assert answer.condition == "C3" and answer.abstained is False
    assert answer.cited_evidence == (
        EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a.2", "a.3")),
    )
    assert trace.cited_acts == {"decisions/es2015a-d01": {"ES2015a": ("a.2", "a.3")}}


def test_missing_workspace_says_how_to_build_it(env: dict[str, Path]) -> None:
    condition = make(env, QueryRunner(), run=2)
    with pytest.raises(WorkspaceNotFoundError, match="afg c3 build") as raised:
        condition.answer(question())
    assert "run-2" in str(raised.value) and RUN_NAME in str(raised.value)


def test_without_a_run_the_error_names_c3(env: dict[str, Path]) -> None:
    unbound = CompiledGoldCondition(
        runner=QueryRunner(), settings=SETTINGS, extraction_run=RUN_NAME, base_dir=env["base"]
    )
    with pytest.raises(ValueError, match="C3 needs a run"):
        unbound.answer(question())
    with pytest.raises(ValueError, match="C3 cannot tell"):
        unbound.with_seed(SETTINGS.base_seed - 1)


def test_a_workspace_with_another_seed_is_rejected(env: dict[str, Path]) -> None:
    with pytest.raises(QueryRejectedError):
        make(env, QueryRunner([_seeded(99)])).answer(question())
