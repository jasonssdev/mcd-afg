"""Tests for AMI transcript rendering (thesis sections 5.3/5.4).

Unit-level behaviours (word parsing, href/range resolution, punctuation joining) run
against small synthetic NXT fixtures written to ``tmp_path``, so they do not require the
corpus. End-to-end rendering (chronological interleaving, role labels, dialogue-act
alignment) is additionally checked against the real download at ``data/raw/ami/``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.corpus.transcripts import (
    WordIndex,
    WordToken,
    join_word_tokens,
    load_word_index,
    load_word_tokens,
    render_meeting_dialogue_acts,
    render_meeting_plain_text,
    render_meeting_transcript,
    resolve_href_tokens,
    speaker_role_labels,
)
from afg.shared.paths import AMI_DIR

_CORPUS_AVAILABLE = (AMI_DIR / "words" / "IS1004d.A.words.xml").exists()

requires_corpus = pytest.mark.skipif(
    not _CORPUS_AVAILABLE, reason="AMI corpus not downloaded at data/raw/ami/"
)

_NITE_NS = 'xmlns:nite="http://nite.sourceforge.net/"'


def _write_words_file(path: Path, body: str) -> None:
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_segments_file(path: Path, segments: list[tuple[float, float, str]]) -> None:
    body = "\n".join(
        f'<segment nite:id="seg.{i}" channel="0" transcriber_start="{start}" '
        f'transcriber_end="{end}">\n   <nite:child href="{href}"/>\n</segment>'
        for i, (start, end, href) in enumerate(segments)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_dialogue_acts_file(path: Path, acts: list[tuple[str, str]]) -> None:
    body = "\n".join(
        f'<dact nite:id="{act_id}">\n'
        f'   <nite:pointer role="da-aspect" href="da-types.xml#id(ami_da_1)"/>\n'
        f'   <nite:child href="{words_href}"/>\n'
        f"</dact>"
        for act_id, words_href in acts
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n{body}\n</nite:root>\n'
    )


def _write_meetings_file(path: Path, observation: str, speakers: list[tuple[str, str]]) -> None:
    """``speakers`` is a list of ``(nxt_agent, role_code)`` pairs."""
    speaker_els = "\n".join(
        f'      <speaker nite:id="{observation}_{i}" nxt_agent="{agent}" role="{role}" '
        f'global_name="P{i}"/>'
        for i, (agent, role) in enumerate(speakers)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>\n'
        f'<nite:root nite:id="root" {_NITE_NS}>\n'
        f'   <meeting nite:id="meet_1" type="scenario" observation="{observation}">\n'
        f"{speaker_els}\n"
        f"   </meeting>\n</nite:root>\n"
    )


def _build_synthetic_meeting(ami_root: Path) -> None:
    """Two-speaker, four-turn synthetic meeting with alternating, non-overlapping
    speech, mirroring the real AMI on-disk layout (``words/``, ``segments/``,
    ``dialogueActs/``, ``corpusResources/meetings.xml``)."""
    (ami_root / "words").mkdir(parents=True, exist_ok=True)
    (ami_root / "segments").mkdir(parents=True, exist_ok=True)
    (ami_root / "dialogueActs").mkdir(parents=True, exist_ok=True)
    (ami_root / "corpusResources").mkdir(parents=True, exist_ok=True)

    _write_words_file(
        ami_root / "words" / "MEET1.A.words.xml",
        '<w nite:id="MEET1.A.words1" starttime="0.0" endtime="0.5">Hello</w>\n'
        '<w nite:id="MEET1.A.words2" starttime="0.5" endtime="1.0">everyone</w>\n'
        '<w nite:id="MEET1.A.words3" starttime="2.0" endtime="2.3">How</w>\n'
        '<w nite:id="MEET1.A.words4" starttime="2.3" endtime="2.6">are</w>\n'
        '<w nite:id="MEET1.A.words5" starttime="2.6" endtime="3.0">you</w>\n'
        '<w nite:id="MEET1.A.words6" starttime="3.0" endtime="3.0" punc="true">?</w>',
    )
    _write_words_file(
        ami_root / "words" / "MEET1.B.words.xml",
        '<w nite:id="MEET1.B.words1" starttime="1.0" endtime="1.3">Hi</w>\n'
        '<w nite:id="MEET1.B.words2" starttime="1.3" endtime="2.0">there</w>\n'
        '<w nite:id="MEET1.B.words3" starttime="3.0" endtime="3.3">Fine</w>\n'
        '<w nite:id="MEET1.B.words4" starttime="3.3" endtime="4.0">thanks</w>',
    )

    _write_segments_file(
        ami_root / "segments" / "MEET1.A.segments.xml",
        [
            (0.0, 1.0, "MEET1.A.words.xml#id(MEET1.A.words1)..id(MEET1.A.words2)"),
            (2.0, 3.0, "MEET1.A.words.xml#id(MEET1.A.words3)..id(MEET1.A.words6)"),
        ],
    )
    _write_segments_file(
        ami_root / "segments" / "MEET1.B.segments.xml",
        [
            (1.0, 2.0, "MEET1.B.words.xml#id(MEET1.B.words1)..id(MEET1.B.words2)"),
            (3.0, 4.0, "MEET1.B.words.xml#id(MEET1.B.words3)..id(MEET1.B.words4)"),
        ],
    )

    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / "MEET1.A.dialog-act.xml",
        [
            (
                "MEET1.A.dialog-act.1",
                "MEET1.A.words.xml#id(MEET1.A.words1)..id(MEET1.A.words2)",
            ),
            (
                "MEET1.A.dialog-act.2",
                "MEET1.A.words.xml#id(MEET1.A.words3)..id(MEET1.A.words6)",
            ),
        ],
    )
    _write_dialogue_acts_file(
        ami_root / "dialogueActs" / "MEET1.B.dialog-act.xml",
        [
            (
                "MEET1.B.dialog-act.1",
                "MEET1.B.words.xml#id(MEET1.B.words1)..id(MEET1.B.words2)",
            ),
            (
                "MEET1.B.dialog-act.2",
                "MEET1.B.words.xml#id(MEET1.B.words3)..id(MEET1.B.words4)",
            ),
        ],
    )

    _write_meetings_file(
        ami_root / "corpusResources" / "meetings.xml",
        "MEET1",
        [("A", "PM"), ("B", "ME")],
    )


class TestLoadWordTokens:
    def test_word_element_has_text(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(words, '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">Okay</w>')
        tokens = load_word_tokens(words)
        assert [t.text for t in tokens] == ["Okay"]

    def test_non_lexical_element_produces_no_text_but_keeps_id_slot(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(
            words,
            '<vocalsound nite:id="M.A.words0" starttime="0.0" endtime="0.5" type="cough"/>\n'
            '<w nite:id="M.A.words1" starttime="0.5" endtime="1.0">Okay</w>',
        )
        tokens = load_word_tokens(words)
        assert len(tokens) == 2
        assert tokens[0].id == "M.A.words0"
        assert tokens[0].text == ""
        assert tokens[1].text == "Okay"

    def test_filler_words_are_kept_as_is(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(words, '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">uh</w>')
        tokens = load_word_tokens(words)
        assert tokens[0].text == "uh"

    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_word_tokens(tmp_path / "missing.words.xml") == []


class TestJoinWordTokens:
    def test_punc_attaches_without_leading_space(self) -> None:
        tokens = [
            WordToken(id="1", text="Okay", is_punc=False, start_time=0.0, end_time=1.0),
            WordToken(id="2", text=".", is_punc=True, start_time=1.0, end_time=1.0),
        ]
        assert join_word_tokens(tokens) == "Okay."

    def test_normal_words_get_a_space(self) -> None:
        tokens = [
            WordToken(id="1", text="Good", is_punc=False, start_time=0.0, end_time=1.0),
            WordToken(id="2", text="morning", is_punc=False, start_time=1.0, end_time=2.0),
        ]
        assert join_word_tokens(tokens) == "Good morning"

    def test_non_lexical_tokens_contribute_nothing(self) -> None:
        tokens = [
            WordToken(id="1", text="Good", is_punc=False, start_time=0.0, end_time=1.0),
            WordToken(id="2", text="", is_punc=False, start_time=1.0, end_time=1.0),
            WordToken(id="3", text="morning", is_punc=False, start_time=1.0, end_time=2.0),
        ]
        assert join_word_tokens(tokens) == "Good morning"

    def test_empty_token_list_is_empty_string(self) -> None:
        assert join_word_tokens([]) == ""


class TestResolveHrefTokens:
    def test_single_id_href(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(words, '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">Okay</w>')
        index = load_word_index(words)
        tokens = resolve_href_tokens("M.A.words.xml#id(M.A.words1)", index)
        assert [t.text for t in tokens] == ["Okay"]

    def test_range_expansion_over_document_order(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(
            words,
            '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">Good</w>\n'
            '<w nite:id="M.A.words2" starttime="1.0" endtime="2.0">morning</w>\n'
            '<w nite:id="M.A.words3" starttime="2.0" endtime="2.0" punc="true">.</w>',
        )
        index = load_word_index(words)
        tokens = resolve_href_tokens("M.A.words.xml#id(M.A.words1)..id(M.A.words3)", index)
        assert join_word_tokens(tokens) == "Good morning."

    def test_range_spanning_a_non_lexical_element(self, tmp_path: Path) -> None:
        """The index-slot trap: a disfmarker/vocalsound between the range's endpoints
        still occupies a document-order slot and must not shift later ids' positions."""
        words = tmp_path / "M.A.words.xml"
        _write_words_file(
            words,
            '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">Okay</w>\n'
            '<disfmarker nite:id="M.A.words2" starttime="1.0" endtime="1.0"/>\n'
            '<w nite:id="M.A.words3" starttime="1.0" endtime="2.0">Good</w>\n'
            '<w nite:id="M.A.words4" starttime="2.0" endtime="2.5">morning</w>',
        )
        index = load_word_index(words)
        tokens = resolve_href_tokens("M.A.words.xml#id(M.A.words1)..id(M.A.words3)", index)
        assert [t.id for t in tokens] == ["M.A.words1", "M.A.words2", "M.A.words3"]
        assert join_word_tokens(tokens) == "Okay Good"
        # And the id *after* the non-lexical slot still resolves correctly.
        tail = resolve_href_tokens("M.A.words.xml#id(M.A.words4)", index)
        assert [t.text for t in tail] == ["morning"]

    def test_dangling_id_returns_empty(self, tmp_path: Path) -> None:
        words = tmp_path / "M.A.words.xml"
        _write_words_file(words, '<w nite:id="M.A.words1" starttime="0.0" endtime="1.0">Okay</w>')
        index = load_word_index(words)
        assert resolve_href_tokens("M.A.words.xml#id(M.A.words99)", index) == []

    def test_empty_index_is_safe(self, tmp_path: Path) -> None:
        empty_index = WordIndex(tokens=[], index_by_id={})
        assert resolve_href_tokens("M.A.words.xml#id(anything)", empty_index) == []


class TestSpeakerRoleLabels:
    def test_resolves_short_role_codes(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        labels = speaker_role_labels(tmp_path, "MEET1")
        assert labels == {"A": "PM", "B": "ME"}

    def test_unrecognized_role_falls_back_to_agent_letter(self, tmp_path: Path) -> None:
        (tmp_path / "corpusResources").mkdir(parents=True)
        _write_meetings_file(tmp_path / "corpusResources" / "meetings.xml", "MEET2", [("C", "XX")])
        labels = speaker_role_labels(tmp_path, "MEET2")
        assert labels == {"C": "C"}

    def test_missing_meetings_file_returns_empty_mapping(self, tmp_path: Path) -> None:
        assert speaker_role_labels(tmp_path, "NOPE") == {}


class TestRenderMeetingTranscript:
    def test_missing_meeting_returns_empty_list(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        assert render_meeting_transcript(tmp_path, "DOES-NOT-EXIST") == []

    def test_missing_corpus_returns_empty_list(self, tmp_path: Path) -> None:
        assert render_meeting_transcript(tmp_path, "MEET1") == []

    def test_chronological_interleaving_across_speakers(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        turns = render_meeting_transcript(tmp_path, "MEET1")
        assert [t.start_time for t in turns] == [0.0, 1.0, 2.0, 3.0]
        assert [t.role_label for t in turns] == ["PM", "ME", "PM", "ME"]
        assert [t.text for t in turns] == [
            "Hello everyone",
            "Hi there",
            "How are you?",
            "Fine thanks",
        ]

    def test_plain_text_rendering_is_chronological_and_labeled(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        text = render_meeting_plain_text(tmp_path, "MEET1")
        lines = text.splitlines()
        assert lines == [
            "PM: Hello everyone",
            "ME: Hi there",
            "PM: How are you?",
            "ME: Fine thanks",
        ]


class TestRenderMeetingDialogueActs:
    def test_missing_meeting_returns_empty_list(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        assert render_meeting_dialogue_acts(tmp_path, "DOES-NOT-EXIST") == []

    def test_keeps_dialogue_act_id_and_ignores_da_types_href(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        acts = render_meeting_dialogue_acts(tmp_path, "MEET1")
        assert [a.dialogue_act_id for a in acts] == [
            "MEET1.A.dialog-act.1",
            "MEET1.B.dialog-act.1",
            "MEET1.A.dialog-act.2",
            "MEET1.B.dialog-act.2",
        ]
        # The da-types.xml pointer must never have contributed text or been resolved
        # against the words file (it would have resolved to nothing/wrongly if it had).
        assert [a.text for a in acts] == [
            "Hello everyone",
            "Hi there",
            "How are you?",
            "Fine thanks",
        ]

    def test_chronological_by_earliest_word_start_time(self, tmp_path: Path) -> None:
        _build_synthetic_meeting(tmp_path)
        acts = render_meeting_dialogue_acts(tmp_path, "MEET1")
        assert [a.start_time for a in acts] == [0.0, 1.0, 2.0, 3.0]


@requires_corpus
class TestCorpusBackedTranscriptRendering:
    """Regression tests against the real download at data/raw/ami/, meeting IS1004d."""

    def test_plain_text_is_substantial_and_readable(self) -> None:
        text = render_meeting_plain_text(AMI_DIR, "IS1004d")
        assert len(text) > 15_000
        assert "Okay" in text or "okay" in text.lower()

    def test_turns_are_chronologically_non_decreasing(self) -> None:
        turns = render_meeting_transcript(AMI_DIR, "IS1004d")
        start_times = [t.start_time for t in turns]
        assert start_times == sorted(start_times)

    def test_speakers_alternate_in_early_turns(self) -> None:
        """Regression test for the original defect: rendering grouped by speaker file
        would put all of one speaker's turns before any other speaker's."""
        turns = render_meeting_transcript(AMI_DIR, "IS1004d")
        early_speakers = {t.speaker_id for t in turns[:20]}
        assert len(early_speakers) > 1

    def test_role_labels_resolve_to_short_codes(self) -> None:
        labels = speaker_role_labels(AMI_DIR, "IS1004d")
        assert labels == {"A": "PM", "B": "UI", "C": "ID", "D": "ME"}

    def test_filler_words_are_not_stripped(self) -> None:
        text = render_meeting_plain_text(AMI_DIR, "IS1004d")
        lowered = text.lower()
        assert " uh " in lowered or " um " in lowered

    def test_dialogue_act_rendering_keeps_ids_and_is_nonempty(self) -> None:
        acts = render_meeting_dialogue_acts(AMI_DIR, "IS1004d")
        assert len(acts) > 0
        assert all(a.dialogue_act_id for a in acts)
        assert all("IS1004d" in a.dialogue_act_id for a in acts)
