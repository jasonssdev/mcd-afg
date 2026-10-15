"""The question worksheet of the judge calibration (thesis section 5.7, issue #82).

The person who writes the calibration questions must only write text. This module prepares a
spreadsheet where everything else is already there:

* one row per ES2015 decision the adjudication kept as a decision, with its sentence, the
  agreed content and the supporting dialogue acts resolved through the AMI ``summlink`` layer
  (the same chain the gold set uses), ready to be used as ``reference_evidence``;
* one row per adjudicated relation pair, with both decisions and the union of their evidence
  (material for the E2 and E3 strata);
* a few blank rows for E4 questions, which have no evidence by definition.

Four columns are left for the human: ``usar`` (``si`` to select the row), ``stratum`` (``E1``
to ``E4``), ``pregunta`` and ``respuesta_referencia``. :func:`validate_worksheet` checks the
selection with messages meant for that person, and :func:`worksheet_questions` turns the
selected rows into the questions the answer generator reads, so there is a single source of
questions. Evidence that cannot be resolved is left empty and flagged, never invented.

The worksheet is UTF-8 without BOM and is read with a BOM tolerated (spreadsheet tools add one).
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.annotation.goldset import summlink_dialogue_act_ids
from afg.conditions.c1_chunking import load_frozen_turns
from afg.domain.decision import EvidenceSpan
from afg.domain.question import (
    QuestionStratum,
    format_reference_evidence,
    parse_reference_evidence,
)
from afg.evaluation.judge_calibration_generation import CalibrationQuestion
from afg.evaluation.judge_calibration_set import DevelopmentSplitError, calibration_series
from afg.shared.csvio import open_csv_reader, open_csv_writer
from afg.shared.paths import JUDGE_CALIBRATION_DIR, TRANSCRIPTS_DIR

SERIES_ID = "ES2015"
WORKSHEET_PATH: Path = JUDGE_CALIBRATION_DIR / f"{SERIES_ID}.preguntas.csv"

HUMAN_COLUMNS: tuple[str, ...] = ("usar", "stratum", "pregunta", "respuesta_referencia")
AUTO_COLUMNS: tuple[str, ...] = (
    "fila",
    "origen",
    "reunion",
    "decision",
    "contenido_acordado",
    "relacion",
    "decision_posterior",
    "contenido_posterior",
    "evidencia_texto",
    "reference_evidence",
    "aviso_evidencia",
)
COLUMNS: tuple[str, ...] = HUMAN_COLUMNS + AUTO_COLUMNS

E4_ORIGIN = "E4"
E4_BLANK_ROWS = 6
MIN_SELECTED = 20
"""Recommended number of questions ("about 20" in issue #82); fewer only warns."""
HARD_MIN_SELECTED = 16
"""Fewest questions the worksheet may select; fewer is an error."""

_YES = frozenset({"si", "sí", "s", "x", "yes", "y", "1"})
_NO = frozenset({"", "no", "n", "0"})
_SHORTHAND = {s.value.split("_", 1)[0].upper(): s for s in QuestionStratum}


class WorksheetError(ValueError):
    """Raised when the worksheet cannot be read or used."""


class WorksheetNotEmptyError(RuntimeError):
    """Raised when regenerating would overwrite cells a person already filled."""


@dataclass(frozen=True, slots=True)
class ResolvedActs:
    """Dialogue acts that support a decision sentence, in transcript order.

    ``dropped`` counts the acts the annotation layer lists that the frozen transcript does not
    contain; they are left out rather than guessed.
    """

    ids: tuple[str, ...]
    dropped: int


ActResolver = Callable[[str, str], ResolvedActs]
"""``(meeting_id, source_sentence_id) -> ResolvedActs``. Injectable; tests use a fake."""


def make_act_resolver(ami_root: Path, transcripts_dir: Path = TRANSCRIPTS_DIR) -> ActResolver:
    """The real resolver: ``summlink`` ids filtered and ordered by the frozen transcript."""
    links: dict[str, dict[str, list[str]]] = {}
    order: dict[str, dict[str, int]] = {}

    def resolve(meeting_id: str, sentence_id: str) -> ResolvedActs:
        if meeting_id not in links:
            links[meeting_id] = summlink_dialogue_act_ids(ami_root, meeting_id)
            position: dict[str, int] = {}
            for turn in load_frozen_turns(meeting_id, transcripts_dir):
                for act in turn.dialogue_act_ids:
                    position.setdefault(act, len(position))
            order[meeting_id] = position
        wanted = list(dict.fromkeys(links[meeting_id].get(sentence_id, [])))
        position = order[meeting_id]
        known = sorted((a for a in wanted if a in position), key=lambda a: position[a])
        return ResolvedActs(ids=tuple(known), dropped=len(wanted) - len(known))

    return resolve


# --- building ---------------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open_csv_reader(path) as handle:
        return [{k: v or "" for k, v in row.items()} for row in csv.DictReader(handle)]


def _blank() -> dict[str, str]:
    return dict.fromkeys(COLUMNS, "")


def _merge_spans(parts: Sequence[tuple[str, tuple[str, ...]]]) -> str:
    """``meeting -> acts`` in first-appearance order, acts of one meeting merged."""
    merged: dict[str, list[str]] = {}
    for meeting_id, acts in parts:
        bucket = merged.setdefault(meeting_id, [])
        bucket.extend(a for a in acts if a not in bucket)
    spans = tuple(
        EvidenceSpan(meeting_id=m, dialogue_act_ids=tuple(a)) for m, a in merged.items() if a
    )
    return format_reference_evidence(spans)


def _warning(resolved: Sequence[ResolvedActs], *, unknown: bool = False) -> str:
    if unknown:
        return "sin evidencia: la decisión no está en el archivo adjudicado"
    if not any(r.ids for r in resolved):
        return "sin evidencia: no se pudo resolver ningún acto de diálogo"
    dropped = sum(r.dropped for r in resolved)
    if dropped or any(not r.ids for r in resolved):
        return f"parcial: {dropped} acto(s) no están en la transcripción o falta una decisión"
    return ""


def build_worksheet_rows(
    decisions_path: Path, relations_path: Path, *, resolve_acts: ActResolver
) -> list[dict[str, str]]:
    """Pre-filled worksheet rows: decisions, relation pairs, then the blank E4 rows."""
    decisions = _read_csv(decisions_path)
    by_id = {d["decision_id"]: d for d in decisions}
    resolved_by_id = {
        d["decision_id"]: resolve_acts(d["meeting_id"], d["source_sentence_id"]) for d in decisions
    }
    rows: list[dict[str, str]] = []

    for d in decisions:
        if d["final_status"].strip() != "decision":
            continue
        resolved = resolved_by_id[d["decision_id"]]
        rows.append(
            {
                **_blank(),
                "origen": d["decision_id"],
                "reunion": d["meeting_id"],
                "decision": d["sentence_text"],
                "contenido_acordado": d["final_content"],
                "evidencia_texto": d["evidence_text"],
                "reference_evidence": _merge_spans([(d["meeting_id"], resolved.ids)]),
                "aviso_evidencia": _warning([resolved]),
            }
        )

    for pair in _read_csv(relations_path):
        relation = pair["final_relation"].strip()
        if not relation:
            continue
        earlier = by_id.get(pair["earlier_decision_id"])
        later = by_id.get(pair["later_decision_id"])
        if earlier is None or later is None:
            parts: list[tuple[str, tuple[str, ...]]] = []
            warning = _warning([], unknown=True)
        else:
            parts = [
                (earlier["meeting_id"], resolved_by_id[earlier["decision_id"]].ids),
                (later["meeting_id"], resolved_by_id[later["decision_id"]].ids),
            ]
            warning = _warning(
                [resolved_by_id[earlier["decision_id"]], resolved_by_id[later["decision_id"]]]
            )
        meetings = [
            pair["earlier_decision_id"].split(".")[0],
            pair["later_decision_id"].split(".")[0],
        ]
        rows.append(
            {
                **_blank(),
                "origen": pair["pair_id"],
                "reunion": " -> ".join(meetings),
                "decision": pair["earlier_text"],
                "contenido_acordado": earlier["final_content"] if earlier else "",
                "relacion": relation,
                "decision_posterior": pair["later_text"],
                "contenido_posterior": later["final_content"] if later else "",
                "evidencia_texto": " || ".join(
                    d["evidence_text"] for d in (earlier, later) if d and d["evidence_text"]
                ),
                "reference_evidence": _merge_spans(parts),
                "aviso_evidencia": warning,
            }
        )

    rows.extend({**_blank(), "origen": E4_ORIGIN} for _ in range(E4_BLANK_ROWS))
    for number, row in enumerate(rows, start=1):
        row["fila"] = str(number)
    return rows


# --- file -------------------------------------------------------------------------------------


def load_worksheet(path: Path) -> list[dict[str, str]]:
    """Read the worksheet (BOM tolerated); every declared column is present in each row."""
    with open_csv_reader(path) as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise WorksheetError(f"{path.name}: faltan columnas {missing}")
        return [{c: (row.get(c) or "") for c in COLUMNS} for row in reader]


def has_human_work(rows: Sequence[dict[str, str]]) -> bool:
    return any(row[c].strip() for row in rows for c in HUMAN_COLUMNS)


def write_worksheet(path: Path, rows: Sequence[dict[str, str]], *, force: bool = False) -> None:
    """Write the worksheet as UTF-8 without BOM.

    Raises:
        WorksheetNotEmptyError: if ``path`` exists with any human-filled cell and ``force``
            is not set. An untouched worksheet may be regenerated freely.
    """
    if path.exists() and not force and has_human_work(load_worksheet(path)):
        raise WorksheetNotEmptyError(
            f"{path.name} ya tiene celdas llenadas por una persona; regenerarla las borraría. "
            "Usa --force solo si quieres descartar ese trabajo."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(path, encoding="utf-8") as writer:
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([row[c] for c in COLUMNS])


# --- validation -------------------------------------------------------------------------------


def parse_stratum(text: str) -> QuestionStratum | None:
    """``E1``..``E4`` (any case) or the full stratum name; ``None`` when not recognized."""
    value = text.strip()
    if not value:
        return None
    try:
        return QuestionStratum(value)
    except ValueError:
        pass
    return _SHORTHAND.get(value.upper())


@dataclass(frozen=True, slots=True)
class WorksheetReport:
    """Problems found in the selection, plus the counts the person needs to balance it."""

    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    n_selected: int
    by_stratum: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary_lines(self) -> list[str]:
        lines = [
            f"Filas seleccionadas: {self.n_selected} "
            f"(recomendado {MIN_SELECTED}, mínimo {HARD_MIN_SELECTED})."
        ]
        for stratum in QuestionStratum:
            count = self.by_stratum.get(stratum.value, 0)
            short = stratum.value.split("_", 1)[0]
            lines.append(f"  {short}: {count}")
        return lines


def _is_selected(value: str, fila: str, errors: list[str]) -> bool:
    text = value.strip().lower()
    if text in _YES:
        return True
    if text in _NO:
        return False
    errors.append(
        f"fila {fila}: `usar` tiene un valor que no se entiende ({value.strip()!r}); "
        "escribe `si` o déjala vacía."
    )
    return False


def validate_worksheet(rows: Sequence[dict[str, str]]) -> WorksheetReport:
    """Check the selected rows; unselected rows are ignored (a draft there is only a warning)."""
    errors: list[str] = []
    warnings: list[str] = []
    counts: Counter[str] = Counter()
    n_selected = 0
    for row in rows:
        fila = row["fila"].strip() or "?"
        if not _is_selected(row["usar"], fila, errors):
            if row["pregunta"].strip():
                warnings.append(
                    f"fila {fila}: tiene una pregunta escrita pero `usar` está vacía; no se usará."
                )
            continue
        n_selected += 1
        stratum = parse_stratum(row["stratum"])
        if not row["stratum"].strip():
            errors.append(f"fila {fila}: falta `stratum` (escribe E1, E2, E3 o E4).")
        elif stratum is None:
            errors.append(
                f"fila {fila}: `stratum` {row['stratum'].strip()!r} no existe; usa E1, E2, E3 o E4."
            )
        else:
            counts[stratum.value] += 1
        if not row["pregunta"].strip():
            errors.append(f"fila {fila}: falta `pregunta`.")
        reference = row["respuesta_referencia"].strip()
        evidence = row["reference_evidence"].strip()
        if stratum is QuestionStratum.E4_UNANSWERABLE:
            if reference:
                errors.append(
                    f"fila {fila}: una pregunta E4 no lleva `respuesta_referencia` "
                    "(no tiene respuesta en el material); déjala vacía."
                )
            continue
        if stratum is None:
            continue
        if not reference:
            errors.append(f"fila {fila}: falta `respuesta_referencia` (solo E4 la lleva vacía).")
        if not evidence:
            detail = row["aviso_evidencia"].strip()
            errors.append(
                f"fila {fila}: no tiene evidencia"
                + (f" ({detail})" if detail else "")
                + "; elige otra fila o márcala como E4 si no tiene respuesta."
            )
        else:
            try:
                parse_reference_evidence(evidence)
            except ValueError as exc:
                errors.append(f"fila {fila}: `reference_evidence` mal formada: {exc}")
    if n_selected == 0:
        errors.append(
            "no hay ninguna fila seleccionada: escribe `si` en `usar` en las filas que elijas."
        )
    elif n_selected < HARD_MIN_SELECTED:
        errors.append(
            f"hay {n_selected} filas seleccionadas y el mínimo es {HARD_MIN_SELECTED}; "
            "elige más filas."
        )
    elif n_selected < MIN_SELECTED:
        warnings.append(
            f"hay {n_selected} filas seleccionadas (recomendado {MIN_SELECTED}). Se puede "
            "seguir, pero con menos preguntas el resultado es menos preciso."
        )
    if n_selected and counts[QuestionStratum.E4_UNANSWERABLE.value] == 0:
        errors.append(
            "no hay ninguna pregunta E4 (sin respuesta en el material): hace falta al menos "
            "una; usa las filas `E4` del final."
        )
    return WorksheetReport(
        errors=tuple(errors),
        warnings=tuple(warnings),
        n_selected=n_selected,
        by_stratum=dict(counts),
    )


# --- bridge to the answer generator -----------------------------------------------------------


def worksheet_questions(rows: Sequence[dict[str, str]]) -> list[CalibrationQuestion]:
    """The selected rows as the questions :func:`generate_calibration_set` reads.

    Ids are ``ES2015.q<fila>``, stable as long as the worksheet rows keep their number.

    Raises:
        WorksheetError: if the selection does not validate (the first problem is named).
        DevelopmentSplitError: if the series is not one of the calibration series.
    """
    report = validate_worksheet(rows)
    if report.errors:
        raise WorksheetError(report.errors[0])
    questions: list[CalibrationQuestion] = []
    for row in rows:
        if row["usar"].strip().lower() not in _YES:
            continue
        stratum = parse_stratum(row["stratum"])
        assert stratum is not None  # validated above
        unanswerable = stratum is QuestionStratum.E4_UNANSWERABLE
        evidence = () if unanswerable else parse_reference_evidence(row["reference_evidence"])
        series = row["reunion"].strip()[:6] or SERIES_ID
        if series not in calibration_series():
            raise DevelopmentSplitError(
                f"fila {row['fila']}: la serie {series!r} no es una serie de calibración "
                f"{sorted(calibration_series())} (solo series de desarrollo, ADR 0005)."
            )
        questions.append(
            CalibrationQuestion(
                id=f"{SERIES_ID}.q{int(row['fila']):03d}",
                series_id=SERIES_ID,
                stratum=stratum,
                question=row["pregunta"].strip(),
                reference_answer=None if unanswerable else row["respuesta_referencia"].strip(),
                reference_evidence=evidence,
            )
        )
    return questions
