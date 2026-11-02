"""Tests for the C1 segmentation / K tuning machinery. No network: fake embedders only."""

from __future__ import annotations

import dataclasses
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
    delivered_recall,
    evaluate_grid,
    evidence_recall,
    first_hit_rank,
    load_tuning_config,
    load_tuning_questions,
    load_tuning_results,
    questions_with_any_delivered_hit,
    save_tuning_results,
    select_winner,
    series_meetings,
)
from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.evaluation.chunk_acts import ChunkActMapper

from .frozen_fixtures import write_frozen_meeting

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


def chunk(chunk_id: str, start: int, end: int, text: str = "x") -> Chunk:
    meeting = chunk_id.split(".")[0]
    return Chunk(
        chunk_id=chunk_id,
        meeting_id=meeting,
        series="ES2015",
        char_start=start,
        char_end=end,
        text=text,
    )


def span(meeting: str, *acts: str) -> EvidenceSpan:
    return EvidenceSpan(meeting_id=meeting, dialogue_act_ids=acts)


def write_meeting(
    directory: Path, meeting_id: str, turns: list[tuple[str, tuple[str, ...]]]
) -> None:
    write_frozen_meeting(directory, meeting_id, turns)


def result(
    chunk_size: int = 1200,
    overlap: int = 0,
    k: int = 5,
    recall: float = 0.5,
    budget_ok: bool = True,
    delivered: float | None = None,
) -> ConfigResult:
    # By default the delivered recall equals the full-chunk recall (nothing was trimmed).
    shown = recall if delivered is None else delivered
    return ConfigResult(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        k=k,
        mean_recall=recall,
        recalls={"q1": recall},
        mean_delivered_recall=shown,
        delivered_recalls={"q1": shown},
        mean_delivered_chars=90.0,
        first_hit_ranks={"q1": 1},
        mean_context_chars=100.0,
        n_chunks=10,
        eligible=budget_ok,
    )


# --- evidence recall -------------------------------------------------------------------

# Body of the fixture below: turn extents (role prefix included)
#   t0 "PM: first turn"   acts a, shared
#   t1 "PM: second turn"  acts b
#   t2 "PM: third turn"   acts c, shared
BODY_TURNS = [
    ("first turn", ("a", "shared")),
    ("second turn", ("b",)),
    ("third turn", ("c", "shared")),
]


@pytest.fixture
def mapper(tmp_path: Path) -> ChunkActMapper:
    write_frozen_meeting(tmp_path, "M1", BODY_TURNS)
    return ChunkActMapper(tmp_path)


def at(mapper: ChunkActMapper, first: int, last: int, chunk_id: str = "M1.c000") -> Chunk:
    """A chunk of M1 covering turns ``first..last`` exactly (extent of the whole lines)."""
    from afg.corpus.frozen import turn_extent

    turns = mapper.turns("M1")
    start, end = turn_extent(turns[first])[0], turn_extent(turns[last])[1]
    from afg.corpus.render import read_meeting_body

    body = read_meeting_body("M1", mapper.transcripts_dir)
    return chunk(chunk_id, start, end, body[start:end])


def test_recall_is_fraction_of_reference_acts_in_the_union_of_chunks(
    mapper: ChunkActMapper,
) -> None:
    chunks = [at(mapper, 0, 0), at(mapper, 2, 2, "M1.c001")]
    evidence = [span("M1", "a", "c", "z", "y")]
    assert evidence_recall(chunks, evidence, mapper) == pytest.approx(0.5)


def test_recall_takes_the_acts_from_the_char_span_not_from_the_chunk(
    mapper: ChunkActMapper,
) -> None:
    only_second = at(mapper, 1, 1)
    assert evidence_recall([only_second], [span("M1", "a")], mapper) == 0.0
    assert evidence_recall([only_second], [span("M1", "b")], mapper) == 1.0
    # a span crossing two turns holds the acts of both
    assert evidence_recall([at(mapper, 0, 1)], [span("M1", "a", "b")], mapper) == 1.0


def test_recall_is_keyed_by_meeting_and_act(mapper: ChunkActMapper) -> None:
    chunks = [at(mapper, 0, 0)]
    assert evidence_recall(chunks, [span("M2", "a")], mapper) == 0.0
    assert evidence_recall(chunks, [span("M1", "a")], mapper) == 1.0


def test_recall_counts_acts_across_spans_once_each(mapper: ChunkActMapper) -> None:
    chunks = [at(mapper, 0, 0)]
    evidence = [span("M1", "a", "x"), span("M1", "shared")]
    assert evidence_recall(chunks, evidence, mapper) == pytest.approx(2 / 3)


def test_recall_with_nothing_retrieved_is_zero(mapper: ChunkActMapper) -> None:
    assert evidence_recall([], [span("M1", "a")], mapper) == 0.0


def test_recall_without_evidence_is_rejected(mapper: ChunkActMapper) -> None:
    with pytest.raises(ValueError, match="evidence"):
        evidence_recall([at(mapper, 0, 0)], [], mapper)


def test_first_hit_rank_is_one_based_and_none_when_missed(mapper: ChunkActMapper) -> None:
    chunks = [at(mapper, 0, 0), at(mapper, 1, 1, "M1.c001"), at(mapper, 1, 2, "M1.c002")]
    assert first_hit_rank(chunks, [span("M1", "c", "b")], mapper) == 2
    assert first_hit_rank(chunks, [span("M1", "zzz")], mapper) is None
    assert first_hit_rank([], [span("M1", "a")], mapper) is None


# --- delivered recall ------------------------------------------------------------------

ELIDED = "\n[... source elided to fit the context window ...]\n"


def block(chunk: Chunk, text: str | None = None) -> tuple[Chunk, str]:
    """A delivered block: the chunk and the text of its body after the label."""
    return chunk, chunk.text if text is None else text


def test_delivered_recall_counts_an_act_whose_turn_survives_intact(
    mapper: ChunkActMapper,
) -> None:
    delivered = [block(at(mapper, 0, 1))]
    assert delivered_recall(delivered, [span("M1", "a", "b")], mapper) == 1.0


def test_delivered_recall_ignores_an_act_whose_turn_was_elided(mapper: ChunkActMapper) -> None:
    whole = at(mapper, 0, 2)
    text = "PM: first turn" + ELIDED + "PM: third turn"
    assert delivered_recall([block(whole, text)], [span("M1", "a", "b")], mapper) == (
        pytest.approx(0.0 + 0.5)
    )


def test_delivered_recall_needs_every_turn_of_the_act(mapper: ChunkActMapper) -> None:
    # act "shared" spans turns 0 and 2: with turn 2 elided the act is not fully delivered.
    whole = at(mapper, 0, 2)
    partial = "PM: first turn\n\nPM: second turn" + ELIDED
    assert delivered_recall([block(whole, partial)], [span("M1", "shared")], mapper) == 0.0
    assert delivered_recall([block(whole)], [span("M1", "shared")], mapper) == 1.0


def test_delivered_recall_unions_the_turns_of_an_act_across_blocks(
    mapper: ChunkActMapper,
) -> None:
    delivered = [block(at(mapper, 0, 0)), block(at(mapper, 2, 2, "M1.c001"))]
    assert delivered_recall(delivered, [span("M1", "shared")], mapper) == 1.0


def test_delivered_recall_does_not_count_a_turn_cut_by_the_chunk_boundary(
    mapper: ChunkActMapper,
) -> None:
    from afg.corpus.render import read_meeting_body

    body = read_meeting_body("M1", mapper.transcripts_dir)
    cut = chunk("M1.c000", 0, 8, body[:8])  # "PM: firs"
    assert delivered_recall([block(cut)], [span("M1", "a")], mapper) == 0.0


def test_delivered_recall_matches_positions_not_substrings(mapper: ChunkActMapper) -> None:
    # The same words elsewhere in the block do not deliver the turn whose span was elided.
    whole = at(mapper, 0, 2)
    text = "PM: second turn" + ELIDED + "PM: third turn"
    assert delivered_recall([block(whole, text)], [span("M1", "a")], mapper) == 0.0


def test_delivered_recall_with_nothing_delivered_is_zero_and_needs_evidence(
    mapper: ChunkActMapper,
) -> None:
    assert delivered_recall([], [span("M1", "a")], mapper) == 0.0
    with pytest.raises(ValueError, match="evidence"):
        delivered_recall([], [], mapper)


# --- selection rule --------------------------------------------------------------------


def test_winner_is_the_eligible_config_with_highest_recall() -> None:
    results = [result(k=3, recall=0.4), result(k=5, recall=0.8), result(k=8, recall=0.6)]
    selection = select_winner(results, tie_margin=0.02)
    assert selection.winner.k == 5
    assert "recall" in selection.reason


def test_selection_ranks_by_delivered_recall_not_full_chunk_recall() -> None:
    results = [
        result(k=3, recall=0.9, delivered=0.30),
        result(k=5, recall=0.5, delivered=0.60),
    ]
    selection = select_winner(results, tie_margin=0.02)
    assert selection.winner.k == 5
    assert "delivered" in selection.reason


def test_ineligible_configs_never_win() -> None:
    results = [result(k=10, recall=0.99, budget_ok=False), result(k=3, recall=0.5)]
    assert select_winner(results, tie_margin=0.02).winner.k == 3


def test_tie_margin_prefers_smaller_k_then_chars_then_overlap() -> None:
    results = [
        result(chunk_size=800, overlap=1, k=8, recall=0.80),
        result(chunk_size=1200, overlap=0, k=5, recall=0.79),
        result(chunk_size=800, overlap=1, k=5, recall=0.785),
        result(chunk_size=800, overlap=0, k=5, recall=0.781),
        result(chunk_size=800, overlap=0, k=3, recall=0.70),
    ]
    winner = select_winner(results, tie_margin=0.02).winner
    assert (winner.k, winner.chunk_size, winner.chunk_overlap) == (5, 800, 0)


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
    assert config.chunk_size == (800, 1200, 1600, 2400)
    assert config.chunk_overlap == (0, 200)
    assert config.k == (3, 5, 8, 10)
    assert config.char_budget == 13516
    assert config.tie_margin == pytest.approx(0.02)


def test_series_outside_development_are_refused() -> None:
    experiments = {
        "retrieval": {
            "tuning": {
                "series": ["ES2002"],
                "chunk_size": [800],
                "chunk_overlap": [0],
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
        "chunk_size": (40, 400),
        "chunk_overlap": (0, 10),
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
    keys = {(r.chunk_size, r.chunk_overlap, r.k) for r in results}
    assert len(keys) == 12
    for r in results:
        assert set(r.recalls) == {"q1", "q2"}
        assert r.mean_recall == pytest.approx(sum(r.recalls.values()) / 2)


def test_whole_meeting_in_one_chunk_has_full_recall(transcripts: Path) -> None:
    config = small_config(chunk_size=(400,), chunk_overlap=(0,), k=(1,))
    (only,) = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert only.mean_recall == 1.0
    assert only.first_hit_ranks == {"q1": 1, "q2": 1}
    assert only.n_chunks == 1


def test_recall_never_decreases_with_k(transcripts: Path) -> None:
    results = evaluate_grid(questions(), ["ES2015a"], small_config(), LetterEmbedder(), transcripts)
    by_config: dict[tuple[int, int], list[ConfigResult]] = {}
    for r in results:
        by_config.setdefault((r.chunk_size, r.chunk_overlap), []).append(r)
    for runs in by_config.values():
        runs.sort(key=lambda r: r.k)
        recalls = [r.mean_recall for r in runs]
        assert recalls == sorted(recalls)


def test_untrimmed_context_delivers_exactly_what_was_retrieved(transcripts: Path) -> None:
    results = evaluate_grid(questions(), ["ES2015a"], small_config(), LetterEmbedder(), transcripts)
    for r in results:
        assert r.delivered_recalls == pytest.approx(r.recalls)
        assert r.mean_delivered_recall == pytest.approx(r.mean_recall)
        assert 0 < r.mean_delivered_chars <= r.mean_context_chars + 200  # + block labels


def test_a_starved_budget_delivers_nothing_though_chunks_are_retrieved(transcripts: Path) -> None:
    config = small_config(chunk_size=(400,), chunk_overlap=(0,), k=(1,))
    (only,) = evaluate_grid(
        questions(),
        ["ES2015a"],
        config,
        LetterEmbedder(),
        transcripts,
        context_window=8192,  # zero characters left for the context
        max_generation_tokens=8192,
    )
    assert only.mean_recall == 1.0
    assert only.mean_delivered_recall == 0.0
    assert only.mean_delivered_chars == 0.0
    assert questions_with_any_delivered_hit(only) == 0


def test_trimming_hides_evidence_that_full_chunks_contain(tmp_path: Path) -> None:
    filler = "word " * 150  # ~750 chars per turn
    turns = [(f"{filler}marker{i}", (f"d{i}",)) for i in range(6)]
    write_meeting(tmp_path, "ES2015a", turns)
    qs = [
        TuningQuestion(
            "q1",
            QuestionStratum.E1_POINT_FACT,
            "marker0 marker5",
            (span("ES2015a", "d0", "d2", "d3", "d5"),),
        )
    ]
    config = small_config(chunk_size=(5000,), chunk_overlap=(0,), k=(1,))
    (full,) = evaluate_grid(qs, ["ES2015a"], config, LetterEmbedder(), tmp_path)
    (tight,) = evaluate_grid(
        qs,
        ["ES2015a"],
        config,
        LetterEmbedder(),
        tmp_path,
        context_window=8192 + 1300,
        max_generation_tokens=8192,
    )
    assert full.mean_recall == 1.0 and full.mean_delivered_recall == 1.0
    assert tight.mean_recall == 1.0
    assert tight.mean_delivered_recall < 1.0
    assert tight.mean_delivered_chars < full.mean_delivered_chars


def test_context_chars_and_eligibility(transcripts: Path) -> None:
    config = small_config(chunk_size=(400,), chunk_overlap=(0,), k=(1, 3), char_budget=900)
    first, second = evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert first.eligible  # 1 * 400 <= 900
    assert not second.eligible  # 3 * 400 > 900
    assert first.mean_context_chars > 0
    assert first.mean_context_chars <= 400


def test_first_hit_rank_is_none_beyond_k(transcripts: Path) -> None:
    config = small_config(chunk_size=(40,), chunk_overlap=(0,), k=(1, 3))
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
    config = small_config(chunk_size=(40,), chunk_overlap=(0,), k=(3, 12))
    evaluate_grid(questions(), ["ES2015a"], config, LetterEmbedder(), transcripts)
    assert sorted(set(limits)) == [3, 12]

    limits.clear()
    config = small_config(chunk_size=(40,), chunk_overlap=(0,), k=(3, 10))
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


def test_questions_with_any_delivered_hit_counts_positive_delivered_recall() -> None:
    r = dataclasses.replace(
        result(k=5, recall=0.5), delivered_recalls={"a": 0.5, "b": 0.0, "c": 0.25}
    )
    assert questions_with_any_delivered_hit(r) == 2


def test_load_pinned_c1_params_reads_the_retrieval_c1_section() -> None:
    experiments = {"retrieval": {"c1": {"chunk_size": 1600, "chunk_overlap": 0, "k": 8}}}
    params = c1_tuning.load_pinned_c1_params(experiments)
    assert (params.chunk_size, params.chunk_overlap, params.k) == (1600, 0, 8)


def test_load_pinned_c1_params_rejects_missing_section() -> None:
    with pytest.raises(ValueError, match=r"retrieval\.c1"):
        c1_tuning.load_pinned_c1_params({"retrieval": {}})


def test_pinned_c1_params_are_the_stored_winner() -> None:
    """``[retrieval.c1]`` pins what the pre-registered rule chose (notebook 06, ADR 0007)."""
    if '"chunk_size"' not in c1_tuning.RESULTS_PATH.read_text(encoding="utf-8"):
        pytest.skip("stored tuning predates the Markdown chunking; rerun `afg c1 tune`")
    stored = load_tuning_results(c1_tuning.RESULTS_PATH)
    pinned = c1_tuning.load_pinned_c1_params()
    w = stored.winner
    assert (pinned.chunk_size, pinned.chunk_overlap, pinned.k) == (
        w.chunk_size,
        w.chunk_overlap,
        w.k,
    )
    assert w.eligible
    assert pinned.k * pinned.chunk_size <= stored.config.char_budget
