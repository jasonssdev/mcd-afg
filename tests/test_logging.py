"""Tests for the shared logging helpers."""

from __future__ import annotations

import logging

from afg.shared.logging import quiet_http_logs


def test_http_client_request_logs_are_silenced() -> None:
    logging.getLogger("httpx").setLevel(logging.INFO)
    quiet_http_logs()
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
