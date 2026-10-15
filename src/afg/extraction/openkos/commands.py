"""The seam between this project and the ``openkos`` executable.

Everything that spawns a process goes through :class:`CommandRunner`, so the orchestrator
and the capability probe are tested with a scripted fake and never need OpenKOS installed.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class OpenKosError(RuntimeError):
    """Base class of every failure raised while driving OpenKOS."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """What one command produced."""

    returncode: int
    stdout: str
    stderr: str
    duration_s: float


class CommandRunner(Protocol):
    """Runs one command and returns its result; never raises on a non-zero exit."""

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        """Run ``args`` (``args[0]`` is the executable) with ``cwd`` as working directory.

        Raises:
            FileNotFoundError: when the executable does not exist.
        """
        ...


class SubprocessRunner:
    """:class:`CommandRunner` backed by :func:`subprocess.run` (no shell, text output)."""

    def run(self, args: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
        started = time.monotonic()
        completed = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=False)
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_s=time.monotonic() - started,
        )
