"""Tests for the token-based cost of a hosted run (ADR 0026, second amendment, decision 5)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from afg.experiments.hosted_cost import (
    MeetingTokens,
    meeting_cost_usd,
    summarize_cost,
    summarize_tokens,
)
from afg.experiments.hosted_extraction import (
    HostedConfigError,
    ModelPrice,
    load_hosted_config,
)
from afg.extraction.openkos.tokens import TokenUsage

PRICE = ModelPrice(
    input_usd_per_mtok=2.0,
    output_usd_per_mtok=10.0,
    prices_date="2026-11-26",
    pricing_url="https://example.test/pricing",
)


def _tokens(*usages: TokenUsage) -> MeetingTokens:
    meeting = MeetingTokens()
    for usage in usages:
        meeting.add(usage)
    return meeting


def test_meeting_tokens_sum_every_ingest_command_of_a_meeting() -> None:
    meeting = _tokens(TokenUsage(2, 2, 100, 20, 130), TokenUsage(1, 1, 50, 10, 60))
    assert (meeting.calls, meeting.reported_calls) == (3, 3)
    assert (meeting.prompt, meeting.completion, meeting.total) == (150, 30, 190)
    assert not meeting.lower_bound


def test_the_cost_charges_hidden_reasoning_as_output() -> None:
    # prompt 1M at $2, (total - prompt) = 500k at $10 even though completion says only 100k.
    meeting = _tokens(TokenUsage(3, 3, 1_000_000, 100_000, 1_500_000))
    assert meeting_cost_usd(meeting, PRICE) == pytest.approx(2.0 + 5.0)


def test_a_partial_or_unreported_call_makes_the_meeting_a_lower_bound() -> None:
    partial = _tokens(TokenUsage(4, 3, 10, 5, 15))
    silent = _tokens(TokenUsage(2, 0, None, None, None))
    assert partial.lower_bound and silent.lower_bound
    assert (silent.prompt, silent.total) == (0, 0)
    assert meeting_cost_usd(silent, PRICE) == 0.0  # known tokens only; flagged as lower bound


def test_tokens_summary_gives_totals_and_the_median_per_meeting() -> None:
    meetings = [
        _tokens(TokenUsage(1, 1, 10, 5, 15)),
        _tokens(TokenUsage(1, 1, 20, 5, 25)),
        _tokens(TokenUsage(1, 1, 30, 5, 35)),
    ]
    summary = summarize_tokens(meetings)
    assert summary == {
        "n_meetings": 3,
        "calls": 3,
        "reported_calls": 3,
        "prompt": 60,
        "completion": 15,
        "total": 75,
        "median_total_per_meeting": 25,
        "lower_bound": False,
    }


def test_no_token_data_gives_no_summary() -> None:
    assert summarize_tokens([]) is None


def test_cost_summary_is_pending_without_a_price_never_zero() -> None:
    meetings = [_tokens(TokenUsage(1, 1, 10, 5, 15))]
    cost = summarize_cost(meetings, None)
    assert cost["status"] == "pendiente"
    assert cost["total_usd"] is None and cost["median_per_meeting_usd"] is None
    assert cost["prices"] is None


def test_cost_summary_without_tokens_has_no_data_never_zero() -> None:
    cost = summarize_cost([], PRICE)
    assert cost["status"] == "sin datos"
    assert cost["total_usd"] is None


def test_cost_summary_sums_the_run_and_takes_the_median_per_meeting() -> None:
    meetings = [
        _tokens(TokenUsage(1, 1, 1_000_000, 0, 1_000_000)),  # $2
        _tokens(TokenUsage(1, 1, 1_000_000, 100_000, 1_100_000)),  # $3
        _tokens(TokenUsage(1, 1, 1_000_000, 200_000, 1_200_000)),  # $4
    ]
    cost = summarize_cost(meetings, PRICE)
    assert cost["status"] == "ok"
    assert cost["total_usd"] == pytest.approx(9.0)
    assert cost["median_per_meeting_usd"] == pytest.approx(3.0)
    assert cost["lower_bound"] is False
    assert cost["n_lower_bound_meetings"] == 0
    assert cost["prices"] == {
        "input_usd_per_mtok": 2.0,
        "output_usd_per_mtok": 10.0,
        "prices_date": "2026-11-26",
        "pricing_url": "https://example.test/pricing",
    }


def test_one_partial_meeting_flags_the_whole_run_as_a_lower_bound() -> None:
    meetings = [
        _tokens(TokenUsage(1, 1, 1_000_000, 0, 1_000_000)),
        _tokens(TokenUsage(2, 1, 1_000_000, 0, 1_000_000)),
    ]
    cost = summarize_cost(meetings, PRICE)
    assert cost["lower_bound"] is True
    assert cost["n_lower_bound_meetings"] == 1


# --- the price table of the configuration ------------------------------------------------------


OFFICIAL_PRICING_HOSTS = (
    "https://developers.openai.com/",
    "https://platform.claude.com/",
    "https://aistudio.google.com/",
)


def test_the_shipped_config_prices_every_model_with_a_date_and_an_official_source() -> None:
    config = load_hosted_config()
    assert set(config.prices) == set(config.models)
    for label, price in config.prices.items():
        assert price.prices_date == "2026-11-26", label
        assert price.pricing_url.startswith(OFFICIAL_PRICING_HOSTS), label


def _without_price_tables(text: str) -> str:
    kept: list[str] = []
    skipping = False
    for line in text.splitlines():
        if line.startswith("["):
            skipping = line.startswith("[prices.")
        if not skipping:
            kept.append(line)
    return "\n".join(kept) + "\n"


def _config_with(tmp_path: Path, extra: str) -> Path:
    base = _without_price_tables(Path("config/hosted_extraction.toml").read_text(encoding="utf-8"))
    path = tmp_path / "hosted.toml"
    path.write_text(base + "\n" + textwrap.dedent(extra), encoding="utf-8")
    return path


def test_a_price_table_entry_is_read_per_model(tmp_path: Path) -> None:
    path = _config_with(
        tmp_path,
        """
        [prices.openai-small]
        input_usd_per_mtok = 0.25
        output_usd_per_mtok = 2.0
        prices_date = "2026-11-26"
        pricing_url = "https://example.test/pricing"
        """,
    )
    config = load_hosted_config(path)
    assert config.prices["openai-small"] == ModelPrice(
        0.25, 2.0, "2026-11-26", "https://example.test/pricing"
    )


@pytest.mark.parametrize(
    "body",
    [
        'input_usd_per_mtok = 1.0\nprices_date = "d"\npricing_url = "u"',  # no output price
        'input_usd_per_mtok = -1.0\noutput_usd_per_mtok = 1.0\nprices_date = "d"\n'
        'pricing_url = "u"',  # negative
        "input_usd_per_mtok = 1.0\noutput_usd_per_mtok = 1.0",  # no date or source
    ],
)
def test_an_incomplete_or_negative_price_is_rejected(tmp_path: Path, body: str) -> None:
    path = _config_with(tmp_path, f"[prices.openai-small]\n{body}\n")
    with pytest.raises(HostedConfigError, match="openai-small"):
        load_hosted_config(path)


def test_a_price_for_an_unknown_model_is_rejected(tmp_path: Path) -> None:
    path = _config_with(
        tmp_path,
        """
        [prices.no-such-model]
        input_usd_per_mtok = 1.0
        output_usd_per_mtok = 1.0
        prices_date = "d"
        pricing_url = "u"
        """,
    )
    with pytest.raises(HostedConfigError, match="no-such-model"):
        load_hosted_config(path)
