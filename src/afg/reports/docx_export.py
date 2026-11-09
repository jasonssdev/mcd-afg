"""Convert an informe written in markdown into a UC-branded Word document.

The markdown stays the living source; the Word file is a derived, gitignored artifact. The
converter walks the ``markdown-it-py`` token stream and builds semantic Word styles (Title,
Heading 1/2, Caption, List Bullet, Reference, ...) on top of the institutional UC template, so the
letterhead logo and page geometry come from the template and nothing institutional is redrawn.

Layout rules (deck-uc skill, Word mode): the cover page keeps the letterhead logo in its own
section; the following pages carry a light running header and a page number instead of repeating
the letterhead.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.image.image import Image as DocxImage
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.parts.numbering import NumberingPart
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from markdown_it import MarkdownIt
from markdown_it.token import Token

from afg.reports.metadata import ReportMetadata, format_date_es, parse_metadata

# Palette. Azul A (Pantone 2727 family) and Azul B come from the deck-uc visual norm
# (references/norma-visual-uc.md); the brand manual itself fixes the shield colors by Pantone.
UC_BLUE = "0176DE"
INK = "1A1E2B"
MUTED = "5B6270"
HAIRLINE = "C9CED6"
TINT = "EAF3FC"

BODY_FONT = "Arial"
MONO_FONT = "Courier New"
KEEP_TOGETHER_MAX_BODY_ROWS = 12
LANGUAGE = "es-CL"

TEXT_MARGIN = Cm(2.4)
BODY_TOP_MARGIN = Cm(2.6)
BODY_BOTTOM_MARGIN = Cm(2.3)
TEXT_WIDTH_CM = 21.59 - 2 * 2.4
FIGURE_WIDTH_CM = 15.0
FIGURE_MAX_HEIGHT_CM = 10.5

_HISTORY_HEADING = "Historial de versiones"
_FIGURE_CAPTION = re.compile(r"^Figura\s+[A-Z]?\d+\.")
_TABLE_CAPTION = re.compile(r"^Tabla\s+[A-Z]?\d+\.")
_REFERENCES_HEADING = re.compile(r"^\d+\.\s+Referencias")
_URL = re.compile(r"https?://[^\s<>]+")
_TRAILING_PUNCTUATION = ".,;:)"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NUMBERING_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"


# --- styles -------------------------------------------------------------------------------


def _rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def _style(styles: Any, name: str, base: str | None = "Normal", *, character: bool = False) -> Any:
    """Return the named style with its formatting cleared, creating it when it is missing."""
    try:
        style = styles[name]
    except KeyError:
        style = styles.add_style(
            name, WD_STYLE_TYPE.CHARACTER if character else WD_STYLE_TYPE.PARAGRAPH
        )
    for tag in ("w:pPr", "w:rPr"):
        for element in style.element.findall(qn(tag)):
            style.element.remove(element)
    style.base_style = styles[base] if base else None
    style.quick_style = True
    return style


def _font(
    style: Any,
    name: str | None,
    size: float,
    *,
    color: str = INK,
    bold: bool = False,
    italic: bool = False,
) -> None:
    font = style.font
    if name:
        font.name = name
        rfonts = style.element.get_or_add_rPr().get_or_add_rFonts()
        for attribute in ("w:cs", "w:eastAsia"):
            rfonts.set(qn(attribute), name)
    font.size = Pt(size)
    font.bold = bold
    font.italic = italic
    font.color.rgb = _rgb(color)


def _spacing(
    style: Any,
    *,
    before: float = 0,
    after: float = 0,
    line: float = 1.15,
    keep_next: bool = False,
    keep_lines: bool = False,
) -> None:
    fmt = style.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    fmt.keep_with_next = keep_next
    fmt.keep_together = keep_lines
    fmt.widow_control = True


def _set_language(style_or_defaults: Any) -> None:
    rpr = style_or_defaults
    for lang in rpr.findall(qn("w:lang")):
        rpr.remove(lang)
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), LANGUAGE)
    lang.set(qn("w:eastAsia"), "es-ES")
    rpr.append(lang)


def _border(paragraph_properties: Any, side: str, color: str, size: int, space: int = 1) -> None:
    borders = paragraph_properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        paragraph_properties.append(borders)
    edge = OxmlElement(f"w:{side}")
    edge.set(qn("w:val"), "single")
    edge.set(qn("w:sz"), str(size))
    edge.set(qn("w:space"), str(space))
    edge.set(qn("w:color"), color)
    borders.append(edge)


def _outline_level(style: Any, level: int) -> None:
    ppr = style.element.get_or_add_pPr()
    outline = OxmlElement("w:outlineLvl")
    outline.set(qn("w:val"), str(level))
    ppr.append(outline)


def _table_style_xml() -> str:
    border = 'w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"'
    return (
        f'<w:style {nsdecls("w")} w:type="table" w:customStyle="1" w:styleId="UCTable">'
        '<w:name w:val="UC Table"/><w:basedOn w:val="TableNormal"/><w:uiPriority w:val="59"/>'
        "<w:qFormat/><w:tblPr><w:tblBorders>"
        f"<w:top {border.format(sz=8, color=INK)}/>"
        f"<w:bottom {border.format(sz=8, color=INK)}/>"
        f"<w:insideH {border.format(sz=4, color=HAIRLINE)}/>"
        '</w:tblBorders><w:tblCellMar><w:top w:w="30" w:type="dxa"/>'
        '<w:left w:w="85" w:type="dxa"/><w:bottom w:w="30" w:type="dxa"/>'
        '<w:right w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    )


def _define_styles(document: Any) -> None:
    styles = document.styles
    defaults = styles.element.find(qn("w:docDefaults"))
    if defaults is not None:
        rpr_default = defaults.find(qn("w:rPrDefault"))
        if rpr_default is not None and rpr_default.find(qn("w:rPr")) is not None:
            _set_language(rpr_default.find(qn("w:rPr")))

    normal = _style(styles, "Normal", base=None)
    _font(normal, BODY_FONT, 11, color=INK)
    _spacing(normal, after=6, line=1.15)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _set_language(normal.element.get_or_add_rPr())

    title = _style(styles, "Title")
    _font(title, BODY_FONT, 26, bold=True)
    _spacing(title, before=0, after=10, line=1.08, keep_next=True)
    subtitle = _style(styles, "Subtitle")
    _font(subtitle, BODY_FONT, 13, color=MUTED)
    _spacing(subtitle, after=14, line=1.25, keep_next=True)

    sizes = {1: (16, 20, 6, UC_BLUE), 2: (12.5, 12, 3, INK), 3: (11.5, 10, 2, MUTED)}
    for level, (size, before, after, color) in sizes.items():
        heading = _style(styles, f"Heading {level}")
        _font(heading, BODY_FONT, size, color=color, bold=True)
        _spacing(heading, before=before, after=after, line=1.1, keep_next=True, keep_lines=True)
        _outline_level(heading, level - 1)
    _border(styles["Heading 1"].element.get_or_add_pPr(), "bottom", HAIRLINE, 4, space=3)

    caption = _style(styles, "Caption")
    _font(caption, BODY_FONT, 9.5, color=MUTED)
    _spacing(caption, before=2, after=10, line=1.15, keep_lines=True)
    figure = _style(styles, "Figure")
    _spacing(figure, before=8, after=2, line=1.0, keep_next=True)
    figure.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    formula = _style(styles, "Formula")
    _font(formula, BODY_FONT, 11.5)
    _spacing(formula, before=4, after=4, line=1.2, keep_next=True)
    formula.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    reference = _style(styles, "Reference")
    _font(reference, BODY_FONT, 10)
    _spacing(reference, after=4, line=1.15, keep_lines=True)
    reference.paragraph_format.left_indent = Cm(1.0)
    reference.paragraph_format.first_line_indent = Cm(-1.0)

    for name in ("List Bullet", "List Number"):
        item = _style(styles, name)
        _font(item, BODY_FONT, 11)
        _spacing(item, after=3, line=1.15)
        item.paragraph_format.left_indent = Cm(0.9)
        item.paragraph_format.first_line_indent = Cm(-0.5)

    quote = _style(styles, "Quote")
    _font(quote, BODY_FONT, 11, color=MUTED, italic=True)
    _spacing(quote, after=6)
    quote.paragraph_format.left_indent = Cm(0.8)

    cell = _style(styles, "Table Text")
    _font(cell, BODY_FONT, 9)
    _spacing(cell, line=1.1)
    head = _style(styles, "Table Heading", base="Table Text")
    _font(head, BODY_FONT, 9, bold=True)
    _spacing(head, line=1.1, keep_next=True)

    code = _style(styles, "Code", base=None, character=True)
    _font(code, MONO_FONT, 9.5, color=INK)
    link = _style(styles, "Hyperlink", base=None, character=True)
    link.font.color.rgb = _rgb(UC_BLUE)
    link.font.underline = True

    cover_label = _style(styles, "Cover Label")
    _font(cover_label, BODY_FONT, 8.5, color=UC_BLUE, bold=True)
    _spacing(cover_label, before=3, after=0, line=1.1)
    cover_value = _style(styles, "Cover Value")
    _font(cover_value, BODY_FONT, 11.5)
    _spacing(cover_value, after=0, line=1.2)
    cover_version = _style(styles, "Cover Version")
    _font(cover_version, BODY_FONT, 12, color=UC_BLUE, bold=True)
    _spacing(cover_version, before=26, after=0)

    for name in ("Header", "Footer"):
        part = _style(styles, name)
        _font(part, BODY_FONT, 8.5, color=MUTED)
        _spacing(part, line=1.0)

    if "UC Table" not in [s.name for s in styles]:
        styles.element.append(parse_xml(_table_style_xml()))


# --- numbering ----------------------------------------------------------------------------


class _Numbering:
    """Bullet and decimal list definitions, added next to whatever the template already has."""

    BULLET_ABSTRACT = 90
    DECIMAL_ABSTRACT = 91

    def __init__(self, document: Any) -> None:
        part = document.part
        try:
            numbering_part = part.part_related_by(RT.NUMBERING)
        except KeyError:
            blob = f"<w:numbering {nsdecls('w')}/>".encode()
            numbering_part = NumberingPart.load(
                PackURI("/word/numbering.xml"), NUMBERING_CT, blob, part.package
            )
            part.relate_to(numbering_part, RT.NUMBERING)
        self.root = numbering_part.element
        self._next_num = 900
        self._add_abstract(self.BULLET_ABSTRACT, "bullet", "•", 567, 283)
        self._add_abstract(self.DECIMAL_ABSTRACT, "decimal", "%1.", 567, 340)
        self.bullet_num = self.new_num(self.BULLET_ABSTRACT)

    def _add_abstract(self, abstract_id: int, fmt: str, text: str, left: int, hanging: int) -> None:
        font = (
            '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/></w:rPr>' if fmt == "bullet" else ""
        )
        xml = (
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">'
            '<w:multiLevelType w:val="singleLevel"/>'
            f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>'
            f'<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="{left}" w:hanging="{hanging}"/></w:pPr>{font}</w:lvl>'
            "</w:abstractNum>"
        )
        element = parse_xml(xml)
        first_num = self.root.find(qn("w:num"))
        if first_num is not None:
            first_num.addprevious(element)
        else:
            self.root.append(element)

    def new_num(self, abstract_id: int) -> int:
        num_id = self._next_num
        self._next_num += 1
        xml = (
            f'<w:num {nsdecls("w")} w:numId="{num_id}"><w:abstractNumId w:val="{abstract_id}"/>'
            '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
        )
        self.root.append(parse_xml(xml))
        return num_id


def _apply_num(paragraph: Paragraph, num_id: int) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    num_pr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_pr.append(ilvl)
    num_pr.append(num)
    ppr.append(num_pr)


# --- inline content -----------------------------------------------------------------------


def _hyperlink(paragraph: Paragraph, url: str) -> Any:
    rel_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    element = OxmlElement("w:hyperlink")
    element.set(qn("r:id"), rel_id)
    element.set(qn("w:history"), "1")
    paragraph._p.append(element)
    return element


def _styled_run(paragraph: Paragraph, text: str, *, bold: bool, italic: bool) -> Any:
    run = paragraph.add_run(text)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    return run


def _add_linked_run(paragraph: Paragraph, text: str, url: str, *, bold: bool, italic: bool) -> None:
    link = _hyperlink(paragraph, url)
    run = _styled_run(paragraph, text, bold=bold, italic=italic)
    run.style = "Hyperlink"
    link.append(run._r)


def _add_text(
    paragraph: Paragraph, text: str, *, bold: bool, italic: bool, href: str | None
) -> None:
    if href:
        _add_linked_run(paragraph, text, href, bold=bold, italic=italic)
        return
    position = 0
    for match in _URL.finditer(text):
        url = match.group(0)
        trailing = ""
        while url and url[-1] in _TRAILING_PUNCTUATION:
            trailing = url[-1] + trailing
            url = url[:-1]
        if match.start() > position:
            _styled_run(paragraph, text[position : match.start()], bold=bold, italic=italic)
        _add_linked_run(paragraph, url, url, bold=bold, italic=italic)
        position = match.end() - len(trailing)
    if position < len(text):
        _styled_run(paragraph, text[position:], bold=bold, italic=italic)


def _add_inline(paragraph: Paragraph, inline: Token, *, bold: bool = False) -> None:
    strong = 1 if bold else 0
    emphasis = 0
    href: str | None = None
    for child in inline.children or []:
        kind = child.type
        if kind == "strong_open":
            strong += 1
        elif kind == "strong_close":
            strong -= 1
        elif kind == "em_open":
            emphasis += 1
        elif kind == "em_close":
            emphasis -= 1
        elif kind == "link_open":
            href = str(child.attrGet("href"))
        elif kind == "link_close":
            href = None
        elif kind == "softbreak":
            _styled_run(paragraph, " ", bold=strong > 0, italic=emphasis > 0)
        elif kind == "hardbreak":
            paragraph.add_run().add_break(WD_BREAK.LINE)
        elif kind == "code_inline":
            run = paragraph.add_run(child.content)
            run.style = "Code"
        elif kind in {"text", "html_inline"}:
            _add_text(paragraph, child.content, bold=strong > 0, italic=emphasis > 0, href=href)


def _plain_text(inline: Token) -> str:
    return "".join(
        child.content for child in inline.children or [] if child.type in {"text", "code_inline"}
    )


# --- fields, header, footer ---------------------------------------------------------------


def _add_field(paragraph: Paragraph, instruction: str) -> None:
    def part(kind: str | None, text: str | None = None) -> None:
        run = paragraph.add_run()
        if kind:
            fld = OxmlElement("w:fldChar")
            fld.set(qn("w:fldCharType"), kind)
            run._r.append(fld)
        if text is not None:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)

    part("begin")
    part(None, f" {instruction} ")
    part("separate")
    paragraph.add_run("1")
    part("end")


def _style_header_footer(document: Any, section: Any, running_title: str) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    header = section.header
    paragraph = header.paragraphs[0]
    for run in list(paragraph.runs):
        run._r.getparent().remove(run._r)
    paragraph.style = document.styles["Header"]
    paragraph.add_run(running_title)
    _border(paragraph._p.get_or_add_pPr(), "bottom", HAIRLINE, 4, space=4)
    footer_paragraph = section.footer.paragraphs[0]
    footer_paragraph.style = document.styles["Footer"]
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _add_field(footer_paragraph, "PAGE")
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.1)


# --- cover --------------------------------------------------------------------------------


def _remove_body_content(document: Any) -> None:
    body = document.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def _build_cover(document: Any, meta: ReportMetadata) -> None:
    document.add_paragraph(meta.title, style="Title").paragraph_format.space_before = Cm(0.9)
    if meta.subtitle:
        document.add_paragraph(meta.subtitle, style="Subtitle")
    rule = document.add_paragraph()
    rule.paragraph_format.space_after = Cm(0.9)
    rule.paragraph_format.right_indent = Cm(10.5)
    _border(rule._p.get_or_add_pPr(), "bottom", UC_BLUE, 18, space=1)

    rows: list[tuple[str, list[str]]] = []
    if meta.authors:
        rows.append(("Autores", list(meta.authors)))
    for label, value in (
        ("Tutor", meta.tutor),
        ("Programa", meta.program),
        ("Curso", meta.course),
        ("Universidad", meta.university),
        ("Fecha", format_date_es(meta.date) if meta.date else ""),
    ):
        if value:
            rows.append((label, [value]))
    table = document.add_table(rows=len(rows), cols=2)
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    widths = (Cm(3.6), Cm(13.2))
    for column, width in zip(table.columns, widths, strict=True):
        column.width = width
    for row, (label, values) in zip(table.rows, rows, strict=True):
        for cell, width in zip(row.cells, widths, strict=True):
            cell.width = width
        row.cells[0].paragraphs[0].style = document.styles["Cover Label"]
        row.cells[0].paragraphs[0].add_run(label)
        value_paragraph = row.cells[1].paragraphs[0]
        value_paragraph.style = document.styles["Cover Value"]
        for position, value in enumerate(values):
            if position:
                value_paragraph.add_run().add_break(WD_BREAK.LINE)
            value_paragraph.add_run(value)
        _row_properties(row, cant_split=True)
        row._tr.get_or_add_trPr()
        for cell in row.cells:
            _cell_margins(cell, top=70, bottom=70)
    document.add_paragraph(f"Versión {meta.version}", style="Cover Version")


def _cell_margins(cell: Any, *, top: int, bottom: int) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for side, value in (("top", top), ("bottom", bottom)):
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    properties.append(margins)


def _row_properties(row: Any, *, cant_split: bool = False, header: bool = False) -> None:
    properties = row._tr.get_or_add_trPr()
    if cant_split:
        properties.append(OxmlElement("w:cantSplit"))
    if header:
        properties.append(OxmlElement("w:tblHeader"))


# --- body blocks --------------------------------------------------------------------------


class _Builder:
    def __init__(self, document: Any, source: Path, tokens: list[Token]) -> None:
        self.document = document
        self.source = source
        self.tokens = tokens
        self.numbering = _Numbering(document)
        self.in_references = False
        self.annex_seen = False
        self.after_table = False
        document.styles["List Bullet"].element.get_or_add_pPr().append(
            self._style_num(self.numbering.bullet_num)
        )

    @staticmethod
    def _style_num(num_id: int) -> Any:
        num_pr = OxmlElement("w:numPr")
        num = OxmlElement("w:numId")
        num.set(qn("w:val"), str(num_id))
        num_pr.append(num)
        return num_pr

    # -- dispatch --
    def build(self) -> None:
        tokens = self.tokens
        index = 0
        skipping_history = False
        while index < len(tokens):
            token = tokens[index]
            if token.type == "heading_open":
                text = tokens[index + 1].content.strip()
                level = int(token.tag[1])
                skipping_history = level == 2 and text == _HISTORY_HEADING
                if not skipping_history:
                    self._heading(level, tokens[index + 1])
                index += 3
                continue
            if skipping_history:
                index = self._skip_block(index)
                continue
            if token.type == "hr":
                index += 1
            elif token.type == "blockquote_open":
                index = self._blockquote(index)
            elif token.type == "paragraph_open":
                index = self._paragraph(index)
            elif token.type in {"bullet_list_open", "ordered_list_open"}:
                index = self._list(index)
            elif token.type == "table_open":
                index = self._table(index)
            else:
                index += 1

    def _skip_block(self, index: int) -> int:
        token = self.tokens[index]
        if not token.type.endswith("_open"):
            return index + 1
        close = token.type.replace("_open", "_close")
        depth = 0
        while index < len(self.tokens):
            if self.tokens[index].type == token.type:
                depth += 1
            elif self.tokens[index].type == close:
                depth -= 1
                if depth == 0:
                    return index + 1
            index += 1
        return index

    def _heading(self, level: int, inline: Token) -> None:
        if level == 1:
            return
        text = inline.content.strip()
        paragraph = self.document.add_paragraph(style=f"Heading {min(level - 1, 3)}")
        _add_inline(paragraph, inline)
        starts_references = bool(_REFERENCES_HEADING.match(text))
        starts_annex = text.startswith("Anexo") and not self.annex_seen
        if level == 2 and (starts_references or starts_annex):
            paragraph.paragraph_format.page_break_before = True
        if level == 2:
            self.in_references = starts_references
            self.annex_seen = self.annex_seen or text.startswith("Anexo")
        self.after_table = False

    def _blockquote(self, index: int) -> int:
        end = self._skip_block(index)
        inner = [t for t in self.tokens[index:end] if t.type == "inline"]
        if not (inner and inner[0].content.startswith("**Cómo versionar")):
            for inline in inner:
                paragraph = self.document.add_paragraph(style="Quote")
                _add_inline(paragraph, inline)
        return end

    def _paragraph(self, index: int) -> int:
        inline = self.tokens[index + 1]
        children = inline.children or []
        text = inline.content.strip()
        if len(children) == 1 and children[0].type == "image":
            self._figure(children[0])
            return index + 3
        paragraph = self.document.add_paragraph()
        style = "Normal"
        keep_next = False
        if _FIGURE_CAPTION.match(_plain_text(inline)):
            style = "Caption"
        elif _TABLE_CAPTION.match(_plain_text(inline)):
            style, keep_next = "Caption", True
        elif self._is_formula(index, text):
            style = "Formula"
        elif self.in_references:
            style = "Reference"
        paragraph.style = self.document.styles[style]
        if keep_next:
            paragraph.paragraph_format.keep_with_next = True
        if self.after_table and style == "Normal":
            paragraph.paragraph_format.space_before = Pt(8)
        self.after_table = False
        _add_inline(paragraph, inline)
        return index + 3

    def _is_formula(self, index: int, text: str) -> bool:
        following = self.tokens[index + 4] if index + 4 < len(self.tokens) else None
        return (
            " = " in text
            and len(text) < 120
            and following is not None
            and following.type == "inline"
            and following.content.startswith("donde ")
        )

    def _figure(self, image: Token) -> None:
        source = str(image.attrGet("src"))
        path = (self.source.parent / source).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"No se encontró la figura {source} (buscada en {path}).")
        raw = DocxImage.from_file(str(path))
        width_cm = FIGURE_WIDTH_CM
        if width_cm * raw.px_height / raw.px_width > FIGURE_MAX_HEIGHT_CM:
            width_cm = FIGURE_MAX_HEIGHT_CM * raw.px_width / raw.px_height
        paragraph = self.document.add_paragraph(style="Figure")
        shape = paragraph.add_run().add_picture(str(path), width=Cm(width_cm))
        alt = image.content or Path(source).stem
        shape._inline.docPr.set("descr", alt)
        shape._inline.docPr.set("name", Path(source).name)
        self.after_table = False

    def _list(self, index: int) -> int:
        end = self._skip_block(index)
        ordered = self.tokens[index].type == "ordered_list_open"
        style = "List Number" if ordered else "List Bullet"
        num_id = self.numbering.new_num(_Numbering.DECIMAL_ABSTRACT) if ordered else None
        for position in range(index, end):
            token = self.tokens[position]
            if token.type == "inline":
                paragraph = self.document.add_paragraph(style=style)
                if num_id is not None:
                    _apply_num(paragraph, num_id)
                _add_inline(paragraph, token)
        self.after_table = False
        return end

    def _table(self, index: int) -> int:
        end = self._skip_block(index)
        rows: list[list[Token]] = []
        header_rows = 0
        current: list[Token] | None = None
        for token in self.tokens[index:end]:
            if token.type == "tr_open":
                current = []
                rows.append(current)
            elif token.type == "th_open":
                header_rows = max(header_rows, len(rows))
            elif token.type == "inline" and current is not None:
                current.append(token)
        _render_table(self.document, rows, header_rows)
        self.after_table = True
        return end


def _column_widths(rows: list[list[Token]]) -> list[float]:
    columns = len(rows[0])
    weights = []
    for column in range(columns):
        lengths = [len(row[column].content) for row in rows if column < len(row)]
        mean = sum(lengths) / len(lengths)
        weights.append(max(6.0, min(55.0, 0.6 * max(lengths) ** 0.5 * 8 + 0.4 * mean)))
    scale = TEXT_WIDTH_CM / sum(weights)
    return [max(1.6, weight * scale) for weight in weights]


def _render_table(document: Any, rows: list[list[Token]], header_rows: int) -> None:
    columns = len(rows[0])
    table = document.add_table(rows=len(rows), cols=columns)
    table.style = document.styles["UC Table"]
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    widths = _column_widths(rows)
    total = sum(widths)
    widths = [w * TEXT_WIDTH_CM / total for w in widths]
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Cm(width)
    # A short table stays on one page; a long one may break, but its header always keeps the
    # first two body rows with it so it never ends a page alone (the header row repeats).
    if len(rows) - header_rows <= KEEP_TOGETHER_MAX_BODY_ROWS:
        keep_until = len(rows) - 1
    else:
        keep_until = header_rows + 2
    for row_index, (row, tokens) in enumerate(zip(table.rows, rows, strict=True)):
        is_header = row_index < header_rows
        _row_properties(row, cant_split=True, header=is_header)
        for cell, token, width in zip(row.cells, tokens, widths, strict=True):
            cell.width = Cm(width)
            paragraph = cell.paragraphs[0]
            paragraph.style = document.styles["Table Heading" if is_header else "Table Text"]
            _add_inline(paragraph, token, bold=is_header)
            if row_index < keep_until:
                paragraph.paragraph_format.keep_with_next = True
            if is_header:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:val"), "clear")
                shading.set(qn("w:color"), "auto")
                shading.set(qn("w:fill"), TINT)
                cell._tc.get_or_add_tcPr().append(shading)


# --- entry point --------------------------------------------------------------------------


def _set_properties(document: Any, meta: ReportMetadata, authors: str) -> None:
    props = document.core_properties
    props.title = meta.title
    props.subject = meta.subtitle
    props.author = authors
    props.last_modified_by = authors
    props.keywords = ""
    props.comments = ""
    props.category = ""
    props.language = LANGUAGE
    props.revision = 1
    stamp = datetime.fromisoformat(f"{meta.date}T12:00:00") if meta.date else datetime.now()
    props.created = stamp
    props.modified = stamp
    props.last_printed = stamp


def _clean_lists(items: Iterable[str]) -> list[str]:
    return [item for item in items if item]


def export_docx(
    source: Path,
    out_path: Path,
    *,
    template: Path | None,
    short_title: str | None = None,
) -> Path:
    """Write the Word version of ``source`` to ``out_path`` and return the path."""
    text = source.read_text(encoding="utf-8")
    meta = parse_metadata(text)
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    first_h2 = next(i for i, t in enumerate(tokens) if t.type == "heading_open" and t.tag == "h2")
    document = Document(str(template)) if template else Document()
    _remove_body_content(document)
    _define_styles(document)

    cover = document.sections[0]
    if template is None:
        cover.top_margin = Cm(2.5)
    _build_cover(document, meta)

    body = document.add_section(WD_SECTION.NEW_PAGE)
    body.left_margin = body.right_margin = TEXT_MARGIN
    body.top_margin = BODY_TOP_MARGIN
    body.bottom_margin = BODY_BOTTOM_MARGIN
    page_numbers = OxmlElement("w:pgNumType")
    page_numbers.set(qn("w:start"), "1")
    body._sectPr.append(page_numbers)
    running = short_title or meta.title.split(":")[0].strip()
    _style_header_footer(document, body, running)

    _Builder(document, source, tokens[first_h2:]).build()
    _set_properties(document, meta, ", ".join(meta.authors))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(out_path))
    return out_path
