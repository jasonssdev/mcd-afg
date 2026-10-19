"""Tests for the English translation of the adjudicated reference (issue #141)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.reference import NotAdjudicatedError, load_reference
from afg.evaluation.translation import (
    TRANSLATION_COLUMNS,
    TranslationError,
    translation_path,
    validate_translation,
    write_translation_template,
)
from tests.test_reference import HEADER, MEETING, _row, _write_csv, transcripts  # noqa: F401

SERIES = "ES2015"


def _adjudicated(directory: Path) -> Path:
    rows = [
        _row("ES2015a.d01", "decision", final_object="precio", final_content="fijar 25 euros"),
        _row("ES2015a.d02", "no_decision"),
        _row("ES2015a.d03", "compuesta", sentence="s.3"),
        _row("ES2015a.d03-1", "decision", final_object="carcasa", final_content="usar goma"),
        _row("ES2015a.d03-2", "descartar"),
    ]
    return _write_csv(directory / f"{SERIES}.decisions.adjudicated.csv", rows, HEADER)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_translation(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TRANSLATION_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in TRANSLATION_COLUMNS})


def _filled(directory: Path) -> Path:
    path = write_translation_template(SERIES, decisions_dir=directory)
    rows = _read(path)
    for row in rows:
        row["object_en"] = f"en {row['final_object']}"
        row["content_en"] = f"en {row['final_content']}"
    _write_translation(path, rows)
    return path


def test_template_has_one_row_per_reference_decision_with_spanish_filled(tmp_path: Path) -> None:
    _adjudicated(tmp_path)

    path = write_translation_template(SERIES, decisions_dir=tmp_path)

    assert path == translation_path(SERIES, tmp_path)
    assert path.name == "ES2015.reference-en.csv"
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(TRANSLATION_COLUMNS)
    rows = _read(path)
    assert [r["decision_id"] for r in rows] == ["ES2015a.d01", "ES2015a.d03-1"]
    assert rows[0]["final_object"] == "precio"
    assert rows[0]["final_content"] == "fijar 25 euros"
    assert rows[0]["object_en"] == "" and rows[0]["content_en"] == ""
    assert rows[0]["translation_method"] == "automatica"


def test_template_refuses_to_overwrite_unless_forced(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    path = write_translation_template(SERIES, decisions_dir=tmp_path)
    path.write_text("manual work", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_translation_template(SERIES, decisions_dir=tmp_path)
    assert path.read_text(encoding="utf-8") == "manual work"

    write_translation_template(SERIES, decisions_dir=tmp_path, force=True)
    assert _read(path)[0]["decision_id"] == "ES2015a.d01"


def test_template_needs_the_adjudicated_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_translation_template(SERIES, decisions_dir=tmp_path)


def test_a_complete_translation_has_no_issues(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    _filled(tmp_path)

    assert validate_translation(SERIES, decisions_dir=tmp_path) == []


def test_missing_file_is_reported(tmp_path: Path) -> None:
    _adjudicated(tmp_path)

    (issue,) = validate_translation(SERIES, decisions_dir=tmp_path)

    assert "ES2015.reference-en.csv" in issue
    assert "translation-template" in issue


def test_empty_english_cells_are_reported(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    write_translation_template(SERIES, decisions_dir=tmp_path)

    issues = validate_translation(SERIES, decisions_dir=tmp_path)

    assert len(issues) == 4
    assert any("ES2015a.d01" in i and "object_en" in i and "vacío" in i for i in issues)
    assert any("ES2015a.d03-1" in i and "content_en" in i for i in issues)


def test_missing_and_extra_and_duplicate_ids_are_reported(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    path = _filled(tmp_path)
    rows = _read(path)
    extra = {**rows[0], "decision_id": "ES2015a.d99"}
    _write_translation(path, [rows[0], rows[0], extra])

    issues = validate_translation(SERIES, decisions_dir=tmp_path)

    assert any("ES2015a.d03-1" in i and "falta" in i for i in issues)
    assert any("ES2015a.d99" in i and "no es una decisión" in i for i in issues)
    assert any("ES2015a.d01" in i and "repetida" in i for i in issues)


def test_stale_spanish_copy_is_reported_as_desactualizada(tmp_path: Path) -> None:
    adjudicated = _adjudicated(tmp_path)
    _filled(tmp_path)
    text = adjudicated.read_text(encoding="utf-8").replace("fijar 25 euros", "fijar 30 euros")
    adjudicated.write_text(text, encoding="utf-8")

    (issue,) = validate_translation(SERIES, decisions_dir=tmp_path)

    assert "ES2015a.d01" in issue and "desactualizada" in issue


def test_unknown_translation_method_is_reported(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    path = _filled(tmp_path)
    rows = _read(path)
    rows[0]["translation_method"] = "magia"
    _write_translation(path, rows)

    (issue,) = validate_translation(SERIES, decisions_dir=tmp_path)

    assert "translation_method" in issue and "magia" in issue


def test_missing_columns_are_reported(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    translation_path(SERIES, tmp_path).write_text("decision_id,object_en\nx,y\n", encoding="utf-8")

    (issue,) = validate_translation(SERIES, decisions_dir=tmp_path)

    assert "columna" in issue and "content_en" in issue


def test_bom_in_the_translation_file_is_tolerated(tmp_path: Path) -> None:
    _adjudicated(tmp_path)
    path = _filled(tmp_path)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    assert validate_translation(SERIES, decisions_dir=tmp_path) == []


def test_load_reference_default_and_es_are_unchanged_and_en_substitutes(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    adjudicated = _adjudicated(tmp_path)
    _filled(tmp_path)

    default = load_reference(adjudicated, sentence_acts={}, transcripts_dir=transcripts)
    spanish = load_reference(
        adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="es"
    )
    english = load_reference(
        adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="en"
    )

    assert default == spanish
    assert [d.decision_object for d in default.decisions] == ["precio", "carcasa"]
    assert [d.decision_object for d in english.decisions] == ["en precio", "en carcasa"]
    assert [d.content for d in english.decisions] == ["en fijar 25 euros", "en usar goma"]
    assert [d.decision_id for d in english.decisions] == [d.decision_id for d in default.decisions]
    assert english.excluded == default.excluded


def test_load_reference_en_fails_clearly_when_missing_incomplete_or_stale(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    adjudicated = _adjudicated(tmp_path)

    with pytest.raises(TranslationError, match=r"ES2015\.reference-en\.csv"):
        load_reference(adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="en")

    write_translation_template(SERIES, decisions_dir=tmp_path)
    with pytest.raises(TranslationError, match="vacío"):
        load_reference(adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="en")

    path = translation_path(SERIES, tmp_path)
    rows = _read(path)
    for row in rows:
        row["object_en"] = row["content_en"] = "x"
    rows[0]["final_object"] = "otro"
    _write_translation(path, rows)
    with pytest.raises(TranslationError, match="desactualizada"):
        load_reference(adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="en")


def test_load_reference_rejects_an_unknown_language(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    adjudicated = _adjudicated(tmp_path)

    with pytest.raises(ValueError, match="language"):
        load_reference(adjudicated, sentence_acts={}, transcripts_dir=transcripts, language="fr")  # type: ignore[arg-type]


def test_translation_error_is_a_value_error_but_not_a_not_adjudicated_error() -> None:
    assert issubclass(TranslationError, ValueError)
    assert not issubclass(TranslationError, NotAdjudicatedError)


# --- CLI ------------------------------------------------------------------------------------


def test_cli_template_then_validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _adjudicated(tmp_path)
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", tmp_path)
    runner = CliRunner()

    made = runner.invoke(afg_cli.app, ["gold", "translation-template", "--series", SERIES])
    assert made.exit_code == 0, made.output
    assert (tmp_path / "ES2015.reference-en.csv").is_file()

    again = runner.invoke(afg_cli.app, ["gold", "translation-template", "--series", SERIES])
    assert again.exit_code == 1

    bad = runner.invoke(afg_cli.app, ["gold", "validate-translation", "--series", SERIES])
    assert bad.exit_code == 1
    assert "vacío" in bad.output

    _filled_after = _read(tmp_path / "ES2015.reference-en.csv")
    for row in _filled_after:
        row["object_en"] = row["content_en"] = "ok"
    _write_translation(tmp_path / "ES2015.reference-en.csv", _filled_after)
    good = runner.invoke(afg_cli.app, ["gold", "validate-translation", "--series", SERIES])
    assert good.exit_code == 0, good.output
    assert "Sin errores" in good.output

    forced = runner.invoke(
        afg_cli.app, ["gold", "translation-template", "--series", SERIES, "--force"]
    )
    assert forced.exit_code == 0
