"""C2 -- structured base built automatically by LLM extraction (thesis section 5.3).

The proposal under test: extraction with a local model, persistence with provenance,
querying over the compiled objects.

C2 answers each question with ``openkos query <question> --json --limit K`` run inside the
OpenKOS workspace that ``afg experiment a`` compiled for the question's series. OpenKOS is the
instrument and is used unmodified (ADR 0006, decision 2): the answer text, the abstentions and
the citations are exactly what its report says, which is also what C1 copies, so the two are
comparable. Only the adapter package contacts OpenKOS (ADR 0003); this module wires it to the
:class:`~afg.conditions.base.Condition` interface.

Binding to Experiment A (``extraction_run`` is the ``--run-name`` of an ``afg experiment a``):

* The Experiment B runner calls :meth:`CompiledAutoCondition.with_seed` with ``base_seed + r``
  before each run ``r``; C2 reads ``r = seed - base_seed`` from it and queries
  ``<base_dir>/<extraction_run>/<series>/run-<r>/``. That is the workspace whose
  ``openkos.yaml`` was written with exactly that seed, and the report's ``llm.seed`` is checked
  against it, so a mismatch between the two experiments cannot go unnoticed.
* A report that withheld content, or that carries a null temperature or seed, is refused (an
  exception, which the runner stores as an error of that key); it is never turned into an answer.

Citations are the concepts in the report's ``citations``, mapped to the dialogue acts of the
quote that supports each decision (the bundle reader of Experiment A). A cited concept that is
not a decision with locatable evidence yields no span and is listed in the trace.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

from afg.conditions.c1_document_rag import NO_ANSWER_IN_CONTEXT, NO_MATCH
from afg.domain.decision import EvidenceSpan
from afg.domain.question import Answer, Question
from afg.extraction.openkos.bundle_reader import read_decision_bundle
from afg.extraction.openkos.capabilities import probe_capabilities, require_capabilities
from afg.extraction.openkos.commands import CommandRunner, OpenKosError
from afg.extraction.openkos.event_dates import POSITION_LETTERS
from afg.extraction.openkos.query import (
    OUTCOME_ANSWERED,
    OUTCOME_NO_ANSWER_IN_CONTEXT,
    Attribution,
    CitedConcept,
    ContextBlock,
    OmittedConcept,
    QueryCounts,
    QueryLlm,
    QueryPrompts,
    RetrievedConcept,
    Sufficiency,
    require_reproducible,
    run_query,
)
from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.extraction.openkos_adapter import BUNDLE_DIRNAME, project_relative
from afg.shared.config import load_experiments_config
from afg.shared.paths import OPENKOS_WORKSPACES_DIR, TRANSCRIPTS_DIR


class WorkspaceNotFoundError(OpenKosError):
    """The Experiment A run has no workspace for the series and run being queried."""


def configured_answer_limit() -> int:
    """``--limit`` of ``openkos query`` for C2: ``[retrieval] answer_limit`` of the config."""
    return int(load_experiments_config()["retrieval"]["answer_limit"])


@dataclass(frozen=True, slots=True)
class CompiledAutoTrace:
    """Everything a schema-v1 report says about one C2 answer, plus where it came from.

    ``cited_acts`` maps each cited concept that has evidence to ``{meeting_id: dialogue act
    ids}``; ``unmapped_cited`` lists the cited concepts that do not (in citation order).
    """

    outcome: str
    question: str
    limit: int
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
    openkos_version: str
    workspace: str
    run: int
    cited_acts: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    unmapped_cited: tuple[str, ...] = ()


@dataclass(slots=True)
class _Shared:
    """State shared by every copy made by ``with_seed`` (capabilities, evidence per workspace)."""

    capabilities_checked: bool = False
    evidence: dict[Path, dict[str, EvidenceSpan]] = field(default_factory=dict)


@dataclass(slots=True)
class CompiledAutoCondition:
    """C2: query the OpenKOS workspaces compiled automatically by ``afg experiment a``."""

    runner: CommandRunner
    settings: OpenKosRunSettings
    extraction_run: str
    base_dir: Path = OPENKOS_WORKSPACES_DIR
    transcripts_dir: Path = TRANSCRIPTS_DIR
    limit: int = field(default_factory=configured_answer_limit)
    condition_id: str = "C2"
    run: int | None = None
    _shared: _Shared = field(default_factory=_Shared, init=False, repr=False)

    def with_seed(self, seed: int) -> CompiledAutoCondition:
        """A copy bound to run ``seed - base_seed`` (the runner's seed of run ``r`` is base + r).

        Caches are shared with the original, so re-seeding does not read a bundle twice.
        """
        run = seed - self.settings.base_seed
        if run < 0:
            raise ValueError(
                f"Seed {seed} is below the base seed {self.settings.base_seed}: "
                "C2 cannot tell which run's workspace to query."
            )
        copy = dataclasses.replace(self, run=run)
        copy._shared = self._shared
        return copy

    def _workspace(self, series_id: str, run: int) -> Path:
        workspace = self.base_dir / self.extraction_run / series_id / f"run-{run}"
        if not (workspace / BUNDLE_DIRNAME).is_dir():
            raise WorkspaceNotFoundError(
                f"No workspace for {series_id} run-{run} in the Experiment A run "
                f"{self.extraction_run!r} ({project_relative(workspace)}). Run "
                f"`afg experiment a --run-name {self.extraction_run}` with enough runs first."
            )
        return workspace

    def _evidence(self, workspace: Path, series_id: str) -> dict[str, EvidenceSpan]:
        """Concept id -> evidence span of the decisions of ``workspace``, read once."""
        if workspace not in self._shared.evidence:
            read = read_decision_bundle(
                workspace / BUNDLE_DIRNAME,
                series_id=series_id,
                meeting_ids=[f"{series_id}{letter}" for letter in POSITION_LETTERS],
                transcripts_dir=self.transcripts_dir,
            )
            self._shared.evidence[workspace] = {d.id: d.evidence for d in read.decisions}
        return self._shared.evidence[workspace]

    def _require_capabilities(self) -> None:
        if not self._shared.capabilities_checked:
            require_capabilities(probe_capabilities(self.runner, self.settings.executable))
            self._shared.capabilities_checked = True

    def answer(self, question: Question) -> Answer:
        """Answer ``question``; see :meth:`answer_with_trace` for the recorded trace."""
        return self.answer_with_trace(question)[0]

    def answer_with_trace(self, question: Question) -> tuple[Answer, CompiledAutoTrace]:
        """Query the workspace of ``(question.series_id, run)`` and map the report to an answer.

        Raises:
            ValueError: the condition was not bound to a run with :meth:`with_seed`.
            WorkspaceNotFoundError: that workspace does not exist.
            afg.extraction.openkos.capabilities.MissingCapabilitiesError: no ``query --json``.
            afg.extraction.openkos.query.QueryRejectedError: withheld content, null or
                unexpected temperature or seed.
            afg.extraction.openkos.commands.OpenKosError: the query failed or printed a report
                that is not schema v1.
        """
        if self.run is None:
            raise ValueError("C2 needs a run: call with_seed(base_seed + run) before answering.")
        workspace = self._workspace(question.series_id, self.run)
        self._require_capabilities()
        report = run_query(
            self.runner, self.settings.executable, workspace, question.text, limit=self.limit
        )
        require_reproducible(
            report,
            expected_seed=self.settings.seed_for(self.run),
            expected_temperature=self.settings.temperature,
        )

        spans: list[EvidenceSpan] = []
        cited_acts: dict[str, dict[str, tuple[str, ...]]] = {}
        unmapped: list[str] = []
        if report.outcome == OUTCOME_ANSWERED:
            evidence = self._evidence(workspace, question.series_id)
            for cited in report.citations:
                span = evidence.get(cited.concept_id)
                if span is None:
                    unmapped.append(cited.concept_id)
                    continue
                cited_acts[cited.concept_id] = {span.meeting_id: tuple(span.dialogue_act_ids)}
                if span not in spans:
                    spans.append(span)

        answered = report.outcome == OUTCOME_ANSWERED
        text = (
            (report.answer or "")
            if answered
            else NO_ANSWER_IN_CONTEXT
            if report.outcome == OUTCOME_NO_ANSWER_IN_CONTEXT
            else NO_MATCH
        )
        answer = Answer(
            question_id=question.id,
            condition=self.condition_id,
            text=text,
            cited_evidence=tuple(spans),
            abstained=not answered,
        )
        trace = CompiledAutoTrace(
            outcome=report.outcome,
            question=report.question,
            limit=report.limit,
            answer=report.answer,
            withheld=report.withheld,
            sufficiency=report.sufficiency,
            attribution=report.attribution,
            context_blocks=report.context_blocks,
            omitted=report.omitted,
            retrieved=report.retrieved,
            citations=report.citations,
            counts=report.counts,
            llm=report.llm,
            prompts=report.prompts,
            openkos_version=report.openkos_version,
            workspace=project_relative(workspace),
            run=self.run,
            cited_acts=cited_acts,
            unmapped_cited=tuple(unmapped),
        )
        return answer, trace
