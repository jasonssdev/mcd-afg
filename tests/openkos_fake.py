"""A scripted stand-in for the OpenKOS command line, shared by the adapter tests."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from afg.extraction.openkos.commands import CommandResult

INGEST_HELP = "Usage: openkos ingest [OPTIONS] SOURCE\n  --auto\n  --event-date TEXT\n"
QUERY_HELP = "Usage: openkos query [OPTIONS] QUESTION\n  --limit INTEGER\n  --json\n"
CONFIG_TEMPLATE = (
    "model: qwen3:8b\n"
    "embedding_model: bge-m3\n"
    "review: true\n"
    "# seed: 42\n"
    "# temperature: 0.1\n"
    "# transcript_decisions: true\n"
)

Handler = Callable[[Sequence[str], Path | None], CommandResult | None]


def ok(stdout: str = "", returncode: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult(returncode=returncode, stdout=stdout, stderr=stderr, duration_s=0.01)


@dataclass
class FakeRunner:
    """Answers OpenKOS subcommands from a script and records every call.

    ``init`` writes ``config_template`` into the working directory, like the real command.
    ``ingest_codes`` maps a source file name to the exit codes to return in order.
    """

    version_output: str = "openkos 0.6.0\n"
    ingest_help: str = INGEST_HELP
    query_help: str = QUERY_HELP
    config_template: str = CONFIG_TEMPLATE
    ingest_codes: dict[str, list[int]] = field(default_factory=dict)
    init_code: int = 0
    reindex_code: int = 0
    calls: list[tuple[tuple[str, ...], Path | None]] = field(default_factory=list)

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        argv = tuple(args)
        self.calls.append((argv, cwd))
        rest = argv[1:]
        if rest == ("--version",):
            return ok(self.version_output)
        if rest == ("ingest", "--help"):
            return ok(self.ingest_help)
        if rest == ("query", "--help"):
            return ok(self.query_help)
        if rest[:1] == ("init",):
            if self.init_code == 0 and cwd is not None:
                (cwd / "openkos.yaml").write_text(self.config_template, encoding="utf-8")
            return ok(returncode=self.init_code, stderr="init failed" if self.init_code else "")
        if rest[:1] == ("reindex",):
            return ok(
                returncode=self.reindex_code, stderr="reindex failed" if self.reindex_code else ""
            )
        if rest[:1] == ("ingest",):
            name = Path(rest[1]).name
            codes = self.ingest_codes.get(name)
            code = codes.pop(0) if codes else 0
            return ok(returncode=code, stderr="boom" if code else "")
        return ok(returncode=2, stderr=f"unexpected command: {argv}")

    def subcommands(self) -> list[tuple[str, ...]]:
        return [argv[1:] for argv, _ in self.calls]
