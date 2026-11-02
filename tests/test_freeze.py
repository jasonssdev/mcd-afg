"""The freeze record: what it stores, how it is written and how the series gate reads it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afg.experiments.freeze import (
    FreezeError,
    FreezeSources,
    SeriesGateError,
    build_freeze_record,
    freeze_differences,
    gate_partition,
    read_freeze_record,
    write_freeze_record,
)
from tests.freeze_fixtures import COMMIT, CONFIG_TEXT, SERIES, make_sources


def partition_of(series: str) -> str:
    if series in ("ES2015", "IS1004"):
        return "development"
    if series in SERIES:
        return "evaluation"
    return "unassigned"


@pytest.fixture
def sources(tmp_path: Path) -> FreezeSources:
    return make_sources(tmp_path)


@pytest.fixture
def record_path(sources: FreezeSources) -> Path:
    path = sources.root / "config" / "freeze.json"
    write_freeze_record(path, sources, series=SERIES, adr="0017", commit=COMMIT)
    return path


def no_code_changes(commit: str) -> list[str]:
    return []


def differences(sources: FreezeSources, record_path: Path, **kwargs: object) -> list[str]:
    return freeze_differences(
        read_freeze_record(record_path),
        sources,
        code_changes=no_code_changes,
        **kwargs,  # type: ignore[arg-type]
    )


# --- write ---------------------------------------------------------------------------------


def test_the_record_holds_adr_commit_and_every_digest(
    sources: FreezeSources, record_path: Path
) -> None:
    data = json.loads(record_path.read_text(encoding="utf-8"))

    assert data["adr"] == "0017" and data["code_commit"] == COMMIT
    assert data["experiments_config"]["path"] == "config/experiments.toml"
    assert len(data["experiments_config"]["sha256"]) == 64
    assert data["question_bank"]["path"] == "data/processed/questions/banco-preguntas.csv"
    es2002 = data["reference"]["ES2002"]
    assert es2002["decisions"]["path"].endswith("ES2002.decisions.adjudicated.csv")
    assert es2002["relations"]["path"].endswith("ES2002.candidates.gv.csv")
    assert es2002["reference_en"]["path"].endswith("ES2002.reference-en.csv")
    assert data["pinned_environment"]["ollama_version"] == "0.32.9"
    assert data["pinned_environment"]["model_digests"] == {"qwen3:8b": "aaa", "bge-m3": "bbb"}


def test_writing_is_deterministic(sources: FreezeSources, tmp_path: Path) -> None:
    first = build_freeze_record(sources, series=SERIES, adr="0017", commit=COMMIT)
    second = build_freeze_record(sources, series=reversed(SERIES), adr="0017", commit=COMMIT)

    assert first == second


def test_an_existing_record_is_never_overwritten(sources: FreezeSources, record_path: Path) -> None:
    with pytest.raises(FreezeError, match=r"[Yy]a existe"):
        write_freeze_record(record_path, sources, series=SERIES, adr="0018", commit=COMMIT)


def test_writing_refuses_a_missing_reference_naming_it(sources: FreezeSources) -> None:
    (sources.decisions_dir / "ES2008.reference-en.csv").unlink()

    with pytest.raises(FreezeError, match=r"ES2008.*reference-en"):
        build_freeze_record(sources, series=SERIES, adr="0017", commit=COMMIT)


def test_a_commit_that_is_not_a_hash_is_refused(sources: FreezeSources) -> None:
    with pytest.raises(FreezeError, match="commit"):
        build_freeze_record(sources, series=SERIES, adr="0017", commit="HEAD")


# --- verify --------------------------------------------------------------------------------


def test_a_matching_record_has_no_differences(sources: FreezeSources, record_path: Path) -> None:
    assert differences(sources, record_path) == []


def test_a_changed_config_is_named(sources: FreezeSources, record_path: Path) -> None:
    sources.config_path.write_text(CONFIG_TEXT + "# edit\n", encoding="utf-8")

    found = differences(sources, record_path)

    assert any("config/experiments.toml" in d and "huella" in d for d in found)


def test_changed_pins_are_named_apart_from_the_file(
    sources: FreezeSources, record_path: Path
) -> None:
    sources.config_path.write_text(CONFIG_TEXT.replace("0.7.0", "0.8.0"), encoding="utf-8")

    found = differences(sources, record_path)

    assert any("openkos_version" in d and "0.8.0" in d and "0.7.0" in d for d in found)


def test_a_changed_reference_file_is_named_by_series(
    sources: FreezeSources, record_path: Path
) -> None:
    (sources.decisions_dir / "ES2008.decisions.adjudicated.csv").write_text("changed\n")

    found = differences(sources, record_path)

    assert any("ES2008" in d and "decisions" in d for d in found)
    assert not any("ES2002" in d for d in found)


def test_a_new_adjudicated_file_changes_which_file_is_the_reference(
    sources: FreezeSources, record_path: Path
) -> None:
    (sources.relations_dir / "ES2002.candidates.adjudicated.csv").write_text("adj\n")

    found = differences(sources, record_path)

    assert any("ES2002" in d and "relations" in d for d in found)


def test_a_missing_reference_file_is_a_difference(
    sources: FreezeSources, record_path: Path
) -> None:
    (sources.decisions_dir / "ES2002.reference-en.csv").unlink()

    assert any("ES2002" in d and "reference_en" in d for d in differences(sources, record_path))


def test_the_question_bank_is_checked(sources: FreezeSources, record_path: Path) -> None:
    sources.question_bank_path.write_text("other bank\n", encoding="utf-8")

    assert any("question_bank" in d for d in differences(sources, record_path))


def test_a_given_questions_file_must_be_the_frozen_bank(
    sources: FreezeSources, record_path: Path, tmp_path: Path
) -> None:
    copy = tmp_path / "copy.csv"
    copy.write_text("bank\n", encoding="utf-8")
    other = tmp_path / "other.csv"
    other.write_text("not the bank\n", encoding="utf-8")

    assert differences(sources, record_path, questions_path=copy) == []
    assert any(
        "question_bank" in d for d in differences(sources, record_path, questions_path=other)
    )


def test_code_changed_since_the_frozen_commit_is_named(
    sources: FreezeSources, record_path: Path
) -> None:
    found = freeze_differences(
        read_freeze_record(record_path),
        sources,
        code_changes=lambda commit: ["src/afg/cli.py", "uv.lock"],
    )

    assert any("src/afg/cli.py" in d and "uv.lock" in d and COMMIT[:7] in d for d in found)


def test_every_difference_is_listed_at_once(sources: FreezeSources, record_path: Path) -> None:
    sources.config_path.write_text("x\n", encoding="utf-8")
    sources.question_bank_path.write_text("x\n", encoding="utf-8")

    assert len(differences(sources, record_path)) >= 3


# --- read ----------------------------------------------------------------------------------


def test_a_missing_record_is_an_error_naming_the_file(tmp_path: Path) -> None:
    with pytest.raises(FreezeError, match=r"freeze\.json"):
        read_freeze_record(tmp_path / "freeze.json")


def test_a_malformed_record_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "freeze.json"
    path.write_text('{"adr": "0017"}', encoding="utf-8")

    with pytest.raises(FreezeError, match="mal formado"):
        read_freeze_record(path)


# --- gate ----------------------------------------------------------------------------------


def gate(sources: FreezeSources, path: Path, series: list[str], **kwargs: object) -> str:
    return gate_partition(
        series,
        partition_of,
        freeze_path=path,
        sources=sources,
        code_changes=no_code_changes,
        **kwargs,  # type: ignore[arg-type]
    )


def test_development_series_pass_without_any_record(sources: FreezeSources, tmp_path: Path) -> None:
    assert gate(sources, tmp_path / "absent.json", ["ES2015", "IS1004"]) == "development"


def test_evaluation_series_are_refused_without_a_record(
    sources: FreezeSources, tmp_path: Path
) -> None:
    with pytest.raises(SeriesGateError) as raised:
        gate(sources, tmp_path / "absent.json", ["ES2002"])

    message = str(raised.value)
    assert "ES2002" in message and "congelamiento" in message and "absent.json" in message
    assert "no se llamó a ningún modelo" in message


def test_evaluation_series_pass_with_a_matching_record(
    sources: FreezeSources, record_path: Path
) -> None:
    assert gate(sources, record_path, ["ES2002", "ES2008"]) == "evaluation"
    assert gate(sources, record_path, ["ES2002", "ES2015"]) == "mixed"


def test_a_mismatch_refuses_naming_every_difference(
    sources: FreezeSources, record_path: Path
) -> None:
    (sources.decisions_dir / "ES2008.decisions.adjudicated.csv").write_text("changed\n")

    with pytest.raises(SeriesGateError) as raised:
        gate(sources, record_path, ["ES2002"])

    assert "ES2008" in str(raised.value) and "decisions" in str(raised.value)


def test_a_series_missing_from_the_record_is_refused(
    sources: FreezeSources, record_path: Path
) -> None:
    def other(series: str) -> str:
        return "evaluation" if series == "ES2014" else partition_of(series)

    with pytest.raises(SeriesGateError, match="ES2014"):
        gate_partition(
            ["ES2014"],
            other,
            freeze_path=record_path,
            sources=sources,
            code_changes=no_code_changes,
        )


def test_unassigned_series_are_refused_even_with_a_record(
    sources: FreezeSources, record_path: Path
) -> None:
    with pytest.raises(SeriesGateError, match="XX9999"):
        gate(sources, record_path, ["XX9999"])


def test_the_gate_checks_the_questions_file_it_is_given(
    sources: FreezeSources, record_path: Path, tmp_path: Path
) -> None:
    other = tmp_path / "other.csv"
    other.write_text("not the bank\n", encoding="utf-8")

    with pytest.raises(SeriesGateError, match="question_bank"):
        gate(sources, record_path, ["ES2002"], questions_path=other)
