"""Human verification of the automatic judge on Experiment B (thesis section 5.7; OE3).

Preregistered rule (``docs/avances/06-jss-metodologia.md``): a human labels 20 % of the judged
answers and the judge-human Cohen's kappa must reach 0.70. The verdict is given PER LABEL
(ADR 0010):

* ``correct`` gates the automatic judging of the primary metric: if its kappa does not reach
  the threshold, the answer correctness is reported only with the human evaluation;
* ``evidence_supported`` has its own reliable / not-reliable flag, used by the report: if it
  does not reach the threshold, that metric is reported only with the human evaluation or
  marked as not reliable. It never gates the primary metric.

The kappa is undefined when judge and humans use a single class; that counts as "does not
pass". Because kappa alone can mislead (undefined, or low when one class dominates), every label
always reports its observed agreement and the share of positive labels of the judge and of the
humans (class prevalence) next to the kappa.

Two files come out of the sample, following the second-labeler convention of
:mod:`afg.evaluation.judge_calibration_agreement`:

* the **sheet** the human fills: opaque ids, question, answer and two empty label columns. It
  hides the condition, the run and the judge verdict, so the person cannot be steered;
* the **key**, kept apart: id -> question, condition, run, stratum and the judge's labels.

The sample takes ONE randomly drawn judged run per (question, condition): runs of a question
are repeated measures of one item and the analysis counts questions (see
:mod:`afg.experiments.analysis`). Per condition x stratum cell its size is
``ceil(fraction * judged answers)`` of the cell, capped at the (question, condition) pairs
available. Pairs are drawn with a seeded generator over the sorted records and then shuffled
before the opaque ids are assigned, so neither the id nor the row order reveals the condition.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question
from afg.evaluation.judge_calibration_agreement import (
    SECOND_SHEET_COLUMNS,
    AgreementError,
    compute_human_agreement,
    write_second_sheet,
)
from afg.shared.csvio import read_rows

__all__ = [
    "EVIDENCE_COLUMN",
    "GATING_COLUMN",
    "KEY_COLUMNS",
    "SHEET_COLUMNS",
    "HumanSample",
    "JudgeHumanCheck",
    "LabelVerdict",
    "check_judge_against_humans",
    "question_context_for",
    "read_csv_rows",
    "save_judge_human_check",
    "select_human_sample",
    "write_human_sample",
]

SHEET_COLUMNS: tuple[str, ...] = SECOND_SHEET_COLUMNS
KEY_COLUMNS: tuple[str, ...] = (
    "id",
    "question_id",
    "condition",
    "run",
    "stratum",
    "judge_correct",
    "judge_evidence_supported",
)
GATING_COLUMN = "correct"
EVIDENCE_COLUMN = "evidence_supported"
KEEP_DECISION = (
    "Se mantiene el juicio automático de la corrección de respuesta (correct): el acuerdo "
    "juez-humano alcanza el umbral."
)
DISCARD_DECISION = (
    "Se descarta el juicio automático de la corrección de respuesta (correct): el acuerdo "
    "juez-humano no alcanza el umbral y se reporta solo la evaluación humana."
)
UNDEFINED_KAPPA_NOTE = (
    ' El kappa es indefinido (juez y personas usan una sola clase) y cuenta como "no cumple"; '
    "se informa el acuerdo observado y la prevalencia."
)
EVIDENCE_RELIABLE_DECISION = (
    "evidence_supported es confiable: el acuerdo juez-humano alcanza el umbral."
)
EVIDENCE_UNRELIABLE_DECISION = (
    "evidence_supported no confiable: el acuerdo juez-humano no alcanza el umbral; esa métrica "
    "se reporta solo con evaluación humana o marcada como no confiable."
)
POSITIVE_LABELS = frozenset({"si", "sí", "true", "1", "yes"})

Record = Mapping[str, Any]
ContextFor = Callable[[Record], tuple[str, str]]
"""``record -> (transcript passage, transcript files)`` for the sheet; blank when not given."""


def question_context_for(
    questions: Iterable[Question],
    *,
    excerpt_for: Callable[[Question], str] | None = None,
    files_for: Callable[[Sequence[EvidenceSpan]], str] | None = None,
) -> ContextFor:
    """The sheet's passage and transcript files, built as the judge and the calibration sheet do.

    The passage is the one the Experiment B runner hands the judge as ``transcript_excerpt``
    (``default_excerpt_for``) and the files are those of the calibration worksheet
    (``transcript_files_text``); a question without evidence (E4) gets both blank, as there.

    Raises:
        ValueError: (when the returned callable runs) the record's question is not in
            ``questions``.
    """
    from afg.evaluation import passage
    from afg.experiments import runner

    by_id = {q.id: q for q in questions}
    excerpt = excerpt_for or runner.default_excerpt_for
    files = files_for or passage.transcript_files_text
    cache: dict[str, tuple[str, str]] = {}

    def context_for(record: Record) -> tuple[str, str]:
        question_id = str(record["question_id"])
        if question_id not in cache:
            question = by_id.get(question_id)
            if question is None:
                raise ValueError(f"Question {question_id!r} is not in the question file.")
            cache[question_id] = (excerpt(question), files(question.reference_evidence))
        return cache[question_id]

    return context_for


@dataclass(frozen=True, slots=True)
class HumanSample:
    sheet_rows: list[dict[str, str]]
    key_rows: list[dict[str, str]]
    per_cell: dict[tuple[str, str], tuple[int, int]]
    """``(condition, stratum) -> (judged answers, sampled)``."""
    pairs_per_cell: dict[tuple[str, str], int] = field(default_factory=dict)
    """``(condition, stratum) -> (question, condition) pairs with a judged run``."""


@dataclass(frozen=True, slots=True)
class LabelVerdict:
    """Judge-human agreement on one label, with the figures that give the kappa its context."""

    column: str
    n_items: int
    n_agree: int
    observed_agreement: float
    kappa: float | None
    """``None`` when undefined (a single class on both sides); it counts as not passing."""
    judge_positive_rate: float
    human_positive_rate: float
    disagreements: tuple[str, ...]
    passes: bool


@dataclass(frozen=True, slots=True)
class JudgeHumanCheck:
    n_items: int
    min_kappa: float
    columns: tuple[LabelVerdict, ...]
    keep_automatic_judging: bool
    """``correct`` reaches the threshold: the automatic judging of the primary metric stands."""
    decision: str
    evidence_supported_reliable: bool
    """``evidence_supported`` reaches the threshold; otherwise the report marks it as such."""
    evidence_decision: str


def _stratum(record: Record) -> str:
    return str(record["stratum"]).split("_", 1)[0]


def _is_judged(record: Record) -> bool:
    return (
        record.get("error") is None
        and record.get("judge_failure") is None
        and bool(record.get("verdict"))
    )


def _yes_no(value: Any) -> str:
    return "si" if value else "no"


def select_human_sample(
    records: Iterable[Record],
    *,
    fraction: float,
    seed: int,
    reference_answers: Mapping[str, str] | None = None,
    context_for: ContextFor | None = None,
) -> HumanSample:
    """The seeded, stratified sample for the human check: one judged run per (question, condition).

    Raises:
        ValueError: ``fraction`` outside (0, 1], or no judged answer to sample from.
    """
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1].")
    judged = sorted(
        (r for r in records if _is_judged(r)),
        key=lambda r: (str(r["condition"]), str(r["question_id"]), int(r["run"])),
    )
    if not judged:
        raise ValueError("There are no judged answers to sample from.")
    cells: dict[tuple[str, str], list[Record]] = {}
    for record in judged:
        cells.setdefault((str(record["condition"]), _stratum(record)), []).append(record)

    rng = random.Random(seed)
    chosen: list[Record] = []
    per_cell: dict[tuple[str, str], tuple[int, int]] = {}
    pairs_per_cell: dict[tuple[str, str], int] = {}
    for cell in sorted(cells):
        members = cells[cell]
        runs_of: dict[str, list[Record]] = {}
        for record in members:
            runs_of.setdefault(str(record["question_id"]), []).append(record)
        questions = sorted(runs_of)
        take = min(len(questions), math.ceil(fraction * len(members)))
        for question_id in rng.sample(questions, take):
            chosen.append(rng.choice(runs_of[question_id]))
        per_cell[cell] = (len(members), take)
        pairs_per_cell[cell] = len(questions)
    rng.shuffle(chosen)

    sheet_rows: list[dict[str, str]] = []
    key_rows: list[dict[str, str]] = []
    for index, record in enumerate(chosen, start=1):
        item_id = f"h{index:03d}"
        passage, files = context_for(record) if context_for else ("", "")
        sheet = dict.fromkeys(SHEET_COLUMNS, "")
        sheet.update(
            id=item_id,
            stratum=_stratum(record),
            question=str((record.get("trace") or {}).get("question") or ""),
            reference_answer=(reference_answers or {}).get(str(record["question_id"]), ""),
            answer_text=str((record.get("answer") or {}).get("text") or ""),
            pasaje_transcripcion=passage,
            archivos_transcripcion=files,
        )
        sheet_rows.append(sheet)
        verdict = record["verdict"]
        key_rows.append(
            {
                "id": item_id,
                "question_id": str(record["question_id"]),
                "condition": str(record["condition"]),
                "run": str(record["run"]),
                "stratum": _stratum(record),
                "judge_correct": _yes_no(verdict.get("correct")),
                "judge_evidence_supported": _yes_no(verdict.get("evidence_supported")),
            }
        )
    return HumanSample(
        sheet_rows=sheet_rows,
        key_rows=key_rows,
        per_cell=per_cell,
        pairs_per_cell=pairs_per_cell,
    )


def write_human_sample(
    sheet_path: Path, key_path: Path, sample: HumanSample, *, force: bool = False
) -> None:
    """Write the blind sheet and the key; refuse to erase a sheet that already has labels."""
    write_second_sheet(sheet_path, sample.sheet_rows, force=force)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with key_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=KEY_COLUMNS)
        writer.writeheader()
        writer.writerows(sample.key_rows)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a sheet or key CSV (UTF-8, BOM tolerated)."""
    return read_rows(path)


def check_judge_against_humans(
    key_rows: Sequence[Mapping[str, str]],
    sheet_rows: Sequence[Mapping[str, str]],
    *,
    min_kappa: float,
) -> JudgeHumanCheck:
    """Cohen's kappa judge vs human per label and the keep-or-discard decision.

    Raises:
        AgreementError: a sampled id is missing from the sheet, the sheet has an unknown id, or
            a label is empty or invalid (the message names the item).
    """
    answered = {row["id"] for row in sheet_rows}
    missing = sorted(row["id"] for row in key_rows if row["id"] not in answered)
    if missing:
        raise AgreementError(f"The sheet has no row for the sampled item(s): {missing}")
    judge_rows = [
        {
            "id": row["id"],
            "correct": row["judge_correct"],
            "evidence_supported": row["judge_evidence_supported"],
        }
        for row in key_rows
    ]
    agreements = compute_human_agreement(judge_rows, sheet_rows, min_kappa=min_kappa)
    judge_by_id = {row["id"]: row for row in judge_rows}
    human_ids = [row["id"] for row in sheet_rows]
    human_by_id = {row["id"]: row for row in sheet_rows}
    columns = tuple(
        LabelVerdict(
            column=agreement.column,
            n_items=agreement.n_items,
            n_agree=agreement.n_agree,
            observed_agreement=agreement.n_agree / agreement.n_items,
            kappa=agreement.kappa,
            judge_positive_rate=_positive_rate(judge_by_id, human_ids, agreement.column),
            human_positive_rate=_positive_rate(human_by_id, human_ids, agreement.column),
            disagreements=agreement.disagreements,
            passes=agreement.passes,
        )
        for agreement in agreements
    )
    gating = next(c for c in columns if c.column == GATING_COLUMN)
    evidence = next(c for c in columns if c.column == EVIDENCE_COLUMN)
    return JudgeHumanCheck(
        n_items=len(sheet_rows),
        min_kappa=min_kappa,
        columns=columns,
        keep_automatic_judging=gating.passes,
        decision=(KEEP_DECISION if gating.passes else DISCARD_DECISION)
        + (UNDEFINED_KAPPA_NOTE if gating.kappa is None else ""),
        evidence_supported_reliable=evidence.passes,
        evidence_decision=(
            EVIDENCE_RELIABLE_DECISION if evidence.passes else EVIDENCE_UNRELIABLE_DECISION
        )
        + (UNDEFINED_KAPPA_NOTE if evidence.kappa is None else ""),
    )


def _positive_rate(rows: Mapping[str, Mapping[str, str]], ids: Sequence[str], column: str) -> float:
    """Share of positive labels among the sampled items (labels were validated upstream)."""
    positives = sum(rows[i][column].strip().lower() in POSITIVE_LABELS for i in ids)
    return positives / len(ids)


def save_judge_human_check(path: Path, check: JudgeHumanCheck) -> None:
    """Store the check next to the run so the report reads it without recomputing."""
    payload = {
        "n_items": check.n_items,
        "min_kappa": check.min_kappa,
        "gating_column": GATING_COLUMN,
        "keep_automatic_judging": check.keep_automatic_judging,
        "decision": check.decision,
        "evidence_supported_reliable": check.evidence_supported_reliable,
        "evidence_decision": check.evidence_decision,
        "columns": [
            {
                "column": c.column,
                "n_items": c.n_items,
                "n_agree": c.n_agree,
                "observed_agreement": c.observed_agreement,
                "judge_positive_rate": c.judge_positive_rate,
                "human_positive_rate": c.human_positive_rate,
                "kappa": c.kappa,
                "disagreements": list(c.disagreements),
                "passes": c.passes,
            }
            for c in check.columns
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
