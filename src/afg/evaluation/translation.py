"""English translation of the adjudicated reference (issue #141).

The extraction output is in the transcript's original language (English) while the human
labels (``final_object``, ``final_content``) are in Spanish. To compare like with like, each
adjudicated series gets a sidecar file ``<SERIES>.reference-en.csv`` with an automatic
translation of those two labels.

The translation is NOT a label: it never decides a status or a relation, and the Spanish
``final_*`` columns stay the ground truth. The sidecar copies the Spanish source
(``final_object``, ``final_content``) so a later change in the adjudication is detected
("desactualizada") instead of silently scoring against an old translation. The sidecar is a
separate file because ``afg gold adjudicate --force`` can regenerate the adjudicated CSV.

One row per reference decision, i.e. per row :func:`afg.evaluation.reference.load_reference`
returns (``final_status == "decision"`` after compuesta-child inheritance).
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from afg.evaluation.reference import _inherit_from_compuesta_parent, _read_adjudicated
from afg.shared.csvio import open_csv_reader, open_csv_writer
from afg.shared.paths import GOLD_DECISIONS_DIR

__all__ = [
    "ALLOWED_METHODS",
    "TRANSLATION_COLUMNS",
    "TranslationError",
    "adjudicated_path",
    "load_translations",
    "translation_path",
    "validate_translation",
    "validate_translation_files",
    "write_translation_template",
]

TRANSLATION_COLUMNS = (
    "decision_id",
    "final_object",
    "final_content",
    "object_en",
    "content_en",
    "translation_method",
    "notes",
)
ALLOWED_METHODS = ("automatica",)
_DEFAULT_METHOD = ALLOWED_METHODS[0]


class TranslationError(ValueError):
    """The English translation of a reference is missing, incomplete or out of date."""


def adjudicated_path(series_id: str, decisions_dir: Path = GOLD_DECISIONS_DIR) -> Path:
    """Adjudicated decisions CSV of ``series_id``."""
    return decisions_dir / f"{series_id}.decisions.adjudicated.csv"


def translation_path(series_id: str, decisions_dir: Path = GOLD_DECISIONS_DIR) -> Path:
    """English translation file of ``series_id``."""
    return decisions_dir / f"{series_id}.reference-en.csv"


def _reference_rows(adjudicated: Path) -> list[dict[str, str]]:
    """Rows that are reference decisions (same rule as ``load_reference``)."""
    rows = _inherit_from_compuesta_parent(
        [r for r in _read_adjudicated(adjudicated) if r.get("decision_id")]
    )
    return [r for r in rows if r.get("final_status") == "decision"]


def write_translation_template(
    series_id: str, *, decisions_dir: Path = GOLD_DECISIONS_DIR, force: bool = False
) -> Path:
    """Write ``<series>.reference-en.csv`` with the Spanish filled and the English empty.

    Raises:
        FileNotFoundError: the series has no adjudicated file.
        FileExistsError: the translation file exists and ``force`` is false.
    """
    source = adjudicated_path(series_id, decisions_dir)
    if not source.is_file():
        raise FileNotFoundError(
            f"No existe {source.name}: la serie {series_id} no está adjudicada todavía."
        )
    target = translation_path(series_id, decisions_dir)
    if target.exists() and not force:
        raise FileExistsError(
            f"{target.name} ya existe y regenerarlo borraría la traducción escrita. "
            "Usa --force solo si quieres empezar de cero."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(target, encoding="utf-8") as writer:
        writer.writerow(list(TRANSLATION_COLUMNS))
        for row in _reference_rows(source):
            writer.writerow(
                [
                    row["decision_id"],
                    row.get("final_object", ""),
                    row.get("final_content", ""),
                    "",
                    "",
                    _DEFAULT_METHOD,
                    "",
                ]
            )
    return target


def _read_translation(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open_csv_reader(path) as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows = [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]
    return header, rows


def validate_translation_files(adjudicated: Path, translation: Path) -> list[str]:
    """Spanish problem messages (empty list = valid) for one series' translation file."""
    name = translation.name
    if not translation.is_file():
        series = name.split(".")[0]
        return [f"Falta {name}. Créalo con: uv run afg gold translation-template --series {series}"]
    header, rows = _read_translation(translation)
    missing = [c for c in TRANSLATION_COLUMNS if c not in header]
    if missing:
        return [f"{name}: faltan las columnas {', '.join(missing)}."]

    issues: list[str] = []
    expected = {r["decision_id"]: r for r in _reference_rows(adjudicated)}
    seen: set[str] = set()
    for row in rows:
        decision_id = row["decision_id"]
        if not decision_id:
            continue
        if decision_id in seen:
            issues.append(f"{name}: la decisión {decision_id} está repetida.")
            continue
        seen.add(decision_id)
        source = expected.get(decision_id)
        if source is None:
            issues.append(
                f"{name}: {decision_id} no es una decisión de la referencia adjudicada "
                "(sobra la fila)."
            )
            continue
        issues.extend(
            f"{name}: {decision_id} tiene {column} vacío."
            for column in ("object_en", "content_en")
            if not row[column]
        )
        if row["final_object"] != source.get("final_object", "") or row[
            "final_content"
        ] != source.get("final_content", ""):
            issues.append(
                f"{name}: la traducción de {decision_id} está desactualizada; el español "
                "adjudicado cambió. Revisa object_en/content_en y copia el español actual."
            )
        if row["translation_method"] not in ALLOWED_METHODS:
            issues.append(
                f"{name}: {decision_id} tiene translation_method {row['translation_method']!r}; "
                f"valores permitidos: {', '.join(ALLOWED_METHODS)}."
            )
    issues.extend(f"{name}: falta la decisión {i}." for i in expected if i not in seen)
    return issues


def validate_translation(series_id: str, *, decisions_dir: Path = GOLD_DECISIONS_DIR) -> list[str]:
    """:func:`validate_translation_files` for ``series_id`` under ``decisions_dir``."""
    return validate_translation_files(
        adjudicated_path(series_id, decisions_dir), translation_path(series_id, decisions_dir)
    )


def load_translations(adjudicated: Path, translation: Path) -> Mapping[str, tuple[str, str]]:
    """``decision_id -> (object_en, content_en)``, only if the file is complete and current.

    Raises:
        TranslationError: the file is missing, incomplete or stale; the message lists why.
    """
    issues = validate_translation_files(adjudicated, translation)
    if issues:
        raise TranslationError(
            "La referencia en inglés no está lista:\n  - " + "\n  - ".join(issues)
        )
    _, rows = _read_translation(translation)
    return {r["decision_id"]: (r["object_en"], r["content_en"]) for r in rows}
