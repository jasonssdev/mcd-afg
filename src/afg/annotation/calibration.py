"""Summaries of a double-annotated, adjudicated series for the annotation-phase notebooks.

The notebook for each annotation phase does not compute (CONTRIBUTING section 7.1): every
figure it shows comes from here. All functions read the two adjudication CSVs written by
``afg gold adjudicate`` and completed by the adjudicator
(``<series>.decisions.adjudicated.csv`` and ``<series>.candidates.adjudicated.csv``) and are
generic over ``series_id``, so the Phase 1, 2 and 3 notebooks share them.

Nothing here writes: the labels are human and this module only reports them.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from afg.annotation.agreement import compute_agreement
from afg.annotation.workspace import TaskKind, WorkspacePaths, _parent_decision_id, _read_rows

__all__ = [
    "DecisionAgreement",
    "FinalStatusCounts",
    "adjudicated_pairs",
    "annotator_status_distribution",
    "chance_agreement",
    "compuesta_children",
    "decision_agreement",
    "disagreement_groups",
    "final_rows",
    "final_status_counts",
    "resolved_disagreements",
    "side_taken_counts",
    "status_contingency",
    "status_labels",
]

_STATUS_SUFFIX = "_status"
_COMPUESTA = "compuesta"
_NO = "no"
_RELATION_SUFFIX = "_relation"


@dataclass(frozen=True, slots=True)
class DecisionAgreement:
    """Agreement of two annotators on the ``status`` of the BASE decision rows (Task A)."""

    series_id: str
    annotator_a: str
    annotator_b: str
    n_items: int
    n_status_agree: int
    percent_agreement: float
    status_kappa: float
    n_acuerdo: int
    """Rows with ``acuerdo = si``: stricter than status equality for ``compuesta`` rows,
    which must also agree on how the sentence is split."""


@dataclass(frozen=True, slots=True)
class FinalStatusCounts:
    """Adjudicated ``final_status`` counts; split children are counted apart from base rows."""

    base: dict[str, int]
    children: dict[str, int]


def _load(
    series_id: str, kind: TaskKind, paths: WorkspacePaths | None
) -> tuple[list[str], list[dict[str, str]]]:
    workspace = paths or WorkspacePaths()
    path: Path = workspace.adjudicated(kind, series_id)
    if not path.exists():
        raise FileNotFoundError(f"Falta {path.name}: la serie {series_id} no está adjudicada.")
    return _read_rows(path)


def _annotators(header: list[str], suffix: str) -> tuple[str, str]:
    """The two annotators' initials, read from ``<ini>_status``-style columns."""
    initials = sorted(
        column.removesuffix(suffix)
        for column in header
        if column.endswith(suffix) and not column.startswith("final_")
    )
    if len(initials) != 2:
        raise ValueError(f"Se esperaban 2 anotadores en las columnas *{suffix}, hay {initials}.")
    return initials[0], initials[1]


def _is_child(row: Mapping[str, str], ids: set[str]) -> bool:
    parent = _parent_decision_id(row["decision_id"])
    return parent != row["decision_id"] and parent in ids


def _split(
    series_id: str, paths: WorkspacePaths | None
) -> tuple[tuple[str, str], list[dict[str, str]], list[dict[str, str]]]:
    header, rows = _load(series_id, TaskKind.DECISIONS, paths)
    ids = {row["decision_id"] for row in rows}
    base = [r for r in rows if not _is_child(r, ids)]
    children = [r for r in rows if _is_child(r, ids)]
    return _annotators(header, _STATUS_SUFFIX), base, children


def status_labels(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> tuple[tuple[str, str], list[str], list[str]]:
    """``(annotators, labels_a, labels_b)``: each annotator's own ``status`` on base rows.

    These are the annotators' labels, never the adjudicated verdict. The one place that
    selects the Task A items, shared by :func:`decision_agreement` and the pooled agreement.
    """
    (a, b), base, _ = _split(series_id, paths)
    return (a, b), [r[f"{a}_status"] for r in base], [r[f"{b}_status"] for r in base]


def decision_agreement(series_id: str, *, paths: WorkspacePaths | None = None) -> DecisionAgreement:
    """Status agreement (raw and Cohen's kappa) between the two annotators on base rows.

    Kappa goes through :func:`afg.annotation.agreement.compute_agreement`, the project's
    single implementation. It is ``nan`` when both annotators used one single category.
    """
    (a, b), labels_a, labels_b = status_labels(series_id, paths=paths)
    _, base, _ = _split(series_id, paths)
    agree = sum(x == y for x, y in zip(labels_a, labels_b, strict=True))
    kappa = compute_agreement(labels_a, labels_b) if base else math.nan
    return DecisionAgreement(
        series_id=series_id,
        annotator_a=a,
        annotator_b=b,
        n_items=len(base),
        n_status_agree=agree,
        percent_agreement=agree / len(base) if base else math.nan,
        status_kappa=kappa,
        n_acuerdo=sum(r["acuerdo"] == "si" for r in base),
    )


def status_contingency(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> list[tuple[str, str, int]]:
    """``(status_a, status_b, count)`` for every combination seen on base rows, sorted."""
    (a, b), base, _ = _split(series_id, paths)
    counts = Counter((r[f"{a}_status"], r[f"{b}_status"]) for r in base)
    return [(x, y, n) for (x, y), n in sorted(counts.items())]


def annotator_status_distribution(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> dict[str, dict[str, int]]:
    """How often each annotator used each ``status`` on base rows, keyed by initials."""
    (a, b), base, _ = _split(series_id, paths)
    return {ini: dict(sorted(Counter(r[f"{ini}_status"] for r in base).items())) for ini in (a, b)}


def chance_agreement(series_id: str, *, paths: WorkspacePaths | None = None) -> float:
    """Agreement expected by chance on base-row ``status`` (the ``p_e`` of Cohen's kappa).

    Sum over labels of the product of the two annotators' proportions. When one annotator
    uses a single label for every row, this equals the observed agreement and kappa is 0.
    """
    (a, b), base, _ = _split(series_id, paths)
    if not base:
        return math.nan
    counts_a = Counter(r[f"{a}_status"] for r in base)
    counts_b = Counter(r[f"{b}_status"] for r in base)
    n = len(base)
    return sum(counts_a[label] * counts_b[label] for label in counts_a) / (n * n)


def final_status_counts(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> FinalStatusCounts:
    """Final status counts, base rows and compuesta children kept apart."""
    _, base, children = _split(series_id, paths)
    return FinalStatusCounts(
        base=dict(sorted(Counter(r["final_status"] for r in base).items())),
        children=dict(sorted(Counter(r["final_status"] for r in children).items())),
    )


def _sided_with(final: str, labels: Mapping[str, str]) -> str:
    """Which annotators' label the verdict coincides with (``ninguno`` if neither)."""
    matches = [ini for ini, label in labels.items() if label and label == final]
    return "+".join(matches) if matches else "ninguno"


def resolved_disagreements(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> list[dict[str, str]]:
    """Base rows with ``acuerdo = no``: both labels, the verdict, the side taken and ``razon``."""
    (a, b), base, _ = _split(series_id, paths)
    return [
        {
            "decision_id": r["decision_id"],
            f"{a}_status": r[f"{a}_status"],
            f"{b}_status": r[f"{b}_status"],
            "final_status": r["final_status"],
            "sided_with": _sided_with(
                r["final_status"], {a: r[f"{a}_status"], b: r[f"{b}_status"]}
            ),
            "razon": r["razon"],
        }
        for r in base
        if r["acuerdo"] == _NO
    ]


def disagreement_groups(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> dict[tuple[str, str], list[dict[str, str]]]:
    """Base-row disagreements grouped by ``(status_a, status_b)``, with the sentence.

    Same rows as :func:`resolved_disagreements` (``acuerdo = no``) plus ``sentence_text``,
    keyed by the pair of statuses in annotator order (``a`` is the alphabetically first
    initials, as everywhere in this module). Keys and rows keep file order within a group;
    groups are sorted by key. Used to prepare the joint criteria session.
    """
    (a, b), base, _ = _split(series_id, paths)
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row, resolved in zip(
        (r for r in base if r["acuerdo"] == _NO),
        resolved_disagreements(series_id, paths=paths),
        strict=True,
    ):
        key = (row[f"{a}_status"], row[f"{b}_status"])
        groups.setdefault(key, []).append(
            {**resolved, "sentence_text": row.get("sentence_text", "")}
        )
    return dict(sorted(groups.items()))


def side_taken_counts(series_id: str, *, paths: WorkspacePaths | None = None) -> dict[str, int]:
    """How many resolved decision disagreements the verdict took from each side."""
    rows = resolved_disagreements(series_id, paths=paths)
    return dict(sorted(Counter(r["sided_with"] for r in rows).items()))


def _final_row(row: Mapping[str, str], ids: set[str]) -> dict[str, str]:
    parent = _parent_decision_id(row["decision_id"])
    return {
        "decision_id": row["decision_id"],
        "parent_id": parent if parent in ids and parent != row["decision_id"] else "",
        "final_status": row["final_status"],
        "final_object": row["final_object"],
        "final_content": row["final_content"],
        "razon": row["razon"],
    }


def compuesta_children(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> list[dict[str, str]]:
    """Rows the adjudicator created under a ``compuesta`` verdict, with their parent id."""
    _, rows = _load(series_id, TaskKind.DECISIONS, paths)
    ids = {r["decision_id"] for r in rows}
    return [_final_row(r, ids) for r in rows if _is_child(r, ids)]


def final_rows(
    series_id: str, status: str, *, paths: WorkspacePaths | None = None
) -> list[dict[str, str]]:
    """Every adjudicated row (base or child) whose ``final_status`` is ``status``."""
    _, rows = _load(series_id, TaskKind.DECISIONS, paths)
    ids = {r["decision_id"] for r in rows}
    return [
        {**_final_row(r, ids), "sentence_text": r.get("sentence_text", "")}
        for r in rows
        if r["final_status"] == status
    ]


def adjudicated_pairs(
    series_id: str, *, paths: WorkspacePaths | None = None
) -> list[dict[str, str]]:
    """One record per candidate pair: both relation labels, the verdict and the side taken."""
    header, rows = _load(series_id, TaskKind.CANDIDATES, paths)
    a, b = _annotators(header, _RELATION_SUFFIX)
    return [
        {
            "pair_id": r["pair_id"],
            "earlier_decision_id": r["earlier_decision_id"],
            "later_decision_id": r["later_decision_id"],
            f"{a}_relation": r[f"{a}_relation"],
            f"{b}_relation": r[f"{b}_relation"],
            "acuerdo": r["acuerdo"],
            "final_relation": r["final_relation"],
            "sided_with": _sided_with(
                r["final_relation"], {a: r[f"{a}_relation"], b: r[f"{b}_relation"]}
            ),
            "razon": r["razon"],
        }
        for r in rows
    ]
