"""A fake Experiment A workspace for the relation-scoring tests: two decisions and a findings.db.

``<root>/<SERIES>/run-<r>/bundle/decisions/{alpha,beta}.md`` (alpha from meeting a, beta from
meeting b) plus frozen transcripts holding their evidence quotes.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from afg.domain.decision import EvidenceSpan
from afg.evaluation.reference import ReferenceDecision
from tests.openkos_bundle import decision_file, write_decision, write_meeting
from tests.openkos_findings import Row, write_findings_db

ALPHA = ("remote battery", "The remote uses a kinetic battery.")
BETA = ("remote case", "The remote case is made of rubber.")


def write_transcripts(transcripts: Path, series: str = "ES2015") -> None:
    write_meeting(
        transcripts, f"{series}a", [("ID", "We use the kinetic battery for the remote.", ("a1",))]
    )
    write_meeting(transcripts, f"{series}b", [("ID", "The case will be made of rubber.", ("b1",))])
    write_meeting(transcripts, f"{series}c", [("PM", "Nothing.", ("c1",))])
    write_meeting(transcripts, f"{series}d", [("PM", "Nothing.", ("d1",))])


def write_workspace(
    root: Path,
    series: str = "ES2015",
    run: int = 0,
    findings: Sequence[Row] | None = (),
) -> Path:
    """Write the bundle of one run; ``findings=None`` leaves out ``findings.db``."""
    workspace = root / series / f"run-{run}"
    bundle = workspace / "bundle"
    write_decision(
        bundle,
        "alpha",
        decision_file(
            title="Kinetic battery",
            subject=ALPHA[0],
            value=ALPHA[1],
            quotes=[(f"{series.lower()}a", "We use the kinetic battery for the remote.")],
        ),
    )
    write_decision(
        bundle,
        "beta",
        decision_file(
            title="Rubber case",
            subject=BETA[0],
            value=BETA[1],
            quotes=[(f"{series.lower()}b", "The case will be made of rubber.")],
        ),
    )
    if findings is not None:
        write_findings_db(workspace, findings)
    return workspace


def reference_decision(decision_id: str, meeting: str, obj: str, content: str) -> ReferenceDecision:
    return ReferenceDecision(
        decision_id=decision_id,
        series_id=meeting[:-1],
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=("x1",)),
        evidence_method="sentence_id",
        role=None,
    )


def text_similarity(predicted: Sequence[str], reference: Sequence[str]):  # type: ignore[no-untyped-def]
    """1.0 for identical texts, 0.0 otherwise."""
    return [[1.0 if p == r else 0.0 for r in reference] for p in predicted]
