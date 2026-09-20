"""Tests for native-language derivation (thesis section 5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.corpus.participants import (
    NativeSpeakerCounts,
    classify_native_speaker_status,
    load_native_language_records,
    load_participants,
    native_language_from_participant_id,
    native_speaker_ratio,
    normalize_native_language,
    role_from_code,
)
from afg.domain.participant import NativeLanguage, NativeSpeakerStatus, Participant, SpeakerRole
from afg.shared.paths import AMI_DIR

_CORPUS_AVAILABLE = (AMI_DIR / "corpusResources" / "participants.xml").exists() and (
    AMI_DIR / "corpusResources" / "meetings.xml"
).exists()

requires_corpus = pytest.mark.skipif(
    not _CORPUS_AVAILABLE, reason="AMI corpus not downloaded at data/raw/ami/"
)


class TestNativeLanguageFromParticipantId:
    """The legacy id-character heuristic. Kept for reference only -- see its docstring
    for why it must never be used as the main resolution path."""

    def test_third_char_e_is_english(self) -> None:
        assert native_language_from_participant_id("ABEcd") == NativeLanguage.ENGLISH

    def test_third_char_d_is_dutch(self) -> None:
        assert native_language_from_participant_id("ABDcd") == NativeLanguage.DUTCH

    def test_third_char_o_is_other(self) -> None:
        assert native_language_from_participant_id("ABOcd") == NativeLanguage.OTHER

    def test_unrecognized_char_is_unknown(self) -> None:
        assert native_language_from_participant_id("ABXcd") == NativeLanguage.UNKNOWN

    def test_lowercase_third_char_is_normalized(self) -> None:
        assert native_language_from_participant_id("ABecd") == NativeLanguage.ENGLISH

    def test_short_id_is_unknown(self) -> None:
        assert native_language_from_participant_id("AB") == NativeLanguage.UNKNOWN

    def test_empty_id_is_unknown(self) -> None:
        assert native_language_from_participant_id("") == NativeLanguage.UNKNOWN

    def test_fabricates_dutch_for_ts3005_style_ids(self) -> None:
        """Documents the exact defect that got this heuristic demoted: it confidently
        (and wrongly) returns Dutch for the TS3005 id format, which is absent from every
        corpus resource file."""
        for pid in ("MTD017PM", "MTD018ID", "FTD019UID", "MTD020ME"):
            assert native_language_from_participant_id(pid) == NativeLanguage.DUTCH


class TestRoleFromCode:
    def test_known_codes(self) -> None:
        assert role_from_code("PM") == SpeakerRole.PROJECT_MANAGER
        assert role_from_code("me") == SpeakerRole.MARKETING_EXPERT

    def test_unknown_code_returns_none(self) -> None:
        assert role_from_code("XX") is None


class TestNormalizeNativeLanguage:
    def test_none_is_none(self) -> None:
        assert normalize_native_language(None) is None

    def test_empty_string_is_none(self) -> None:
        assert normalize_native_language("") is None

    def test_whitespace_only_is_none(self) -> None:
        assert normalize_native_language("   ") is None

    def test_already_canonical_is_unchanged(self) -> None:
        assert normalize_native_language("English") == "English"

    def test_lowercase_is_titled(self) -> None:
        assert normalize_native_language("romanian") == "Romanian"

    def test_chines_alias_maps_to_chinese(self) -> None:
        assert normalize_native_language("Chines") == "Chinese"

    def test_mandarin_chinese_alias_maps_to_chinese(self) -> None:
        assert normalize_native_language("Mandarin Chinese") == "Chinese"

    def test_czeque_alias_maps_to_czech(self) -> None:
        assert normalize_native_language("Czeque") == "Czech"

    def test_alias_matching_is_case_insensitive(self) -> None:
        assert normalize_native_language("CZEQUE") == "Czech"


class TestClassifyNativeSpeakerStatus:
    def test_none_is_unknown(self) -> None:
        assert classify_native_speaker_status(None) == NativeSpeakerStatus.UNKNOWN

    def test_english_is_native(self) -> None:
        assert classify_native_speaker_status("English") == NativeSpeakerStatus.NATIVE

    def test_english_case_insensitive(self) -> None:
        assert classify_native_speaker_status("english") == NativeSpeakerStatus.NATIVE

    def test_other_language_is_non_native(self) -> None:
        assert classify_native_speaker_status("French") == NativeSpeakerStatus.NON_NATIVE


class TestLoadParticipants:
    def test_missing_corpus_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_participants(tmp_path) == []

    def test_missing_corpus_native_language_records_empty(self, tmp_path: Path) -> None:
        assert load_native_language_records(tmp_path) == []


class TestNativeSpeakerRatio:
    def test_empty_roster(self) -> None:
        counts = native_speaker_ratio([])
        assert counts == NativeSpeakerCounts(native=0, non_native=0, unknown=0)
        assert counts.ratio_of_known is None

    def test_all_native(self) -> None:
        participants = [
            Participant(
                id="p1",
                role=SpeakerRole.PROJECT_MANAGER,
                native_language="English",
                native_speaker_status=NativeSpeakerStatus.NATIVE,
            )
        ]
        counts = native_speaker_ratio(participants)
        assert counts.native == 1
        assert counts.non_native == 0
        assert counts.unknown == 0
        assert counts.ratio_of_known == pytest.approx(1.0)

    def test_mixed_ratio(self) -> None:
        participants = [
            Participant(
                id="p1",
                role=SpeakerRole.PROJECT_MANAGER,
                native_language="English",
                native_speaker_status=NativeSpeakerStatus.NATIVE,
            ),
            Participant(
                id="p2",
                role=SpeakerRole.MARKETING_EXPERT,
                native_language="French",
                native_speaker_status=NativeSpeakerStatus.NON_NATIVE,
            ),
        ]
        counts = native_speaker_ratio(participants)
        assert counts.ratio_of_known == pytest.approx(0.5)

    def test_unknown_never_folded_into_known_denominator(self) -> None:
        participants = [
            Participant(
                id="p1",
                role=SpeakerRole.PROJECT_MANAGER,
                native_language="English",
                native_speaker_status=NativeSpeakerStatus.NATIVE,
            ),
            Participant(
                id="p2",
                role=SpeakerRole.MARKETING_EXPERT,
                native_language="Unknown",
                native_speaker_status=NativeSpeakerStatus.UNKNOWN,
            ),
        ]
        counts = native_speaker_ratio(participants)
        assert counts.native == 1
        assert counts.non_native == 0
        assert counts.unknown == 1
        # A naive `native / total` would report 0.5; the unknown case must not silently
        # deflate the ratio of participants whose condition is actually known.
        assert counts.ratio_of_known == pytest.approx(1.0)


@requires_corpus
class TestCorpusBackedNativeLanguageRecords:
    """Regression tests against the real download at data/raw/ami/."""

    def test_total_participant_count(self) -> None:
        records = load_native_language_records(AMI_DIR)
        assert len(records) == 189

    def test_native_non_native_unknown_split(self) -> None:
        records = load_native_language_records(AMI_DIR)
        counts = native_speaker_ratio(records)
        # Measured against the real corpus (2026-09-20): 91 native (English), 2 with an
        # empty native_language attribute (UNKNOWN, never folded into non_native), and
        # the remainder (96) genuinely non-native. 91 + 96 + 2 == 189.
        assert counts.native == 91
        assert counts.unknown == 2
        assert counts.non_native == 96
        assert counts.total == 189

    def test_alias_normalization_against_real_data(self) -> None:
        records = load_native_language_records(AMI_DIR)
        by_id = {r.participant_id: r.native_language for r in records}
        # Exact ids carrying the dirty spellings, verified against the real corpus.
        chines_or_mandarin = {
            pid: lang
            for pid, lang in by_id.items()
            if lang == "Chinese"
        }
        assert len(chines_or_mandarin) == 5  # "Chinese" x3, "Chines" x1, "Mandarin Chinese" x1
        czech_entries = [lang for lang in by_id.values() if lang == "Czech"]
        assert len(czech_entries) == 4  # "Czech" x2, "Czeque" x2

    def test_no_language_is_left_as_dirty_spelling(self) -> None:
        records = load_native_language_records(AMI_DIR)
        languages = {r.native_language for r in records}
        assert "Chines" not in languages
        assert "Mandarin Chinese" not in languages
        assert "Czeque" not in languages
        assert "romanian" not in languages  # must be title-cased to "Romanian"


@requires_corpus
class TestCorpusBackedSixSeriesRoster:
    """Regression tests for the meetings.xml -> participants.xml join, against the six
    configured target series in the real download."""

    def test_total_six_series_participant_count(self) -> None:
        participants = load_participants(AMI_DIR)
        assert len(participants) == 24

    def test_ts3005_resolves_to_unknown_not_dutch(self) -> None:
        participants = load_participants(AMI_DIR)
        by_id = {p.id: p for p in participants}
        for pid in ("MTD017PM", "MTD018ID", "FTD019UID", "MTD020ME"):
            assert pid in by_id, (
                f"{pid} should be present (from meetings.xml) even though it is "
                "absent from participants.xml"
            )
            participant = by_id[pid]
            assert participant.native_speaker_status == NativeSpeakerStatus.UNKNOWN
            assert participant.native_language != "Dutch"
            assert participant.native_language == "Unknown"

    def test_six_series_native_non_native_unknown_split(self) -> None:
        participants = load_participants(AMI_DIR)
        counts = native_speaker_ratio(participants)
        assert counts.native == 11
        assert counts.non_native == 9
        assert counts.unknown == 4
        assert counts.total == 24

    def test_role_distribution_is_balanced(self) -> None:
        participants = load_participants(AMI_DIR)
        role_counts: dict[SpeakerRole, int] = {}
        for participant in participants:
            role_counts[participant.role] = role_counts.get(participant.role, 0) + 1
        assert role_counts == {
            SpeakerRole.PROJECT_MANAGER: 6,
            SpeakerRole.MARKETING_EXPERT: 6,
            SpeakerRole.USER_INTERFACE_DESIGNER: 6,
            SpeakerRole.INDUSTRIAL_DESIGNER: 6,
        }

    def test_all_series_represented(self) -> None:
        participants = load_participants(AMI_DIR)
        series_ids = {p.series_id for p in participants}
        assert series_ids == {"ES2015", "ES2016", "IS1004", "IS1006", "IS1008", "TS3005"}
