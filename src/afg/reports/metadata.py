"""Metadata of an informe, read from the markdown header (title, subtitle and info table)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

_MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class ReportMetadata:
    """What the cover page and the document properties need from the markdown header."""

    title: str
    version: str
    date: str
    subtitle: str = ""
    authors: tuple[str, ...] = ()
    tutor: str = ""
    program: str = ""
    course: str = ""
    university: str = ""


def format_date_es(iso_date: str) -> str:
    """Return ``2026-11-09`` as ``9 de noviembre de 2026``."""
    if not _ISO_DATE.fullmatch(iso_date):
        raise ValueError(f"La fecha '{iso_date}' no tiene el formato AAAA-MM-DD.")
    parsed = date.fromisoformat(iso_date)
    return f"{parsed.day} de {_MONTHS_ES[parsed.month - 1]} de {parsed.year}"


def parse_metadata(markdown: str) -> ReportMetadata:
    """Read title, subtitle and the ``| **Clave** | valor |`` rows that follow the H1."""
    tokens = MarkdownIt("commonmark").enable("table").parse(markdown)
    title = subtitle = ""
    rows: dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1" and not title:
            title = tokens[index + 1].content.strip()
            following = tokens[index + 4] if index + 4 < len(tokens) else None
            if following is not None and following.type == "inline":
                subtitle = following.content.strip()
        elif token.type == "heading_open" and token.tag == "h2" and title:
            break
        elif token.type == "tr_open" and title:
            cells = []
            for later in tokens[index + 1 :]:
                if later.type == "tr_close":
                    break
                if later.type == "inline":
                    cells.append(later.content.strip())
            if len(cells) == 2:
                rows[cells[0].strip("*").strip()] = cells[1]
    if not title:
        raise ValueError("El markdown no tiene un título de primer nivel (# ...).")
    if "Versión" not in rows:
        raise ValueError("La tabla de encabezado no tiene la fila **Versión**.")
    return ReportMetadata(
        title=title,
        subtitle=subtitle,
        version=rows["Versión"],
        date=rows.get("Fecha", ""),
        authors=tuple(a.strip() for a in rows.get("Autores", "").split(", ") if a.strip()),
        tutor=rows.get("Tutor", ""),
        program=rows.get("Programa", ""),
        course=rows.get("Curso", ""),
        university=rows.get("Universidad", ""),
    )


def default_output_path(source: Path, meta: ReportMetadata, out_dir: Path) -> Path:
    """``<out_dir>/<source stem>-v<version>.docx``."""
    return out_dir / f"{source.stem}-v{meta.version}.docx"
