"""Tests for the bibliography loader and audit, against the real seeded refs.bib.

These tests exercise the actual `bibliography/refs.bib` shipped with this repository
(seeded from thesis section 8), not a synthetic fixture -- catching a malformed entry or a
broken section keyword is exactly the kind of regression this project cannot afford to
discover only when someone runs `afg biblio audit` by hand.
"""

from __future__ import annotations

from afg.bibliography.audit import EXPECTED_SECTIONS, audit_library
from afg.bibliography.library import load_library


class TestLoadLibrary:
    def test_loads_a_substantial_number_of_entries(self) -> None:
        entries = load_library()
        # Thesis section 8 lists 48 references across 8.1-8.7; assert a floor rather than
        # an exact count so minor future additions don't break this test.
        assert len(entries) >= 40

    def test_every_entry_has_a_key_and_type(self) -> None:
        for entry in load_library():
            assert entry.key, "every BibTeX entry must have a citation key"
            assert entry.entry_type, f"entry {entry.key} is missing an ENTRYTYPE"

    def test_known_entry_is_present(self) -> None:
        entries = {e.key: e for e in load_library()}
        assert "carletta2006ami" in entries
        assert entries["carletta2006ami"].doi == "10.1007/11677482_3"

    def test_preprints_are_flagged(self) -> None:
        entries = {e.key: e for e in load_library()}
        assert entries["edge2024graphrag"].is_preprint is True
        assert entries["carletta2006ami"].is_preprint is False


class TestAuditLibrary:
    def test_every_expected_section_has_at_least_one_entry(self) -> None:
        audit = audit_library(load_library())
        assert audit.sections_with_no_entries == ()

    def test_expected_sections_cover_8_1_through_8_7(self) -> None:
        assert tuple(f"section-8-{i}" for i in range(1, 8)) == EXPECTED_SECTIONS

    def test_total_entries_matches_loaded_entries(self) -> None:
        entries = load_library()
        audit = audit_library(entries)
        assert audit.total_entries == len(entries)

    def test_no_duplicate_dois_in_the_seeded_bibliography(self) -> None:
        audit = audit_library(load_library())
        assert audit.duplicate_doi_groups == (), (
            f"unexpected duplicate DOIs: {audit.duplicate_doi_groups}"
        )

    def test_missing_doi_entries_are_the_known_doi_less_ones(self) -> None:
        audit = audit_library(load_library())
        # A handful of entries (workshop papers predating DOI assignment, a W3C
        # recommendation, a NIST report cited by number, a draft spec) legitimately have
        # no DOI; this just asserts the count is non-trivial and bounded, not exact
        # membership, so a correction to one entry doesn't spuriously break this test.
        assert 0 < len(audit.missing_doi_keys) < len(load_library())
