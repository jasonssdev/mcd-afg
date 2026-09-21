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
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import _csv

__all__ = ["open_csv_writer"]


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
