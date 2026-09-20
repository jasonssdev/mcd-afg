"""Participants, speaker roles, and native-language condition, per thesis sections 5.1/6.3.

Both stratification axes required by OE2 (thesis section 3) and the fairness audit (thesis
section 6.3) -- speaker role and native/non-native English -- are modeled here as closed
enums so downstream stratified metrics (``src/afg/evaluation/metrics.py``) cannot silently
drift to free-text categories.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SpeakerRole(StrEnum):
    """AMI scenario roles. Fixed by the corpus design (thesis section 6.3)."""

    PROJECT_MANAGER = "project_manager"
    MARKETING_EXPERT = "marketing_expert"
    USER_INTERFACE_DESIGNER = "user_interface_designer"
    INDUSTRIAL_DESIGNER = "industrial_designer"


class NativeLanguage(StrEnum):
    """Output of the LEGACY id-character heuristic only (thesis 5.1) -- NOT the
    authoritative native-language representation.

    ``ENGLISH`` / ``DUTCH`` / ``OTHER`` mirror the E/D/O coding VERIFIED (2026-09-20) as
    the third character of the AMI participant id, per
    ``afg.corpus.participants.native_language_from_participant_id``. That function is a
    demoted, explicitly opt-in fallback: the authoritative source is the
    ``native_language`` attribute in ``corpusResources/participants.xml``, which is an
    open set of real language names (e.g. "French", "Hindi") and is modeled as plain
    ``str`` on :class:`Participant`, not as this enum. See
    ``src/afg/corpus/participants.py`` for both derivations.
    """

    ENGLISH = "english"
    DUTCH = "dutch"
    OTHER = "other"
    UNKNOWN = "unknown"


class NativeSpeakerStatus(StrEnum):
    """Native/non-native English classification (thesis 5.1 / 6.3 stratification axis).

    Derived from the authoritative ``native_language`` attribute in
    ``corpusResources/participants.xml`` (see ``afg.corpus.participants``).
    ``UNKNOWN`` is a first-class outcome -- for a participant absent from
    ``participants.xml`` entirely, or present with an empty ``native_language`` -- and
    must never be folded into ``NATIVE`` or ``NON_NATIVE``.
    """

    NATIVE = "native"
    NON_NATIVE = "non_native"
    UNKNOWN = "unknown"


class Participant(BaseModel):
    """An AMI participant, as seen in one meeting's speaker roster (thesis 5.1/6.3)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="AMI participant id, e.g. 'FEE057' (meetings.xml global_name).")
    role: SpeakerRole
    series_id: str | None = Field(
        default=None,
        description="Series id (e.g. 'ES2015') of the meeting this occurrence was read "
        "from, when the participant was loaded via a meetings.xml join.",
    )
    native_language: str = Field(
        default="Unknown",
        description="Normalized native-language name from corpusResources/"
        "participants.xml (e.g. 'English', 'French'), or 'Unknown' when the participant "
        "is absent from that file or its native_language attribute is empty.",
    )
    native_speaker_status: NativeSpeakerStatus = Field(default=NativeSpeakerStatus.UNKNOWN)
