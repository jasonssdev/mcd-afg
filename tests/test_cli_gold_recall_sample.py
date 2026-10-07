"""Tests for the overwrite guard of ``afg gold recall-sample``.

The recall sample is drawn once with a fixed seed and then annotated (Tarea C). Running the
command again used to overwrite it silently, and a sample regenerated after seeing results
is no longer a valid estimate. The command must refuse to write over an existing sample
unless ``--force`` is passed explicitly.

Nothing here reads the AMI corpus: the existing-file check runs before the corpus is
loaded, and the ``--force`` path stubs out decision loading and sampling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli

_EXISTING_SAMPLE = "pair_id,relation\nIS1004.r001,refina\n"


@pytest.fixture
def relations_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "relations"
    directory.mkdir()
    monkeypatch.setattr(afg_cli, "GOLD_RELATIONS_DIR", directory)
    return directory


@pytest.fixture
def stub_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(afg_cli, "_decisions_for_series_or_exit", lambda ami_root, series: [])
    monkeypatch.setattr(afg_cli, "sample_rejected", lambda decisions, **kwargs: [])


def _invoke(*extra: str) -> object:
    return CliRunner().invoke(afg_cli.app, ["gold", "recall-sample", "--series", "IS1004", *extra])


class TestRecallSampleOverwriteGuard:
    def test_refuses_to_overwrite_an_existing_sample(self, relations_dir: Path) -> None:
        sample = relations_dir / "IS1004.recall-sample.csv"
        sample.write_text(_EXISTING_SAMPLE, encoding="utf-8")

        result = _invoke()

        assert result.exit_code == 1
        assert sample.read_text(encoding="utf-8") == _EXISTING_SAMPLE
        message = " ".join(result.output.split())  # the console wraps long lines
        assert "ya existe" in message
        assert "--force" in message

    def test_force_overwrites_an_existing_sample(
        self, relations_dir: Path, stub_sampling: None
    ) -> None:
        sample = relations_dir / "IS1004.recall-sample.csv"
        sample.write_text(_EXISTING_SAMPLE, encoding="utf-8")

        result = _invoke("--force")

        assert result.exit_code == 0, result.output
        assert sample.read_text(encoding="utf-8") != _EXISTING_SAMPLE

    def test_writes_a_new_sample_without_force(
        self, relations_dir: Path, stub_sampling: None
    ) -> None:
        result = _invoke()

        assert result.exit_code == 0, result.output
        assert (relations_dir / "IS1004.recall-sample.csv").exists()
