"""Canned ``openkos query --json`` (schema v1) reports and a scripted runner for C2 tests."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from afg.extraction.openkos.commands import CommandResult
from tests.openkos_fake import INGEST_HELP, QUERY_HELP, ok


def query_report(**overrides: Any) -> dict[str, Any]:
    """An ``answered`` schema-v1 report citing one decision; override any top-level key."""
    report: dict[str, Any] = {
        "schema_version": 1,
        "openkos_version": "0.5.5",
        "question": "Which battery?",
        "limit": 5,
        "outcome": "answered",
        "answer": "A kinetic battery.",
        "sufficiency": {
            "enabled": True,
            "invoked": True,
            "refused": False,
            "degraded": False,
            "raw_reply": "YES",
        },
        "attribution": {"status": "reported", "used_indices": [1]},
        "context_blocks": [
            {
                "index": 1,
                "concept_id": "decisions/battery",
                "title": "Kinetic battery",
                "excerpted": False,
                "text": "The remote uses a kinetic battery.",
            }
        ],
        "omitted": [
            {"concept_id": "decisions/other", "title": "Other", "reason": "context_budget"}
        ],
        "retrieved": [
            {
                "rank": 1,
                "concept_id": "decisions/battery",
                "title": "Kinetic battery",
                "fts_rank": 1,
                "dense_rank": None,
                "rrf_score": 0.03,
            }
        ],
        "citations": [
            {"concept_id": "decisions/battery", "title": "Kinetic battery", "excerpted": False}
        ],
        "counts": {"fts_hits": 2, "dense_hits": 1, "fused": 2, "context_blocks": 1},
        "withheld": 0,
        "llm": {
            "backend": "ollama",
            "model": "qwen3:8b",
            "embedding_model": "bge-m3",
            "num_ctx": 12288,
            "num_predict": 8192,
            "temperature": 0.1,
            "seed": 42,
        },
        "prompts": {"system_sha256": "s", "user_sha256": "u", "sufficiency_sha256": "f"},
    }
    report.update(overrides)
    return report


@dataclass
class QueryRunner:
    """Answers ``--version``/help probes and ``query`` calls with canned reports.

    ``reports`` are returned in order (the last one repeats); a ``str`` is returned as raw
    stdout, anything else is JSON encoded.
    """

    reports: list[Any] = field(default_factory=lambda: [query_report()])
    query_help: str = QUERY_HELP
    query_code: int = 0
    query_stderr: str = ""
    calls: list[tuple[tuple[str, ...], Path | None]] = field(default_factory=list)

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        argv = tuple(args)
        self.calls.append((argv, cwd))
        rest = argv[1:]
        if rest == ("--version",):
            return ok("openkos 0.5.5\n")
        if rest == ("ingest", "--help"):
            return ok(INGEST_HELP)
        if rest == ("query", "--help"):
            return ok(self.query_help)
        if rest[:1] == ("query",):
            report = self.reports.pop(0) if len(self.reports) > 1 else self.reports[0]
            stdout = report if isinstance(report, str) else json.dumps(report)
            return ok(stdout, returncode=self.query_code, stderr=self.query_stderr)
        return ok(returncode=2, stderr=f"unexpected command: {argv}")

    def queries(self) -> list[tuple[tuple[str, ...], Path | None]]:
        return [
            call for call in self.calls if call[0][1:2] == ("query",) and "--help" not in call[0]
        ]
