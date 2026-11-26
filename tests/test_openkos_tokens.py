"""Tests for the ``tokens:`` line parser of ``openkos ingest`` (OpenKOS 0.7.3); no model calls."""

from __future__ import annotations

import pytest

from afg.extraction.openkos.tokens import TokenUsage, parse_token_usage


def test_a_full_report_gives_every_count() -> None:
    out = "wrote 3 objects\n  tokens: 14 calls, prompt 52310, completion 9120, total 61430\n"
    assert parse_token_usage(out) == TokenUsage(
        calls=14, reported_calls=14, prompt=52310, completion=9120, total=61430
    )


def test_a_single_call_uses_the_singular() -> None:
    out = "  tokens: 1 call, prompt 10, completion 5, total 15\n"
    assert parse_token_usage(out) == TokenUsage(1, 1, 10, 5, 15)


def test_a_partial_report_keeps_the_reported_calls() -> None:
    out = "  tokens: 12 of 14 calls reported, prompt 100, completion 40, total 140\n"
    assert parse_token_usage(out) == TokenUsage(
        calls=14, reported_calls=12, prompt=100, completion=40, total=140
    )


def test_a_backend_that_reports_nothing_has_no_counts() -> None:
    out = "  tokens: not reported by the backend (14 calls)\n"
    assert parse_token_usage(out) == TokenUsage(
        calls=14, reported_calls=0, prompt=None, completion=None, total=None
    )


def test_a_single_unreported_call_uses_the_singular() -> None:
    out = "  tokens: not reported by the backend (1 call)\n"
    assert parse_token_usage(out) == TokenUsage(1, 0, None, None, None)


@pytest.mark.parametrize("out", ["", "wrote 3 objects\n", "tokens-ish: nothing\n"])
def test_no_line_means_no_chat_call(out: str) -> None:
    assert parse_token_usage(out) is None


def test_the_record_serialises_to_plain_json_values() -> None:
    usage = TokenUsage(2, 2, 7, 3, 10)
    assert usage.as_dict() == {
        "calls": 2,
        "reported_calls": 2,
        "prompt": 7,
        "completion": 3,
        "total": 10,
    }
    assert TokenUsage.from_dict(usage.as_dict()) == usage
