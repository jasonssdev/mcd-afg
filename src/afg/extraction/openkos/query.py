"""``openkos query --json`` (schema v1): build the call, parse and validate the report.

This is the only place that queries OpenKOS (ADR 0003); like the rest of the package it goes
through the injectable :class:`~afg.extraction.openkos.commands.CommandRunner`, so nothing here
needs OpenKOS installed.

Choices fixed here:

* Only ``--json`` and ``--limit`` are passed. ``--allow-unattributed``, ``--include-confidential``
  and ``--save`` are never passed: the query must stay read-only and must not widen what OpenKOS
  discloses (ADR 0006).
* The outcome is read from the report's ``outcome``, never from the exit code: OpenKOS exits
  non-zero for refusals that still print a complete report.
* ``temperature`` and ``seed`` cannot be set on ``query``; the workspace's ``openkos.yaml`` fixes
  them (written by the Experiment A orchestrator). The report echoes them under ``llm``, and
  :func:`require_reproducible` refuses a report that does not carry the expected ones
  (ADR 0006, point 7).
* ``withheld`` counts the concepts OpenKOS refused to name because they are confidential (or
  because the context and the disclosed set disagree, which it treats as fail-closed). The
  corpus has no confidential content and the query never asks for it, so any non-zero count is
  an anomaly the experiment must not paper over (ADR 0006, decision 9).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.extraction.openkos.commands import CommandRunner, OpenKosError

SCHEMA_VERSION = 1
OUTCOME_ANSWERED = "answered"
OUTCOME_NO_MATCH = "no_match"
OUTCOME_NO_ANSWER_IN_CONTEXT = "no_answer_in_context"
OUTCOME_WITHHELD = "withheld"
OUTCOMES = (OUTCOME_ANSWERED, OUTCOME_NO_MATCH, OUTCOME_NO_ANSWER_IN_CONTEXT, OUTCOME_WITHHELD)
_TAIL_CHARS = 2000


class QueryFailedError(OpenKosError):
    """``openkos query`` exited non-zero and printed no report."""


class QueryOutputError(OpenKosError):
    """The standard output of ``openkos query --json`` is not a JSON object."""


class QuerySchemaError(OpenKosError):
    """The report is not a schema-v1 report (wrong version, missing or mistyped field)."""


class QueryRejectedError(OpenKosError):
    """The report is well formed but the experiment must not use it."""


@dataclass(frozen=True, slots=True)
class Sufficiency:
    enabled: bool
    invoked: bool
    refused: bool
    degraded: bool
    raw_reply: str | None


@dataclass(frozen=True, slots=True)
class Attribution:
    status: str
    used_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ContextBlock:
    index: int
    concept_id: str
    title: str
    excerpted: bool
    text: str


@dataclass(frozen=True, slots=True)
class OmittedConcept:
    concept_id: str
    title: str
    reason: str


@dataclass(frozen=True, slots=True)
class RetrievedConcept:
    rank: int
    concept_id: str
    title: str
    fts_rank: int | None
    dense_rank: int | None
    rrf_score: float


@dataclass(frozen=True, slots=True)
class CitedConcept:
    concept_id: str
    title: str
    excerpted: bool


@dataclass(frozen=True, slots=True)
class QueryCounts:
    fts_hits: int
    dense_hits: int
    fused: int
    context_blocks: int


@dataclass(frozen=True, slots=True)
class QueryLlm:
    backend: str
    model: str
    embedding_model: str
    num_ctx: int | None
    num_predict: int | None
    temperature: float | None
    seed: int | None


@dataclass(frozen=True, slots=True)
class QueryPrompts:
    system_sha256: str | None
    user_sha256: str | None
    sufficiency_sha256: str | None


@dataclass(frozen=True, slots=True)
class QueryReport:
    """One ``openkos query --json`` schema-v1 report, with every field it carries."""

    openkos_version: str
    question: str
    limit: int
    outcome: str
    answer: str | None
    withheld: int
    sufficiency: Sufficiency
    attribution: Attribution
    context_blocks: tuple[ContextBlock, ...]
    omitted: tuple[OmittedConcept, ...]
    retrieved: tuple[RetrievedConcept, ...]
    citations: tuple[CitedConcept, ...]
    counts: QueryCounts
    llm: QueryLlm
    prompts: QueryPrompts


def _mapping(value: object, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise QuerySchemaError(f"`{where}` is not an object.")
    return value


def _field(data: Mapping[str, Any], key: str, kind: type | tuple[type, ...], where: str) -> Any:
    if key not in data:
        raise QuerySchemaError(f"`{where}{key}` is missing from the report.")
    value = data[key]
    # bool is an int subclass; a flag is never a number here.
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is not bool):
        raise QuerySchemaError(f"`{where}{key}` has the wrong type.")
    return value


def _nullable(data: Mapping[str, Any], key: str, kind: type | tuple[type, ...], where: str) -> Any:
    if key in data and data[key] is None:
        return None
    return _field(data, key, kind, where)


def _rows(data: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    return [_mapping(row, f"{key}[]") for row in _field(data, key, list, "")]


def parse_query_report(stdout: str) -> QueryReport:
    """Validate ``stdout`` as a schema-v1 report.

    Raises:
        QueryOutputError: ``stdout`` is not a JSON object.
        QuerySchemaError: the version is not 1 or a field is missing or mistyped.
    """
    try:
        loaded = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise QueryOutputError(f"openkos query did not print JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise QueryOutputError("openkos query printed JSON, but not an object.")
    version = loaded.get("schema_version")
    if version != SCHEMA_VERSION or isinstance(version, bool):
        raise QuerySchemaError(
            f"`schema_version` is {version!r}; only schema_version {SCHEMA_VERSION} is supported."
        )
    outcome = _field(loaded, "outcome", str, "")
    if outcome not in OUTCOMES:
        raise QuerySchemaError(f"`outcome` {outcome!r} is not one of {', '.join(OUTCOMES)}.")
    answer = _nullable(loaded, "answer", str, "")
    if outcome == OUTCOME_ANSWERED and answer is None:
        raise QuerySchemaError("`answer` is null although the outcome is `answered`.")
    sufficiency = _mapping(loaded.get("sufficiency"), "sufficiency")
    attribution = _mapping(loaded.get("attribution"), "attribution")
    counts = _mapping(loaded.get("counts"), "counts")
    llm = _mapping(loaded.get("llm"), "llm")
    prompts = _mapping(loaded.get("prompts"), "prompts")
    return QueryReport(
        openkos_version=_field(loaded, "openkos_version", str, ""),
        question=_field(loaded, "question", str, ""),
        limit=_field(loaded, "limit", int, ""),
        outcome=outcome,
        answer=answer,
        withheld=_field(loaded, "withheld", int, ""),
        sufficiency=Sufficiency(
            enabled=_field(sufficiency, "enabled", bool, "sufficiency."),
            invoked=_field(sufficiency, "invoked", bool, "sufficiency."),
            refused=_field(sufficiency, "refused", bool, "sufficiency."),
            degraded=_field(sufficiency, "degraded", bool, "sufficiency."),
            raw_reply=_nullable(sufficiency, "raw_reply", str, "sufficiency."),
        ),
        attribution=Attribution(
            status=_field(attribution, "status", str, "attribution."),
            used_indices=tuple(_field(attribution, "used_indices", list, "attribution.")),
        ),
        context_blocks=tuple(
            ContextBlock(
                index=_field(row, "index", int, "context_blocks[]."),
                concept_id=_field(row, "concept_id", str, "context_blocks[]."),
                title=_field(row, "title", str, "context_blocks[]."),
                excerpted=_field(row, "excerpted", bool, "context_blocks[]."),
                text=_field(row, "text", str, "context_blocks[]."),
            )
            for row in _rows(loaded, "context_blocks")
        ),
        omitted=tuple(
            OmittedConcept(
                concept_id=_field(row, "concept_id", str, "omitted[]."),
                title=_field(row, "title", str, "omitted[]."),
                reason=_field(row, "reason", str, "omitted[]."),
            )
            for row in _rows(loaded, "omitted")
        ),
        retrieved=tuple(
            RetrievedConcept(
                rank=_field(row, "rank", int, "retrieved[]."),
                concept_id=_field(row, "concept_id", str, "retrieved[]."),
                title=_field(row, "title", str, "retrieved[]."),
                fts_rank=_nullable(row, "fts_rank", int, "retrieved[]."),
                dense_rank=_nullable(row, "dense_rank", int, "retrieved[]."),
                rrf_score=float(_field(row, "rrf_score", (int, float), "retrieved[].")),
            )
            for row in _rows(loaded, "retrieved")
        ),
        citations=tuple(
            CitedConcept(
                concept_id=_field(row, "concept_id", str, "citations[]."),
                title=_field(row, "title", str, "citations[]."),
                excerpted=_field(row, "excerpted", bool, "citations[]."),
            )
            for row in _rows(loaded, "citations")
        ),
        counts=QueryCounts(
            fts_hits=_field(counts, "fts_hits", int, "counts."),
            dense_hits=_field(counts, "dense_hits", int, "counts."),
            fused=_field(counts, "fused", int, "counts."),
            context_blocks=_field(counts, "context_blocks", int, "counts."),
        ),
        llm=QueryLlm(
            backend=_field(llm, "backend", str, "llm."),
            model=_field(llm, "model", str, "llm."),
            embedding_model=_field(llm, "embedding_model", str, "llm."),
            num_ctx=_nullable(llm, "num_ctx", int, "llm."),
            num_predict=_nullable(llm, "num_predict", int, "llm."),
            temperature=_nullable(llm, "temperature", (int, float), "llm."),
            seed=_nullable(llm, "seed", int, "llm."),
        ),
        prompts=QueryPrompts(
            system_sha256=_nullable(prompts, "system_sha256", str, "prompts."),
            user_sha256=_nullable(prompts, "user_sha256", str, "prompts."),
            sufficiency_sha256=_nullable(prompts, "sufficiency_sha256", str, "prompts."),
        ),
    )


def query_args(executable: str, question: str, *, limit: int) -> list[str]:
    """The command line of one query: ``--json`` and ``--limit`` and nothing else."""
    return [executable, "query", question, "--json", "--limit", str(limit)]


def run_query(
    runner: CommandRunner, executable: str, workspace: Path, question: str, *, limit: int
) -> QueryReport:
    """Run ``openkos query`` in ``workspace`` and return its validated report.

    Raises:
        QueryFailedError: a non-zero exit with no JSON on stdout.
        QueryOutputError, QuerySchemaError: see :func:`parse_query_report`.
    """
    result = runner.run(query_args(executable, question, limit=limit), cwd=workspace)
    try:
        return parse_query_report(result.stdout)
    except QueryOutputError as exc:
        if result.returncode != 0:
            raise QueryFailedError(
                f"openkos query exited {result.returncode} without a report: "
                f"{result.stderr[-_TAIL_CHARS:]}"
            ) from exc
        raise


def require_reproducible(
    report: QueryReport, *, expected_seed: int, expected_temperature: float
) -> None:
    """Refuse a report the experiment cannot use.

    Raises:
        QueryRejectedError: something was withheld, or the generation did not run with
            ``expected_temperature`` (compared as floats) and ``expected_seed``; any such state
            means the workspace is not the one the run was meant to query.
    """
    if report.outcome == OUTCOME_WITHHELD or report.withheld > 0:
        raise QueryRejectedError(
            f"OpenKOS withheld content (outcome {report.outcome!r}, withheld {report.withheld}); "
            "the corpus holds nothing confidential, so the workspace is not trustworthy."
        )
    if report.llm.temperature is None:
        raise QueryRejectedError(
            "The workspace reports a null llm.temperature: generation is not reproducible "
            "(ADR 0006, point 7)."
        )
    if not math.isclose(report.llm.temperature, expected_temperature, rel_tol=0, abs_tol=1e-9):
        raise QueryRejectedError(
            f"The workspace reports llm.temperature {report.llm.temperature}, expected "
            f"{expected_temperature}: it is not the workspace of this run."
        )
    if report.llm.seed is None:
        raise QueryRejectedError(
            "The workspace reports a null llm.seed: generation is not reproducible "
            "(ADR 0006, point 7)."
        )
    if report.llm.seed != expected_seed:
        raise QueryRejectedError(
            f"The workspace reports llm.seed {report.llm.seed}, expected {expected_seed}: "
            "it is not the workspace of this run."
        )
