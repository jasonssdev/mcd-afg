"""Answer generation for the judge calibration set (thesis section 5.7, issue #82).

A person writes the calibration questions (with reference answer and evidence) from the
adjudicated decisions of a development series. This module turns each question into two
system answers with the generative model, so the set holds correct and incorrect answers in
similar proportion:

* ``grounded``: the model sees the transcript passage that covers the reference dialogue
  acts, so it can answer correctly.
* ``ungrounded``: the model sees a passage of the same series that contains none of those
  acts, chosen deterministically from the seed, and is told to answer anyway, so a confident
  wrong answer is likely.
* E4 (unanswerable) questions have no reference acts: they get the ``ungrounded`` passage
  and a ``no_context`` answer instead.

The variant that produced each answer is recorded in a sidecar file (``id,answer_variant``,
see :func:`afg.evaluation.judge_calibration_set.variants_path`) and never shown to the labelers
or the judge; the rows of the labeling file are shuffled with ``[shared_budget].seed`` so
neither the variant nor the pairing of the two answers can be read from the order.
The human labels (``correct``, ``evidence_supported``) are left empty: labels are always human.
Temperature, seed and top-p come from ``[shared_budget]``.
"""

from __future__ import annotations

import csv
import random
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from afg.conditions.c1_chunking import FrozenTurn, load_frozen_turns
from afg.domain.decision import EvidenceSpan
from afg.domain.question import (
    QuestionStratum,
    format_reference_evidence,
    parse_reference_evidence,
)
from afg.evaluation.judge_calibration_set import (
    COLUMNS,
    VARIANT_COLUMNS,
    CalibrationSetError,
    DevelopmentSplitError,
    calibration_series,
    load_variants,
    variants_path,
)
from afg.evaluation.passage import (
    evidence_passage,
    judge_evidence_passage,
    render_turns,
    transcript_files_text,
)
from afg.shared.config import load_experiments_config
from afg.shared.csvio import open_csv_writer
from afg.shared.paths import JUDGE_CALIBRATION_DIR, TRANSCRIPTS_DIR

QUESTIONS_TEMPLATE_PATH: Path = JUDGE_CALIBRATION_DIR / "_plantilla-preguntas-calibracion.csv"
QUESTIONS_PATH: Path = JUDGE_CALIBRATION_DIR / "preguntas-calibracion-juez.csv"
CALIBRATION_PATH: Path = JUDGE_CALIBRATION_DIR / "calibracion-juez.csv"

QUESTION_COLUMNS: tuple[str, ...] = (
    "id",
    "series_id",
    "stratum",
    "question",
    "reference_answer",
    "reference_evidence",
)

ABSTAIN_MARKER = "NO_ANSWER"
ABSTENTION_TEXT = "The material does not contain enough information to answer."
"""Stored as the answer text when the model abstains; questions, answers and the judge prompt
are in English, like the question bank."""

_NO_CONTEXT = "(none)"
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)

_SYSTEM_PROMPT = (
    "You answer questions about a meeting using only the context you are given. "
    "Answer in the language of the question, in at most three sentences. "
    "Do not use outside knowledge. "
    f"If the context does not contain the answer, reply with exactly {ABSTAIN_MARKER}."
)

_FORCED_SYSTEM_PROMPT = (
    "You answer questions about a meeting using the context you are given. "
    "Answer in the language of the question, in at most three sentences. "
    "Always give a direct, confident answer; never say that the context lacks the answer."
)
"""Used for the ``ungrounded`` answer of an answerable question. Left free to abstain, the
model abstains on almost every wrong passage, and the set then tests only whether the judge
rejects abstentions. Forcing an answer yields the failure section 5.6 singles out as the most
dangerous one: a confident answer that the evidence does not support."""


class CalibrationQuestion(BaseModel):
    """A human-written calibration question with its reference answer and evidence."""

    model_config = ConfigDict(frozen=True)

    id: str
    series_id: str
    stratum: QuestionStratum
    question: str
    reference_answer: str | None = None
    reference_evidence: tuple[EvidenceSpan, ...] = Field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    variant: str
    text: str
    abstained: bool


@dataclass(frozen=True, slots=True)
class GenerationReport:
    questions_processed: int
    questions_skipped: int
    rows_written: int

    def summary(self) -> str:
        if self.questions_processed == 0 and self.questions_skipped == 0:
            return "No questions to process: the question file is empty; nothing was generated."
        return (
            f"Generated {self.rows_written} answers for {self.questions_processed} questions "
            f"({self.questions_skipped} already present, skipped)."
        )


class GenerationBackend(Protocol):
    """Runs one generation call and returns the raw text. Injectable; tests use a fake."""

    def generate(
        self, system: str, user: str, *, model: str, seed: int, temperature: float, top_p: float
    ) -> str: ...


class OllamaGenerationBackend:
    """Generation through a local Ollama server; needs the optional ``llm`` extra.

    The client is imported on first use so the rest of the package works without it.
    """

    def __init__(self, host: str | None = None) -> None:
        self._host = host

    def generate(
        self, system: str, user: str, *, model: str, seed: int, temperature: float, top_p: float
    ) -> str:
        try:
            import ollama
        except ImportError as exc:
            raise RuntimeError(
                "OllamaGenerationBackend needs the optional `llm` extra: `uv sync --extra llm`."
            ) from exc
        from afg.conditions.c1_retrieval import resolve_ollama_host

        client = ollama.Client(host=self._host or resolve_ollama_host())
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options={"temperature": temperature, "seed": seed, "top_p": top_p},
        )
        return str(response.message.content or "")


# --- questions -------------------------------------------------------------------------------


def load_calibration_questions(path: Path) -> list[CalibrationQuestion]:
    """Read the calibration question CSV (BOM accepted), guarding series and evidence."""
    allowed = calibration_series()
    questions: list[CalibrationQuestion] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in QUESTION_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise CalibrationSetError(f"{path.name}: missing columns {missing}")
        for row in reader:
            qid = (row["id"] or "").strip()
            series = (row["series_id"] or "").strip()
            if series not in allowed:
                raise DevelopmentSplitError(
                    f"question {qid!r}: series {series!r} is not one of the calibration "
                    f"series {sorted(allowed)} (development split only, ADR 0005)."
                )
            try:
                question = CalibrationQuestion(
                    id=qid,
                    series_id=series,
                    stratum=QuestionStratum((row["stratum"] or "").strip()),
                    question=row["question"],
                    reference_answer=row["reference_answer"] or None,
                    reference_evidence=parse_reference_evidence(row["reference_evidence"] or ""),
                )
            except ValueError as exc:
                raise CalibrationSetError(f"question {qid!r}: {exc}") from exc
            unanswerable = question.stratum is QuestionStratum.E4_UNANSWERABLE
            if unanswerable and (question.reference_answer or question.reference_evidence):
                raise CalibrationSetError(
                    f"question {qid!r}: E4 questions carry no reference answer or evidence."
                )
            if not unanswerable and not (question.reference_answer and question.reference_evidence):
                raise CalibrationSetError(
                    f"question {qid!r}: answerable questions need a reference answer and "
                    "reference evidence."
                )
            questions.append(question)
    return questions


# --- passages --------------------------------------------------------------------------------


def grounded_passage(
    question: CalibrationQuestion,
    *,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    context_turns: int = 2,
) -> str:
    """The transcript passage covering the reference acts, padded by ``context_turns``.

    The windowing is shared with the judge's excerpt (:func:`afg.evaluation.passage.
    evidence_passage`); only the padding differs.

    Raises:
        ValueError: if a reference act does not appear in its meeting's frozen transcript.
    """
    return evidence_passage(
        question.reference_evidence, context_turns=context_turns, transcripts_dir=transcripts_dir
    )


def ungrounded_passage(
    question: CalibrationQuestion,
    *,
    seed: int,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    window_turns: int = 12,
) -> str:
    """A passage of the same series with none of the reference acts, picked from the seed.

    Each meeting of the series is tiled into consecutive windows of ``window_turns`` turns;
    the windows that contain a reference act are dropped and one of the rest is drawn with a
    generator seeded by ``seed`` and the question id, so the choice is reproducible.

    Raises:
        ValueError: if every window contains a reference act.
    """
    reference_acts = {a for s in question.reference_evidence for a in s.dialogue_act_ids}
    meetings = sorted(path.stem for path in transcripts_dir.glob(f"{question.series_id}*.jsonl"))
    windows: list[tuple[str, list[FrozenTurn]]] = []
    for meeting_id in meetings:
        turns = load_frozen_turns(meeting_id, transcripts_dir)
        for start in range(0, len(turns), window_turns):
            window = turns[start : start + window_turns]
            if reference_acts.isdisjoint(a for t in window for a in t.dialogue_act_ids):
                windows.append((meeting_id, window))
    if not windows:
        raise ValueError(
            f"no passage of series {question.series_id} is free of the reference acts of "
            f"question {question.id!r} (window of {window_turns} turns)."
        )
    meeting_id, window = random.Random(f"{seed}:{question.id}").choice(windows)
    return render_turns(meeting_id, window)


# --- answers ---------------------------------------------------------------------------------


def _user_prompt(question: CalibrationQuestion, context: str) -> str:
    return f"Context:\n{context}\n\nQuestion: {question.question}"


def _clean(raw: str) -> GeneratedAnswer:
    text = _THINK_BLOCK.sub("", raw).strip()
    if text == ABSTAIN_MARKER:
        return GeneratedAnswer(variant="", text=ABSTENTION_TEXT, abstained=True)
    return GeneratedAnswer(variant="", text=text, abstained=False)


def generate_answers(
    question: CalibrationQuestion,
    *,
    backend: GenerationBackend,
    model: str,
    seed: int,
    temperature: float,
    top_p: float,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
) -> list[GeneratedAnswer]:
    """Two answers for one question, each tagged with the variant that produced it."""
    distractor = ungrounded_passage(question, seed=seed, transcripts_dir=transcripts_dir)
    if question.stratum is QuestionStratum.E4_UNANSWERABLE:
        contexts = [
            ("ungrounded", distractor, _SYSTEM_PROMPT),
            ("no_context", _NO_CONTEXT, _SYSTEM_PROMPT),
        ]
    else:
        contexts = [
            (
                "grounded",
                grounded_passage(question, transcripts_dir=transcripts_dir),
                _SYSTEM_PROMPT,
            ),
            ("ungrounded", distractor, _FORCED_SYSTEM_PROMPT),
        ]
    answers: list[GeneratedAnswer] = []
    for variant, context, system in contexts:
        raw = backend.generate(
            system,
            _user_prompt(question, context),
            model=model,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
        )
        cleaned = _clean(raw)
        answers.append(GeneratedAnswer(variant, cleaned.text, cleaned.abstained))
    return answers


# --- the calibration CSV ---------------------------------------------------------------------


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{c: row.get(c) or "" for c in COLUMNS} for row in csv.DictReader(handle)]


def generate_calibration_set(
    questions_path: Path = QUESTIONS_PATH,
    calibration_path: Path = CALIBRATION_PATH,
    *,
    backend: GenerationBackend,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    questions: Sequence[CalibrationQuestion] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> GenerationReport:
    """Generate the answers of every new question and append them to the calibration CSV.

    Rows already in the CSV (possibly labeled) are kept byte-for-byte in meaning and are
    never regenerated: a question is skipped when any of its answer ids exists. The label
    columns of new rows stay empty. Nothing is written, and the backend is never called,
    when there are no questions. The file is written as UTF-8 without a BOM. ``questions``
    replaces the question file when given (the worksheet bridge passes them directly).
    ``on_progress(done, total)`` is called after each question, skipped ones included.
    """
    if questions is None:
        questions = load_calibration_questions(questions_path)
    if not questions:
        return GenerationReport(0, 0, 0)
    budget = load_experiments_config()["shared_budget"]
    model = str(budget["generative_model"])
    existing = _read_rows(calibration_path)
    taken = {row["id"] for row in existing}
    new_rows: list[dict[str, str]] = []
    new_variants: dict[str, str] = {}
    processed = skipped = 0
    for position, question in enumerate(questions, start=1):
        if any(row_id.startswith(f"{question.id}.") for row_id in taken):
            skipped += 1
            if on_progress is not None:
                on_progress(position, len(questions))
            continue
        answers = generate_answers(
            question,
            backend=backend,
            model=model,
            seed=int(budget["seed"]),
            temperature=float(budget["temperature"]),
            top_p=float(budget["top_p"]),
            transcripts_dir=transcripts_dir,
        )
        excerpt = judge_evidence_passage(
            question.reference_evidence, transcripts_dir=transcripts_dir
        )
        files = transcript_files_text(question.reference_evidence, transcripts_dir=transcripts_dir)
        for answer in answers:
            new_variants[f"{question.id}.{answer.variant}"] = answer.variant
            new_rows.append(
                {
                    **dict.fromkeys(COLUMNS, ""),
                    "id": f"{question.id}.{answer.variant}",
                    "series_id": question.series_id,
                    "stratum": question.stratum.value,
                    "question": question.question,
                    "reference_answer": question.reference_answer or "",
                    "reference_evidence": format_reference_evidence(question.reference_evidence),
                    "answer_text": answer.text,
                    "pasaje_transcripcion": excerpt,
                    "archivos_transcripcion": files,
                    "answer_abstained": str(answer.abstained).lower(),
                    "adjudicated": "false",
                }
            )
        processed += 1
        if on_progress is not None:
            on_progress(position, len(questions))
    if new_rows:
        variants = {**load_variants(calibration_path), **new_variants}
        # Shuffle (deterministically) so the two answers of a question are not adjacent and
        # their order does not reveal which one is grounded.
        rows = sorted([*existing, *new_rows], key=lambda row: row["id"])
        random.Random(int(budget["seed"])).shuffle(rows)
        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        with open_csv_writer(calibration_path, encoding="utf-8") as writer:
            writer.writerow(COLUMNS)
            for row in rows:
                writer.writerow([row[c] for c in COLUMNS])
        with open_csv_writer(variants_path(calibration_path), encoding="utf-8") as writer:
            writer.writerow(VARIANT_COLUMNS)
            for row_id in sorted(variants):
                writer.writerow([row_id, variants[row_id]])
    return GenerationReport(processed, skipped, len(new_rows))
