"""The summaries printed by ``afg gold build|agreement|candidates|recall-sample`` are Spanish.

The numbers and the markup stay as they were; only the wording is pinned here. Corpus loading,
sampling and kappa computation are stubbed: nothing reads the AMI corpus.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import afg.annotation.agreement as agreement_module
import afg.annotation.goldset as goldset_module
import afg.cli as afg_cli
from afg.shared.config import Settings


def _flat(output: str) -> str:
    return " ".join(output.split())  # the console wraps long lines


@pytest.fixture
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("GOLD_RELATIONS_DIR", "GOLD_DECISIONS_DIR", "TABLES_DIR"):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(afg_cli, name, directory)
    monkeypatch.setattr(afg_cli, "_refuse_or_warn_if_series_annotated", lambda s, *, force: None)
    monkeypatch.setattr(
        afg_cli, "get_settings", lambda: Settings(_env_file=None, ami_root=tmp_path)
    )
    return tmp_path


def test_recall_sample_summary_is_spanish(isolated_dirs: Path, monkeypatch) -> None:
    monkeypatch.setattr(afg_cli, "_decisions_for_series_or_exit", lambda ami_root, series: [])
    monkeypatch.setattr(afg_cli, "sample_rejected", lambda decisions, **kwargs: [])

    result = CliRunner().invoke(afg_cli.app, ["gold", "recall-sample", "--series", "IS1004"])

    assert result.exit_code == 0, result.output
    text = _flat(result.output)
    assert "Serie IS1004: muestra de 0 pares rechazados (semilla=" in text
    assert "sampled" not in text


def test_candidates_summary_is_spanish(isolated_dirs: Path, monkeypatch) -> None:
    monkeypatch.setattr(afg_cli, "_decisions_for_series_or_exit", lambda ami_root, series: [])

    result = CliRunner().invoke(afg_cli.app, ["gold", "candidates", "--series", "IS1004"])

    assert result.exit_code == 0, result.output
    text = _flat(result.output)
    assert "Serie IS1004: 0 pares considerados, 0 candidatos seleccionados (0.0 %)" in text
    assert "pairs considered" not in text


def test_build_summary_is_spanish(isolated_dirs: Path, monkeypatch) -> None:
    rows = [
        SimpleNamespace(meeting_id="IS1004a", machine_flags="short;no_verb"),
        SimpleNamespace(meeting_id="IS1004b", machine_flags=""),
    ]
    monkeypatch.setattr(goldset_module, "build_gold_decisions", lambda ami_root, series: rows)
    monkeypatch.setattr(goldset_module, "write_gold_decisions_csv", lambda rows, path: None)

    result = CliRunner().invoke(afg_cli.app, ["gold", "build", "--series", "IS1004"])

    assert result.exit_code == 0, result.output
    text = _flat(result.output)
    assert "Serie IS1004: 2 oraciones de decisión en 2 reuniones." in text
    assert "machine_flags son pistas de triaje, NO un veredicto" in text
    assert "triage hints" not in text


def test_build_without_rows_explains_in_spanish(isolated_dirs: Path, monkeypatch) -> None:
    monkeypatch.setattr(goldset_module, "build_gold_decisions", lambda ami_root, series: [])

    result = CliRunner().invoke(afg_cli.app, ["gold", "build", "--series", "IS1004"])

    assert result.exit_code == 1
    text = _flat(result.output)
    assert "No se encontraron oraciones DECISIONS" in text
    assert "No abstractive" not in text


def _agreement(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "series_id": "IS1004",
        "annotator_a": "gm",
        "annotator_b": "gv",
        "n_items": 10,
        "existence_kappa": 0.5,
        "existence_disagreements": ("p1",),
        "n_type_items": 4,
        "type_kappa": 0.25,
        "type_disagreements": ("p2",),
        "direction_kappa": 1.0,
        "direction_disagreements": (),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _stub_agreement(monkeypatch, paths: list[Path], result: SimpleNamespace) -> None:
    monkeypatch.setattr(agreement_module, "annotator_csvs", lambda *a, **k: paths)
    monkeypatch.setattr(agreement_module, "compute_series_agreement", lambda p: result)
    monkeypatch.setattr(agreement_module, "write_agreement_csv", lambda r, p: None)


def test_agreement_summary_is_spanish(isolated_dirs: Path, monkeypatch) -> None:
    _stub_agreement(monkeypatch, [Path("a.csv"), Path("b.csv")], _agreement())

    result = CliRunner().invoke(afg_cli.app, ["gold", "agreement", "--series", "IS1004"])

    assert result.exit_code == 0, result.output
    text = _flat(result.output)
    assert "Serie IS1004: gm vs gv (10 ítems pareados)." in text
    assert "kappa de existencia: 0.500 (1 desacuerdos)" in text
    assert "kappa de tipo:" in text
    assert "kappa de dirección: 1.000 (0 desacuerdos)" in text
    assert "desacuerdos de existencia (por adjudicar): p1" in text
    assert "paired items" not in text


def test_agreement_without_type_pairs_says_so_in_spanish(isolated_dirs: Path, monkeypatch) -> None:
    _stub_agreement(
        monkeypatch,
        [Path("a.csv"), Path("b.csv")],
        _agreement(type_kappa=None, n_type_items=0, type_disagreements=()),
    )

    result = CliRunner().invoke(afg_cli.app, ["gold", "agreement", "--series", "IS1004"])

    assert "n/d (ningún par fue marcado como vínculo existente por ambos anotadores)" in _flat(
        result.output
    )


def test_agreement_needs_two_files_in_spanish(isolated_dirs: Path, monkeypatch) -> None:
    _stub_agreement(monkeypatch, [Path("a.csv")], _agreement())

    result = CliRunner().invoke(afg_cli.app, ["gold", "agreement", "--series", "IS1004"])

    assert result.exit_code == 1
    text = _flat(result.output)
    assert "Hacen falta al menos 2 archivos de anotadores" in text
    assert "Need at least" not in text


def test_agreement_warns_about_extra_files_in_spanish(isolated_dirs: Path, monkeypatch) -> None:
    _stub_agreement(monkeypatch, [Path("a.csv"), Path("b.csv"), Path("c.csv")], _agreement())

    result = CliRunner().invoke(afg_cli.app, ["gold", "agreement", "--series", "IS1004"])

    text = _flat(result.output)
    assert "Se encontraron 3 archivos de anotadores; se usan los dos primeros" in text
    assert "Found 3" not in text
