"""Tests for the Experiment B runner engine. No network: conditions and judge are fakes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.judge import JudgeConfigurationError
from afg.experiments.runner import (
    ManifestMismatchError,
    RunAbortedError,
    RunSettings,
    load_records,
    run_experiment_b,
)

GOOD = json.dumps({"correct": True, "evidence_supported": True, "rationale": "ok"})
SPAN = EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("d1",))


def _question(qid: str = "q1", series: str = "ES2015", *, e4: bool = False) -> Question:
    return Question(
        id=qid,
        series_id=series,
        stratum=QuestionStratum.E4_UNANSWERABLE if e4 else QuestionStratum.E1_POINT_FACT,
        text=f"text of {qid}",
        reference_answer=None if e4 else "ref",
        reference_evidence=() if e4 else (SPAN,),
    )


@dataclass
class FakeCondition:
    """Answers with a citation to ``d1``; records the seeds it was asked to use."""

    condition_id: str = "C1"
    seed: int | None = None
    fail_on: set[str] = field(default_factory=set)
    calls: list[tuple[str, int | None]] = field(default_factory=list)

    def with_seed(self, seed: int) -> FakeCondition:
        return replace(self, seed=seed, calls=self.calls, fail_on=self.fail_on)

    def answer(self, question: Question) -> Answer:
        self.calls.append((question.id, self.seed))
        if question.id in self.fail_on:
            raise RuntimeError("chat backend down")
        return Answer(
            question_id=question.id, condition=self.condition_id, text="a", cited_evidence=(SPAN,)
        )


@dataclass
class TracedCondition(FakeCondition):
    def answer_with_trace(self, question: Question) -> tuple[Answer, Any]:
        @dataclass
        class Trace:
            outcome: str
            retrieved: tuple[str, ...]

        return self.answer(question), Trace("answered", ("c1",))


class PlainCondition:
    """No ``with_seed``, no trace."""

    condition_id = "C2"

    def answer(self, question: Question) -> Answer:
        return Answer(question_id=question.id, condition="C2", text="p", abstained=True)


class FakeBackend:
    def __init__(self, reply: str = GOOD, raises: Exception | None = None) -> None:
        self.reply = reply
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    def complete(self, system: str, user: str, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return self.reply


def _settings(**over: Any) -> RunSettings:
    values: dict[str, Any] = {
        "generative_model": "qwen3:8b",
        "temperature": 0.1,
        "base_seed": 42,
        "runs": 2,
        "judge_model": "gpt-oss:20b",
        "judge_order": "reference_first",
        "judge_seed": 42,
        "judge_temperature": 0.0,
    }
    values.update(over)
    return RunSettings(**values)


def _run(tmp_path: Path, questions: list[Question], conditions: list[Any], **over: Any) -> Any:
    kwargs: dict[str, Any] = {
        "settings": _settings(),
        "judge_backend": FakeBackend(),
        "run_dir": tmp_path / "run",
        "partition_of": lambda series: "development",
        "excerpt_for": lambda q: "" if not q.reference_evidence else "passage",
        "git_commit": "abc123",
    }
    kwargs.update(over)
    return run_experiment_b(questions, {c.condition_id: c for c in conditions}, **kwargs)


def test_one_record_per_question_condition_run(tmp_path: Path) -> None:
    _run(tmp_path, [_question("q1"), _question("q2")], [FakeCondition(), PlainCondition()])
    records = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert len(records) == 2 * 2 * 2
    keys = {(r["question_id"], r["condition"], r["run"]) for r in records}
    assert len(keys) == 8


def test_record_fields_and_citation(tmp_path: Path) -> None:
    _run(tmp_path, [_question("q1")], [FakeCondition()], settings=_settings(runs=1))
    (record,) = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert record["answer"]["text"] == "a"
    assert record["verdict"]["correct"] is True
    assert record["judge_failure"] is None
    assert record["citation_correct"] is True
    assert record["citation_precision"] == 1.0
    assert record["schema_version"] == 2
    assert record["error"] is None
    assert record["partition"] == "development"
    assert record["series_id"] == "ES2015"
    assert record["stratum"] == "E1_point_fact"
    assert record["generative_model"] == "qwen3:8b"
    assert record["temperature"] == 0.1
    assert record["judge"] == {
        "model": "gpt-oss:20b",
        "order": "reference_first",
        "seed": 42,
        "temperature": 0.0,
    }
    for name in ("started_at", "finished_at", "answer_seconds", "judge_seconds"):
        assert record[name] is not None


def test_generation_seed_is_base_plus_run_index(tmp_path: Path) -> None:
    condition = FakeCondition()
    _run(tmp_path, [_question()], [condition], settings=_settings(runs=3, base_seed=42))
    assert condition.calls == [("q1", 42), ("q1", 43), ("q1", 44)]
    records = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert [(r["run"], r["seed"], r["seed_applied"]) for r in records] == [
        (0, 42, True),
        (1, 43, True),
        (2, 44, True),
    ]


def test_condition_without_with_seed_marks_seed_not_applied(tmp_path: Path) -> None:
    _run(tmp_path, [_question()], [PlainCondition()], settings=_settings(runs=1))
    (record,) = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert record["seed"] == 42
    assert record["seed_applied"] is False
    assert record["trace"] is None
    assert record["citation_correct"] is None  # abstention
    assert record["citation_precision"] is None


def test_trace_serialized_when_condition_offers_it(tmp_path: Path) -> None:
    _run(tmp_path, [_question()], [TracedCondition()], settings=_settings(runs=1))
    (record,) = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert record["trace"] == {"outcome": "answered", "retrieved": ["c1"]}


def test_resume_skips_completed_keys(tmp_path: Path) -> None:
    first = FakeCondition()
    _run(tmp_path, [_question("q1")], [first])
    second = FakeCondition()
    summary = _run(tmp_path, [_question("q1"), _question("q2")], [second])
    assert {c[0] for c in second.calls} == {"q2"}
    assert summary.skipped == 2
    assert len(load_records(tmp_path / "run" / "respuestas.jsonl")) == 4


def test_condition_error_is_recorded_and_retried_on_resume(tmp_path: Path) -> None:
    broken = FakeCondition(fail_on={"q1"})
    summary = _run(tmp_path, [_question("q1"), _question("q2")], [broken])
    assert summary.errors == 2
    records = load_records(tmp_path / "run" / "respuestas.jsonl")
    failed = [r for r in records if r["question_id"] == "q1"]
    assert all(r["error"].startswith("RuntimeError") for r in failed)
    assert all(r["error_stage"] == "condition" and r["verdict"] is None for r in failed)

    healthy = FakeCondition()
    _run(tmp_path, [_question("q1"), _question("q2")], [healthy])
    assert {c[0] for c in healthy.calls} == {"q1"}  # only the failed key is retried
    latest = load_records(tmp_path / "run" / "respuestas.jsonl", latest_only=True)
    assert len(latest) == 4
    assert all(r["error"] is None for r in latest)


def test_judge_failure_is_a_complete_record(tmp_path: Path) -> None:
    backend = FakeBackend(reply="not json")
    _run(tmp_path, [_question()], [FakeCondition()], judge_backend=backend)
    records = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert all(
        r["verdict"] is None and r["judge_failure"]["reason"] == "invalid_json" for r in records
    )
    assert all(r["error"] is None for r in records)
    calls_before = len(backend.calls)
    _run(tmp_path, [_question()], [FakeCondition()], judge_backend=backend)
    assert len(backend.calls) == calls_before  # not retried


def test_judge_exception_is_recorded_as_error(tmp_path: Path) -> None:
    backend = FakeBackend(raises=ConnectionError("ollama down"))
    _run(tmp_path, [_question()], [FakeCondition()], judge_backend=backend)
    (first, _second) = load_records(tmp_path / "run" / "respuestas.jsonl")
    assert first["error_stage"] == "judge"
    assert first["answer"]["text"] == "a"  # the answer is kept
    assert first["verdict"] is None


def test_judge_uses_configured_settings(tmp_path: Path) -> None:
    backend = FakeBackend()
    _run(tmp_path, [_question()], [FakeCondition()], judge_backend=backend)
    assert backend.calls[0]["model"] == "gpt-oss:20b"
    assert backend.calls[0]["seed"] == 42
    assert backend.calls[0]["temperature"] == 0.0


def test_judge_equal_to_generative_model_is_refused(tmp_path: Path) -> None:
    with pytest.raises(JudgeConfigurationError):
        _run(tmp_path, [_question()], [FakeCondition()], settings=_settings(judge_model="qwen3:8b"))
    assert not (tmp_path / "run" / "respuestas.jsonl").exists()


def test_manifest_contents(tmp_path: Path) -> None:
    _run(tmp_path, [_question("q1"), _question("q2", e4=True)], [FakeCondition()])
    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["partition"] == "development"
    assert manifest["development_only"] is True
    assert manifest["git_commit"] == "abc123"
    assert manifest["conditions"] == ["C1"]
    assert manifest["settings"]["runs"] == 2
    assert manifest["settings"]["judge_model"] == "gpt-oss:20b"
    assert manifest["counts"] == {
        "questions": 2,
        "expected": 4,
        "records": 4,
        "complete": 4,
        "errors": 0,
    }
    assert manifest["series"] == ["ES2015"]


def test_manifest_partition_evaluation_and_mixed(tmp_path: Path) -> None:
    part = {"ES2015": "development", "ES2002": "evaluation"}.get
    _run(
        tmp_path / "a",
        [_question("q1", "ES2002")],
        [FakeCondition()],
        partition_of=lambda s: part(s, "unassigned"),
    )
    a = json.loads((tmp_path / "a" / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert a["partition"] == "evaluation" and a["development_only"] is False
    _run(
        tmp_path / "b",
        [_question("q1", "ES2002"), _question("q2", "ES2015")],
        [FakeCondition()],
        partition_of=lambda s: part(s, "unassigned"),
    )
    b = json.loads((tmp_path / "b" / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert b["partition"] == "mixed" and b["development_only"] is False


def test_resume_with_different_settings_is_refused(tmp_path: Path) -> None:
    _run(tmp_path, [_question()], [FakeCondition()])
    with pytest.raises(ManifestMismatchError):
        _run(tmp_path, [_question()], [FakeCondition()], settings=_settings(temperature=0.5))


def test_resume_may_raise_the_number_of_runs(tmp_path: Path) -> None:
    _run(tmp_path, [_question()], [FakeCondition()], settings=_settings(runs=1))
    summary = _run(tmp_path, [_question()], [FakeCondition()], settings=_settings(runs=2))
    assert summary.written == 1 and summary.skipped == 1


def test_truncated_last_line_is_ignored_on_resume(tmp_path: Path) -> None:
    _run(tmp_path, [_question()], [FakeCondition()], settings=_settings(runs=1))
    path = tmp_path / "run" / "respuestas.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"question_id": "q9", "cond')  # interrupted write
    condition = FakeCondition()
    summary = _run(tmp_path, [_question()], [condition], settings=_settings(runs=1))
    assert summary.skipped == 1 and condition.calls == []


def test_aborts_after_consecutive_errors(tmp_path: Path) -> None:
    questions = [_question(f"q{i}") for i in range(5)]
    broken = FakeCondition(fail_on={q.id for q in questions})
    with pytest.raises(RunAbortedError):
        _run(tmp_path, questions, [broken], max_consecutive_errors=3)
    assert len(load_records(tmp_path / "run" / "respuestas.jsonl")) == 3


def test_records_are_flushed_one_by_one(tmp_path: Path) -> None:
    seen: list[int] = []

    def progress(done: int, total: int) -> None:
        seen.append(len((tmp_path / "run" / "respuestas.jsonl").read_text().splitlines()))

    _run(tmp_path, [_question("q1"), _question("q2")], [FakeCondition()], progress=progress)
    assert seen == [1, 2, 3, 4]


def test_provenance_is_merged_into_the_manifest(tmp_path: Path) -> None:
    extra = {"generative_model_digest": "aaa", "git_dirty": False, "ollama_version": None}
    _run(tmp_path, [_question("q1")], [FakeCondition()], provenance=extra)
    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generative_model_digest"] == "aaa"
    assert manifest["git_dirty"] is False
    assert manifest["ollama_version"] is None
    assert manifest["git_commit"] == "abc123"


def test_manifest_without_provenance_keeps_the_previous_shape(tmp_path: Path) -> None:
    _run(tmp_path, [_question("q1")], [FakeCondition()])
    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert "generative_model_digest" not in manifest
