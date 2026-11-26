"""Token totals and token-based cost of a hosted run (ADR 0026, second amendment, decision 5).

OpenKOS 0.7.3 prints one ``tokens:`` line per ingest; the workspace manifest keeps it per command
(:mod:`~afg.extraction.openkos.tokens`). A meeting may have more than one ingest command (the
drift retry), so its tokens are the SUM over its commands. Calls of an ingest that failed are
billed too, so every command counts, not only the ones of extracted meetings.

Cost of a meeting = ``prompt * input_price + (total - prompt) * output_price`` (per million
tokens). The provider's ``total`` includes hidden reasoning tokens that ``completion`` may not,
so charging ``total - prompt`` as output bills them. When a call did not report tokens the known
tokens under-count the bill, so the meeting is flagged as a **lower bound**. A missing price or
missing token data gives ``None`` / a non-``ok`` status, never a zero.

The figure is descriptive; the provider dashboard may still be used as a cross-check.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from afg.experiments.hosted_extraction import ModelPrice
from afg.extraction.openkos.tokens import TokenUsage

__all__ = [
    "COST_NO_DATA",
    "COST_OK",
    "COST_PENDING",
    "MeetingTokens",
    "meeting_cost_usd",
    "summarize_cost",
    "summarize_tokens",
]

COST_OK = "ok"
COST_PENDING = "pendiente"  # no price in the configuration yet
COST_NO_DATA = "sin datos"  # no token record in the run (a run of OpenKOS before 0.7.3)
_PER_MILLION = 1_000_000


@dataclass(slots=True)
class MeetingTokens:
    """Tokens of one meeting of one run, summed over its ingest commands.

    The counts add only what was reported; ``lower_bound`` says some call reported nothing.
    """

    calls: int = 0
    reported_calls: int = 0
    prompt: int = 0
    completion: int = 0
    total: int = 0

    def add(self, usage: TokenUsage) -> None:
        self.calls += usage.calls
        self.reported_calls += usage.reported_calls
        self.prompt += usage.prompt or 0
        self.completion += usage.completion or 0
        self.total += usage.total or 0

    @property
    def lower_bound(self) -> bool:
        return self.reported_calls < self.calls


def meeting_cost_usd(meeting: MeetingTokens, price: ModelPrice) -> float:
    """Dollars of one meeting (known tokens only; see ``MeetingTokens.lower_bound``)."""
    return (
        meeting.prompt * price.input_usd_per_mtok
        + (meeting.total - meeting.prompt) * price.output_usd_per_mtok
    ) / _PER_MILLION


def summarize_tokens(meetings: Sequence[MeetingTokens]) -> dict[str, Any] | None:
    """Totals over the meetings of a run and the median total per meeting; ``None`` if no data."""
    if not meetings:
        return None
    return {
        "n_meetings": len(meetings),
        "calls": sum(m.calls for m in meetings),
        "reported_calls": sum(m.reported_calls for m in meetings),
        "prompt": sum(m.prompt for m in meetings),
        "completion": sum(m.completion for m in meetings),
        "total": sum(m.total for m in meetings),
        "median_total_per_meeting": statistics.median(m.total for m in meetings),
        "lower_bound": any(m.lower_bound for m in meetings),
    }


def summarize_cost(meetings: Sequence[MeetingTokens], price: ModelPrice | None) -> dict[str, Any]:
    """Cost of a model's run: total, median per meeting, lower-bound flag and the prices used."""
    result: dict[str, Any] = {
        "status": COST_OK,
        "total_usd": None,
        "median_per_meeting_usd": None,
        "lower_bound": False,
        "n_lower_bound_meetings": 0,
        "prices": None,
    }
    if price is None:
        return {**result, "status": COST_PENDING}
    result["prices"] = {
        "input_usd_per_mtok": price.input_usd_per_mtok,
        "output_usd_per_mtok": price.output_usd_per_mtok,
        "prices_date": price.prices_date,
        "pricing_url": price.pricing_url,
    }
    if not meetings:
        return {**result, "status": COST_NO_DATA}
    costs = [meeting_cost_usd(m, price) for m in meetings]
    flagged = sum(1 for m in meetings if m.lower_bound)
    return {
        **result,
        "total_usd": sum(costs),
        "median_per_meeting_usd": statistics.median(costs),
        "lower_bound": flagged > 0,
        "n_lower_bound_meetings": flagged,
    }
