"""Tests for the C1 segmentation / K tuning machinery. No network: fake embedders only."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.conditions import c1_tuning
from afg.conditions.c1_chunking import Chunk
from afg.conditions.c1_retrieval import HybridRetriever
from afg.conditions.c1_tuning import (
    ConfigResult,
    NoEligibleConfigError,
    TuningConfig,
    TuningQuestion,
    evaluate_grid,
    evidence_recall,
    first_hit_rank,
    load_tuning_config,
    load_tuning_questions,
    load_tuning_results,
    save_tuning_results,
    select_winner,
    series_meetings,
)
from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum

# --- helpers ---------------------------------------------------------------------------


class LetterEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * 26
            for ch in text.lower():
                if "a" <= ch <= "z":
                    vec[ord(ch) - ord("a")] += 1.0
            out.append(vec)
        return out


def chunk(chunk_id: str, acts: tuple[str, ...], text: str = "x") -> Chunk:
    meeting = chunk_id.split(".")[0]
    return Chunk(
        chunk_id=chunk_id,
        meeting_id=meeting,
        series="ES2015",
        first_turn=0,
        last_turn=0,
        start=None,
        end=None,
        dialogue_act_ids=acts,
        text=text,
    )


def span(meeting: str, *acts: str) -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting, dialogue_act_ids=acts)


def write_meeting(
    directory: Path, meeting_id: str, turns: list[tuple[str, tuple[str, ...]]]
) -> None:
    lines = []
    offset = 0
    for index, (text, acts) in enumerate(turns):
        lines.append(
            json.dumps(
                {
                    "meeting_id": meeting_id,
                    "turn_index": index,
                    "speaker": "A",
                    "role": "PM",
                    "text": text,
                    "start": None,
                    "end": None,
                    "char_start": offset,
                    "char_end": offset + len(text),
                    "dialogue_act_ids": list(acts),
                }
            )
        )
        offset += len(text) + 2
    (directory / f"{meeting_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def result(
    max_chars: int = 1200,
    overlap: int = 0,
    k: int = 5,
    recall: float = 0.5,
    budget_ok: bool = True,
) -> ConfigResult:
    return ConfigResult(
        max_chars=max_chars,
        overlap_turns=overlap,
        k=k,
        mean_recall=recall,
        recalls={"q1": recall},
        first_hit_ranks={"q1": 1},
        mean_context_chars=100.0,
        n_chunks=10,
        eligible=budget_ok,
    )


# --- evidence recall -------------------------------------------------------------------


def test_recall_is_fraction_of_reference_acts_in_the_union_of_chunks() -> None:
    chunks = [chunk("M1.c000", ("a", "b")), chunk("M1.c001", ("c",))]
    evidence = [span("M1", "a", "c", "z", "y")]
    assert evidence_recall(chunks, evidence) == pytest.approx(0.5)


def test_recall_is_keyed_by_meeting_and_act() -> None:
    chunks = [chunk("M1.c000", ("a",))]
    assert evidence_recall(chunks, [span("M2", "a")]) == 0.0
    assert evidence_recall(chunks, [span("M1", "a")]) == 1.0


def test_recall_counts_acts_across_spans_once_each() -> None:
    chunks = [chunk("M1.c000", ("a",)), chunk("M2.c000", ("b",))]
    evidence = [span("M1", "a", "x"), span("M2", "b")]
    assert evidence_recall(chunks, evidence) == pytest.approx(2 / 3)


def test_recall_with_nothing_retrieved_is_zero() -> None:
    assert evidence_recall([], [span("M1", "a")]) == 0.0


def test_recall_without_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="evidence"):
        evidence_recall([chunk("M1.c000", ("a",))], [])


def test_first_hit_rank_is_one_based_and_none_when_missed() -> None:
    chunks = [chunk("M1.c000", ("a",)), chunk("M1.c001", ("b",)), chunk("M1.c002", ("b", "c"))]
    assert first_hit_rank(chunks, [span("M1", "c", "b")]) == 2
    assert first_hit_rank(chunks, [span("M1", "zzz")]) is None
    assert first_hit_rank([], [span("M1", "a")]) is None


# --- selection rule --------------------------------------------------------------------


def test_winner_is_the_eligible_config_with_highest_recall() -> None:
    results = [result(k=3, recall=0.4), result(k=5, recall=0.8), result(k=8, recall=0.6)]
    selection = select_winner(results, tie_margin=0.02)
    assert selection.winner.k == 5
    assert "recall" in selection.reason


def test_ineligible_configs_never_win() -> None:
    results = [result(k=10, recall=0.99, budget_ok=False), result(k=3, recall=0.5)]
    assert select_winner(results, tie_margin=0.02).winner.k == 3


def test_tie_margin_prefers_smaller_k_then_chars_then_overlap() -> None:
    results = [
        result(max_chars=800, overlap=1, k=8, recall=0.80),
        result(max_chars=1200, overlap=0, k=5, recall=0.79),
        result(max_chars=800, overlap=1, k=5, recall=0.785),
        result(max_chars=800, overlap=0, k=5, recall=0.781),
        result(max_chars=800, overlap=0, k=3, recall=0.70),
    ]
    winner = select_winner(results, tie_margin=0.02).winner
    assert (winner.k, winner.max_chars, winner.overlap_turns) == (5, 800, 0)


def test_tie_margin_is_inclusive_and_excludes_clearly_worse() -> None:
    results = [result(k=8, recall=0.80), result(k=3, recall=0.78), result(k=5, recall=0.77)]
    assert select_winner(results, tie_margin=0.02).winner.k == 3


def test_no_eligible_config_raises_a_clear_error() -> None:
    with pytest.raises(NoEligibleConfigError, match="char_budget"):
        select_winner([result(budget_ok=False)], tie_margin=0.02)
    with pytest.raises(NoEligibleConfigError):
        select_winner([], tie_margin=0.02)


# --- config ----------------------------------------------------------------------------


def test_real_config_is_pre_registered_grid() -> None:
    config = load_tuning_config()
    assert config.series == ("ES2015",)
    assert config.max_chars == (800, 1200, 1600, 2400)
    assert config.overlap_turns == (0, 1)
    assert config.k == (3, 5, 8, 10)
    assert config.char_budget == 13516
    assert config.tie_margin == pytest.approx(0.02)


def test_series_outside_development_are_refused() -> None:
    experiments = {
        "retrieval": {
            "tuning": {
                "series": ["ES2002"],
                "max_chars": [800],
                "overlap_turns": [0],
                "k": [3],
                "char_budget": 1000,
                "tie_margin": 0.0,
            }
        }
    }
    with pytest.raises(ValueError, match="ADR 0005"):
        load_tuning_config(experiments=experiments, development=frozenset({"ES2015"}))


# --- questions -------------------------------------------------------------------------

_HEADER = (
    "id,series_id,stratum,question,reference_answer,reference_evidence,answer_text,"
    "pasaje_transcripcion,archivos_transcripcion,answer_abstained,correct,evidence_supported,"
    "citation_correct,labeler_a,labeler_b,adjudicated\n"
)


def test_questions_are_deduplicated_and_unanswerable_are_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [
        "ES2015.q001.grounded,ES2015,E1_point_fact,Q one?,ans,ES2015a:d1;d2,t,,,no,,,,,,no",
        "ES2015.q001.ungrounded,ES2015,E1_point_fact,Q one?,ans,ES2015a:d1;d2,t,,,no,,,,,,no",
        "ES2015.q002.grounded,ES2015,E3_evolution,Q two?,ans,ES2015a:d3|ES2015b:d4,t,,,no,,,,,,no",
        "ES2015.q003.grounded,ES2015,E4_unanswerable,Q three?,,,t,,,no,,,,,,no",
    ]
    path = tmp_path / "cal.csv"
    path.write_text(_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        "afg.evaluation.judge_calibration_set.calibration_series",
        lambda: frozenset({"ES2015"}),
    )
    questions = load_tuning_questions(path, series=("ES2015",))
    assert [q.question_id for q in questions] == ["ES2015.q001", "ES2015.q002"]
    assert questions[0].stratum is QuestionStratum.E1_POINT_FACT
    assert questions[1].evidence == (span("ES2015a", "d3"), span("ES2015b", "d4"))


# --- transcripts and grid --------------------------------------------------------------


def test_series_meetings_lists_only_that_series_sorted(tmp_path: Path) -> None:
    for name in ("ES2015b", "ES2015a", "ES2016a", "IS2015a"):
        write_meeting(tmp_path, name, [("hello", ())])
    assert series_meetings("ES2015", tmp_path) == ["ES2015a", "ES2015b"]


def test_series_meetings_without_transcripts_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ES2015"):
        series_meetings("ES2015", tmp_path)


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    write_meeting(
        tmp_path,
        "ES2015a",
        [
            ("remote control battery solar panel", ("d1",)),
            ("budget twelve euros fifty", ("d2",)),
            ("banana smoothie recipe", ("d3",)),
            ("the logo and colour of the company", ("d4",)),
        ],
    )
    return tmp_path


def small_config(**overrides: object) -> TuningConfig:
    values: dict[str, object] = {
        "series": ("ES2015",),
        "max_chars": (40, 400),
        "overlap_turns": (0, 1),
        "k": (1, 2, 3),
        "char_budget": 1000,
        "tie_margin": 0.02,
    }
    values.update(overrides)
    return TuningConfig(**values)  # type: ignore[arg-type]


def questions() -> list[TuningQuestion]:
    return [
        TuningQuestion(
            question_id="q1",
            stratum=QuestionStratum.E1_POINT_FACT,
            question="budget euros",
            evidence=(span("ES2015a", "d2"),),
        ),
        TuningQuestion(
            question_id="q2",
            stratum=QuestionStratum.E1_POINT_FACT,
            question="logo colour company",
            evidence=(span("ES2015a", "d4"),),
        ),
    ]


def test_grid_yields_one_result_per_config_and_k(transcripts: Path) -> None:
    config = small_config()
    results = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert len(results) == 2 * 2 * 3
    keys = {(r.max_chars, r.overlap_turns, r.k) for r in results}
    assert len(keys) == 12
    for r in results:
        assert set(r.recalls) == {"q1", "q2"}
        assert r.mean_recall == pytest.approx(sum(r.recalls.values()) / 2)


def test_whole_meeting_in_one_chunk_has_full_recall(transcripts: Path) -> None:
    config = small_config(max_chars=(400,), overlap_turns=(0,), k=(1,))
    (only,) = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert only.mean_recall == 1.0
    assert only.first_hit_ranks == {"q1": 1, "q2": 1}
    assert only.n_chunks == 1


def test_recall_never_decreases_with_k(transcripts: Path) -> None:
    results = evaluate_grid(questions(), ["ES2015a"], small_config(), LetterEmbedder(), transcripts)
    by_config: dict[tuple[int, int], list[ConfigResult]] = {}
    for r in results:
        by_config.setdefault((r.max_chars, r.overlap_turns), []).append(r)
    for runs in by_config.values():
        runs.sort(key=lambda r: r.k)
        recalls = [r.mean_recall for r in runs]
        assert recalls == sorted(recalls)


def test_context_chars_and_eligibility(transcripts: Path) -> None:
    config = small_config(max_chars=(400,), overlap_turns=(0,), k=(1, 3), char_budget=900)
    first, second = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert first.eligible  # 1 * 400 <= 900
    assert not second.eligible  # 3 * 400 > 900
    assert first.mean_context_chars > 0
    assert first.mean_context_chars <= 400


def test_first_hit_rank_is_none_beyond_k(transcripts: Path) -> None:
    config = small_config(max_chars=(40,), overlap_turns=(0,), k=(1, 3))
    results = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    k1 = next(r for r in results if r.k == 1)
    k3 = next(r for r in results if r.k == 3)
    for qid, rank in k1.first_hit_ranks.items():
        assert rank is None or rank == 1
        if rank is None and k3.first_hit_ranks[qid] is not None:
            assert k3.first_hit_ranks[qid] > 1  # type: ignore[operator]


def test_truncating_max_k_equals_per_k_retrieval_up_to_the_pool(transcripts: Path) -> None:
    # Prefix stability: for limit <= MIN_POOL the candidate pool is fixed, so the top-K is a
    # prefix of the top-maxK ranking. Tuning relies on this to retrieve once per config.
    chunks = c1_tuning.chunk_meetings(["ES2015a"], 40, 0, transcripts)
    retriever = HybridRetriever(chunks, LetterEmbedder())
    for text in ("budget euros", "logo colour company", "banana", "zzz"):
        full = [h.chunk.chunk_id for h in retriever.retrieve(text, 10)]
        for k in range(1, 11):
            assert [h.chunk.chunk_id for h in retriever.retrieve(text, k)] == full[:k]


def test_above_the_pool_the_grid_retrieves_per_k(
    transcripts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    limits: list[int] = []
    original = HybridRetriever.retrieve

    def spy(self: HybridRetriever, question: str, limit: int) -> list:  # type: ignore[type-arg]
        limits.append(limit)
        return original(self, question, limit)

    monkeypatch.setattr(HybridRetriever, "retrieve", spy)
    config = small_config(max_chars=(40,), overlap_turns=(0,), k=(3, 12))
    evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert sorted(set(limits)) == [3, 12]

    limits.clear()
    config = small_config(max_chars=(40,), overlap_turns=(0,), k=(3, 10))
    evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert set(limits) == {10}


def test_progress_reports_each_chunking_config(transcripts: Path) -> None:
    seen: list[tuple[int, int, int, int]] = []
    evaluate_grid(
        questions(),
        ["ES2015a"],
        small_config(),
        LetterEmbedder(),
        transcripts,
        progress=lambda mc, ov, done, total: seen.append((mc, ov, done, total)),
    )
    assert [(done, total) for _, _, done, total in seen] == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_empty_question_list_is_rejected(transcripts: Path) -> None:
    with pytest.raises(ValueError, match="questions"):
        evaluate_grid([], ["ES2015a"], small_config(), LetterEmbedder(), transcripts)


# --- results file ----------------------------------------------------------------------


def test_results_round_trip(tmp_path: Path) -> None:
    results = [result(k=3, recall=0.25), result(k=5, recall=0.75, budget_ok=False)]
    selection = select_winner(results[:1], tie_margin=0.02)
    path = tmp_path / "out" / "resultados.json"
    config = small_config()
    save_tuning_results(path, results, selection, config=config, n_questions=17)
    stored = load_tuning_results(path)
    assert stored.n_questions == 17
    assert stored.results == tuple(results)
    assert stored.winner == results[0]
    assert stored.config == config
    assert stored.reason == selection.reason


def test_unreadable_results_raise(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"r\.json"):
        load_tuning_results(path)


# --- derived figures and pinned parameters ---------------------------------------------


def test_questions_with_any_hit_counts_non_null_ranks() -> None:
    r = dataclasses.replace(
        result(k=5, recall=0.5), first_hit_ranks={"a": 1, "b": None, "c": 4, "d": None}
    )
    assert c1_tuning.questions_with_any_hit(r) == 2


def test_load_pinned_c1_params_reads_the_retrieval_c1_section() -> None:
    experiments = {"retrieval": {"c1": {"max_chars": 1600, "overlap_turns": 0, "k": 8}}}
    params = c1_tuning.load_pinned_c1_params(experiments)
    assert (params.max_chars, params.overlap_turns, params.k) == (1600, 0, 8)


def test_load_pinned_c1_params_rejects_missing_section() -> None:
    with pytest.raises(ValueError, match=r"retrieval\.c1"):
        c1_tuning.load_pinned_c1_params({"retrieval": {}})


def test_pinned_c1_params_are_the_stored_winner() -> None:
    """``[retrieval.c1]`` pins what the pre-registered rule chose (notebook 06, ADR 0007)."""
    stored = load_tuning_results(c1_tuning.RESULTS_PATH)
    pinned = c1_tuning.load_pinned_c1_params()
    w = stored.winner
    assert (pinned.max_chars, pinned.overlap_turns, pinned.k) == (
        w.max_chars,
        w.overlap_turns,
        w.k,
    )
    assert w.eligible
    assert pinned.k * pinned.max_chars <= stored.config.char_budget
