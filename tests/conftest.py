"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator

import numpy as np
import pytest

# Rich wraps CLI output at the console width it detects (``COLUMNS`` wins over the terminal).
# GitHub Actions runners report about 100 columns, which splits long file paths in the middle
# of their name and broke tests that look for ``ES2015.candidates.gv.csv`` in the output;
# locally, with no terminal, Rich falls back to 80 and the breaks happen to land elsewhere.
# A fixed, wide console makes the tests assert on content, never on where a line wrapped.
os.environ["COLUMNS"] = "200"


@pytest.fixture
def rng() -> Iterator[np.random.Generator]:
    yield np.random.default_rng(seed=42)
