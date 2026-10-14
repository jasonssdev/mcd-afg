"""Tests for calibration answer generation (thesis section 5.7, issue #82). No network."""

from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.evaluation.judge_calibration_generation import (
    ABSTENTION_TEXT,
    QUESTIONS_TEMPLATE_PATH,
    CalibrationQuestion,
    OllamaGenerationBackend,
    generate_answers,
    generate_calibration_set,
    grounded_passage,
    load_calibration_questions,
    ungrounded_passage,
)
from afg.evaluation.judge_calibration_set import (
    COLUMNS,
    DevelopmentSplitError,
    load_calibration_items,
    variants_path,
)

QUESTION_HEADER = "id,series_id,stratum,question,reference_answer,reference_evidence\n"


def _act(meeting: str, n: int) -> str:
    return f"{meeting}.A.dialog-act.x.{n}"


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    """Two meetings of 20 one-act turns each; the text of turn i is 'ES2015a-turn-i'."""
    root = tmp_path / "transcripts"
    root.mkdir()
    for meeting in ("ES2015a", "ES2015b"):
        with (root / f"{meeting}.jsonl").open("w", encoding="utf-8") as handle:
            for i in range(20):
                row = {
                    "meeting_id": meeting,
                    "turn_index": i,
                    "speaker": "A",
                    "role": "PM",
                    "text": f"{meeting}-turn-{i}",
                    "start": float(i),
                    "end": float(i) + 0.5,
                    "char_start": 0,
                    "char_end": 1,
                    "dialogue_act_ids": [_act(meeting, i)],
                }
                handle.write(json.dumps(row) + "\n")
    return root


def _question(
    stratum: QuestionStratum = QuestionStratum.E1_POINT_FACT, qid: str = "ES2015.q001"
) -> CalibrationQuestion:
    answerable = stratum is not QuestionStratum.E4_UNANSWERABLE
    return CalibrationQuestion(
        id=qid,
        series_id="ES2015",
        stratum=stratum,
        question="¿Cuál es el precio?",
        reference_answer="Veinticinco euros." if answerable else None,
        reference_evidence=(
            (EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=(_act("ES2015a", 10),)),)
            if answerable
            else ()
        ),
    )


class FakeBackend:
    def __init__(self, reply: str = "Veinticinco euros.") -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def generate(
        self, system: str, user: str, *, model: str, seed: int, temperature: float, top_p: float
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "model": model,
                "seed": seed,
                "temperature": temperature,
                "top_p": top_p,
            }
        )
        return self.reply


class TestPassages:
    def test_grounded_passage_covers_the_reference_acts_with_padding(
        self, transcripts: Path
    ) -> None:
        passage = grounded_passage(_question(), transcripts_dir=transcripts, context_turns=2)
        for i in range(8, 13):
            assert f"ES2015a-turn-{i}" in passage
        assert "ES2015a-turn-7" not in passage and "ES2015a-turn-13" not in passage
        assert passage.splitlines()[:2] == ["[ES2015a]", "PM: ES2015a-turn-8"]

    def test_ungrounded_passage_never_contains_a_reference_act(self, transcripts: Path) -> None:
        question = _question()
        for seed in range(20):
            passage = ungrounded_passage(
                question, seed=seed, transcripts_dir=transcripts, window_turns=5
            )
            assert "ES2015a-turn-10" not in passage

    def test_ungrounded_passage_is_deterministic_per_seed(self, transcripts: Path) -> None:
        kwargs = {"transcripts_dir": transcripts, "window_turns": 5}
        first = ungrounded_passage(_question(), seed=3, **kwargs)  # type: ignore[arg-type]
        again = ungrounded_passage(_question(), seed=3, **kwargs)  # type: ignore[arg-type]
        assert first == again

    def test_ungrounded_passage_varies_with_the_seed(self, transcripts: Path) -> None:
        passages = {
            ungrounded_passage(_question(), seed=s, transcripts_dir=transcripts, window_turns=5)
            for s in range(30)
        }
        assert len(passages) > 1

    def test_ungrounded_passage_fails_when_no_window_is_free(self, transcripts: Path) -> None:
        both = _question().model_copy(
            update={
                "reference_evidence": (
                    EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=(_act("ES2015a", 10),)),
                    EvidenceSpan(meeting_id="ES2015b", dialogue_act_ids=(_act("ES2015b", 3),)),
                )
            }
        )
        with pytest.raises(ValueError, match="no passage"):
            ungrounded_passage(both, seed=1, transcripts_dir=transcripts, window_turns=500)

    def test_grounded_passage_fails_when_an_act_is_not_in_the_transcript(
        self, transcripts: Path
    ) -> None:
        bad = _question().model_copy(
            update={
                "reference_evidence": (
                    EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.nope",)),
                )
            }
        )
        with pytest.raises(ValueError, match=r"ES2015a\.nope"):
            grounded_passage(bad, transcripts_dir=transcripts)

    def test_missing_transcript_names_the_meeting(self, transcripts: Path) -> None:
        question = _question().model_copy(
            update={
                "reference_evidence": (
                    EvidenceSpan(meeting_id="ES2015d", dialogue_act_ids=("ES2015d.A.x.1",)),
                )
            }
        )
        with pytest.raises(FileNotFoundError, match="ES2015d"):
            grounded_passage(question, transcripts_dir=transcripts)


class TestGenerateAnswers:
    def test_answerable_question_gets_a_grounded_and_an_ungrounded_answer(
        self, transcripts: Path
    ) -> None:
        backend = FakeBackend()
        answers = generate_answers(
            _question(),
            backend=backend,
            model="qwen3:8b",
            seed=42,
            temperature=0.1,
            top_p=0.9,
            transcripts_dir=transcripts,
        )
        assert [a.variant for a in answers] == ["grounded", "ungrounded"]
        assert "ES2015a-turn-10" in backend.calls[0]["user"]
        assert "ES2015a-turn-10" not in backend.calls[1]["user"]
        assert all("¿Cuál es el precio?" in c["user"] for c in backend.calls)

    def test_budget_parameters_reach_the_backend(self, transcripts: Path) -> None:
        backend = FakeBackend()
        generate_answers(
            _question(),
            backend=backend,
            model="qwen3:8b",
            seed=7,
            temperature=0.1,
            top_p=0.9,
            transcripts_dir=transcripts,
        )
        for call in backend.calls:
            assert (call["model"], call["seed"], call["temperature"], call["top_p"]) == (
                "qwen3:8b",
                7,
                0.1,
                0.9,
            )

    def test_unanswerable_question_gets_a_distractor_and_a_no_context_answer(
        self, transcripts: Path
    ) -> None:
        backend = FakeBackend()
        answers = generate_answers(
            _question(QuestionStratum.E4_UNANSWERABLE),
            backend=backend,
            model="m",
            seed=1,
            temperature=0.1,
            top_p=0.9,
            transcripts_dir=transcripts,
        )
        assert [a.variant for a in answers] == ["ungrounded", "no_context"]
        assert "turn-" in backend.calls[0]["user"]
        assert "turn-" not in backend.calls[1]["user"]

    def test_abstention_marker_becomes_an_abstained_answer(self, transcripts: Path) -> None:
        answers = generate_answers(
            _question(),
            backend=FakeBackend("NO_ANSWER"),
            model="m",
            seed=1,
            temperature=0.1,
            top_p=0.9,
            transcripts_dir=transcripts,
        )
        assert all(a.abstained and a.text == ABSTENTION_TEXT for a in answers)

    def test_abstention_text_is_english_like_the_answers_and_the_judge_prompt(self) -> None:
        assert ABSTENTION_TEXT == "The material does not contain enough information to answer."

    def test_reasoning_block_is_stripped(self, transcripts: Path) -> None:
        answers = generate_answers(
            _question(),
            backend=FakeBackend("<think>hmm\nlong</think>\n\nVeinticinco euros."),
            model="m",
            seed=1,
            temperature=0.1,
            top_p=0.9,
            transcripts_dir=transcripts,
        )
        assert answers[0].text == "Veinticinco euros." and not answers[0].abstained


def _write_questions(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "questions.csv"
    path.write_text(QUESTION_HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


Q1 = f"ES2015.q001,ES2015,E1_point_fact,¿Precio?,25 euros,ES2015a:{_act('ES2015a', 10)}"
Q4 = "ES2015.q004,ES2015,E4_unanswerable,¿Garantía?,,"


class TestLoadQuestions:
    def test_reads_questions_and_evidence(self, tmp_path: Path) -> None:
        questions = load_calibration_questions(_write_questions(tmp_path, Q1, Q4))
        assert [q.id for q in questions] == ["ES2015.q001", "ES2015.q004"]
        assert questions[0].reference_evidence[0].meeting_id == "ES2015a"
        assert questions[1].reference_answer is None and questions[1].reference_evidence == ()

    def test_header_only_file_is_empty(self, tmp_path: Path) -> None:
        assert load_calibration_questions(_write_questions(tmp_path)) == []

    def test_answerable_question_without_evidence_is_rejected(self, tmp_path: Path) -> None:
        row = "ES2015.q002,ES2015,E1_point_fact,¿Precio?,25 euros,"
        with pytest.raises(ValueError, match=r"ES2015\.q002"):
            load_calibration_questions(_write_questions(tmp_path, row))

    def test_series_outside_the_calibration_config_is_rejected(self, tmp_path: Path) -> None:
        row = f"IS1004.q001,IS1004,E1_point_fact,¿Precio?,x,IS1004a:{_act('IS1004a', 1)}"
        with pytest.raises(DevelopmentSplitError, match="IS1004"):
            load_calibration_questions(_write_questions(tmp_path, row))

    def test_shipped_template_is_header_only_and_loadable(self) -> None:
        assert load_calibration_questions(QUESTIONS_TEMPLATE_PATH) == []

    def test_reads_a_file_with_bom(self, tmp_path: Path) -> None:
        path = _write_questions(tmp_path, Q1)
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        assert len(load_calibration_questions(path)) == 1


class TestGenerateCalibrationSet:
    def test_empty_question_file_does_nothing_and_says_so(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        backend = FakeBackend()
        target = tmp_path / "calibration.csv"
        report = generate_calibration_set(
            _write_questions(tmp_path), target, backend=backend, transcripts_dir=transcripts
        )
        assert backend.calls == [] and not target.exists()
        assert report.questions_processed == 0
        assert "no questions" in report.summary().lower()

    def test_questions_can_be_passed_directly_instead_of_a_file(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        target = tmp_path / "calibration.csv"
        report = generate_calibration_set(
            tmp_path / "does-not-exist.csv",
            target,
            backend=FakeBackend(),
            transcripts_dir=transcripts,
            questions=[_question()],
        )
        assert report.questions_processed == 1 and report.rows_written == 2
        assert sorted(i.id for i in load_calibration_items(target)) == [
            "ES2015.q001.grounded",
            "ES2015.q001.ungrounded",
        ]

    def test_writes_two_unlabeled_rows_per_question_that_the_loader_accepts(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        target = tmp_path / "calibration.csv"
        report = generate_calibration_set(
            _write_questions(tmp_path, Q1, Q4),
            target,
            backend=FakeBackend(),
            transcripts_dir=transcripts,
        )
        assert report.questions_processed == 2 and report.rows_written == 4
        assert not target.read_bytes().startswith(b"\xef\xbb\xbf")
        items = load_calibration_items(target)
        assert sorted(i.id for i in items) == [
            "ES2015.q001.grounded",
            "ES2015.q001.ungrounded",
            "ES2015.q004.no_context",
            "ES2015.q004.ungrounded",
        ]
        assert all(i.correct is None and i.evidence_supported is None for i in items)
        assert all(not i.labelers and not i.adjudicated for i in items)
        by_id = {i.id: i for i in items}
        assert by_id["ES2015.q001.grounded"].reference_evidence
        assert by_id["ES2015.q004.ungrounded"].reference_evidence == ()
        assert {i.id: i.answer_variant for i in items} == {
            "ES2015.q001.grounded": "grounded",
            "ES2015.q001.ungrounded": "ungrounded",
            "ES2015.q004.ungrounded": "ungrounded",
            "ES2015.q004.no_context": "no_context",
        }

    def test_variant_is_kept_out_of_the_labeling_file_and_written_to_a_sidecar(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        target = tmp_path / "calibration.csv"
        generate_calibration_set(
            _write_questions(tmp_path, Q1, Q4),
            target,
            backend=FakeBackend(),
            transcripts_dir=transcripts,
        )
        assert "answer_variant" not in target.read_text(encoding="utf-8").splitlines()[0]
        sidecar = variants_path(target)
        assert sidecar.name == "calibration.variantes.csv"
        with sidecar.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert {r["id"]: r["answer_variant"] for r in rows} == {
            "ES2015.q001.grounded": "grounded",
            "ES2015.q001.ungrounded": "ungrounded",
            "ES2015.q004.ungrounded": "ungrounded",
            "ES2015.q004.no_context": "no_context",
        }

    def test_item_order_is_shuffled_deterministically_with_the_seed(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        q = [_question(qid=f"ES2015.q{n:03d}") for n in range(1, 9)]
        orders = []
        for name in ("a", "b"):
            target = tmp_path / f"{name}.csv"
            generate_calibration_set(
                tmp_path / "unused.csv",
                target,
                backend=FakeBackend(),
                transcripts_dir=transcripts,
                questions=q,
            )
            orders.append([i.id for i in load_calibration_items(target)])
        generation_order = [f"{x.id}.{v}" for x in q for v in ("grounded", "ungrounded")]
        assert orders[0] == orders[1]
        assert sorted(orders[0]) == sorted(generation_order)
        assert orders[0] != generation_order
        assert orders[0] != sorted(orders[0])

    def test_rerun_skips_questions_already_generated_and_keeps_labels(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        target = tmp_path / "calibration.csv"
        questions = _write_questions(tmp_path, Q1)
        generate_calibration_set(
            questions, target, backend=FakeBackend(), transcripts_dir=transcripts
        )
        with target.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        labeled_id = rows[0]["id"]
        rows[0]["correct"], rows[0]["labeler_a"] = "true", "jss"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

        backend = FakeBackend()
        questions = _write_questions(tmp_path, Q1, Q4)
        report = generate_calibration_set(
            questions, target, backend=backend, transcripts_dir=transcripts
        )
        assert report.questions_skipped == 1 and report.questions_processed == 1
        assert len(backend.calls) == 2  # only Q4
        items = load_calibration_items(target)
        assert len(items) == 4
        kept = next(i for i in items if i.id == labeled_id)
        assert kept.correct is True and kept.labelers == ("jss",)
        assert {i.answer_variant for i in items} == {"grounded", "ungrounded", "no_context"}

    def test_uses_the_shared_budget_from_the_config(
        self, tmp_path: Path, transcripts: Path
    ) -> None:
        backend = FakeBackend()
        generate_calibration_set(
            _write_questions(tmp_path, Q1),
            tmp_path / "calibration.csv",
            backend=backend,
            transcripts_dir=transcripts,
        )
        call = backend.calls[0]
        assert (call["model"], call["seed"], call["temperature"], call["top_p"]) == (
            "qwen3:8b",
            42,
            0.1,
            0.9,
        )


class TestOllamaGenerationBackend:
    def test_calls_chat_with_the_budget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: dict[str, Any] = {}

        class FakeClient:
            def __init__(self, host: str) -> None:
                seen["host"] = host

            def chat(self, **kwargs: Any) -> Any:
                seen.update(kwargs)
                return types.SimpleNamespace(message=types.SimpleNamespace(content="out"))

        monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=FakeClient))
        out = OllamaGenerationBackend(host="http://h:1").generate(
            "SYS", "USR", model="m", seed=3, temperature=0.1, top_p=0.9
        )
        assert out == "out" and seen["host"] == "http://h:1"
        assert seen["options"] == {"temperature": 0.1, "seed": 3, "top_p": 0.9}
        assert seen["messages"][0] == {"role": "system", "content": "SYS"}

    def test_missing_llm_extra_gives_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "ollama", None)
        with pytest.raises(RuntimeError, match="llm"):
            OllamaGenerationBackend(host="http://h:1").generate(
                "s", "u", model="m", seed=1, temperature=0.1, top_p=0.9
            )
