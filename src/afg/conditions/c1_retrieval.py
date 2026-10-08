"""Hybrid retrieval for C1 (plain document-RAG baseline, thesis section 5.3).

C1 retrieves turn-aligned transcript chunks (see ``c1_chunking``) with two channels, a
lexical one (BM25 Okapi) and a dense one (cosine over ``bge-m3`` embeddings), fused with
reciprocal rank fusion (RRF). It is C1's own retrieval, separate from OpenKOS (ADR 0006),
but it deliberately mirrors OpenKOS wherever the comparison with C2/C3 could otherwise be
confounded.

Fairness choices mirrored from OpenKOS:

* Candidate pool: each channel is queried for ``max(limit, 10)`` candidates.
* Fusion: ``score = sum(1 / (k + rank))`` over channels, 1-based ranks, ``k = 60``
  (``[retrieval] rrf_k`` in ``config/experiments.toml``), then the top ``limit``.
* Dense embeddings: the same model (``[shared_budget] embedding_model``) served by the
  same runtime (Ollama ``POST /api/embed``, host from ``OLLAMA_HOST``).

Declared differences:

* The lexical channel is BM25 Okapi implemented here, not SQLite FTS5.
* No stemming (OpenKOS' FTS5 uses the porter stemmer). Tokens are lowercase letter runs
  with English function words removed, mirroring the spirit of OpenKOS' query-term filter.
* Neither condition has a reranker.

Only the standard library is used (``urllib`` for HTTP) so the module needs no extra
dependency.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from afg.conditions.c1_chunking import Chunk
from afg.shared.config import load_experiments_config

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
MIN_POOL = 10

# English function words dropped from BM25 documents and queries. Small and explicit on
# purpose: it removes grammatical glue and question words, not content words.
STOPWORDS: frozenset[str] = frozenset(
    """
    a about above after again all also am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from
    further had has have having he her here hers herself him himself his how i if in into is
    it its itself just me more most my myself no nor not now of off on once only or other our
    ours ourselves out over own same she should so some such than that the their theirs them
    themselves then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your yours yourself
    yourselves
    """.split()  # noqa: SIM905 - a flat word list is easier to audit than quoted items
)

_WORD_RE = re.compile(r"[^\W\d_]+")


def tokenize(text: str) -> list[str]:
    """Lowercase letter-only runs with stopwords removed (no stemming)."""
    return [t for t in _WORD_RE.findall(text.lower()) if t not in STOPWORDS]


# --- embeddings ------------------------------------------------------------------------


class Embedder(Protocol):
    """Turns texts into dense vectors, one per text, in order."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def resolve_ollama_host() -> str:
    """``OLLAMA_HOST`` (``http://`` prefixed when it has no scheme) or the local default."""
    raw = os.environ.get("OLLAMA_HOST", "").strip()
    if not raw:
        return DEFAULT_OLLAMA_HOST
    if "://" not in raw:
        raw = f"http://{raw}"
    return raw.rstrip("/")


def configured_embedding_model() -> str:
    return str(load_experiments_config()["shared_budget"]["embedding_model"])


def configured_rrf_k() -> int:
    return int(load_experiments_config()["retrieval"]["rrf_k"])


@dataclass(frozen=True, slots=True)
class OllamaEmbedder:
    """Embeds through Ollama ``POST {host}/api/embed`` (same runtime as OpenKOS)."""

    model: str
    host: str = DEFAULT_OLLAMA_HOST
    timeout: float = 120.0
    batch_size: int = 32

    @classmethod
    def from_config(cls, model: str | None = None, **kwargs: Any) -> OllamaEmbedder:
        """Model from the experiments config (unless given), host from ``OLLAMA_HOST``."""
        return cls(
            model=model or configured_embedding_model(),
            host=resolve_ollama_host(),
            **kwargs,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        where = f"model {self.model!r} at {self.host}"
        request = urllib.request.Request(
            f"{self.host}/api/embed",
            data=json.dumps({"model": self.model, "input": batch}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Ollama embed request failed for {where}: HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"Cannot reach Ollama for {where}: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON for {where}") from exc

        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if embeddings is None and isinstance(payload, dict) and "embedding" in payload:
            embeddings = [payload["embedding"]]  # legacy singular response
        if (
            not isinstance(embeddings, list)
            or len(embeddings) != len(batch)
            or not all(isinstance(v, list) and v for v in embeddings)
        ):
            raise RuntimeError(
                f"Unexpected Ollama embed response for {where}: expected {len(batch)} "
                "non-empty vectors under 'embeddings'"
            )
        return [[float(x) for x in v] for v in embeddings]


# --- lexical channel -------------------------------------------------------------------


class Bm25Index:
    """BM25 Okapi (k1=1.5, b=0.75) with the negative-idf floor of ``rank_bm25``."""

    def __init__(
        self,
        documents: Sequence[tuple[str, str]],
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ) -> None:
        self._ids = [doc_id for doc_id, _ in documents]
        self._k1 = k1
        self._b = b
        self._tfs = [Counter(tokenize(text)) for _, text in documents]
        self._lengths = [sum(tf.values()) for tf in self._tfs]
        n_docs = len(self._ids)
        self._avgdl = sum(self._lengths) / n_docs if n_docs else 0.0
        doc_freq: Counter[str] = Counter()
        for tf in self._tfs:
            doc_freq.update(tf.keys())
        idf = {term: math.log((n_docs - n + 0.5) / (n + 0.5)) for term, n in doc_freq.items()}
        average_idf = sum(idf.values()) / len(idf) if idf else 0.0
        floor = epsilon * average_idf
        self._idf = {term: (value if value >= 0 else floor) for term, value in idf.items()}

    def scores(self, query: str) -> list[tuple[str, float]]:
        """All documents ranked by score descending; ties keep insertion order."""
        terms = tokenize(query)
        scored: list[tuple[str, float]] = []
        for doc_id, tf, length in zip(self._ids, self._tfs, self._lengths, strict=True):
            score = 0.0
            for term in terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                norm = 1 - self._b + self._b * length / self._avgdl if self._avgdl else 1.0
                score += self._idf[term] * freq * (self._k1 + 1) / (freq + self._k1 * norm)
            scored.append((doc_id, score))
        return sorted(scored, key=lambda item: -item[1])


# --- dense channel ---------------------------------------------------------------------


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else [0.0] * len(vector)


class DenseIndex:
    """Cosine-similarity search over stored vectors (normalized defensively)."""

    def __init__(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        if len(ids) != len(vectors):
            raise ValueError(f"{len(ids)} ids but {len(vectors)} vectors")
        self._ids = list(ids)
        self._vectors = [_normalize(v) for v in vectors]

    def search(self, query_vector: Sequence[float], limit: int) -> list[tuple[str, float]]:
        query = _normalize(query_vector)
        scored = [
            (doc_id, sum(a * b for a, b in zip(query, vec, strict=True)))
            for doc_id, vec in zip(self._ids, self._vectors, strict=True)
        ]
        return sorted(scored, key=lambda item: -item[1])[:limit]


# --- fusion ----------------------------------------------------------------------------


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], k: int = 60
) -> list[tuple[str, float]]:
    """``score = sum(1 / (k + rank))`` with 1-based ranks; ties by first appearance."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + position)
    return sorted(scores.items(), key=lambda item: -item[1])


# --- hybrid retriever ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A fused hit; channel ranks are 1-based within the pool, ``None`` if absent."""

    chunk: Chunk
    rank: int
    rrf_score: float
    lexical_rank: int | None
    dense_rank: int | None


@dataclass(slots=True)
class HybridRetriever:
    """BM25 + dense retrieval fused with RRF over a fixed set of chunks."""

    chunks: Sequence[Chunk]
    embedder: Embedder
    rrf_k: int = 60
    _by_id: dict[str, Chunk] = field(init=False, repr=False)
    _bm25: Bm25Index = field(init=False, repr=False)
    _dense: DenseIndex = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {c.chunk_id: c for c in self.chunks}
        if len(self._by_id) != len(self.chunks):
            raise ValueError("chunk_id values must be unique")
        self._bm25 = Bm25Index([(c.chunk_id, c.text) for c in self.chunks])
        vectors = self.embedder.embed([c.text for c in self.chunks]) if self.chunks else []
        self._dense = DenseIndex([c.chunk_id for c in self.chunks], vectors)

    @classmethod
    def from_config(cls, chunks: Sequence[Chunk], embedder: Embedder) -> HybridRetriever:
        """Build with ``rrf_k`` from ``config/experiments.toml``."""
        return cls(chunks, embedder, rrf_k=configured_rrf_k())

    def retrieve(self, question: str, limit: int) -> list[RetrievedChunk]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if not self.chunks:
            return []
        pool = max(limit, MIN_POOL)
        lexical = [i for i, score in self._bm25.scores(question)[:pool] if score > 0.0]
        query_vector = self.embedder.embed([question])[0]
        dense = [i for i, _ in self._dense.search(query_vector, pool)]
        lexical_rank = {i: r for r, i in enumerate(lexical, start=1)}
        dense_rank = {i: r for r, i in enumerate(dense, start=1)}
        fused = reciprocal_rank_fusion([lexical, dense], k=self.rrf_k)[:limit]
        return [
            RetrievedChunk(
                chunk=self._by_id[chunk_id],
                rank=rank,
                rrf_score=score,
                lexical_rank=lexical_rank.get(chunk_id),
                dense_rank=dense_rank.get(chunk_id),
            )
            for rank, (chunk_id, score) in enumerate(fused, start=1)
        ]
