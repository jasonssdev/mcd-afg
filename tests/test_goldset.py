"""Tests for the OE1 Task-A gold decision builder (manual de anotacion secciones 2, 3).

Two kinds of coverage, following ``tests/test_blocking.py``'s pattern:

- Pure unit tests of the NITE href parsing, word-span rendering, and ``machine_flags``
  heuristics against small synthetic XML fixtures -- these need no corpus and always run.
- Corpus-backed regression tests (decision counts per series/meeting, the turbo-button
  evidence chain, the exact verified transcript rendering) measured by hand against the
  real download. Skipped when the corpus is absent.
"""

from __future__ import annotations

import pytest
from lxml import etree

from afg.annotation.goldset import (
    EvidenceHit,
    GoldDecisionRow,
    MeetingNotFoundError,
    build_gold_decisions,
    find_term_occurrences,
    machine_flags_for,
    parse_nite_href,
    render_word_element,
    resolve_word_span,
    write_gold_decisions_csv,
)
from afg.shared.paths import AMI_DIR

_corpus_present = AMI_DIR.exists() and any(
    p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".") for p in AMI_DIR.rglob("*")
)

requires_corpus = pytest.mark.skipif(
    not _corpus_present, reason="AMI corpus not downloaded at data/raw/ami/"
)


# --- parse_nite_href ------------------------------------------------------------------


class TestParseNiteHref:
    def test_single_id(self) -> None:
        filename, first, last = parse_nite_href("IS1004c.A.dialog-act.xml#id(IS1004c.A.da.1)")
        assert filename == "IS1004c.A.dialog-act.xml"
        assert first == "IS1004c.A.da.1"
        assert last is None

    def test_id_range(self) -> None:
        filename, first, last = parse_nite_href(
            "IS1004c.A.words.xml#id(IS1004c.A.words1)..id(IS1004c.A.words9)"
        )
        assert filename == "IS1004c.A.words.xml"
        assert first == "IS1004c.A.words1"
        assert last == "IS1004c.A.words9"

    def test_malformed_raises(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized NITE href"):
            parse_nite_href("not-a-href-at-all")


# --- render_word_element / resolve_word_span -------------------------------------------


def _words_root(xml: str) -> etree._Element:
    return etree.fromstring(xml)


_WORDS_NS = 'xmlns:nite="http://nite.sourceforge.net/"'


class TestRenderWordElement:
    def test_w_element_renders_text(self) -> None:
        root = _words_root(f'<nite:root {_WORDS_NS}><w nite:id="w1">Hello</w></nite:root>')
        assert render_word_element(root[0]) == "Hello"

    @pytest.mark.parametrize(
        "tag", ["vocalsound", "disfmarker", "pause", "gap", "nonvocalsound"]
    )
    def test_no_text_tags_render_literally(self, tag: str) -> None:
        root = _words_root(f'<nite:root {_WORDS_NS}><{tag} nite:id="x1"/></nite:root>')
        assert render_word_element(root[0]) == f"<{tag}>"


class TestResolveWordSpan:
    def _elements_and_index(self) -> tuple[list[etree._Element], dict[str, int]]:
        root = _words_root(
            f"""<nite:root {_WORDS_NS}>
                <w nite:id="w1">So</w>
                <w nite:id="w2">we</w>
                <disfmarker nite:id="w3"/>
                <w nite:id="w4">okay</w>
            </nite:root>"""
        )
        elements = list(root)
        id_to_index = {
            el.get("{http://nite.sourceforge.net/}id"): i for i, el in enumerate(elements)
        }
        return elements, id_to_index

    def test_resolves_inclusive_range(self) -> None:
        elements, id_to_index = self._elements_and_index()
        span = resolve_word_span(elements, id_to_index, "w1", "w3")
        rendered = " ".join(render_word_element(e) for e in span)
        assert rendered == "So we <disfmarker>"

    def test_single_id_no_range(self) -> None:
        elements, id_to_index = self._elements_and_index()
        span = resolve_word_span(elements, id_to_index, "w2", None)
        assert [render_word_element(e) for e in span] == ["we"]

    def test_unknown_id_returns_empty(self) -> None:
        elements, id_to_index = self._elements_and_index()
        assert resolve_word_span(elements, id_to_index, "missing", None) == []

    def test_swapped_ids_still_resolve(self) -> None:
        elements, id_to_index = self._elements_and_index()
        span = resolve_word_span(elements, id_to_index, "w4", "w1")
        assert [render_word_element(e) for e in span] == ["So", "we", "<disfmarker>", "okay"]


# --- machine_flags_for ------------------------------------------------------------------


class TestMachineFlagsFor:
    def test_zero_evidence_flags_sin_evidencia(self) -> None:
        flags = machine_flags_for(evidence_da_count=0, sentence_text="Some sentence with words.")
        assert "sin_evidencia" in flags.split(";")

    def test_nonzero_evidence_no_sin_evidencia(self) -> None:
        flags = machine_flags_for(evidence_da_count=3, sentence_text="Some sentence with words.")
        assert "sin_evidencia" not in flags.split(";")

    def test_short_sentence_flags_frase_corta(self) -> None:
        # Verified real corpus sentence (manual worked example precursor).
        flags = machine_flags_for(
            evidence_da_count=1, sentence_text="The control will be the approx."
        )
        assert "frase_corta" in flags.split(";")

    def test_long_sentence_no_frase_corta(self) -> None:
        flags = machine_flags_for(
            evidence_da_count=1,
            sentence_text="The remote will have a base station with several buttons on it.",
        )
        assert "frase_corta" not in flags.split(";")

    def test_enumeration_flags_posible_compuesta(self) -> None:
        # Verified real corpus sentence (IS1004c.elana.s.29, manual section 3).
        flags = machine_flags_for(
            evidence_da_count=6,
            sentence_text=(
                "The remote will have a base station, a button on the base station to "
                "press, 2 scroll wheels for the channels and volume, a turbo button "
                "(possibly underneath the device), and an on/off button for the TV."
            ),
        )
        assert "posible_compuesta" in flags.split(";")

    def test_simple_sentence_no_posible_compuesta(self) -> None:
        flags = machine_flags_for(
            evidence_da_count=1, sentence_text="They agree on having a base station."
        )
        assert "posible_compuesta" not in flags.split(";")

    def test_flags_never_include_a_verdict_value(self) -> None:
        allowed = {"sin_evidencia", "posible_compuesta", "frase_corta", ""}
        flags = machine_flags_for(evidence_da_count=0, sentence_text="short one")
        assert set(flags.split(";")) <= allowed


# --- write_gold_decisions_csv (pure, no corpus needed) ---------------------------------


class TestWriteGoldDecisionsCsv:
    def test_human_columns_always_empty(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import csv

        row = GoldDecisionRow(
            decision_id="ES2015a.d01",
            meeting_id="ES2015a",
            source_sentence_id="ES2015a.elana.s.1",
            sentence_text="They decide to use titanium.",
            evidence_da_count=2,
            evidence_text="A: We use titanium .",
            machine_flags="",
        )
        out_path = write_gold_decisions_csv([row], tmp_path / "ES2015.decisions.csv")

        with out_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == [
                "decision_id",
                "meeting_id",
                "source_sentence_id",
                "sentence_text",
                "evidence_da_count",
                "evidence_text",
                "status",
                "decision_object",
                "decision_content",
                "annotator",
                "notes",
                "machine_flags",
            ]
            csv_rows = list(reader)

        assert len(csv_rows) == 1
        for column in ("status", "decision_object", "decision_content", "annotator", "notes"):
            assert csv_rows[0][column] == ""
        assert csv_rows[0]["decision_id"] == "ES2015a.d01"


# --- evidence finder (manual section 3.3) -----------------------------------------------


class TestFindTermOccurrences:
    @requires_corpus
    def test_missing_meeting_raises(self) -> None:
        with pytest.raises(MeetingNotFoundError):
            find_term_occurrences(AMI_DIR, "NOT-A-REAL-MEETING", "turbo")


# --- corpus-backed regression tests ------------------------------------------------------


@requires_corpus
class TestBuildGoldDecisionsCorpus:
    @pytest.mark.parametrize(
        ("series", "expected_total"),
        [("IS1004", 24), ("ES2015", 29)],
    )
    def test_series_total_decision_count(self, series: str, expected_total: int) -> None:
        rows = build_gold_decisions(AMI_DIR, series)
        assert len(rows) == expected_total

    @pytest.mark.parametrize(
        ("meeting", "expected_count"),
        [("IS1004c", 2), ("IS1004d", 12), ("ES2015b", 9), ("IS1004a", 4)],
    )
    def test_per_meeting_decision_count(self, meeting: str, expected_count: int) -> None:
        series = meeting[:-1]
        rows = build_gold_decisions(AMI_DIR, series)
        meeting_rows = [r for r in rows if r.meeting_id == meeting]
        assert len(meeting_rows) == expected_count

    def test_is1004c_s29_resolves_six_dialogue_acts(self) -> None:
        rows = build_gold_decisions(AMI_DIR, "IS1004")
        row = next(r for r in rows if r.source_sentence_id == "IS1004c.elana.s.29")
        assert row.evidence_da_count == 6

    def test_is1004d_s22_has_zero_evidence_and_sin_evidencia_flag(self) -> None:
        rows = build_gold_decisions(AMI_DIR, "IS1004")
        row = next(r for r in rows if r.source_sentence_id == "IS1004d.elana.s.22")
        assert row.evidence_da_count == 0
        assert "sin_evidencia" in row.machine_flags.split(";")

    def test_dact_dharshi_203_renders_verified_transcript(self) -> None:
        rows = build_gold_decisions(AMI_DIR, "IS1004")
        row = next(r for r in rows if r.source_sentence_id == "IS1004c.elana.s.29")
        assert "So we <disfmarker> that means we need a button on th on the on the basis ." in (
            row.evidence_text
        )

    def test_written_csv_has_empty_human_columns(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        from afg.annotation.goldset import write_gold_decisions_csv

        rows = build_gold_decisions(AMI_DIR, "IS1004")
        out_path = write_gold_decisions_csv(rows, tmp_path / "IS1004.decisions.csv")

        import csv

        with out_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            csv_rows = list(reader)

        assert len(csv_rows) == len(rows)
        for csv_row in csv_rows:
            assert csv_row["status"] == ""
            assert csv_row["decision_object"] == ""
            assert csv_row["decision_content"] == ""
            assert csv_row["annotator"] == ""
            assert csv_row["notes"] == ""

    def test_evidence_finder_matches_manual_worked_example(self) -> None:
        hits = find_term_occurrences(AMI_DIR, "IS1004d", "turbo")
        assert len(hits) == 8
        assert any(hit.word_id == "IS1004d.B.words1560" for hit in hits)

    def test_evidence_finder_is_case_insensitive_whole_word(self) -> None:
        hits_lower = find_term_occurrences(AMI_DIR, "IS1004d", "turbo")
        hits_upper = find_term_occurrences(AMI_DIR, "IS1004d", "TURBO")
        assert len(hits_lower) == len(hits_upper) == 8
        for hit in hits_lower:
            assert isinstance(hit, EvidenceHit)
