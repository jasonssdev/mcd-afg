"""A tiny frozen tree under ``tmp_path`` for the freeze gate tests; never the real repository."""

from __future__ import annotations

from pathlib import Path

from afg.experiments.freeze import FreezeSources

CONFIG_TEXT = """[pinned_environment]
ollama_version = "0.32.9"
openkos_version = "0.7.0"

[pinned_environment.model_digests]
"qwen3:8b" = "aaa"
"bge-m3" = "bbb"
"""
SERIES = ("ES2002", "ES2008")
"""Two evaluation series of ``config/corpus.toml``."""
COMMIT = "c" * 40


def make_sources(
    root: Path, *, bank_text: str = "bank\n", series: tuple[str, ...] = SERIES
) -> FreezeSources:
    """Config, references of ``SERIES`` and a question bank, laid out like the repository."""
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "experiments.toml").write_text(CONFIG_TEXT, encoding="utf-8")
    decisions = root / "data" / "processed" / "decisions"
    relations = root / "data" / "processed" / "relations"
    questions = root / "data" / "processed" / "questions"
    for folder in (decisions, relations, questions):
        folder.mkdir(parents=True, exist_ok=True)
    for name in series:
        (decisions / f"{name}.decisions.adjudicated.csv").write_text(f"d {name}\n")
        (decisions / f"{name}.reference-en.csv").write_text(f"en {name}\n")
        (relations / f"{name}.candidates.gv.csv").write_text(f"r {name}\n")
    (questions / "banco-preguntas.csv").write_text(bank_text, encoding="utf-8")
    (root / "config" / "corpus.toml").write_text("[oe1]\n", encoding="utf-8")
    (root / "config" / "annotation.toml").write_text("[phase]\n", encoding="utf-8")
    transcripts = root / "data" / "interim" / "transcripts"
    transcripts.mkdir(parents=True, exist_ok=True)
    for name in ("ES2002a", "ES2002b"):
        (transcripts / f"{name}.md").write_text(f"md {name}\n", encoding="utf-8")
        (transcripts / f"{name}.jsonl").write_text(f"jl {name}\n", encoding="utf-8")
    return FreezeSources(
        root=root,
        config_path=root / "config" / "experiments.toml",
        decisions_dir=decisions,
        relations_dir=relations,
        question_bank_path=questions / "banco-preguntas.csv",
        transcripts_dir=transcripts,
        corpus_config_path=root / "config" / "corpus.toml",
        annotation_config_path=root / "config" / "annotation.toml",
    )
