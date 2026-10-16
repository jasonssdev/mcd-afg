"""Reproducibility fields of the Experiment B manifest (probes are faked: no network)."""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from afg.experiments import provenance as prov
from afg.experiments.provenance import LiveProbe, collect_provenance

_C1 = {"max_chars": 1200, "overlap_turns": 1, "k": 5, "extra": "ignored"}


class FakeProbe:
    def __init__(
        self,
        digests: Mapping[str, str] | None = None,
        ollama: str | None = "0.9.9",
        openkos: str | None = "0.5.2",
        dirty: bool | None = False,
    ) -> None:
        self._digests = digests
        self._ollama = ollama
        self._openkos = openkos
        self._dirty = dirty

    def model_digests(self) -> Mapping[str, str] | None:
        return self._digests

    def ollama_version(self) -> str | None:
        return self._ollama

    def openkos_version(self) -> str | None:
        return self._openkos

    def git_dirty(self) -> bool | None:
        return self._dirty


def _collect(probe: FakeProbe, questions: Path | None = None, **over: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "generative_model": "qwen3:8b",
        "judge_model": "gpt-oss:20b",
        "embedding_model": "bge-m3",
        "c1_params": _C1,
        "questions_path": questions,
    }
    kwargs.update(over)
    return collect_provenance(probe, **kwargs)


def test_digests_versions_and_params_are_recorded(tmp_path: Path) -> None:
    questions = tmp_path / "q.csv"
    questions.write_bytes(b"id,text\nq1,hola\n")
    probe = FakeProbe(
        digests={"qwen3:8b": "aaa", "gpt-oss:20b": "bbb", "bge-m3:latest": "ccc"}, dirty=True
    )
    out = _collect(probe, questions)
    assert out["generative_model_digest"] == "aaa"
    assert out["judge_model_digest"] == "bbb"
    assert out["embedding_model_digest"] == "ccc"  # untagged name resolves to :latest
    assert out["model_digest_source"] == "ollama /api/tags"
    assert out["ollama_version"] == "0.9.9"
    assert out["openkos_version"] == "0.5.2"
    assert out["c1_params"] == {"max_chars": 1200, "overlap_turns": 1, "k": 5}
    assert out["questions_sha256"] == hashlib.sha256(b"id,text\nq1,hola\n").hexdigest()
    assert out["git_dirty"] is True


def test_unreachable_ollama_gives_null_digests_with_a_source_note() -> None:
    out = _collect(FakeProbe(digests=None, ollama=None, openkos=None, dirty=None))
    assert out["generative_model_digest"] is None
    assert out["judge_model_digest"] is None
    assert out["embedding_model_digest"] is None
    assert out["model_digest_source"].startswith("unavailable")
    assert out["ollama_version"] is None
    assert out["openkos_version"] is None
    assert out["git_dirty"] is None
    assert out["questions_sha256"] is None


def test_a_model_missing_from_the_listing_has_a_null_digest() -> None:
    out = _collect(FakeProbe(digests={"qwen3:8b": "aaa"}))
    assert out["generative_model_digest"] == "aaa"
    assert out["judge_model_digest"] is None


def test_the_manifest_is_json_serializable(tmp_path: Path) -> None:
    json.dumps(_collect(FakeProbe(digests={})))


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_live_probe_reads_digests_and_version_from_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = {
        "/api/tags": {"models": [{"name": "qwen3:8b", "digest": "d1"}, {"name": "x"}]},
        "/api/version": {"version": "0.32.9"},
    }

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        path = str(request).removeprefix("http://ollama.test:1")
        return _Response(json.dumps(payloads[path]).encode())

    monkeypatch.setattr(prov.urllib.request, "urlopen", fake_urlopen)
    probe = LiveProbe(host="http://ollama.test:1")
    assert probe.model_digests() == {"qwen3:8b": "d1"}
    assert probe.ollama_version() == "0.32.9"


def test_live_probe_returns_none_when_ollama_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(request: Any, timeout: float) -> _Response:
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(prov.urllib.request, "urlopen", refuse)
    probe = LiveProbe(host="http://ollama.test:1")
    assert probe.model_digests() is None
    assert probe.ollama_version() is None
