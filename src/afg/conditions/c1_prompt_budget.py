"""Context-window budgeting for C1, ported from OpenKOS v0.5.4 (ADR 0006).

``openkos query`` plans its prompt against the context window it will send to Ollama: the
retrieved bodies share ``(window - reply reserve) / TOKENS_PER_CHAR - overhead`` characters
and the ones that do not fit are excerpted (``src/openkos/prompt_budget.py``, issue #882).
C1 must do the same or it would send the model a different amount of text than C2 and C3
read. This is a line-for-line port of the pure functions OpenKOS uses (``budget_chars``,
``chunk_lines``, ``bounded_text``, ``fair_shares``); nothing is imported from OpenKOS and the
semantics are not changed. OpenKOS's ``nested_shares`` (revision history) is not ported: it
only runs when ``revision_history`` is on, which is off by default and in the experiment.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

# openkos.prompt_budget.TOKENS_PER_CHAR: deliberately pessimistic chars-to-tokens ratio.
TOKENS_PER_CHAR: Final = 0.40

# openkos.prompt_budget.ELISION_MARKER: rendered between non-adjacent windows of an excerpt.
ELISION_MARKER: Final = "\n[... source elided to fit the context window ...]\n"

# openkos.retrieval.answer._CONTEXT_CHUNK_TARGET: window size an excerpted block is cut into.
CONTEXT_CHUNK_TARGET: Final = 800


def budget_chars(*, planning: int, generation_reserve_tokens: int, overhead_chars: int) -> int:
    """Characters available for the bounded text (``prompt_budget.budget_chars``)."""
    budget = int((planning - generation_reserve_tokens) / TOKENS_PER_CHAR) - overhead_chars
    return max(budget, 0)


def chunk_lines(text: str, target: int) -> list[str]:
    """Pack lines into windows of at most ``target`` chars, never splitting a line.

    Lossless: ``"\\n".join(chunk_lines(text, n)) == text``.
    """
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.split("\n"):
        if current and size + len(line) + 1 > target:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def bounded_text(
    text: str,
    *,
    budget: int,
    windows: Sequence[str],
    marker: str = ELISION_MARKER,
) -> tuple[str, bool]:
    """``text`` if it fits ``budget``, else an even-coverage excerpt of ``windows``.

    Returns the text and whether it was excerpted. A fitting text is returned byte-identical.
    """
    if len(text) <= budget:
        return text, False
    if not windows:
        return "", True

    total_windows = len(windows)
    for count in range(total_windows - 1, 1, -1):
        picked = sorted({round(i * (total_windows - 1) / (count - 1)) for i in range(count)})
        size = sum(len(windows[index]) for index in picked)
        for position, index in enumerate(picked[1:], start=1):
            adjacent = index == picked[position - 1] + 1
            size += 1 if adjacent else len(marker)
        if size > budget:
            continue
        parts: list[str] = []
        previous: int | None = None
        for index in picked:
            if previous is not None:
                parts.append(marker if index > previous + 1 else "\n")
            parts.append(windows[index])
            previous = index
        return "".join(parts), True
    return windows[0][:budget], True


def _remainder_order(sizes: Sequence[int], open_indexes: list[int]) -> list[int]:
    """Largest need first, ties by lowest index (keeps ``fair_shares`` order-independent)."""
    return sorted(open_indexes, key=lambda index: (-sizes[index], index))


def fair_shares(sizes: Sequence[int], *, budget: int) -> list[int]:
    """Water-filling split of a shared ``budget`` across blocks of the given ``sizes``."""
    if not sizes:
        return []
    shares = [0] * len(sizes)
    settled = [False] * len(sizes)
    remaining = max(budget, 0)
    while True:
        open_indexes = [i for i, done in enumerate(settled) if not done]
        if not open_indexes or remaining <= 0:
            break
        share = remaining // len(open_indexes)
        if share <= 0:
            for index in _remainder_order(sizes, open_indexes):
                if remaining <= 0:
                    break
                if sizes[index] <= shares[index]:
                    continue
                shares[index] += 1
                remaining -= 1
            break
        released = False
        for index in open_indexes:
            if sizes[index] <= share:
                shares[index] = sizes[index]
                settled[index] = True
                remaining -= sizes[index]
                released = True
        if not released:
            for index in open_indexes:
                shares[index] = share
                remaining -= share
            for index in _remainder_order(sizes, open_indexes)[:remaining]:
                shares[index] += 1
            break
    return shares
