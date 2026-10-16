"""Markers for tests that need local data that is not versioned (the AMI corpus, transcripts).

``requires(name, available=..., reason=...)`` returns a decorator that tags the test with the
registered marker ``name`` (so ``pytest -m "not requires_corpus"`` deselects it) and skips it
when the data is absent. The skip reason is prefixed with the marker name, so ``pytest -rs``
tells exactly which kind of data is missing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


def requires(name: str, *, available: bool, reason: str) -> Callable[[Any], Any]:
    """Tag with marker ``name`` and skip when ``available`` is false."""
    skip = pytest.mark.skipif(not available, reason=f"{name}: {reason}")
    tag = getattr(pytest.mark, name)

    def decorate(target: Any) -> Any:
        return tag(skip(target))

    return decorate
