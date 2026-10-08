"""Tests for C1 hybrid retrieval (BM25 + dense + RRF). No network: fake embedders only."""

from __future__ import annotations

import io
import json
import math
import urllib.error
from collections.abc import Sequence
from typing import Any

import pytest

from afg.conditions import c1_retrieval
from afg.conditions.c1_chunking import Chunk
from afg.conditions.c1_retrieval import (
    Bm25Index,
    DenseIndex,
    HybridRetriever,
    OllamaEmbedder,
    reciprocal_rank_fusion,
    tokenize,
)

# --- helpers ---------------------------------------------------------------------------


class LetterEmbedder:
    """Deterministic bag-of-letters embedder (26 dims)."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * 26
            for ch in text.lower():
                if "a" <= ch <= "z":
                    vec[ord(ch) - ord("a")] += 1.0
            out.append(vec)
        return out


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        meeting_id=chunk_id.split(".")[0],
        series="ES2015",
        first_turn=0,
        last_turn=0,
        start=None,
        end=None,
        dialogue_act_ids=(),
        text=text,
    )


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# --- tokenize --------------------------------------------------------------------------


def test_tokenize_lowercases_and_keeps_letter_runs_only() -> None:
    assert tokenize("Remote-Control costs 25 euros!") == ["remote", "control", "costs", "euros"]


def test_tokenize_drops_stopwords_and_digits() -> None:
    assert tokenize("What is the price of 12 apples") == ["price", "apples"]


def test_tokenize_only_stopwords_is_empty() -> None:
    assert tokenize("What did they do with it?") == []


# --- BM25 ------------------------------------------------------------------------------


def test_bm25_ranks_more_frequent_term_first() -> None:
    index = Bm25Index(
        [
            ("a", "banana apple cherry"),
            ("b", "banana banana apple"),
            ("c", "grape melon plum"),
            ("d", "kiwi lemon lime"),
            ("e", "fig date nut"),
        ]
    )
    ranked = index.scores("banana")
    assert [i for i, _ in ranked][:2] == ["b", "a"]
    assert ranked[0][1] > ranked[1][1] > 0.0
    assert ranked[2][1] == 0.0


def test_bm25_exact_score_matches_okapi_formula() -> None:
    # N=4, n=1 for "cherry" -> idf = ln((4-1+.5)/(1+.5)); doc c has tf=1, len=3, avgdl=2.5
    index = Bm25Index(
        [
            ("a", "banana apple"),
            ("b", "banana banana apple"),
            ("c", "cherry grape melon"),
            ("d", "kiwi"),
        ]
    )
    avgdl = (2 + 3 + 3 + 1) / 4
    idf = math.log((4 - 1 + 0.5) / (1 + 0.5))
    k1, b = 1.5, 0.75
    expected = idf * (1 * (k1 + 1)) / (1 + k1 * (1 - b + b * 3 / avgdl))
    scores = dict(index.scores("cherry"))
    assert scores["c"] == pytest.approx(expected)


def test_bm25_length_normalization_prefers_shorter_doc() -> None:
    index = Bm25Index(
        [
            ("short", "banana apple"),
            ("long", "banana apple cherry grape melon kiwi lemon lime"),
            ("other", "zebra"),
        ]
    )
    ranked = [i for i, _ in index.scores("banana")]
    assert ranked[:2] == ["short", "long"]


def test_bm25_rare_term_outweighs_common_term() -> None:
    index = Bm25Index(
        [
            ("a", "common rare"),
            ("b", "common"),
            ("c", "common"),
            ("d", "common"),
            ("e", "other"),
        ]
    )
    ranked = index.scores("common rare")
    assert ranked[0][0] == "a"


def test_bm25_negative_idf_is_floored_not_negative() -> None:
    # "common" appears in all docs -> raw idf < 0 -> replaced by epsilon * average idf (>= 0)
    index = Bm25Index(
        [
            (k, f"common {w}")
            for k, w in zip("abcdef", ["al", "be", "ga", "de", "ep", "ze"], strict=True)
        ]
    )
    assert all(score >= 0.0 for _, score in index.scores("common"))


def test_bm25_ties_keep_insertion_order() -> None:
    index = Bm25Index([("x", "banana"), ("y", "banana"), ("z", "cherry")])
    ranked = [i for i, _ in index.scores("banana")]
    assert ranked[:2] == ["x", "y"]


def test_bm25_empty_query_scores_all_zero_in_insertion_order() -> None:
    index = Bm25Index([("x", "banana"), ("y", "cherry")])
    assert index.scores("what is it") == [("x", 0.0), ("y", 0.0)]


def test_bm25_empty_corpus() -> None:
    assert Bm25Index([]).scores("banana") == []


# --- dense -----------------------------------------------------------------------------


def test_dense_search_orders_by_cosine_and_limits() -> None:
    index = DenseIndex(["a", "b", "c"], [[1.0, 0.0], [0.7, 0.7], [0.0, 1.0]])
    result = index.search([1.0, 0.1], 2)
    assert [i for i, _ in result] == ["a", "b"]
    assert result[0][1] == pytest.approx(1.0 / math.sqrt(1.01))


def test_dense_normalizes_defensively() -> None:
    index = DenseIndex(["a", "b"], [[10.0, 0.0], [0.0, 0.1]])
    result = dict(index.search([5.0, 0.0], 2))
    assert result["a"] == pytest.approx(1.0)
    assert result["b"] == pytest.approx(0.0)


def test_dense_ties_keep_insertion_order() -> None:
    index = DenseIndex(["a", "b", "c"], [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    assert [i for i, _ in index.search([1.0, 0.0], 3)] == ["a", "b", "c"]


def test_dense_zero_vector_scores_zero() -> None:
    index = DenseIndex(["a"], [[0.0, 0.0]])
    assert index.search([1.0, 0.0], 1) == [("a", 0.0)]


def test_dense_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        DenseIndex(["a", "b"], [[1.0]])


# --- RRF -------------------------------------------------------------------------------


def test_rrf_worked_example_exact_scores() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "d"]], k=60)
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["c"] == pytest.approx(1 / 63 + 1 / 62)
    assert scores["d"] == pytest.approx(1 / 63)
    assert [i for i, _ in fused] == ["b", "c", "a", "d"]


def test_rrf_ties_break_by_first_appearance() -> None:
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "a"]])
    assert [i for i, _ in fused] == ["a", "b"]
    assert fused[0][1] == pytest.approx(fused[1][1])


def test_rrf_default_k_is_60_and_empty_input() -> None:
    assert reciprocal_rank_fusion([["a"]]) == [("a", pytest.approx(1 / 61))]
    assert reciprocal_rank_fusion([]) == []


# --- HybridRetriever -------------------------------------------------------------------


def corpus() -> list[Chunk]:
    return [
        make_chunk("M.c000", "price of the remote control is twelve euros"),
        make_chunk("M.c001", "the battery lasts long"),
        make_chunk("M.c002", "colour yellow and blue"),
        make_chunk("M.c003", "marketing wants a fancy logo"),
    ]


def test_retriever_embeds_all_chunks_once_in_order() -> None:
    emb = LetterEmbedder()
    HybridRetriever(corpus(), emb)
    assert len(emb.calls) == 1
    assert emb.calls[0] == [c.text for c in corpus()]


def test_retriever_returns_ranked_chunks_with_channel_ranks() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    results = retriever.retrieve("price remote control", limit=2)
    assert len(results) == 2
    assert [r.rank for r in results] == [1, 2]
    top = results[0]
    assert top.chunk.chunk_id == "M.c000"
    assert top.lexical_rank == 1
    assert top.dense_rank is not None
    assert top.rrf_score > results[1].rrf_score


def test_retriever_score_is_sum_of_channel_contributions() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder(), rrf_k=60)
    top = retriever.retrieve("price remote control", limit=1)[0]
    assert top.lexical_rank is not None and top.dense_rank is not None
    expected = 1 / (60 + top.lexical_rank) + 1 / (60 + top.dense_rank)
    assert top.rrf_score == pytest.approx(expected)


def test_pool_is_at_least_ten_and_ranks_none_outside_pool() -> None:
    chunks = [make_chunk(f"M.c{i:03d}", f"filler{'x' * i} text") for i in range(30)]
    chunks[7] = make_chunk("M.c007", "unicorn")
    retriever = HybridRetriever(chunks, LetterEmbedder())
    results = retriever.retrieve("unicorn", limit=3)
    assert results[0].chunk.chunk_id == "M.c007"
    assert results[0].lexical_rank == 1
    # lexical channel returns 10 candidates (pool), the rest of 30 fall out of it;
    # only 1 chunk matches lexically, but the pool still holds zero-score fillers.
    ranks = [r.lexical_rank for r in results]
    assert all(r is None or 1 <= r <= 10 for r in ranks)
    assert all(r.dense_rank is None or 1 <= r.dense_rank <= 10 for r in results)


def test_pool_size_follows_limit_when_above_ten() -> None:
    uniq = [chr(97 + i // 26) * 2 + chr(97 + i % 26) * 3 for i in range(40)]
    chunks = [
        make_chunk(f"M.c{i:03d}", f"alpha {uniq[i]}" if i < 15 else uniq[i]) for i in range(40)
    ]
    retriever = HybridRetriever(chunks, LetterEmbedder())
    results = retriever.retrieve("alpha", limit=12)
    assert len(results) == 12
    ranks = [r.lexical_rank for r in results if r.lexical_rank is not None]
    assert ranks and max(ranks) <= 12


def test_lexical_channel_excludes_zero_score_chunks() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    results = retriever.retrieve("logo", limit=4)
    by_id = {r.chunk.chunk_id: r for r in results}
    assert by_id["M.c003"].lexical_rank == 1
    assert by_id["M.c001"].lexical_rank is None


def test_question_with_only_stopwords_still_gets_dense_results() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    results = retriever.retrieve("What did they do?", limit=3)
    assert len(results) == 3
    assert all(r.lexical_rank is None for r in results)
    assert all(r.dense_rank is not None for r in results)


def test_retrieve_limit_larger_than_corpus_and_empty_corpus() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    assert len(retriever.retrieve("price", limit=50)) == 4
    empty = HybridRetriever([], LetterEmbedder())
    assert empty.retrieve("price", limit=5) == []


def test_retrieve_is_deterministic() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    first = retriever.retrieve("colour of the remote", limit=4)
    second = retriever.retrieve("colour of the remote", limit=4)
    assert first == second


def test_retrieve_rejects_non_positive_limit() -> None:
    retriever = HybridRetriever(corpus(), LetterEmbedder())
    with pytest.raises(ValueError):
        retriever.retrieve("price", limit=0)


def test_from_config_reads_rrf_k_and_embedding_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        c1_retrieval,
        "load_experiments_config",
        lambda: {"shared_budget": {"embedding_model": "m-x"}, "retrieval": {"rrf_k": 7}},
    )
    assert c1_retrieval.configured_rrf_k() == 7
    assert c1_retrieval.configured_embedding_model() == "m-x"
    retriever = HybridRetriever.from_config(corpus(), LetterEmbedder())
    top = retriever.retrieve("price remote control", limit=1)[0]
    assert top.lexical_rank is not None and top.dense_rank is not None
    assert top.rrf_score == pytest.approx(1 / (7 + top.lexical_rank) + 1 / (7 + top.dense_rank))
    emb = OllamaEmbedder.from_config()
    assert emb.model == "m-x"


# --- OllamaEmbedder --------------------------------------------------------------------


def capture_urlopen(monkeypatch: pytest.MonkeyPatch, responder: Any) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    def fake(request: Any, timeout: float | None = None) -> FakeResponse:
        seen.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data.decode("utf-8")),
                "method": request.get_method(),
                "timeout": timeout,
                "content_type": request.get_header("Content-type"),
            }
        )
        return FakeResponse(responder(seen[-1]["body"]))

    monkeypatch.setattr("urllib.request.urlopen", fake)
    return seen


def test_ollama_request_construction_and_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture_urlopen(
        monkeypatch, lambda body: {"embeddings": [[1.0, 2.0] for _ in body["input"]]}
    )
    emb = OllamaEmbedder(model="bge-m3", host="http://h:1", timeout=9.0)
    assert emb.embed(["a", "b"]) == [[1.0, 2.0], [1.0, 2.0]]
    assert seen == [
        {
            "url": "http://h:1/api/embed",
            "body": {"model": "bge-m3", "input": ["a", "b"]},
            "method": "POST",
            "timeout": 9.0,
            "content_type": "application/json",
        }
    ]


def test_ollama_batches_and_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture_urlopen(
        monkeypatch, lambda body: {"embeddings": [[float(t)] for t in body["input"]]}
    )
    emb = OllamaEmbedder(model="m", host="http://h", batch_size=2)
    assert emb.embed(["1", "2", "3", "4", "5"]) == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    assert [s["body"]["input"] for s in seen] == [["1", "2"], ["3", "4"], ["5"]]


def test_ollama_empty_input_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture_urlopen(monkeypatch, lambda body: {"embeddings": []})
    assert OllamaEmbedder(model="m", host="http://h").embed([]) == []
    assert seen == []


def test_ollama_legacy_singular_embedding_key(monkeypatch: pytest.MonkeyPatch) -> None:
    capture_urlopen(monkeypatch, lambda body: {"embedding": [0.5, 0.25]})
    assert OllamaEmbedder(model="m", host="http://h").embed(["a"]) == [[0.5, 0.25]]


def test_ollama_wrong_count_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    capture_urlopen(monkeypatch, lambda body: {"embeddings": [[1.0]]})
    with pytest.raises(RuntimeError, match=r"bge-m3.*http://h"):
        OllamaEmbedder(model="bge-m3", host="http://h").embed(["a", "b"])


def test_ollama_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    capture_urlopen(monkeypatch, lambda body: {"oops": 1})
    with pytest.raises(RuntimeError, match="bge-m3"):
        OllamaEmbedder(model="bge-m3", host="http://h").embed(["a"])


def test_ollama_http_error_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(request: Any, timeout: float | None = None) -> FakeResponse:
        raise urllib.error.HTTPError(
            request.full_url,
            404,
            "model not found",
            None,
            io.BytesIO(b"nope"),  # type: ignore[arg-type]
        )

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(RuntimeError, match="bge-m3") as info:
        OllamaEmbedder(model="bge-m3", host="http://h").embed(["a"])
    assert "http://h" in str(info.value)


def test_ollama_connection_error_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(request: Any, timeout: float | None = None) -> FakeResponse:
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(RuntimeError, match="http://h"):
        OllamaEmbedder(model="m", host="http://h").embed(["a"])


def test_ollama_invalid_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class Bad(FakeResponse):
        def read(self) -> bytes:
            return b"not json"

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=None: Bad({}))
    with pytest.raises(RuntimeError, match="bge-m3"):
        OllamaEmbedder(model="bge-m3", host="http://h").embed(["a"])


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (None, "http://localhost:11434"),
        ("myhost:9999", "http://myhost:9999"),
        ("https://secure:1", "https://secure:1"),
        ("http://plain:2/", "http://plain:2"),
    ],
)
def test_ollama_host_resolution(
    monkeypatch: pytest.MonkeyPatch, env: str | None, expected: str
) -> None:
    if env is None:
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
    else:
        monkeypatch.setenv("OLLAMA_HOST", env)
    assert c1_retrieval.resolve_ollama_host() == expected
    assert OllamaEmbedder.from_config(model="m").host == expected
