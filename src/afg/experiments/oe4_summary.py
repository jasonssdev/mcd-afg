"""Summary of the human stage labels of an OE4 worksheet (issue #244).

The worksheet written by :func:`~afg.experiments.c2_base_evidence.write_oe4_worksheet` has one
row per failure and a ``etapa_humana`` column a person fills (CONTRIBUTING 7.6). This module
only reads and counts: per stage, with how often the person disagrees with the stage the
automatic hint (``pista_automatica``) points at. It never writes a label and calls no model.
The sheet carries no condition column; the caller names the condition (the run manifest).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from afg.experiments.c2_base_evidence import (
    ETAPA_VALUES,
    HINT_ALL_TERMS_RETRIEVED,
    HINT_ALL_TERMS_UNRETRIEVED,
    HINT_NO_TERMS,
    HINT_ONLY_RAW_SOURCE,
    count_stages,
    stage_shares,
    suggested_stage,
)

OE4_SUMMARY_FILE = "oe4-resumen.json"
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Disagreement:
    """A row where the human stage differs from the stage the automatic hint points at."""

    question_id: str
    rule_stage: str
    human_stage: str


@dataclass(frozen=True, slots=True)
class Oe4Summary:
    """Human stage labels of one condition's worksheet."""

    condition: str
    n_failures: int
    stages: dict[str, int]
    shares: dict[str, float]
    with_suggestion: int
    agree: int
    disagree: int
    disagreements: tuple[Disagreement, ...]

    @property
    def without_suggestion(self) -> int:
        return self.n_failures - self.with_suggestion

    @property
    def agreement_rate(self) -> float | None:
        """Share of the rows with a suggestion where the person agreed; ``None`` with none."""
        return self.agree / self.with_suggestion if self.with_suggestion else None

    def to_record(self, *, run_name: str, sheet: str) -> dict[str, Any]:
        """The JSON-ready dict written to the run folder."""
        return {
            "schema_version": SCHEMA_VERSION,
            "run_name": run_name,
            "condition": self.condition,
            "sheet": sheet,
            "n_failures": self.n_failures,
            "stages": {s: {"cases": self.stages[s], "share": self.shares[s]} for s in self.stages},
            "rule_agreement": {
                "with_suggestion": self.with_suggestion,
                "without_suggestion": self.without_suggestion,
                "agree": self.agree,
                "disagree": self.disagree,
                "agreement_rate": self.agreement_rate,
            },
            "disagreements": [
                {
                    "question_id": d.question_id,
                    "rule_stage": d.rule_stage,
                    "human_stage": d.human_stage,
                }
                for d in self.disagreements
            ],
        }


def summarize_oe4_sheet(rows: Sequence[Mapping[str, str]], *, condition: str) -> Oe4Summary:
    """Count the human labels per stage and compare them with the automatic hint.

    Raises:
        ValueError: a row has an empty or unknown ``etapa_humana`` (a half-labelled sheet never
            yields a partial figure), or a question appears twice.
    """
    ids = [r["pregunta_id"] for r in rows]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"preguntas duplicadas en la hoja: {', '.join(repeated)}")
    stages = count_stages([], rows)
    shares = stage_shares(stages)["share"]
    disagreements: list[Disagreement] = []
    agree = 0
    for row in rows:
        rule = suggested_stage(row.get("pista_automatica", ""))
        if rule is None:
            continue
        human = row["etapa_humana"].strip()
        if rule == human:
            agree += 1
        else:
            disagreements.append(Disagreement(row["pregunta_id"], rule, human))
    return Oe4Summary(
        condition=condition,
        n_failures=len(rows),
        stages=stages,
        shares={s: float(shares[s]) for s in ETAPA_VALUES},
        with_suggestion=agree + len(disagreements),
        agree=agree,
        disagree=len(disagreements),
        disagreements=tuple(disagreements),
    )


__all__ = [
    "HINT_ALL_TERMS_RETRIEVED",
    "HINT_ALL_TERMS_UNRETRIEVED",
    "HINT_NO_TERMS",
    "HINT_ONLY_RAW_SOURCE",
    "OE4_SUMMARY_FILE",
    "Disagreement",
    "Oe4Summary",
    "suggested_stage",
    "summarize_oe4_sheet",
]
