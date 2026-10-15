"""Probe what the installed ``openkos`` executable supports, without assuming a version.

The OpenKOS version is open (ADR 0006), so capabilities are detected from behaviour, not
from a version threshold:

* ``ingest --auto`` and ``ingest --event-date`` and ``query --json`` are read from the
  ``--help`` text of the corresponding subcommand.
* The decision pass (``transcript_decisions``) is a configuration key, not a flag, so it
  cannot be seen in ``--help``. It is detected on the workspace that ``openkos init``
  generates: the packaged template documents every key the version understands (see
  :func:`afg.extraction.openkos.workspace.require_config_key`).
* The version string is only recorded (provenance), never compared.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from afg.extraction.openkos.commands import CommandRunner, OpenKosError

_VERSION_RE = re.compile(r"^openkos\s+(\S+)", re.MULTILINE)


class MissingCapabilitiesError(OpenKosError):
    """The executable lacks something the adapter needs; ``missing`` names every item."""

    def __init__(self, missing: tuple[str, ...], *, executable: str, version: str | None) -> None:
        self.missing = missing
        self.executable = executable
        self.version = version
        shown = version if version is not None else "unknown version"
        super().__init__(
            f"{executable} ({shown}) is missing required capabilities: {', '.join(missing)}."
        )


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What one ``openkos`` executable offered when probed."""

    executable: str
    version: str | None
    ingest_auto: bool
    ingest_event_date: bool
    query_json: bool


def parse_version(output: str) -> str | None:
    """Return the version in the ``openkos <X>`` banner, or ``None`` if unrecognized."""
    match = _VERSION_RE.search(output.strip())
    return match.group(1) if match else None


def _mentions_flag(help_text: str, flag: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", help_text) is not None


def probe_capabilities(runner: CommandRunner, executable: str) -> Capabilities:
    """Run ``--version``, ``ingest --help`` and ``query --help`` and report what they show.

    Raises:
        MissingCapabilitiesError: if the executable cannot be run at all.
    """
    try:
        version_out = runner.run([executable, "--version"])
        ingest_help = runner.run([executable, "ingest", "--help"])
        query_help = runner.run([executable, "query", "--help"])
    except FileNotFoundError as exc:
        raise MissingCapabilitiesError(
            ("executable",), executable=executable, version=None
        ) from exc
    return Capabilities(
        executable=executable,
        version=parse_version(version_out.stdout) if version_out.returncode == 0 else None,
        ingest_auto=ingest_help.returncode == 0 and _mentions_flag(ingest_help.stdout, "--auto"),
        ingest_event_date=ingest_help.returncode == 0
        and _mentions_flag(ingest_help.stdout, "--event-date"),
        query_json=query_help.returncode == 0 and _mentions_flag(query_help.stdout, "--json"),
    )


def require_capabilities(capabilities: Capabilities, *, need_event_date: bool = False) -> None:
    """Raise :class:`MissingCapabilitiesError` listing everything that is missing."""
    missing: list[str] = []
    if capabilities.version is None:
        missing.append("version")
    if not capabilities.ingest_auto:
        missing.append("ingest --auto")
    if not capabilities.query_json:
        missing.append("query --json")
    if need_event_date and not capabilities.ingest_event_date:
        missing.append("ingest --event-date")
    if missing:
        raise MissingCapabilitiesError(
            tuple(missing), executable=capabilities.executable, version=capabilities.version
        )
