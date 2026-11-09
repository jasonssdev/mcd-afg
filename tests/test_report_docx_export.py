"""Markdown to UC-branded Word: structure, styles, figures, tables and metadata.

Tests build small markdown fixtures under ``tmp_path`` and read the resulting DOCX back with
python-docx. The UC template is gitignored institutional material, so the one test that needs
it skips when it is absent (CI never has it).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

docx = pytest.importorskip("docx")

import afg.cli as afg_cli  # noqa: E402
from afg.reports.docx_export import export_docx  # noqa: E402
from afg.shared.paths import SKILLS_DIR  # noqa: E402

runner = CliRunner()

TEMPLATE = SKILLS_DIR / "deck-uc" / "assets" / "word-uc-sin-texto.docx"


def _png(width: int, height: int) -> bytes:
    """A valid, solid-color PNG of the requested pixel size."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    row = b"\x00" + b"\x40\x80\xc0" * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height))
        + chunk(b"IEND", b"")
    )


PNG_1X1 = _png(300, 180)

SOURCE = """# Compilar o recuperar: medición

Pre-informe de prueba.

| | |
|---|---|
| **Documento** | 02 — Documento |
| **Universidad** | Pontificia Universidad Católica de Chile |
| **Programa** | Magíster en Ciencia de Datos |
| **Curso** | MDS 3060 |
| **Autores** | Ana Pérez S., Luis Soto |
| **Tutor** | Tutor Uno |
| **Versión** | 1.3 |
| **Fecha** | 2026-11-09 |
| **Estado** | En revisión |

## Historial de versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1 | 2026-11-07 | Texto del historial |

> **Cómo versionar.** Texto que no debe salir.

---

## 1. Introducción

### 1.1 Tema

Texto con **negrita**, *cursiva*, `código` y un [enlace](https://example.org/x) más.

- Primer punto
- Segundo punto

**Tabla 1.** Partición de ejemplo.

| Partición | Series |
|---|---|
| Desarrollo | 3 |
| Evaluación | 11 |

![Texto alternativo de la figura](figs/f.png)

**Figura 1.** Pie de la figura.

Fórmula:

*overlap*(A, B) = |A ∩ B| / mín(|A|, |B|),

donde A y B son conjuntos.

## 8. Referencias

Autor, A. (2020). *Título*. https://doi.org/10.1/abc

## Anexo A. Extra

Contenido del anexo.
"""


@pytest.fixture
def built(tmp_path: Path):  # type: ignore[no-untyped-def]
    src = tmp_path / "informe.md"
    src.write_text(SOURCE, encoding="utf-8")
    figs = tmp_path / "figs"
    figs.mkdir()
    (figs / "f.png").write_bytes(PNG_1X1)
    out = tmp_path / "out" / "informe.docx"
    export_docx(src, out, template=None, short_title="Corto · Pre-informe")
    return docx.Document(str(out)), out


def _para(document, text: str):  # type: ignore[no-untyped-def]
    for p in document.paragraphs:
        if p.text.startswith(text):
            return p
    raise AssertionError(f"no paragraph starting with {text!r}")


def test_headings_map_to_word_heading_styles(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    assert _para(document, "1. Introducción").style.name == "Heading 1"
    assert _para(document, "1.1 Tema").style.name == "Heading 2"
    assert _para(document, "Compilar o recuperar").style.name == "Title"
    assert _para(document, "Pre-informe de prueba.").style.name == "Subtitle"


def test_tables_become_word_tables_with_a_repeating_header_row(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    data_tables = [t for t in document.tables if t.rows[0].cells[0].text == "Partición"]
    assert len(data_tables) == 1
    table = data_tables[0]
    assert [c.text for c in table.rows[1].cells] == ["Desarrollo", "3"]
    header_flags = table.rows[0]._tr.xpath("./w:trPr/w:tblHeader")
    assert header_flags, "first row must repeat as the table header"
    caption = _para(document, "Tabla 1.")
    assert caption.style.name == "Caption"
    body = document.element.body
    order = [child for child in body.iterchildren()]
    assert order.index(caption._p) + 1 == order.index(table._tbl)


def _keeps(table) -> list[bool]:  # type: ignore[no-untyped-def]
    return [bool(row.cells[0].paragraphs[0].paragraph_format.keep_with_next) for row in table.rows]


def test_short_tables_stay_together_and_long_tables_may_break(tmp_path: Path) -> None:
    body_rows = "\n".join(f"| fila {i} | {i} |" for i in range(20))
    long_table = f"**Tabla 9.** Larga.\n\n| Clave | Valor |\n|---|---|\n{body_rows}\n\n"
    src = tmp_path / "informe.md"
    src.write_text(
        SOURCE.replace("## Anexo A. Extra", long_table + "## Anexo A. Extra"), encoding="utf-8"
    )
    figs = tmp_path / "figs"
    figs.mkdir()
    (figs / "f.png").write_bytes(PNG_1X1)
    out = tmp_path / "informe.docx"
    export_docx(src, out, template=None)
    document = docx.Document(str(out))
    short = next(t for t in document.tables if t.rows[0].cells[0].text == "Partición")
    long = next(t for t in document.tables if t.rows[0].cells[0].text == "Clave")
    assert all(_keeps(short)[:-1]), "a short table is kept on one page"
    keeps = _keeps(long)
    assert keeps[:3] == [True, True, True], "the header never ends a page alone"
    assert not any(keeps[3:]), "a long table may continue on the next page"


def test_figure_is_embedded_with_its_caption_below(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    assert len(document.inline_shapes) == 1
    shape = document.inline_shapes[0]
    assert shape.width.cm == pytest.approx(15.5, abs=0.6)
    picture_para = shape._inline.getparent().getparent().getparent()
    caption = _para(document, "Figura 1.")
    assert caption.style.name == "Caption"
    assert caption._p is picture_para.getnext()
    assert "Texto alternativo de la figura" in shape._inline.docPr.get("descr")


def test_inline_bold_italic_code_and_links(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    p = _para(document, "Texto con")
    runs = {r.text: r for r in p.runs}
    assert runs["negrita"].bold
    assert runs["cursiva"].italic
    assert runs["código"].style.name == "Code"
    links = p._p.xpath("./w:hyperlink")
    assert len(links) == 1
    rid = links[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    assert document.part.rels[rid].target_ref == "https://example.org/x"
    assert "enlace" in "".join(links[0].itertext())


def test_bare_urls_in_references_are_clickable(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    ref = _para(document, "Autor, A.")
    assert ref.style.name == "Reference"
    targets = [document.part.rels[r].target_ref for r in ref._p.xpath("./w:hyperlink/@r:id")]
    assert targets == ["https://doi.org/10.1/abc"]
    assert ref.text.endswith("https://doi.org/10.1/abc")


def test_lists_use_list_styles(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    assert _para(document, "Primer punto").style.name == "List Bullet"


def test_formula_line_has_its_own_style(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    assert _para(document, "overlap(A, B) =").style.name == "Formula"


def test_history_blockquote_rules_and_unwanted_rows_are_excluded(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    text = "\n".join(p.text for p in document.paragraphs)
    cells = "\n".join(c.text for t in document.tables for r in t.rows for c in r.cells)
    for forbidden in ("Historial de versiones", "Cómo versionar", "Texto del historial"):
        assert forbidden not in text + cells
    assert "Documento" not in text + cells
    assert "En revisión" not in text + cells
    assert not document.element.body.xpath(".//w:pBdr/w:top[@w:val='single' and @w:sz='6']")


def test_cover_carries_title_authors_tutor_date_and_version(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    cover = "\n".join(p.text for p in document.paragraphs[:20]) + "\n".join(
        c.text for c in document.tables[0].rows[0].cells
    )
    cover += "\n".join(c.text for r in document.tables[0].rows for c in r.cells)
    for expected in (
        "Ana Pérez S.",
        "Luis Soto",
        "Tutor Uno",
        "9 de noviembre de 2026",
        "Versión 1.3",
    ):
        assert expected in cover


def test_references_and_annex_start_on_a_new_page(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    assert _para(document, "8. Referencias").paragraph_format.page_break_before
    assert _para(document, "Anexo A.").paragraph_format.page_break_before
    assert not _para(document, "1. Introducción").paragraph_format.page_break_before


def test_cover_and_body_are_separate_sections_with_running_header(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    cover, body = document.sections[0], document.sections[-1]
    assert cover is not body
    header_text = "".join(p.text for p in body.header.paragraphs)
    assert "Corto · Pre-informe" in header_text
    assert "Corto" not in "".join(p.text for p in cover.header.paragraphs)
    assert body.footer.part.element.xpath(".//w:instrText[contains(., 'PAGE')]")
    assert not cover.footer.part.element.xpath(".//w:instrText[contains(., 'PAGE')]")


def test_core_properties_carry_the_team_and_never_the_library_default(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    props = document.core_properties
    assert props.title == "Compilar o recuperar: medición"
    assert props.author == "Ana Pérez S., Luis Soto"
    assert props.last_modified_by == "Ana Pérez S., Luis Soto"
    values = [
        str(getattr(props, name))
        for name in (
            "author",
            "title",
            "subject",
            "keywords",
            "comments",
            "last_modified_by",
            "category",
        )
    ]
    assert not any("python-docx" in v.lower() for v in values)


def test_styles_set_spanish_chile_language(built) -> None:  # type: ignore[no-untyped-def]
    document, _ = built
    langs = document.styles.element.xpath(".//w:docDefaults//w:lang/@w:val")
    assert langs == ["es-CL"]


def test_missing_image_is_reported(tmp_path: Path) -> None:
    src = tmp_path / "x.md"
    src.write_text(SOURCE, encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=r"f\.png"):
        export_docx(src, tmp_path / "o.docx", template=None)


@pytest.mark.skipif(not TEMPLATE.exists(), reason="deck-uc assets not installed")
def test_uc_template_keeps_logo_on_the_cover_only(tmp_path: Path) -> None:
    src = tmp_path / "informe.md"
    src.write_text(SOURCE, encoding="utf-8")
    (tmp_path / "figs").mkdir()
    (tmp_path / "figs" / "f.png").write_bytes(PNG_1X1)
    out = export_docx(src, tmp_path / "o.docx", template=TEMPLATE, short_title="Corto")
    document = docx.Document(str(out))
    cover, body = document.sections[0], document.sections[-1]
    assert cover.header.part.element.xpath(".//w:drawing")
    assert not body.header.part.element.xpath(".//w:drawing")
    assert document.core_properties.author == "Ana Pérez S., Luis Soto"
    assert "Karen" not in document.core_properties.last_modified_by


def test_cli_writes_the_docx_to_the_requested_path(tmp_path: Path) -> None:
    src = tmp_path / "informe.md"
    src.write_text(SOURCE, encoding="utf-8")
    (tmp_path / "figs").mkdir()
    (tmp_path / "figs" / "f.png").write_bytes(PNG_1X1)
    out = tmp_path / "salida.docx"
    result = runner.invoke(
        afg_cli.app, ["informe", "docx", str(src), "--out", str(out), "--no-template"]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_fails_clearly_when_the_template_is_missing(tmp_path: Path) -> None:
    src = tmp_path / "informe.md"
    src.write_text(SOURCE, encoding="utf-8")
    result = runner.invoke(
        afg_cli.app,
        ["informe", "docx", str(src), "--template", str(tmp_path / "no.docx")],
    )
    assert result.exit_code == 1
    assert "make skill-assets" in result.output
