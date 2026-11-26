"""Parse the ``tokens:`` line that ``openkos ingest`` prints from OpenKOS 0.7.3 on.

The line appears on stdout on every way out of an ingest (written, source-only, refused) when at
least one chat call happened, and is absent when there were none. Three formats exist::

    tokens: 14 calls, prompt 52310, completion 9120, total 61430
    tokens: 12 of 14 calls reported, prompt P, completion C, total T
    tokens: not reported by the backend (14 calls)

``1 call`` is the singular. The total is the provider's, so it may exceed prompt + completion
(hidden reasoning tokens that are billed as output).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = ["TokenUsage", "parse_token_usage"]

_COUNTS = r"prompt (\d+), completion (\d+), total (\d+)"
_FULL = re.compile(rf"^\s*tokens: (\d+) calls?, {_COUNTS}\s*$", re.MULTILINE)
_PARTIAL = re.compile(rf"^\s*tokens: (\d+) of (\d+) calls? reported, {_COUNTS}\s*$", re.MULTILINE)
_NONE = re.compile(r"^\s*tokens: not reported by the backend \((\d+) calls?\)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Chat calls of one ingest command and the tokens they reported.

    ``reported_calls < calls`` means the counts are a lower bound; the counts are ``None`` when
    the backend reported nothing.
    """

    calls: int
    reported_calls: int
    prompt: int | None
    completion: int | None
    total: int | None

    def as_dict(self) -> dict[str, int | None]:
        return {
            "calls": self.calls,
            "reported_calls": self.reported_calls,
            "prompt": self.prompt,
            "completion": self.completion,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TokenUsage:
        return cls(
            calls=int(raw["calls"]),
            reported_calls=int(raw["reported_calls"]),
            prompt=None if raw.get("prompt") is None else int(raw["prompt"]),
            completion=None if raw.get("completion") is None else int(raw["completion"]),
            total=None if raw.get("total") is None else int(raw["total"]),
        )


def parse_token_usage(stdout: str) -> TokenUsage | None:
    """The token record of an ingest's stdout, or ``None`` when it has no ``tokens:`` line."""
    if (match := _FULL.search(stdout)) is not None:
        calls, prompt, completion, total = (int(g) for g in match.groups())
        return TokenUsage(calls, calls, prompt, completion, total)
    if (match := _PARTIAL.search(stdout)) is not None:
        reported, calls, prompt, completion, total = (int(g) for g in match.groups())
        return TokenUsage(calls, reported, prompt, completion, total)
    if (match := _NONE.search(stdout)) is not None:
        return TokenUsage(int(match.group(1)), 0, None, None, None)
    return None
