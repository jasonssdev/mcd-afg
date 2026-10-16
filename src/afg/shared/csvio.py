"""Shared CSV writer configuration for every tracked table this package writes.

``csv.writer`` defaults to CRLF line endings (per the ``csv`` module's own dialect
default). Git normalizes CRLF to LF on commit, so a CSV written by our code never
byte-for-byte matches the same file once it is checked out again -- the very next
regeneration then shows the whole file as modified, destroying the file's value as a
diffable, reproducible record.

This is the third time this exact defect has appeared in this codebase (first fixed
ad hoc in ``afg.corpus.render.write_manifest_csv``, then found again at six more call
sites). Every writer of a tracked CSV in this package MUST go through
:func:`open_csv_writer` instead of calling ``csv.writer`` directly, so the fix lives in
one place and cannot regress a fourth time.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import _csv

__all__ = ["CsvFormatError", "open_csv_reader", "open_csv_writer", "read_rows", "semicolon_hint"]


@contextmanager
def open_csv_writer(path: Path, *, encoding: str | None = None) -> Iterator[_csv.Writer]:
    """Open ``path`` for writing and yield a ``csv.writer`` that emits LF line endings.

    Sets ``newline=""`` on the file handle (required by the ``csv`` module so it can
    control line endings itself) and ``lineterminator="\\n"`` on the writer (so it
    actually does, instead of falling back to the default CRLF). ``encoding`` is passed
    through to ``Path.open`` unchanged, defaulting to the platform default when omitted,
    matching what the call sites did before this helper existed.
    """
    with path.open("w", newline="", encoding=encoding) as fh:
        writer = csv.writer(fh, lineterminator="\n")
        yield writer


class CsvFormatError(ValueError):
    """An annotator's CSV cannot be read as UTF-8 text; the message tells how to fix it."""


_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")

_HOW_TO_SAVE = (
    "Guárdalo de nuevo como UTF-8: en Excel, «Guardar como → CSV UTF-8 (delimitado por "
    "comas)»; en LibreOffice, «Juego de caracteres: Unicode (UTF-8)» y separador coma."
)


@contextmanager
def open_csv_reader(path: Path) -> Iterator[io.StringIO]:
    """Open an annotator-edited CSV as text: UTF-8, with or without BOM.

    Excel's plain "CSV" is latin-1/cp1252 and its "Unicode text" is UTF-16; both used to
    surface as a raw ``'utf-8' codec can't decode`` traceback. Here either case raises
    :class:`CsvFormatError` naming the file and how to re-save it. Latin-1 is deliberately
    *not* guessed: decoding it silently would hide corruption in the annotators' text.

    Raises:
        CsvFormatError: the file is UTF-16 or not valid UTF-8.
        FileNotFoundError: ``path`` does not exist.
    """
    raw = path.read_bytes()
    if raw.startswith(_UTF16_BOMS):
        raise CsvFormatError(
            f"{path.name}: el archivo está guardado como «Unicode» (UTF-16), que este programa "
            f"no lee. {_HOW_TO_SAVE}"
        )
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError(
            f"{path.name}: el archivo no está guardado como UTF-8 (probablemente Excel lo "
            f"guardó como «CSV» simple y las tildes y la «ñ» se corrompen). {_HOW_TO_SAVE}"
        ) from exc
    with io.StringIO(text, newline="") as handle:
        yield handle


def semicolon_hint(path: Path, fieldnames: Sequence[str]) -> str | None:
    """Spanish explanation when the header shows a ``;``-separated file, else ``None``."""
    if len(fieldnames) == 1 and ";" in fieldnames[0]:
        return (
            f"{path.name}: el archivo parece guardado con `;` como separador. Guárdalo con "
            "comas (en Excel: «CSV UTF-8 (delimitado por comas)»; ver «Editar el CSV» en "
            "docs/anotacion/asignacion/EMPIEZA-AQUI.md)."
        )
    return None


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV into plain ``dict[str, str]`` rows: UTF-8 (BOM tolerated), no ``None``.

    Missing cells (a short row) come back as ``""``. Goes through :func:`open_csv_reader`, so
    UTF-16 / non-UTF-8 files raise :class:`CsvFormatError`; a ``;``-separated file raises it
    too, with the :func:`semicolon_hint` text, instead of yielding one mangled column.

    Raises:
        CsvFormatError: the file is not UTF-8 text or is saved with ``;`` as separator.
        FileNotFoundError: ``path`` does not exist.
    """
    with open_csv_reader(path) as handle:
        reader = csv.DictReader(handle)
        hint = semicolon_hint(path, reader.fieldnames or [])
        if hint is not None:
            raise CsvFormatError(hint)
        return [{k: v or "" for k, v in row.items() if k is not None} for row in reader]
