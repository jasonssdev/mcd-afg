"""Annotation layer catalogue and discovery.

The gold set (OE1) is built from three existing AMI layers plus the *Decision Discussion
Segmentation* (DDS) layer; the layer catalogue and file discovery both live here so
``inventory.py`` and ``goldset.py`` share one definition of what a layer is.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from afg.corpus.nxt import discover_annotation_files


class AnnotationLayer(StrEnum):
    """AMI annotation layers this project depends on (thesis section 5.0)."""

    ABSTRACTIVE_SUMMARY = "abstractive_summary"
    """Abstractive summary, including DECISIONS headers (Hsueh & Moore operationalization)."""

    EXTRACTIVE_SUMMARY_LINKS = "extractive_summary_links"
    """Links from abstractive summary sentences to supporting dialogue acts."""

    DECISION_DISCUSSION_SEGMENTATION = "decision_discussion_segmentation"
    """DDS layer: present in 47 meetings (thesis section 5.0)."""

    DIALOGUE_ACTS = "dialogue_acts"
    """Base dialogue act segmentation, needed to resolve evidence spans."""

    WORDS = "words"
    """Word-level transcription, needed to render plain transcripts for C1."""


# VERIFIED at paso cero (2026-09-20) against ami_public_manual_1.6.2, by globbing the
# extracted tree. Observed file counts are recorded so a future corpus release that
# changes them is caught rather than silently absorbed:
#   *.abssumm.xml     142 files   abstractive/
#   *.summlink.xml    137 files   extractive/     (extractive/ also holds *.extsumm.xml,
#                                                  137 files -- the extracted summary
#                                                  itself, not the links we need here)
#   *.decision.xml     47 files   decision/manual/  <- note the nested `manual/` dir;
#                                                     discovery is rglob, so it is found
#   *.dialog-act.xml  556 files   dialogueActs/   (one file per meeting AND speaker)
#   *.words.xml       687 files   words/          (one file per meeting AND speaker)
# Two patterns were wrong before this verification and silently matched nothing:
# ".dsegs.xml" (real: ".decision.xml") and ".dialogue-acts.xml" (real: ".dialog-act.xml").
_LAYER_GLOB_PATTERNS: dict[AnnotationLayer, str] = {
    AnnotationLayer.ABSTRACTIVE_SUMMARY: "*.abssumm.xml",
    AnnotationLayer.EXTRACTIVE_SUMMARY_LINKS: "*.summlink.xml",
    AnnotationLayer.DECISION_DISCUSSION_SEGMENTATION: "*.decision.xml",
    AnnotationLayer.DIALOGUE_ACTS: "*.dialog-act.xml",
    AnnotationLayer.WORDS: "*.words.xml",
}


@dataclass(frozen=True, slots=True)
class LayerFile:
    layer: AnnotationLayer
    meeting_id: str
    path: Path


def glob_pattern_for(layer: AnnotationLayer) -> str:
    """Return the glob pattern used to discover files for ``layer``.

    Centralized so a single correction (once paso cero confirms the real naming) fixes
    discovery for every caller.
    """
    return _LAYER_GLOB_PATTERNS[layer]


def discover_layer_files(ami_root: Path, layer: AnnotationLayer) -> list[LayerFile]:
    """Glob ``ami_root`` for files belonging to ``layer``.

    Returns an empty list (never raises) when ``ami_root`` does not exist or no matching
    files are found -- absence of the corpus is a normal, expected state before paso cero,
    not an error condition for this function to report.
    """
    pattern = glob_pattern_for(layer)
    files = discover_annotation_files(ami_root, pattern)
    results: list[LayerFile] = []
    for path in files:
        # Meeting id is conventionally the first '.'-delimited component of the filename.
        meeting_id = path.name.split(".", 1)[0]
        results.append(LayerFile(layer=layer, meeting_id=meeting_id, path=path))
    return results


def discover_meetings_with_layer(ami_root: Path, layer: AnnotationLayer) -> set[str]:
    """Return the set of meeting ids that have at least one file for ``layer``."""
    return {f.meeting_id for f in discover_layer_files(ami_root, layer)}
