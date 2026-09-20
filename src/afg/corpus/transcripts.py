"""Render plain-text transcripts from AMI word/dialogue-act layers, for the C1 baseline.

C1 (document RAG, thesis section 5.3) indexes transcripts, not the structured annotation
layers. This module turns the low-level word/dialogue-act XML into flat, chunkable text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.nxt import NxtParseError, find_by_local_name, get_attr, get_href_targets, parse_xml
from afg.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One dialogue-act-sized segment of a rendered transcript."""

    meeting_id: str
    speaker_id: str
    dialogue_act_id: str
    text: str


def _extract_words_text(words_file: Path) -> dict[str, str]:
    """Map word element id -> surface form, from a words-layer file.

    # ASSUMPTION (verify at paso cero): AMI word elements are commonly represented with
    # the surface form either as element text or as a 'punc'/'text' attribute; this has
    # not been confirmed against a real extracted file. Returns an empty dict (never
    # raises) on parse failure so a single unreadable meeting does not abort a larger run.
    """
    try:
        root = parse_xml(words_file)
    except NxtParseError as exc:
        logger.warning("Could not parse words file %s: %s", words_file, exc)
        return {}

    words: dict[str, str] = {}
    for el in find_by_local_name(root, "w"):
        word_id = get_attr(el, "{http://nite.sourceforge.net/}id") or get_attr(el, "id")
        if not word_id:
            continue
        text = (el.text or get_attr(el, "text") or get_attr(el, "punc") or "").strip()
        if text:
            words[word_id] = text
    return words


def render_meeting_transcript(ami_root: Path, meeting_id: str) -> list[TranscriptSegment]:
    """Render a flat transcript for one meeting.

    Returns an empty list when the meeting has no discoverable words/dialogue-act files
    rather than raising -- callers building a corpus-wide index should simply skip
    meetings that render empty and log accordingly.
    """
    words_files = [
        f
        for f in discover_layer_files(ami_root, AnnotationLayer.WORDS)
        if f.meeting_id == meeting_id
    ]
    dialogue_act_files = [
        f
        for f in discover_layer_files(ami_root, AnnotationLayer.DIALOGUE_ACTS)
        if f.meeting_id == meeting_id
    ]

    if not words_files or not dialogue_act_files:
        logger.info(
            "No words/dialogue-act files found for meeting %s; cannot render transcript.",
            meeting_id,
        )
        return []

    word_text_by_speaker: dict[str, dict[str, str]] = {}
    for wf in words_files:
        # ASSUMPTION (verify at paso cero): the speaker id is commonly encoded in the
        # words filename as "<meeting_id>.<speaker>.words.xml"; not independently verified.
        parts = wf.path.stem.split(".")
        speaker_id = parts[1] if len(parts) > 1 else "unknown"
        word_text_by_speaker[speaker_id] = _extract_words_text(wf.path)

    segments: list[TranscriptSegment] = []
    for daf in dialogue_act_files:
        parts = daf.path.stem.split(".")
        speaker_id = parts[1] if len(parts) > 1 else "unknown"
        words_for_speaker = word_text_by_speaker.get(speaker_id, {})
        try:
            root = parse_xml(daf.path)
        except NxtParseError as exc:
            logger.warning("Could not parse dialogue-act file %s: %s", daf.path, exc)
            continue

        for el in find_by_local_name(root, "dact"):
            act_id = get_attr(el, "{http://nite.sourceforge.net/}id") or get_attr(el, "id") or ""
            word_ids = [href.split("#")[-1] for href in get_href_targets(el)]
            words = [words_for_speaker[w] for w in word_ids if w in words_for_speaker]
            text = " ".join(words).strip()
            if text:
                segments.append(
                    TranscriptSegment(
                        meeting_id=meeting_id,
                        speaker_id=speaker_id,
                        dialogue_act_id=act_id,
                        text=text,
                    )
                )

    return segments


def render_meeting_plain_text(ami_root: Path, meeting_id: str) -> str:
    """Render a meeting transcript as a single plain-text document, for C1 indexing."""
    segments = render_meeting_transcript(ami_root, meeting_id)
    return "\n".join(f"{seg.speaker_id}: {seg.text}" for seg in segments)
