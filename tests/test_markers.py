"""The ``requires_*`` markers: registered, selectable with ``-m`` and explicit when skipped."""

from __future__ import annotations

import tomllib
from typing import Any

from afg.shared.paths import PROJECT_ROOT
from tests.markers import requires


def _marks(obj: Any) -> dict[str, Any]:
    return {mark.name: mark for mark in obj.pytestmark}


def test_requires_adds_a_selectable_marker_and_a_skip_with_the_reason() -> None:
    @requires("requires_corpus", available=False, reason="needs the AMI corpus")
    def sample() -> None: ...

    marks = _marks(sample)
    assert "requires_corpus" in marks
    assert marks["skipif"].args == (True,)
    assert marks["skipif"].kwargs["reason"] == "requires_corpus: needs the AMI corpus"


def test_requires_does_not_skip_when_available() -> None:
    @requires("requires_corpus", available=True, reason="needs the AMI corpus")
    def sample() -> None: ...

    assert _marks(sample)["skipif"].args == (False,)


def test_every_requires_marker_is_registered_in_pyproject() -> None:
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    registered = {
        m.split(":")[0].strip() for m in config["tool"]["pytest"]["ini_options"]["markers"]
    }
    assert {"requires_corpus", "requires_meetings_xml", "requires_data"} <= registered
