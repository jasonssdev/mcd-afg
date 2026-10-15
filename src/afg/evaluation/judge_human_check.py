"""Human verification of the automatic judge on Experiment B (thesis section 5.7; OE3).

Preregistered rule (``docs/avances/06-jss-metodologia.md``): a human labels 20 % of the judged
answers and the judge-human Cohen's kappa must reach 0.70; otherwise the automatic judging is
discarded and only the human evaluation is reported.

Two files come out of the sample, following the second-labeler convention of
:mod:`afg.evaluation.judge_calibration_agreement`:

* the **sheet** the human fills: opaque ids, question, answer and two empty label columns. It
  hides the condition, the run and the judge verdict, so the person cannot be steered;
* the **key**, kept apart: id -> question, condition, run, stratum and the judge's labels.

The sample is stratified by condition x stratum (``ceil(fraction * judged answers)`` per cell, so
every cell is covered at least at the requested fraction), drawn with a seeded generator over the
sorted records and then shuffled before the opaque ids are assigned, so neither the id nor the
row order reveals the condition. The decision is gated on the ``correct`` label (the one
``[judge.calibration].min_kappa_correct`` and the D16 criterion rest on); ``evidence_supported``
is reported with its own pass flag.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question
from afg.evaluation.judge_calibration_agreement import (
    SECOND_SHEET_COLUMNS,
    AgreementError,
    ColumnAgreement,
    compute_human_agreement,
    write_second_sheet,
)

__all__ = [
    "GATING_COLUMN",
    "KEY_COLUMNS",
    "SHEET_COLUMNS",
    "HumanSample",
    "JudgeHumanCheck",
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
KEEP_DECISION = "Se mantiene el juicio automático: el acuerdo juez-humano alcanza el umbral."
DISCARD_DECISION = (
    "Se descarta el juicio automático: el acuerdo juez-humano no alcanza el umbral y se reporta "
    "solo la evaluación humana."
)

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


@dataclass(frozen=True, slots=True)
class JudgeHumanCheck:
    n_items: int
    min_kappa: float
    columns: tuple[ColumnAgreement, ...]
    keep_automatic_judging: bool
    decision: str


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
    """The seeded, stratified sample of judged answers for the human check.

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
    for cell in sorted(cells):
        members = cells[cell]
        take = min(len(members), math.ceil(fraction * len(members)))
        chosen.extend(rng.sample(members, take))
        per_cell[cell] = (len(members), take)
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
    return HumanSample(sheet_rows=sheet_rows, key_rows=key_rows, per_cell=per_cell)


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
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{k: v or "" for k, v in row.items()} for row in csv.DictReader(handle)]


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
    columns = compute_human_agreement(judge_rows, sheet_rows, min_kappa=min_kappa)
    gating = next(c for c in columns if c.column == GATING_COLUMN)
    return JudgeHumanCheck(
        n_items=len(sheet_rows),
        min_kappa=min_kappa,
        columns=columns,
        keep_automatic_judging=gating.passes,
        decision=KEEP_DECISION if gating.passes else DISCARD_DECISION,
    )


def save_judge_human_check(path: Path, check: JudgeHumanCheck) -> None:
    """Store the check next to the run so the report reads it without recomputing."""
    payload = {
        "n_items": check.n_items,
        "min_kappa": check.min_kappa,
        "gating_column": GATING_COLUMN,
        "keep_automatic_judging": check.keep_automatic_judging,
        "decision": check.decision,
        "columns": [
            {
                "column": c.column,
                "n_items": c.n_items,
                "n_agree": c.n_agree,
                "kappa": c.kappa,
                "disagreements": list(c.disagreements),
                "passes": c.passes,
            }
            for c in check.columns
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
