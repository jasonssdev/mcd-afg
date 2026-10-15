"""Tests for the annotator-facing CSV reader (``afg.shared.csvio.open_csv_reader``)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from afg.shared.csvio import CsvFormatError, open_csv_reader


def _rows(path: Path) -> list[dict[str, str]]:
    with open_csv_reader(path) as handle:
        return list(csv.DictReader(handle))


def test_reads_plain_utf8(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("id,texto\nq1,¿Qué se decidió?\n", encoding="utf-8")
    assert _rows(path) == [{"id": "q1", "texto": "¿Qué se decidió?"}]


def test_tolerates_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_bytes(b"\xef\xbb\xbfid,texto\nq1,hola\n")
    assert _rows(path) == [{"id": "q1", "texto": "hola"}]


def test_keeps_embedded_newlines_in_quoted_cells(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_bytes(b'id,texto\nq1,"una\r\ndos"\n')
    assert _rows(path)[0]["texto"] == "una\r\ndos"


def test_latin1_file_raises_typed_spanish_error_naming_the_file(tmp_path: Path) -> None:
    path = tmp_path / "ES2015.decisions.gm.csv"
    path.write_bytes("id,texto\nq1,decisión\n".encode("latin-1"))
    with pytest.raises(CsvFormatError) as caught:
        _rows(path)
    message = str(caught.value)
    assert "ES2015.decisions.gm.csv" in message
    assert "CSV UTF-8 (delimitado por comas)" in message
    assert "Juego de caracteres: Unicode (UTF-8)" in message
    assert "codec" not in message


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
def test_utf16_file_raises_typed_error(tmp_path: Path, encoding: str) -> None:
    path = tmp_path / "banco.csv"
    data = "id,texto\nq1,hola\n".encode(encoding)
    if encoding != "utf-16":
        data = (b"\xff\xfe" if encoding.endswith("le") else b"\xfe\xff") + data
    path.write_bytes(data)
    with pytest.raises(CsvFormatError) as caught:
        _rows(path)
    assert "banco.csv" in str(caught.value)
    assert "UTF-16" in str(caught.value)


def test_missing_file_still_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _rows(tmp_path / "nope.csv")


def test_error_is_a_value_error(tmp_path: Path) -> None:
    assert issubclass(CsvFormatError, ValueError)
