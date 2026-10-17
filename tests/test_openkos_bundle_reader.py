"""Tests for the reader of an OpenKOS bundle's ``decisions/`` folder.

Fixtures are built to match what OpenKOS v0.5.5 writes. Source lines (tag ``v0.5.5``):

* ``src/openkos/extraction/decision_pass.py:184`` ``to_result``: a ``Decision`` candidate with
  description ``<subject>: <value>`` (``:184-193``) and body ``<value>\\n\\n> <evidence>``
  (``compose_body``, ``:160``); the title is the value without closing punctuation
  (``compose_title``, ``:165``).
* ``src/openkos/model/okf.py:1554`` ``build_concept``: frontmatter with ``type``, ``title``,
  ``description``, ``provenance`` (``:1661``, Concept IDs ``sources/<slug>``) and its
  ``sources`` projection; the document is ``# title``, the description, the body and a
  ``## Related`` list (``:1686``).
* ``src/openkos/application/ingest.py:375`` / ``:962``: the source slug is
  ``slugify(<file stem>)`` (lowercase), and a new concept cites ``sources/<slug>``.
* ``src/openkos/model/okf.py:3270`` ``build_attached_document``: a decision restated in a later
  meeting is attached to the existing concept, adding the later source to ``provenance`` and an
  ``## Update from <title> (sources/<slug>)`` section with the later quote (``:3322``).
* ``src/openkos/bundle/decisions.py`` is NOT this folder: it holds the operator's contradiction
  and identity rulings under ``bundle/.state/decisions/*.decisions.okf``, which is never read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.domain.decision import DecisionStatus
from afg.extraction.openkos.bundle_reader import BundleFormatError, read_decision_bundle
from tests.openkos_bundle import decision_file, write_decision, write_meeting

MEETINGS = ("ES2015a", "ES2015b", "ES2015c", "ES2015d")

# Verbatim output of OpenKOS 0.5.5 (okf.build_concept over decision_pass.to_result).
REAL_SINGLE = """---
description: 'remote control battery: The remote control will use a kinetic battery,
  not a solar one.'
freshness: snapshot
generated:
  at: '2004-11-23T09:00:00Z'
  by: openkos 0.5.5
provenance:
- sources/es2015a
sensitivity: private
sources:
- id: sources/es2015a
  resource: /sources/es2015a.md
status: stable
tags: []
title: The remote control will use a kinetic battery, not a solar one
type: Decision
version: 1
---

# The remote control will use a kinetic battery, not a solar one

remote control battery: The remote control will use a kinetic battery, not a solar one.

The remote control will use a kinetic battery, not a solar one.

> we're going with the kinetic battery, not solar

## Related

- [sources/es2015a](/sources/es2015a.md) — source this was extracted from

"""

BATTERY = "The remote control will use a kinetic battery, not a solar one."
BATTERY_TITLE = "The remote control will use a kinetic battery, not a solar one"


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    directory = tmp_path / "transcripts"
    write_meeting(
        directory,
        "ES2015a",
        [
            ("PM", "Welcome to the kick-off.", ("a1",)),
            ("ID", "We're going with the kinetic battery, not solar.", ("a2", "a3")),
            ("PM", "Fine.", ("a4",)),
        ],
    )
    write_meeting(directory, "ES2015b", [("PM", "Nothing relevant here.", ("b1",))])
    write_meeting(directory, "ES2015c", [("PM", "Still nothing.", ("c1",))])
    write_meeting(
        directory,
        "ES2015d",
        [("PM", "So kinetic it is, final answer.", ("d1", "d2"))],
    )
    return directory


def _read(bundle: Path, transcripts: Path):  # type: ignore[no-untyped-def]
    return read_decision_bundle(
        bundle, series_id="ES2015", meeting_ids=MEETINGS, transcripts_dir=transcripts
    )


def test_reads_a_decision_written_by_openkos_0_5_5(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    write_decision(bundle, "kinetic", REAL_SINGLE)

    result = _read(bundle, transcripts)

    [decision] = result.decisions
    assert decision.id == "decisions/kinetic"
    assert decision.series_id == "ES2015"
    assert decision.meeting_id == "ES2015a"
    assert decision.origin_meeting_ids == ()
    assert decision.decision_object == "remote control battery"
    assert decision.content == BATTERY
    assert decision.status is DecisionStatus.ACCEPTED
    assert decision.annotator is None
    assert decision.evidence.meeting_id == "ES2015a"
    assert decision.evidence.dialogue_act_ids == ("a2", "a3")
    assert result.quotes.total == 1
    assert result.quotes.found == 1
    assert result.unmapped == ()


def test_test_helper_reproduces_the_real_file_byte_for_byte() -> None:
    built = decision_file(
        title=BATTERY_TITLE,
        subject="remote control battery",
        value=BATTERY,
        quotes=[("es2015a", "we're going with the kinetic battery, not solar")],
    )
    assert built == REAL_SINGLE


def test_attached_decision_keeps_every_meeting_of_origin(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    text = decision_file(
        title=BATTERY_TITLE,
        subject="remote control battery",
        value=BATTERY,
        quotes=[
            ("es2015a", "we're going with the kinetic battery, not solar"),
            ("es2015d", "so kinetic it is, final answer"),
        ],
    )
    write_decision(bundle, "kinetic", text)

    [decision] = _read(bundle, transcripts).decisions

    assert decision.meeting_id == "ES2015a"
    assert decision.origin_meeting_ids == ("ES2015a", "ES2015d")
    assert decision.evidence.meeting_id == "ES2015a"
    assert decision.evidence.dialogue_act_ids == ("a2", "a3")


def test_later_quote_is_used_when_the_first_is_not_found(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    text = decision_file(
        title=BATTERY_TITLE,
        subject="remote control battery",
        value=BATTERY,
        quotes=[("es2015a", "never said this"), ("es2015d", "So kinetic it is")],
    )
    write_decision(bundle, "kinetic", text)

    result = _read(bundle, transcripts)

    [decision] = result.decisions
    assert decision.evidence.meeting_id == "ES2015d"
    assert decision.evidence.dialogue_act_ids == ("d1", "d2")
    assert (result.quotes.total, result.quotes.found, result.quotes.not_found) == (2, 1, 1)


def test_decision_whose_quotes_are_all_missing_is_reported_not_returned(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    write_decision(
        bundle,
        "ghost",
        decision_file(
            title="Ghost", subject="s", value="a value of words", quotes=[("es2015b", "nope")]
        ),
    )
    write_decision(bundle, "kinetic", REAL_SINGLE)

    result = _read(bundle, transcripts)

    assert [d.id for d in result.decisions] == ["decisions/kinetic"]
    [missed] = result.unmapped
    assert missed.concept_id == "decisions/ghost"
    assert missed.meeting_ids == ("ES2015b",)
    assert missed.reasons == ("not_found",)
    assert (result.quotes.total, result.quotes.found, result.quotes.not_found) == (2, 1, 1)


def test_quote_in_turns_without_dialogue_acts_is_counted_apart(
    tmp_path: Path, transcripts: Path
) -> None:
    write_meeting(transcripts, "ES2015c", [("PM", "Spoken but unannotated.", ())])
    bundle = tmp_path / "bundle"
    write_decision(
        bundle,
        "bare",
        decision_file(
            title="Bare", subject="s", value="a value of words", quotes=[("es2015c", "unannotated")]
        ),
    )

    result = _read(bundle, transcripts)

    assert result.decisions == ()
    assert result.quotes.no_dialogue_acts == 1
    assert result.quotes.not_found == 0
    assert result.unmapped[0].reasons == ("no_dialogue_acts",)


def test_subject_with_a_colon_is_split_with_the_body_value(
    tmp_path: Path, transcripts: Path
) -> None:
    bundle = tmp_path / "bundle"
    write_decision(
        bundle,
        "colon",
        decision_file(
            title="Case: colors",
            subject="case: colors",
            value="Use a yellow case, not a red one.",
            quotes=[("es2015a", "Welcome to the kick-off")],
        ),
    )

    [decision] = _read(bundle, transcripts).decisions

    assert decision.decision_object == "case: colors"
    assert decision.content == "Use a yellow case, not a red one."


def test_missing_decisions_folder_means_no_decisions(tmp_path: Path, transcripts: Path) -> None:
    result = _read(tmp_path / "bundle", transcripts)
    assert result.decisions == ()
    assert result.quotes.total == 0


def test_operator_sidecars_are_not_decisions(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    sidecar = bundle / ".state" / "decisions" / "x.decisions.okf"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("---\nschema: openkos.decisions/v2\n---\n", encoding="utf-8")
    write_decision(bundle, "kinetic", REAL_SINGLE)

    assert len(_read(bundle, transcripts).decisions) == 1


def test_decisions_are_read_in_file_name_order(tmp_path: Path, transcripts: Path) -> None:
    bundle = tmp_path / "bundle"
    write_decision(bundle, "b-second", REAL_SINGLE)
    write_decision(bundle, "a-first", REAL_SINGLE)
    ids = [d.id for d in _read(bundle, transcripts).decisions]
    assert ids == ["decisions/a-first", "decisions/b-second"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda t: t.replace("type: Decision", "type: Entity"), "type"),
        (
            lambda t: t.replace("- sources/es2015a\nsensitivity", "- sources/zzz\nsensitivity"),
            "zzz",
        ),
        (lambda t: t.replace("provenance:\n- sources/es2015a\n", "provenance: []\n"), "provenance"),
        (lambda t: t.replace("description:", "summary:"), "description"),
        (lambda t: t.split("---\n", 2)[2], "front matter"),
    ],
)
def test_malformed_file_raises_a_clear_error(
    tmp_path: Path,
    transcripts: Path,
    mutate,
    message: str,  # type: ignore[no-untyped-def]
) -> None:
    bundle = tmp_path / "bundle"
    write_decision(bundle, "bad", mutate(REAL_SINGLE))
    with pytest.raises(BundleFormatError, match=message):
        _read(bundle, transcripts)
