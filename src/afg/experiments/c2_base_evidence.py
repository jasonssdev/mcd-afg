"""Evidence from the compiled base for the C2 failures the trace cannot attribute (issue #146).

:mod:`afg.experiments.c2_context` leaves a C2 failure without a stage when the whole reference
answer is not visible in the retrieved blocks: the saved trace cannot tell OE4 ``extraccion``
(the fact never reached the compiled base correctly) from ``recuperacion`` (it is in the base
and was not retrieved). That needs the compiled base itself (``data/interim/openkos/``, not
versioned). This module reads it and ranks its objects by how many content terms of the
reference answer each one holds, so a person can label each case quickly.

Three cautions are part of the contract:

* The coverage is the lexical proxy of :func:`~afg.experiments.c2_context.reference_term_coverage`.
  It cannot tell "25" from "twenty-five", so a low value is a cue to read the object, not proof
  that the fact is missing.
* ``sources/`` objects are the raw transcript, imported verbatim. A fact found only there is NOT
  evidence that extraction captured it, so they are ranked apart from the extracted objects.
* Nothing here assigns a stage. The worksheet leaves ``etapa_humana`` empty (CONTRIBUTING 7.6);
  ``pista_automatica`` is a triage hint in the style of ``machine_flags``, never a label.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.domain.question import Question
from afg.experiments.c2_context import (
    _blocks,
    concept_kind,
    context_rows,
    error_evidence,
    reference_term_coverage,
)
from afg.shared.csvio import open_csv_writer, read_rows
from afg.shared.paths import OPENKOS_WORKSPACES_DIR

BUNDLE_NAMESPACES = ("decisions", "concepts", "events", "people", "projects", "sources")
ETAPA_VALUES = ("extraccion", "recuperacion", "sintesis")
"""The values a person may write in ``etapa_humana``; code never writes one."""
WORKSHEET_COLUMNS: tuple[str, ...] = (
    "pregunta_id",
    "pregunta",
    "respuesta_referencia",
    "respuesta_c2",
    "mejor_objeto",
    "mejor_objeto_recuperado",
    "objetos_de_la_base",
    "mejor_fuente",
    "pista_automatica",
    "etapa_humana",
    "nota",
)
HUMAN_COLUMNS = ("etapa_humana", "nota")

_FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_RELATED_RE = re.compile(r"\n## Related\b.*\Z", re.DOTALL)


class WorksheetLabeledError(ValueError):
    """The worksheet already holds a human label and would be erased."""


@dataclass(frozen=True, slots=True)
class ObjectCoverage:
    """One bundle object and how much of the reference answer its text holds."""

    object_id: str
    kind: str
    coverage: float
    retrieved: bool


@dataclass(frozen=True, slots=True)
class BaseEvidence:
    """Bundle objects ranked by reference coverage: extracted ones, and raw sources apart."""

    objects: tuple[ObjectCoverage, ...]
    sources: tuple[ObjectCoverage, ...]


def _object_text(path: Path) -> str:
    """The text of a bundle file without its front matter and its ``## Related`` links."""
    text = _FRONT_MATTER_RE.sub("", path.read_text(encoding="utf-8"), count=1).lstrip("\n")
    return _RELATED_RE.sub("", text)


def rank_bundle_objects(
    reference: str,
    bundle_dir: Path,
    *,
    retrieved_ids: Iterable[str] = (),
    meeting_id: str | None = None,
) -> BaseEvidence:
    """Rank the objects of a compiled bundle by the share of ``reference`` terms they hold.

    ``retrieved_ids`` are the concept ids the C2 query returned. ``meeting_id`` keeps only the
    ``sources/`` transcript of that meeting. Ties break by object id, so the order is stable.

    Raises:
        FileNotFoundError: ``bundle_dir`` is not a directory.
    """
    if not bundle_dir.is_dir():
        raise FileNotFoundError(f"No existe la base compilada en {bundle_dir}.")
    retrieved = set(retrieved_ids)
    wanted_source = f"sources/{meeting_id.lower()}" if meeting_id else None
    extracted: list[ObjectCoverage] = []
    sources: list[ObjectCoverage] = []
    for namespace in BUNDLE_NAMESPACES:
        for path in sorted((bundle_dir / namespace).glob("*.md")):
            object_id = f"{namespace}/{path.stem}"
            if namespace == "sources" and wanted_source and object_id != wanted_source:
                continue
            coverage = reference_term_coverage(reference, [{"text": _object_text(path)}])
            item = ObjectCoverage(
                object_id=object_id,
                kind=concept_kind(object_id),
                coverage=coverage,
                retrieved=object_id in retrieved,
            )
            (sources if namespace == "sources" else extracted).append(item)

    def order(item: ObjectCoverage) -> tuple[float, str]:
        return (-item.coverage, item.object_id)

    return BaseEvidence(
        objects=tuple(sorted(extracted, key=order)), sources=tuple(sorted(sources, key=order))
    )


def bundle_dir_for_run(
    manifest: Mapping[str, Any], *, base_dir: Path = OPENKOS_WORKSPACES_DIR, run: int = 0
) -> Path:
    """The bundle C2 queried, from the ``c2_extraction`` and series of an Experiment B manifest.

    C2 reads ``<base_dir>/<c2_extraction>/<series>/run-<r>/bundle`` (see
    :class:`~afg.conditions.c2_compiled_auto.CompiledAutoCondition`).

    Raises:
        ValueError: the manifest has no ``c2_extraction`` or not exactly one series.
    """
    extraction = manifest.get("c2_extraction")
    series = manifest.get("series") or []
    if not extraction or len(series) != 1:
        raise ValueError("The manifest needs a c2_extraction and exactly one series.")
    return base_dir / str(extraction) / str(series[0]) / f"run-{run}" / "bundle"


def _fmt(item: ObjectCoverage) -> str:
    return f"{item.object_id} ({item.coverage:.2f}, {'' if item.retrieved else 'no '}recuperado)"


def _hint(best: ObjectCoverage | None, source: ObjectCoverage | None) -> str:
    """A triage hint (never a stage) from the best extracted object and the best source."""
    if best is not None and best.coverage == 1.0:
        where = "y se recuperó" if best.retrieved else "y no se recuperó"
        return f"un objeto de la base tiene todos los términos de la referencia {where}"
    if source is not None and source.coverage == 1.0:
        return (
            "solo la transcripción en bruto tiene todos los términos; no prueba que la "
            "extracción lo capturó"
        )
    return "ningún objeto ni fuente tiene todos los términos (puede ser una diferencia léxica)"


def oe4_worksheet_rows(
    c2_records: Sequence[Mapping[str, Any]],
    questions: Mapping[str, Question],
    bundle_dir: Path,
    *,
    top: int = 3,
) -> list[dict[str, str]]:
    """One row per incorrect E1 answer whose stage the trace cannot attribute.

    Rows follow :data:`WORKSHEET_COLUMNS`; ``etapa_humana`` and ``nota`` are always empty.
    """
    by_question = {str(r["question_id"]): r for r in c2_records}
    out: list[dict[str, str]] = []
    for row in context_rows(c2_records, [], questions):
        if row.correct is not False or row.stratum != "E1":
            continue
        (evidence,) = error_evidence([row], c2_records, questions)
        if evidence.rule_stage is not None:
            continue
        record = by_question[row.question_id]
        question = questions[row.question_id]
        reference = question.reference_answer or ""
        meeting = question.reference_evidence[0].meeting_id if question.reference_evidence else None
        ids = [str(b.get("concept_id", "")) for b in _blocks(record)]
        found = rank_bundle_objects(reference, bundle_dir, retrieved_ids=ids, meeting_id=meeting)
        best = found.objects[0] if found.objects else None
        source = found.sources[0] if found.sources else None
        out.append(
            {
                "pregunta_id": row.question_id,
                "pregunta": question.text,
                "respuesta_referencia": reference,
                "respuesta_c2": str((record.get("answer") or {}).get("text", "")),
                "mejor_objeto": best.object_id if best else "",
                "mejor_objeto_recuperado": (
                    "" if best is None else "sí" if best.retrieved else "no"
                ),
                "objetos_de_la_base": " | ".join(_fmt(o) for o in found.objects[:top]),
                "mejor_fuente": f"{source.object_id} ({source.coverage:.2f})" if source else "",
                "pista_automatica": _hint(best, source),
                "etapa_humana": "",
                "nota": "",
            }
        )
    return out


def write_oe4_worksheet(
    path: Path, rows: Sequence[Mapping[str, str]], *, force: bool = False
) -> None:
    """Write the worksheet; refuse to erase one a person has already labeled.

    Raises:
        WorksheetLabeledError: ``path`` holds a human label and ``force`` is false.
    """
    if path.exists() and not force:
        labeled = [r for r in read_rows(path) if any(r.get(c, "").strip() for c in HUMAN_COLUMNS)]
        if labeled:
            raise WorksheetLabeledError(
                f"{path.name} ya tiene etiquetas ({len(labeled)} fila(s)); use --force para "
                "sobrescribir."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(path, encoding="utf-8") as writer:
        writer.writerow(WORKSHEET_COLUMNS)
        writer.writerows([[row.get(c, "") for c in WORKSHEET_COLUMNS] for row in rows])


def read_worksheet_rows(path: Path) -> list[dict[str, str]]:
    """Read the worksheet back (UTF-8, BOM tolerated), with the labels a person wrote."""
    return read_rows(path)


def count_stages(
    rule_stages: Iterable[str], worksheet: Sequence[Mapping[str, str]]
) -> dict[str, int]:
    """Count failures per OE4 stage: rule-based ones plus the worksheet's human labels.

    Every worksheet row must carry one of :data:`ETAPA_VALUES`; an empty or unknown label
    raises ``ValueError`` so a half-labelled sheet never yields a partial figure.
    """
    counts = dict.fromkeys(ETAPA_VALUES, 0)
    for stage in rule_stages:
        counts[stage] += 1
    for row in worksheet:
        label = row["etapa_humana"].strip()
        if label not in counts:
            raise ValueError(f"{row['pregunta_id']}: etapa_humana invalida o vacia ({label!r})")
        counts[label] += 1
    return counts


__all__ = [
    "ETAPA_VALUES",
    "WORKSHEET_COLUMNS",
    "BaseEvidence",
    "ObjectCoverage",
    "WorksheetLabeledError",
    "bundle_dir_for_run",
    "count_stages",
    "oe4_worksheet_rows",
    "rank_bundle_objects",
    "read_worksheet_rows",
    "write_oe4_worksheet",
]
