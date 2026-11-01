"""C3 -- structured base built from human gold annotation (thesis section 5.3).

The upper reference: identical to C2 except the decisions come from the OE1 annotation rather
than from automatic extraction. Thesis section 3 (OE3): explicitly NOT called a "theoretical
ceiling" -- a human annotation with measured reliability is a reference, not a demonstrable
upper bound, especially given the negative-kappa precedent (thesis section 1.4).

C3 is C2 pointed at another set of workspaces. ``afg c3 build`` writes, for every run ``r`` of an
Experiment A run, a copy of the C2 workspace ``run-r`` whose ``bundle/decisions/`` holds the gold
decisions (ADR 0013, :mod:`afg.extraction.openkos.gold_bundle`), indexed again. Everything else
-- the ``openkos query`` call, the seed and temperature checks, the mapping of citations to
dialogue acts -- is the code of C2, so a difference between the two conditions comes from the
decisions alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from afg.conditions.c2_compiled_auto import CompiledAutoCondition
from afg.extraction.openkos_adapter import project_relative
from afg.shared.paths import OPENKOS_C3_WORKSPACES_DIR


@dataclass(slots=True)
class CompiledGoldCondition(CompiledAutoCondition):
    """C3: query the gold-decision workspaces that ``afg c3 build`` derived from a C2 run.

    ``extraction_run`` is the ``--run-name`` of the Experiment A run the workspaces derive from.
    """

    base_dir: Path = OPENKOS_C3_WORKSPACES_DIR
    condition_id: str = "C3"

    def _missing_workspace_message(self, series_id: str, run: int, workspace: Path) -> str:
        return (
            f"No C3 workspace for {series_id} run-{run} derived from the Experiment A run "
            f"{self.extraction_run!r} ({project_relative(workspace)}). Run "
            f"`afg c3 build --c2-extraction {self.extraction_run} --series {series_id}` "
            "with enough runs first."
        )
