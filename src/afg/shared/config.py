"""Runtime settings and TOML configuration loaders.

Two layers of configuration exist on purpose:

- **Runtime settings** (secrets, machine-specific paths, model endpoints) come from the
  environment / ``.env`` file via :class:`Settings` (pydantic-settings).
- **Experiment design parameters** (the AMI series list, the tau grid, question-bank
  strata) come from version-controlled TOML files under ``config/`` and are loaded with
  :func:`load_corpus_config` / :func:`load_experiments_config`. These are part of the
  published methodology (thesis section 5) and must not depend on any environment.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from afg.shared.paths import CONFIG_DIR, ENV_PATH


class Settings(BaseSettings):
    """Environment-backed runtime settings. See ``.env.example`` for the full list."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        env_prefix="AFG_",
        extra="ignore",
    )

    ami_root: Path | None = Field(default=None, description="Root of the extracted AMI corpus.")
    ollama_host: str = Field(default="http://localhost:11434")
    generative_model: str = Field(default="qwen3:8b")
    judge_model: str = Field(default="")
    embedding_model: str = Field(default="bge-m3")
    openkos_workspace: str | None = Field(default=None)
    seed: int = Field(default=42)
    log_level: str = Field(default="INFO")


def get_settings() -> Settings:
    """Return a fresh :class:`Settings` instance (re-reads the environment each call)."""
    return Settings()


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}. This repository ships this file "
            "under version control; a missing file suggests a broken checkout, not a "
            "runtime condition to handle gracefully."
        )
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_corpus_config() -> dict[str, Any]:
    """Load ``config/corpus.toml`` (AMI series, layers, download source, licence)."""
    return _load_toml(CONFIG_DIR / "corpus.toml")


def load_experiments_config() -> dict[str, Any]:
    """Load ``config/experiments.toml`` (C1/C2/C3 params, models, seeds, tau grid)."""
    return _load_toml(CONFIG_DIR / "experiments.toml")


def load_annotation_config() -> dict[str, Any]:
    """Load ``config/annotation.toml`` (who annotates which series, in which phase).

    The machine-readable form of ``docs/anotacion/asignacion/README.md``. It is the single
    source of truth for the split: ``afg gold prepare``, ``afg gold validate`` and
    ``afg gold status`` read this file, never the prose.
    """
    return _load_toml(CONFIG_DIR / "annotation.toml")
