"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest


@pytest.fixture
def rng() -> Iterator[np.random.Generator]:
    yield np.random.default_rng(seed=42)
