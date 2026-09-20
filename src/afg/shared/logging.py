"""Rich-backed logging setup, shared by the CLI and library code."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with a single Rich handler.

    Idempotent: calling this more than once (e.g. once from the CLI entry point and again
    from a test fixture) never duplicates handlers.
    """
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED:
        root.setLevel(level.upper())
        return

    root.setLevel(level.upper())
    handler = RichHandler(rich_tracebacks=True, show_path=False)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger. Call :func:`configure_logging` once beforehand."""
    return logging.getLogger(name)
