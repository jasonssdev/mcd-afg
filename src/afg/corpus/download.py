"""Fetch, verify, and unzip the AMI manual annotations.

This module is written so it *can* be run, but nothing in this repository's automation,
tests, or CI calls :func:`download_annotations` -- it is only reachable via the explicit
``afg corpus download`` CLI command, which itself prints the licence and asks for
confirmation before writing anything. See the project spec: "NEVER download the AMI
corpus. Write the downloader; do not run it."
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
from tqdm import tqdm

from afg.shared.config import load_corpus_config
from afg.shared.logging import get_logger
from afg.shared.paths import AMI_DIR

logger = get_logger(__name__)


class DownloadError(RuntimeError):
    """Raised when the annotations archive cannot be fetched or fails verification."""


@dataclass(frozen=True, slots=True)
class DownloadResult:
    archive_path: Path
    extracted_to: Path
    bytes_downloaded: int


def _annotation_source() -> tuple[str, str, int]:
    """Return (url, filename, approximate_size_mb) from ``config/corpus.toml``."""
    cfg = load_corpus_config()
    annotations = cfg["corpus"]["annotations"]
    return annotations["url"], annotations["filename"], annotations["approximate_size_mb"]


def download_annotations(
    dest_dir: Path = AMI_DIR,
    *,
    chunk_size: int = 1 << 16,
    timeout_seconds: float = 120.0,
) -> DownloadResult:
    """Download the AMI manual annotations archive and extract it into ``dest_dir``.

    Not called by any test, CLI default, or CI step. The only entry point that reaches
    this function is ``afg corpus download``, which requires interactive confirmation
    after printing the licence.

    Raises:
        DownloadError: on any network failure, non-2xx response, or a downloaded archive
            that does not open as a valid zip file. No AMI-specific checksum is asserted
            here because none is published in the verified source material (thesis 5.0);
            structural validity (openable zip, non-empty) is the verification performed.
    """
    url, filename, approximate_size_mb = _annotation_source()
    dest_dir.mkdir(parents=True, exist_ok=True)
    archive_path = dest_dir / filename

    logger.info("Downloading %s (~%d MB) to %s", url, approximate_size_mb, archive_path)
    bytes_downloaded = 0
    try:
        with httpx.stream("GET", url, timeout=timeout_seconds, follow_redirects=True) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            with (
                archive_path.open("wb") as fh,
                tqdm(total=total or None, unit="B", unit_scale=True, desc=filename) as progress,
            ):
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    fh.write(chunk)
                    bytes_downloaded += len(chunk)
                    progress.update(len(chunk))
    except httpx.HTTPError as exc:
        raise DownloadError(f"Failed to download {url}: {exc}") from exc

    if not zipfile.is_zipfile(archive_path):
        raise DownloadError(
            f"Downloaded file at {archive_path} is not a valid zip archive. "
            "Not extracting; the corrupt file is left in place for inspection."
        )

    logger.info("Extracting %s into %s", archive_path, dest_dir)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(dest_dir)

    return DownloadResult(
        archive_path=archive_path, extracted_to=dest_dir, bytes_downloaded=bytes_downloaded
    )
