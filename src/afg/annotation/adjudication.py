"""Adjudication CSVs: both annotators side by side plus the adjudicator's verdict.

``afg gold adjudicate --series <ID>`` writes two files, the machine-readable OE1 gold set
once the adjudicator has filled them:

- ``data/processed/decisions/<ID>.decisions.adjudicated.csv`` -- one row per BASE decision.
- ``data/processed/relations/<ID>.candidates.adjudicated.csv`` -- one row per pair.

## The invariant

The machine never chooses between two disagreeing humans. Where both annotators gave the
same answer (``acuerdo = si``) the ``final_*`` columns are prefilled with that human value
and ``adjudicator`` is set to the configured adjudicator; where they differ (``acuerdo =
no``) every ``final_*`` column, ``razon`` and ``adjudicator`` stay empty. A row where
neither annotator answered is not an agreement: there is nothing to copy.

## ``compuesta``

Annotators align on the BASE row. When an annotator marked the base row ``compuesta``, their
child rows (``<base>-1``, ``<base>-2``, ...) are summarised in ``<ini>_split``. If the
adjudicator rules a row ``compuesta`` they add child rows right below it, with the same ids,
and fill ``final_*`` for each; the annotator columns of those child rows may stay empty.

## Overwrite protection

Regenerating would discard the adjudicator's work, so it is refused (``FileExistsError``)
when any row carries a ``razon`` or a ``final_*`` value different from what a fresh prefill
would produce, unless ``force`` is set.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from afg.annotation.agreement import annotator_csvs, annotator_initials
from afg.annotation.workspace import (
    AnnotationPlan,
    IssueKind,
    TaskKind,
    ValidationIssue,
    WorkspacePaths,
    _legal_values,
    _parent_decision_id,
    _read_rows,
    _write_rows,
)
from afg.domain.decision import AnnotationStatus

__all__ = [
    "CANDIDATE_ADJUDICATED_FIXED",
    "DECISION_ADJUDICATED_FIXED",
    "validate_adjudication",
    "write_adjudication_csvs",
]

DECISION_ADJUDICATED_FIXED = (
    "decision_id",
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_text",
)
CANDIDATE_ADJUDICATED_FIXED = (
    "pair_id",
    "earlier_decision_id",
    "later_decision_id",
    "earlier_text",
    "later_text",
    "blocker_score",
)

_DECISION_PER_ANNOTATOR = ("status", "object", "content", "notes", "split")
_DECISION_SOURCE_COLUMN = {
    "status": "status",
    "object": "decision_object",
    "content": "decision_content",
    "notes": "notes",
}
_DECISION_FINAL = ("final_status", "final_object", "final_content")
_CANDIDATE_PER_ANNOTATOR = ("relation", "direction_ok", "confidence", "notes")
_CANDIDATE_FINAL = ("final_relation", "final_direction_ok")
_VERDICT_TAIL = ("razon", "adjudicator")

_YES, _NO = "si", "no"
_COMPUESTA = AnnotationStatus.COMPUESTA.value
_DECISION = AnnotationStatus.DECISION.value
_SIN_SOPORTE = AnnotationStatus.SIN_SOPORTE.value


# --- reading the inputs -------------------------------------------------------------------


def _pick_annotators(directory: Path, series_id: str, kind: TaskKind) -> list[Path]:
    return annotator_csvs(directory, series_id, kind.value)


def _decision_children(rows: Sequence[Mapping[str, str]]) -> dict[str, list[Mapping[str, str]]]:
    """Group an annotator's ``-N`` child rows under their parent id, in file order."""
    ids = {row["decision_id"] for row in rows}
    children: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        row_id = row["decision_id"]
        parent = _parent_decision_id(row_id)
        if parent != row_id and parent in ids:
            children.setdefault(parent, []).append(row)
    return children


def _split_summary(children: Sequence[Mapping[str, str]]) -> str:
    parts = []
    for child in children:
        status = child.get("status", "").strip()
        text = f"{child['decision_id']} {status}".rstrip()
        if status == _DECISION:
            text += f" ({child.get('decision_object', '').strip()}: " + (
                f"{child.get('decision_content', '').strip()})"
            )
        parts.append(text)
    return "; ".join(parts)


class _DecisionSide:
    """One annotator's decisions file, indexed for alignment on the base row."""

    def __init__(self, path: Path) -> None:
        _, rows = _read_rows(path)
        rows = [row for row in rows if row.get("decision_id", "").strip()]
        self.children = _decision_children(rows)
        child_ids = {c["decision_id"] for group in self.children.values() for c in group}
        self.rows = {row["decision_id"]: row for row in rows if row["decision_id"] not in child_ids}

    def status(self, decision_id: str) -> str:
        return self.rows.get(decision_id, {}).get("status", "").strip()

    def child_statuses(self, decision_id: str) -> tuple[str, ...]:
        return tuple(c.get("status", "").strip() for c in self.children.get(decision_id, ()))

    def cell(self, decision_id: str, column: str) -> str:
        return self.rows.get(decision_id, {}).get(_DECISION_SOURCE_COLUMN[column], "").strip()

    def split(self, decision_id: str) -> str:
        if self.status(decision_id) != _COMPUESTA:
            return ""
        return _split_summary(self.children.get(decision_id, ()))


def _decisions_agree(a: _DecisionSide, b: _DecisionSide, decision_id: str) -> bool:
    status_a, status_b = a.status(decision_id), b.status(decision_id)
    if not status_a or status_a != status_b:
        return False
    if status_a == _COMPUESTA:
        return a.child_statuses(decision_id) == b.child_statuses(decision_id)
    return True


# --- building the rows --------------------------------------------------------------------


def _decision_rows(
    base_rows: Sequence[Mapping[str, str]],
    sides: Mapping[str, _DecisionSide],
    initials: Sequence[str],
    adjudicator: str,
) -> list[dict[str, str]]:
    first, second = initials
    rows: list[dict[str, str]] = []
    for base in base_rows:
        decision_id = base["decision_id"]
        row = {column: base.get(column, "") for column in DECISION_ADJUDICATED_FIXED}
        for ini in initials:
            side = sides[ini]
            for column in _DECISION_PER_ANNOTATOR:
                row[f"{ini}_{column}"] = (
                    side.split(decision_id) if column == "split" else side.cell(decision_id, column)
                )
        agree = _decisions_agree(sides[first], sides[second], decision_id)
        row["acuerdo"] = _YES if agree else _NO
        for column in (*_DECISION_FINAL, *_VERDICT_TAIL):
            row[column] = ""
        if agree:
            row["final_status"] = row[f"{first}_status"]
            row["final_object"] = row[f"{first}_object"]
            row["final_content"] = row[f"{first}_content"]
            row["adjudicator"] = adjudicator
        rows.append(row)
    return rows


def _candidate_rows(
    base_rows: Sequence[Mapping[str, str]],
    sides: Mapping[str, Mapping[str, Mapping[str, str]]],
    initials: Sequence[str],
    adjudicator: str,
) -> list[dict[str, str]]:
    first, second = initials
    rows: list[dict[str, str]] = []
    for base in base_rows:
        pair_id = base["pair_id"]
        row = {column: base.get(column, "") for column in CANDIDATE_ADJUDICATED_FIXED}
        for ini in initials:
            source = sides[ini].get(pair_id, {})
            for column in _CANDIDATE_PER_ANNOTATOR:
                row[f"{ini}_{column}"] = source.get(column, "").strip()
        agree = (
            bool(row[f"{first}_relation"])
            and row[f"{first}_relation"] == row[f"{second}_relation"]
            and row[f"{first}_direction_ok"] == row[f"{second}_direction_ok"]
        )
        row["acuerdo"] = _YES if agree else _NO
        for column in (*_CANDIDATE_FINAL, *_VERDICT_TAIL):
            row[column] = ""
        if agree:
            row["final_relation"] = row[f"{first}_relation"]
            row["final_direction_ok"] = row[f"{first}_direction_ok"]
            row["adjudicator"] = adjudicator
        rows.append(row)
    return rows


def _decision_header(initials: Sequence[str]) -> list[str]:
    return [
        *DECISION_ADJUDICATED_FIXED,
        *(f"{ini}_{column}" for ini in initials for column in _DECISION_PER_ANNOTATOR),
        "acuerdo",
        *_DECISION_FINAL,
        *_VERDICT_TAIL,
    ]


def _candidate_header(initials: Sequence[str]) -> list[str]:
    return [
        *CANDIDATE_ADJUDICATED_FIXED,
        *(f"{ini}_{column}" for ini in initials for column in _CANDIDATE_PER_ANNOTATOR),
        "acuerdo",
        *_CANDIDATE_FINAL,
        *_VERDICT_TAIL,
    ]


# --- overwrite protection -----------------------------------------------------------------


def _has_verdicts(
    path: Path, fresh: Sequence[Mapping[str, str]], id_column: str, final: Sequence[str]
) -> bool:
    """Whether ``path`` holds anything a fresh prefill would not have written."""
    if not path.exists():
        return False
    _, existing = _read_rows(path)
    expected = {row[id_column]: row for row in fresh}
    for row in existing:
        if row.get("razon", "").strip():
            return True
        reference = expected.get(row.get(id_column, ""), {})
        if any(row.get(column, "").strip() != reference.get(column, "") for column in final):
            return True
    return False


# --- write --------------------------------------------------------------------------------


def write_adjudication_csvs(
    plan: AnnotationPlan,
    series_id: str,
    *,
    paths: WorkspacePaths | None = None,
    force: bool = False,
) -> tuple[Path, Path]:
    """Write the decisions and candidates adjudication CSVs for ``series_id``.

    Returns ``(decisions_path, candidates_path)``. The two annotators are the two
    lexicographically first initials found among ``<series>.candidates.<ini>.csv``; the
    ``adjudicated`` suffix is never an annotator.

    Raises:
        FileNotFoundError: fewer than two annotators, a missing decisions file for one of
            them, or a missing base file.
        FileExistsError: an output already holds verdicts and ``force`` is not set.
    """
    paths = paths or WorkspacePaths()
    candidate_paths = _pick_annotators(paths.relations_dir, series_id, TaskKind.CANDIDATES)
    if len(candidate_paths) < 2:
        raise FileNotFoundError(
            f"Se necesitan al menos 2 archivos "
            f"data/processed/relations/{series_id}.candidates.<iniciales>.csv para "
            f"adjudicar la serie {series_id} (hay {len(candidate_paths)}). Cada anotador "
            "crea el suyo con `uv run afg gold prepare --annotator <iniciales>`."
        )
    candidate_paths = candidate_paths[:2]
    initials = [annotator_initials(path) for path in candidate_paths]

    decision_sources: dict[str, Path] = {}
    for ini in initials:
        source = paths.target(TaskKind.DECISIONS, series_id, ini)
        if not source.exists():
            raise FileNotFoundError(
                f"Falta data/processed/decisions/{source.name}: la serie {series_id} tiene "
                f"candidatos de `{ini}` pero no sus decisiones (Tarea A)."
            )
        decision_sources[ini] = source
    base_decisions = paths.source(TaskKind.DECISIONS, series_id)
    base_candidates = paths.source(TaskKind.CANDIDATES, series_id)
    for base in (base_decisions, base_candidates):
        if not base.exists():
            raise FileNotFoundError(
                f"Falta el archivo base {base.name}; regenéralo con `uv run afg gold ...`."
            )

    _, base_decision_rows = _read_rows(base_decisions)
    _, base_candidate_rows = _read_rows(base_candidates)
    sides = {ini: _DecisionSide(path) for ini, path in decision_sources.items()}
    candidate_sides = {
        ini: {r["pair_id"]: r for r in _read_rows(path)[1] if r.get("pair_id", "").strip()}
        for ini, path in zip(initials, candidate_paths, strict=True)
    }

    decision_rows = _decision_rows(
        [r for r in base_decision_rows if r.get("decision_id", "").strip()],
        sides,
        initials,
        plan.adjudicator,
    )
    candidate_rows = _candidate_rows(
        [r for r in base_candidate_rows if r.get("pair_id", "").strip()],
        candidate_sides,
        initials,
        plan.adjudicator,
    )

    decisions_out = paths.adjudicated(TaskKind.DECISIONS, series_id)
    candidates_out = paths.adjudicated(TaskKind.CANDIDATES, series_id)
    if not force:
        locked = [
            out.name
            for out, fresh, id_column, final in (
                (decisions_out, decision_rows, "decision_id", _DECISION_FINAL),
                (candidates_out, candidate_rows, "pair_id", _CANDIDATE_FINAL),
            )
            if _has_verdicts(out, fresh, id_column, final)
        ]
        if locked:
            raise FileExistsError(
                f"{' y '.join(locked)} ya tiene veredictos escritos a mano (razón o etiqueta "
                f"final). No se regenera: perderías el criterio registrado de la serie "
                f"{series_id}. Usa --force solo si de verdad quieres descartarlo."
            )

    _write_rows(decisions_out, _decision_header(initials), decision_rows)
    _write_rows(candidates_out, _candidate_header(initials), candidate_rows)
    return decisions_out, candidates_out


# --- validate -----------------------------------------------------------------------------


def _issue(path: Path, row_id: str, column: str, value: str, message: str) -> ValidationIssue:
    return ValidationIssue(
        path=path,
        row_id=row_id,
        column=column,
        value=value,
        message=f"{path.name}, fila {row_id}, columna {column}: {message}",
    )


def _check_verdict_tail(
    path: Path, row: Mapping[str, str], row_id: str, *, needs_razon: bool
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if needs_razon and not row.get("razon", "").strip():
        issues.append(_issue(path, row_id, "razon", "", "la razón es obligatoria aquí."))
    if not row.get("adjudicator", "").strip():
        issues.append(
            _issue(
                path, row_id, "adjudicator", "", "falta el adjudicador en una fila con veredicto."
            )
        )
    return issues


def _check_decision_final(
    path: Path, row: Mapping[str, str], row_id: str, *, disagreed: bool
) -> list[ValidationIssue]:
    status = row.get("final_status", "").strip()
    if not status:
        return [_issue(path, row_id, "final_status", "", "falta el veredicto final.")]
    if status not in _legal_values("status"):
        return [
            _issue(
                path,
                row_id,
                "final_status",
                status,
                f"{status!r} no pertenece al conjunto cerrado. Valores permitidos: "
                f"{', '.join(_legal_values('status'))}.",
            )
        ]
    issues: list[ValidationIssue] = []
    if status == _DECISION:
        for column in ("final_object", "final_content"):
            if not row.get(column, "").strip():
                issues.append(
                    _issue(path, row_id, column, "", "`final_status = decision` exige este valor.")
                )
    issues.extend(
        _check_verdict_tail(path, row, row_id, needs_razon=disagreed or status == _SIN_SOPORTE)
    )
    return issues


def _check_compuesta_children(
    path: Path, rows: Sequence[Mapping[str, str]], index: int
) -> list[ValidationIssue]:
    base_id = rows[index]["decision_id"]
    following: list[Mapping[str, str]] = []
    for row in rows[index + 1 :]:
        if _parent_decision_id(row["decision_id"]) == base_id != row["decision_id"]:
            following.append(row)
        else:
            break
    expected = [f"{base_id}-{n}" for n in range(1, len(following) + 1)]
    if len(following) < 2 or [r["decision_id"] for r in following] != expected:
        return [
            _issue(
                path,
                base_id,
                "final_status",
                _COMPUESTA,
                "una fila `compuesta` necesita al menos 2 filas hijas consecutivas "
                f"({base_id}-1, {base_id}-2, ...) justo debajo, con su veredicto final.",
            )
        ]
    return []


def _validate_decisions(path: Path) -> list[ValidationIssue]:
    _, rows = _read_rows(path)
    ids = {row.get("decision_id", "") for row in rows}
    issues: list[ValidationIssue] = []
    for index, row in enumerate(rows):
        row_id = row.get("decision_id", "").strip() or "(sin id)"
        parent = _parent_decision_id(row_id)
        if parent != row_id and parent in ids:
            parent_row = next(r for r in rows if r.get("decision_id") == parent)
            issues.extend(_check_decision_final(path, row, row_id, disagreed=False))
            if parent_row.get("final_status", "").strip() != _COMPUESTA:
                issues.append(
                    _issue(
                        path,
                        row_id,
                        "decision_id",
                        row_id,
                        f"fila hija de {parent}, cuyo veredicto final no es `compuesta`.",
                    )
                )
            continue
        acuerdo = row.get("acuerdo", "").strip()
        if acuerdo not in (_YES, _NO):
            issues.append(
                _issue(
                    path, row_id, "acuerdo", acuerdo, "debe ser `si` o `no` (columna de máquina)."
                )
            )
        row_issues = _check_decision_final(path, row, row_id, disagreed=acuerdo == _NO)
        issues.extend(row_issues)
        if row.get("final_status", "").strip() == _COMPUESTA:
            issues.extend(_check_compuesta_children(path, rows, index))
    return issues


def _validate_candidates(path: Path) -> list[ValidationIssue]:
    _, rows = _read_rows(path)
    issues: list[ValidationIssue] = []
    for row in rows:
        row_id = row.get("pair_id", "").strip() or "(sin id)"
        acuerdo = row.get("acuerdo", "").strip()
        if acuerdo not in (_YES, _NO):
            issues.append(
                _issue(
                    path, row_id, "acuerdo", acuerdo, "debe ser `si` o `no` (columna de máquina)."
                )
            )
        complete = True
        for column, closed in (
            ("final_relation", "relation"),
            ("final_direction_ok", "direction_ok"),
        ):
            value = row.get(column, "").strip()
            if not value:
                complete = False
                issues.append(_issue(path, row_id, column, "", "falta el veredicto final."))
            elif value not in _legal_values(closed):
                complete = False
                issues.append(
                    _issue(
                        path,
                        row_id,
                        column,
                        value,
                        f"{value!r} no pertenece al conjunto cerrado. Valores permitidos: "
                        f"{', '.join(_legal_values(closed))}.",
                    )
                )
        if complete:
            issues.extend(_check_verdict_tail(path, row, row_id, needs_razon=acuerdo == _NO))
        elif acuerdo == _NO and not row.get("razon", "").strip():
            issues.append(_issue(path, row_id, "razon", "", "la razón es obligatoria aquí."))
    return issues


def validate_adjudication(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> list[ValidationIssue]:
    """Check that the adjudicator finished both CSVs for ``series_id``.

    Every error carries the row id and the column, in Spanish. A missing file is reported as
    a ``MISSING_FILE`` issue so the CLI can point at ``afg gold adjudicate``.
    """
    paths = paths or WorkspacePaths()
    issues: list[ValidationIssue] = []
    for kind, check in (
        (TaskKind.DECISIONS, _validate_decisions),
        (TaskKind.CANDIDATES, _validate_candidates),
    ):
        path = paths.adjudicated(kind, series_id)
        if not path.exists():
            issues.append(
                ValidationIssue(
                    path=path,
                    row_id="-",
                    column="-",
                    value="",
                    kind=IssueKind.MISSING_FILE,
                    message=(
                        f"Falta {path.name}. Ejecuta `uv run afg gold adjudicate "
                        f"--series {series_id}` para crearlo."
                    ),
                )
            )
            continue
        issues.extend(check(path))
    return issues
