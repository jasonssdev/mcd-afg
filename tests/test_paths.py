"""Tests for the shared path constants."""

from __future__ import annotations

from afg.shared.paths import CONFIG_DIR, EXPERIMENTS_CONFIG_PATH, PROJECT_ROOT


def test_the_experiments_config_path_points_at_the_versioned_file() -> None:
    assert EXPERIMENTS_CONFIG_PATH == CONFIG_DIR / "experiments.toml"
    assert EXPERIMENTS_CONFIG_PATH.is_file()
    assert EXPERIMENTS_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix() == "config/experiments.toml"
