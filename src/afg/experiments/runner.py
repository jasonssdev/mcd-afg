"""Condition-agnostic runner of Experiment B (thesis sections 5.3, 5.6 and 5.7).

For every run index, question and condition the runner obtains the answer, judges it,
computes the deterministic citation correctness and appends one JSON line to
``respuestas.jsonl``. A ``manifest.json`` next to it records the configuration, the
partition of the questions (ADR 0005) and the counts.

Design decisions:

* Conditions and the judge backend are injected, so any :class:`~afg.conditions.base.Condition`
  (C1 today, C2 and C3 later) runs unchanged and the tests need no network.
* Generation seed of run ``r`` is ``base_seed + r``. A condition that offers
  ``with_seed(seed)`` receives it; one that does not keeps its own fixed seed and the record
  says so (``seed_applied``). The judge uses one fixed seed, order and temperature for every
  record, so the judge is a constant of the experiment and not a source of variance.
* Resume: the file is append-only and the latest record of a key wins. A record is complete
  when it has no ``error``. A judge output that could not be parsed is a complete record
  (``judge_failure``): it is a measured outcome that the JSON-validity rate counts, and
  repeating it would not change it. A condition or judge exception is an ``error`` and is
  retried on the next execution.
* A truncated last line (interrupted write) is ignored when reading.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from afg.conditions.base import Condition
from afg.domain.question import Answer, Question, QuestionStratum
from afg.evaluation.citation import citation_correct
from afg.evaluation.judge import (
    JudgeBackend,
    JudgeFailure,
    PresentationOrder,
    judge_answer,
    require_distinct_model_families,
)
from afg.evaluation.passage import judge_evidence_passage
from afg.shared.config import load_corpus_config
from afg.shared.paths import PROJECT_ROOT

RECORDS_FILE = "respuestas.jsonl"
MANIFEST_FILE = "manifest.json"
SCHEMA_VERSION = 1

DEFAULT_MAX_CONSECUTIVE_ERRORS = 10
"""A systemic failure (backend down) must not fill the file with hundreds of error records."""


class ManifestMismatchError(ValueError):
    """Raised when a run directory is resumed with settings that differ from its manifest."""


class RunAbortedError(RuntimeError):
    """Raised when too many consecutive records failed: the cause is probably systemic."""


@dataclass(frozen=True, slots=True)
class RunSettings:
    """Everything that defines a run besides the questions and the conditions."""

    generative_model: str
    temperature: float
    base_seed: int
    runs: int
    judge_model: str
    judge_order: PresentationOrder
    judge_seed: int
    judge_temperature: float


@dataclass(frozen=True, slots=True)
class RunSummary:
    """What one execution did; ``written`` excludes the keys it skipped as already done."""

    written: int
    skipped: int
    errors: int


ExcerptFor = Callable[[Question], str]
"""Builds the transcript excerpt the judge reads for a question; injectable for tests."""


def default_excerpt_for(question: Question) -> str:
    """The judge's passage around the reference evidence; empty when there is none (E4)."""
    if question.stratum is QuestionStratum.E4_UNANSWERABLE or not question.reference_evidence:
        return ""
    return judge_evidence_passage(question.reference_evidence)


def configured_partition_of() -> Callable[[str], str]:
    """``series -> development | evaluation | unassigned`` from ``config/corpus.toml``."""
    oe1 = load_corpus_config()["oe1"]
    development = frozenset(oe1["development_series"])
    evaluation = frozenset(oe1["evaluation_series"])

    def partition_of(series: str) -> str:
        if series in development:
            return "development"
        if series in evaluation:
            return "evaluation"
        return "unassigned"

    return partition_of


def current_git_commit() -> str | None:
    """HEAD of the project repository, or ``None`` when git is unavailable."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


# --- persistence -------------------------------------------------------------------------------


def load_records(path: Path, *, latest_only: bool = False) -> list[dict[str, Any]]:
    """Read the JSONL file, skipping blank and malformed (truncated) lines.

    With ``latest_only`` only the last record of each ``(question, condition, run)`` key is
    returned, in the order the keys first appeared.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and {"question_id", "condition", "run"} <= parsed.keys():
            records.append(parsed)
    if not latest_only:
        return records
    latest: dict[tuple[str, str, int], dict[str, Any]] = {}
    for record in records:
        latest[_key_of(record)] = record
    return list(latest.values())


def _key_of(record: Mapping[str, Any]) -> tuple[str, str, int]:
    return (str(record["question_id"]), str(record["condition"]), int(record["run"]))


def _append(path: Path, record: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        handle.flush()


def _jsonable(value: Any) -> Any:
    """A dataclass or pydantic model as plain JSON-ready data."""
    if hasattr(value, "model_dump"):
        return json.loads(json.dumps(value.model_dump(mode="json")))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return json.loads(json.dumps(asdict(value), default=str))
    return json.loads(json.dumps(value, default=str))


def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _compared_settings(settings: Mapping[str, Any]) -> dict[str, Any]:
    """The settings that must not change across executions of one run directory."""
    return {k: v for k, v in settings.items() if k != "runs"}


# --- engine ------------------------------------------------------------------------------------


def _partition(series: Iterable[str], partition_of: Callable[[str], str]) -> str:
    found = {partition_of(s) for s in series}
    if len(found) == 1:
        return found.pop()
    return "mixed"


def run_experiment_b(
    questions: Iterable[Question],
    conditions: Mapping[str, Condition],
    *,
    settings: RunSettings,
    judge_backend: JudgeBackend,
    run_dir: Path,
    partition_of: Callable[[str], str] | None = None,
    excerpt_for: ExcerptFor = default_excerpt_for,
    git_commit: str | None = None,
    max_consecutive_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
    progress: Callable[[int, int], None] | None = None,
    clock: Callable[[], float] = time.perf_counter,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> RunSummary:
    """Run (or resume) Experiment B into ``run_dir`` and return what this execution did.

    ``conditions`` maps the condition id to the condition. ``progress(done, total)`` is called
    after each record written by this execution (``total`` counts only the pending keys).

    Raises:
        JudgeConfigurationError: if the judge and generative models coincide.
        ManifestMismatchError: if ``run_dir`` already holds a run with other settings.
        RunAbortedError: after ``max_consecutive_errors`` failed records in a row.
        ValueError: on duplicate question ids or an empty experiment.
    """
    require_distinct_model_families(settings.judge_model, settings.generative_model)
    bank = list(questions)
    if len({q.id for q in bank}) != len(bank):
        raise ValueError("duplicate question ids.")
    if not bank or not conditions or settings.runs < 1:
        raise ValueError("an experiment needs at least one question, condition and run.")
    partitioner = partition_of or configured_partition_of()

    run_dir.mkdir(parents=True, exist_ok=True)
    records_path = run_dir / RECORDS_FILE
    manifest_path = run_dir / MANIFEST_FILE
    settings_dict = asdict(settings)
    previous = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    if previous is not None and _compared_settings(previous["settings"]) != _compared_settings(
        settings_dict
    ):
        raise ManifestMismatchError(
            f"{manifest_path} was written with other settings; use another --run-name "
            "or restore them to resume."
        )

    series = sorted({q.series_id for q in bank})
    partition = _partition(series, partitioner)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_name": run_dir.name,
        "created_at": previous["created_at"] if previous else now().isoformat(),
        "updated_at": now().isoformat(),
        "git_commit": git_commit,
        "settings": settings_dict,
        "conditions": sorted(conditions),
        "series": series,
        "partition": partition,
        "development_only": partition == "development",
        "note": (
            "Development series (ADR 0005): these figures never enter a results table."
            if partition == "development"
            else None
        ),
        "counts": {},
    }

    done = {
        _key_of(r) for r in load_records(records_path, latest_only=True) if r.get("error") is None
    }
    pending = sum(
        1
        for r in range(settings.runs)
        for q in bank
        for c in conditions
        if (q.id, c, r) not in done
    )
    expected = len(bank) * len(conditions) * settings.runs
    written = errors = streak = 0

    def finish() -> None:
        latest = load_records(records_path, latest_only=True)
        manifest["updated_at"] = now().isoformat()
        manifest["counts"] = {
            "questions": len(bank),
            "expected": expected,
            "records": len(load_records(records_path)),
            "complete": sum(1 for r in latest if r.get("error") is None),
            "errors": sum(1 for r in latest if r.get("error") is not None),
        }
        _write_manifest(manifest_path, manifest)

    _write_manifest(manifest_path, manifest)
    try:
        for run in range(settings.runs):
            seed = settings.base_seed + run
            seeded: dict[str, tuple[Condition, bool]] = {}
            for condition_id, condition in conditions.items():
                with_seed = getattr(condition, "with_seed", None)
                seeded[condition_id] = (
                    (with_seed(seed), True) if callable(with_seed) else (condition, False)
                )
            for question in bank:
                for condition_id, (condition, applied) in seeded.items():
                    if (question.id, condition_id, run) in done:
                        continue
                    record = _evaluate(
                        question,
                        condition,
                        condition_id=condition_id,
                        run=run,
                        seed=seed,
                        seed_applied=applied,
                        settings=settings,
                        backend=judge_backend,
                        partition=partitioner(question.series_id),
                        excerpt_for=excerpt_for,
                        clock=clock,
                        now=now,
                        run_name=run_dir.name,
                    )
                    _append(records_path, record)
                    written += 1
                    if record["error"] is None:
                        streak = 0
                    else:
                        errors += 1
                        streak += 1
                    if progress is not None:
                        progress(written, pending)
                    if streak >= max_consecutive_errors:
                        raise RunAbortedError(
                            f"{streak} consecutive records failed (last: {record['error']}); "
                            "fix the cause and run again to resume."
                        )
    finally:
        finish()
    return RunSummary(written=written, skipped=expected - pending, errors=errors)


def _evaluate(
    question: Question,
    condition: Condition,
    *,
    condition_id: str,
    run: int,
    seed: int,
    seed_applied: bool,
    settings: RunSettings,
    backend: JudgeBackend,
    partition: str,
    excerpt_for: ExcerptFor,
    clock: Callable[[], float],
    now: Callable[[], datetime],
    run_name: str,
) -> dict[str, Any]:
    """Answer, judge and score one key; exceptions become an ``error`` in the record."""
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_name": run_name,
        "question_id": question.id,
        "condition": condition_id,
        "run": run,
        "series_id": question.series_id,
        "stratum": question.stratum.value,
        "partition": partition,
        "generative_model": settings.generative_model,
        "temperature": settings.temperature,
        "seed": seed,
        "seed_applied": seed_applied,
        "judge": {
            "model": settings.judge_model,
            "order": settings.judge_order,
            "seed": settings.judge_seed,
            "temperature": settings.judge_temperature,
        },
        "started_at": now().isoformat(),
        "answer": None,
        "trace": None,
        "verdict": None,
        "judge_failure": None,
        "citation_correct": None,
        "error": None,
        "error_stage": None,
        "answer_seconds": None,
        "judge_seconds": None,
    }
    started = clock()
    try:
        answer, trace = _answer(condition, question)
    except Exception as exc:  # a failing key is data, not a crash (see module docstring)
        record.update(error=f"{type(exc).__name__}: {exc}", error_stage="condition")
        record["answer_seconds"] = clock() - started
        record["finished_at"] = now().isoformat()
        return record
    record["answer_seconds"] = clock() - started
    record["answer"] = _jsonable(answer)
    record["trace"] = None if trace is None else _jsonable(trace)
    record["citation_correct"] = citation_correct(question, answer)

    started = clock()
    try:
        outcome = judge_answer(
            question,
            answer,
            judge_model=settings.judge_model,
            generative_model=settings.generative_model,
            backend=backend,
            order=settings.judge_order,
            seed=settings.judge_seed,
            temperature=settings.judge_temperature,
            transcript_excerpt=excerpt_for(question),
        )
    except Exception as exc:
        record.update(error=f"{type(exc).__name__}: {exc}", error_stage="judge")
    else:
        key = "judge_failure" if isinstance(outcome, JudgeFailure) else "verdict"
        record[key] = _jsonable(outcome)
    record["judge_seconds"] = clock() - started
    record["finished_at"] = now().isoformat()
    return record


def _answer(condition: Condition, question: Question) -> tuple[Answer, Any | None]:
    """The answer and, when the condition offers ``answer_with_trace``, its trace."""
    with_trace = getattr(condition, "answer_with_trace", None)
    if callable(with_trace):
        answer, trace = with_trace(question)
        return answer, trace
    return condition.answer(question), None
