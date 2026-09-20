"""Adapter from :class:`~afg.extraction.protocol.Extractor` to the OpenKOS instrument.

Thesis section 5.9: the implementation runs on OpenKOS (local-first knowledge compilation
engine, Apache-2.0, same author, preexisting). OpenKOS itself is an optional dependency
(``uv sync --extra instrument``) so that the base `mcd-afg` install never requires it.
"""

from __future__ import annotations

from dataclasses import dataclass

from afg.extraction.protocol import ExtractionResult, Extractor
from afg.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class OpenKosAdapter(Extractor):
    """Extractor backed by the ``openkos`` package (thesis section 5.9 "instrument").

    Per thesis section 5.9, the boundary between instrument and contribution is explicit:
    OpenKOS provides ingestion, typed extraction with provenance, storage, and hybrid
    retrieval. This project's contribution is the reference set, the three-condition
    design, the alignment protocol, and the error-attribution measurement -- not the
    extraction engine itself.
    """

    workspace: str
    model: str

    def extract(self, meeting_id: str, transcript: str) -> ExtractionResult:
        """Run OpenKOS extraction over one meeting's transcript.

        Not implemented: this requires both the ``openkos`` optional dependency
        (``uv sync --extra instrument``) and a real transcript, which in turn requires
        the AMI corpus to be downloaded and paso cero (thesis section 5.0) to have
        confirmed the transcript rendering. Implement once
        ``src/afg/corpus/transcripts.py`` has been validated against real corpus files
        and the OpenKOS CLI/package surface used for extraction has been chosen.
        """
        raise NotImplementedError(
            "OpenKosAdapter.extract requires the `openkos` optional dependency and a "
            "real AMI transcript; it implements the extraction step of OE2 (thesis "
            "section 3) using the instrument described in thesis section 5.9. Run paso "
            "cero first (`afg corpus inventory`), then wire this adapter to the openkos "
            "package's actual extraction API."
        )
