"""Metadata parsing for the informe exporter: pure functions, no Word library needed."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.reports.metadata import (
    ReportMetadata,
    default_output_path,
    format_date_es,
    parse_metadata,
)

HEADER = """# Título largo: con subtítulo

Subtítulo del documento.

| | |
|---|---|
| **Documento** | 02 — Pre-informe |
| **Universidad** | Pontificia Universidad Católica de Chile |
| **Programa** | Magíster en Ciencia de Datos |
| **Curso** | MDS 3060 |
| **Autores** | Ana Pérez S., Luis Soto, Eva Rey |
| **Tutor** | Tutor Uno |
| **Versión** | 1.3 |
| **Fecha** | 2026-11-09 |
| **Estado** | En revisión |

## 1. Introducción
"""


def test_parse_metadata_reads_title_subtitle_and_header_rows() -> None:
    meta = parse_metadata(HEADER)
    assert meta.title == "Título largo: con subtítulo"
    assert meta.subtitle == "Subtítulo del documento."
    assert meta.version == "1.3"
    assert meta.date == "2026-11-09"
    assert meta.authors == ("Ana Pérez S.", "Luis Soto", "Eva Rey")
    assert meta.tutor == "Tutor Uno"
    assert meta.program == "Magíster en Ciencia de Datos"
    assert meta.course == "MDS 3060"
    assert meta.university == "Pontificia Universidad Católica de Chile"


def test_parse_metadata_requires_a_version_row() -> None:
    with pytest.raises(ValueError, match="Versión"):
        parse_metadata(HEADER.replace("| **Versión** | 1.3 |\n", ""))


def test_parse_metadata_requires_an_h1() -> None:
    with pytest.raises(ValueError, match="título"):
        parse_metadata("| | |\n|---|---|\n| **Versión** | 1.0 |\n")


def test_format_date_es_spells_the_month_in_spanish() -> None:
    assert format_date_es("2026-11-09") == "9 de noviembre de 2026"
    assert format_date_es("2026-03-01") == "1 de marzo de 2026"


def test_format_date_es_rejects_non_iso_dates() -> None:
    with pytest.raises(ValueError, match="fecha"):
        format_date_es("09/11/2026")


def test_default_output_path_uses_stem_and_version(tmp_path: Path) -> None:
    meta = ReportMetadata(title="T", version="1.3", date="2026-11-09")
    out = default_output_path(Path("docs/02-jss-pre-informe.md"), meta, tmp_path / "exportados")
    assert out == tmp_path / "exportados" / "02-jss-pre-informe-v1.3.docx"
