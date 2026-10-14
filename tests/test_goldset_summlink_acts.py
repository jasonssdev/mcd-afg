"""Tests for :func:`afg.annotation.goldset.summlink_dialogue_act_ids` (issue #82)."""

from __future__ import annotations

from pathlib import Path

from afg.annotation.goldset import summlink_dialogue_act_ids

_SUMMLINK = """<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
<nite:root nite:id="ES2015a.summlink" xmlns:nite="http://nite.sourceforge.net/">
  <summlink nite:id="ES2015a.summlink.dharshi.1">
    <nite:pointer role="extractive" href="a.xml#id(ES2015a.A.dialog-act.dharshi.7)"/>
    <nite:pointer role="abstractive" href="ES2015a.abssumm.xml#id(ES2015a.elana.s.12)"/>
  </summlink>
  <summlink nite:id="ES2015a.summlink.dharshi.2">
    <nite:pointer role="extractive" href="b.xml#id(ES2015a.B.dialog-act.dharshi.3)"/>
    <nite:pointer role="abstractive" href="ES2015a.abssumm.xml#id(ES2015a.elana.s.12)"/>
  </summlink>
  <summlink nite:id="ES2015a.summlink.dharshi.3">
    <nite:pointer role="extractive" href="a.xml#id(ES2015a.A.dialog-act.dharshi.9)"/>
    <nite:pointer role="abstractive" href="ES2015a.abssumm.xml#id(ES2015a.elana.s.5)"/>
  </summlink>
</nite:root>
"""


def test_maps_each_sentence_to_its_dialogue_act_ids_in_file_order(tmp_path: Path) -> None:
    folder = tmp_path / "extractive"
    folder.mkdir()
    (folder / "ES2015a.summlink.xml").write_text(_SUMMLINK, encoding="utf-8")
    (folder / "ES2015b.summlink.xml").write_text(_SUMMLINK, encoding="utf-8")

    result = summlink_dialogue_act_ids(tmp_path, "ES2015a")

    assert result == {
        "ES2015a.elana.s.12": ["ES2015a.A.dialog-act.dharshi.7", "ES2015a.B.dialog-act.dharshi.3"],
        "ES2015a.elana.s.5": ["ES2015a.A.dialog-act.dharshi.9"],
    }


def test_meeting_without_summlinks_gives_an_empty_map(tmp_path: Path) -> None:
    assert summlink_dialogue_act_ids(tmp_path, "ES2015a") == {}
