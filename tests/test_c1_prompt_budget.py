"""Tests for the OpenKOS v0.5.4 prompt-budget port used by C1 (ADR 0006)."""

from __future__ import annotations

import pytest

from afg.conditions.c1_prompt_budget import (
    ELISION_MARKER,
    bounded_text,
    budget_chars,
    chunk_lines,
    fair_shares,
)


def test_budget_chars_converts_the_free_tokens_and_subtracts_the_overhead() -> None:
    # (12288 - 8192) tokens / 0.40 tokens-per-char = 10240 chars, minus the overhead.
    assert budget_chars(planning=12288, generation_reserve_tokens=8192, overhead_chars=1000) == 9240


def test_budget_chars_floors_at_zero() -> None:
    assert budget_chars(planning=12288, generation_reserve_tokens=8192, overhead_chars=99999) == 0
    assert budget_chars(planning=100, generation_reserve_tokens=8192, overhead_chars=0) == 0


def test_chunk_lines_is_lossless_and_never_splits_a_line() -> None:
    text = "aaaa\nbbbb\ncccc\n\ndddd"
    windows = chunk_lines(text, 10)
    assert "\n".join(windows) == text
    assert windows == ["aaaa\nbbbb", "cccc\n", "dddd"]


def test_fair_shares_releases_what_small_blocks_do_not_need() -> None:
    assert fair_shares([5, 500, 500], budget=105) == [5, 50, 50]


def test_fair_shares_never_exceeds_the_budget_or_a_block() -> None:
    shares = fair_shares([7, 9, 100], budget=11)
    assert sum(shares) <= 11
    assert all(s <= size for s, size in zip(shares, [7, 9, 100], strict=True))


def test_fair_shares_is_order_independent() -> None:
    forward = fair_shares([7, 9, 100], budget=11)
    backward = fair_shares([100, 9, 7], budget=11)
    assert sorted(forward) == sorted(backward)


def test_fair_shares_skips_empty_blocks_when_chars_are_scarce() -> None:
    assert fair_shares([0, 100], budget=1) == [0, 1]


def test_fair_shares_of_nothing_is_empty() -> None:
    assert fair_shares([], budget=10) == []


def test_bounded_text_returns_a_fitting_text_untouched() -> None:
    assert bounded_text("abc", budget=3, windows=["abc"]) == ("abc", False)


def test_bounded_text_keeps_first_and_last_window_with_a_marker() -> None:
    windows = ["aaaa", "bbbb", "cccc", "dddd"]
    text = "\n".join(windows)
    assert bounded_text(text, budget=10, windows=windows, marker="~") == ("aaaa~dddd", True)


def test_bounded_text_hard_truncates_the_first_window_as_a_last_resort() -> None:
    windows = ["aaaaaaaaaa", "bbbbbbbbbb"]
    assert bounded_text("\n".join(windows), budget=4, windows=windows) == ("aaaa", True)


def test_bounded_text_is_empty_when_there_is_no_budget() -> None:
    windows = ["aaaa", "bbbb"]
    assert bounded_text("\n".join(windows), budget=0, windows=windows) == ("", True)


def test_default_marker_is_the_openkos_one() -> None:
    assert ELISION_MARKER == "\n[... source elided to fit the context window ...]\n"


@pytest.mark.parametrize("target", [1, 5, 50])
def test_chunk_lines_roundtrip_for_any_target(target: int) -> None:
    text = "one\ntwo two\nthree three three"
    assert "\n".join(chunk_lines(text, target)) == text
