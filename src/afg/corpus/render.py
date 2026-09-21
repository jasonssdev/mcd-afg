"""Freeze rendered AMI transcripts to disk, plus a tracked manifest (``afg corpus
transcripts``).

Two artifacts per meeting, both derived from :mod:`afg.corpus.transcripts`'s
segment-level and dialogue-act-level rendering:

* ``<meeting_id>.md`` -- hand-written front matter (plain ``key: value`` lines, no YAML
  dependency) followed by the plain-text body OpenKOS (C2) ingests and C1 indexes.
* ``<meeting_id>.jsonl`` -- one JSON object per turn, the map back to the annotations:
  ``char_start``/``char_end`` locate the turn inside the ``.md`` body, and
  ``dialogue_act_ids`` is the bridge from rendered text to ``extractive/<meeting>
  .summlink.xml`` and therefore the OE1 gold set.

``dialogue_act_ids`` is a many-to-many OVERLAP computation, not a lookup: segments
(turn boundaries) and dialogue acts (analytic boundaries) are two different
segmentations of the same word stream and disagree about where to cut. Both
:class:`~afg.corpus.transcripts.TranscriptTurn` and
:class:`~afg.corpus.transcripts.DialogueActTurn` carry the inclusive document-order
word-index range (``word_start_index``/``word_end_index``, into that speaker's own words
file) they were resolved from; a turn's ``dialogue_act_ids`` is every same-speaker
dialogue act whose range intersects the turn's range.

Determinism is a hard requirement (see module-level ``render_meetings`` docstring): no
timestamps anywhere, ``json.dumps(..., sort_keys=True)`` for stable key order, and
``renderer_revision`` degrading to ``"unknown"`` rather than ever raising, since it is
provenance metadata, not control flow.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.transcripts import (
    DialogueActTurn,
    render_meeting_dialogue_acts,
    render_meeting_transcript,
)
from afg.shared.config import load_corpus_config
from afg.shared.logging import get_logger
from afg.shared.paths import PROJECT_ROOT, TABLES_DIR

logger = get_logger(__name__)

MANIFEST_CSV_NAME = "transcripts_manifest.csv"

_GIT_TIMEOUT_SECONDS = 5

# Paths whose contents can change the rendered output. The ``-dirty`` flag on
# :func:`renderer_revision` is computed over these alone -- see its docstring.
_RENDER_SOURCE_PATHS: tuple[str, ...] = ("src/afg/corpus", "src/afg/shared/paths.py")


def renderer_revision() -> str:
    """Return the git revision that produced a render, for provenance (the front matter's
    ``renderer`` field and the manifest's ``renderer_revision`` column), with a ``-dirty``
    suffix when the rendering code itself has uncommitted changes.

    BOTH halves are SCOPED to :data:`_RENDER_SOURCE_PATHS` rather than the whole
    repository, and this is deliberate. The field answers "which code produced this text",
    so only paths that can change the text may move it.

    * The revision is the last commit that touched those paths, not ``HEAD``. Using
      ``HEAD`` couples the stamp to every unrelated commit -- including the commit of the
      manifest itself, which is circular: committing the manifest moves ``HEAD``, which
      rewrites the front matter, which changes every ``sha256_md`` in the manifest. The
      render would never converge.
    * The dirty flag uses a scoped ``git status``. Unscoped, it also reports untracked and
      unrelated files, so the previous render rewriting the manifest would mark the next
      one ``-dirty`` on its own.

    Together these make a re-render over an unchanged corpus a genuine no-op: byte-identical
    artifacts and an empty ``git diff``.

    Returns the literal ``"unknown"`` -- never raises -- when git is unavailable or any
    call fails; this is provenance metadata, not control flow.
    """
    try:
        rev_result = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", *_RENDER_SOURCE_PATHS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
        if rev_result.returncode != 0:
            return "unknown"
        revision = rev_result.stdout.strip()
        if not revision:
            return "unknown"

        status_result = subprocess.run(
            ["git", "status", "--porcelain", "--", *_RENDER_SOURCE_PATHS],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
        if status_result.returncode == 0 and status_result.stdout.strip():
            revision += "-dirty"
        return revision
    except Exception:
        logger.warning("Could not determine renderer revision; falling back to 'unknown'.")
        return "unknown"


def discover_meeting_ids(ami_root: Path, series_filter: Sequence[str] | None = None) -> list[str]:
    """Discover every meeting id with a words-layer file under ``ami_root``, optionally
    restricted to the given series ids (e.g. ``["IS1004"]``). Sorted for deterministic
    processing order."""
    words_files = discover_layer_files(ami_root, AnnotationLayer.WORDS)
    meeting_ids = sorted({f.meeting_id for f in words_files})
    if series_filter:
        allowed = set(series_filter)
        meeting_ids = [m for m in meeting_ids if m[:-1] in allowed]
    return meeting_ids


def _source_archive_stem() -> str:
    """The AMI annotations archive filename, without its ``.zip`` extension (e.g.
    ``ami_public_manual_1.6.2``), read from ``config/corpus.toml`` -- the single place
    that name is already declared."""
    cfg = load_corpus_config()
    filename: str = cfg["corpus"]["annotations"]["filename"]
    return Path(filename).stem


def _licence_name() -> str:
    cfg = load_corpus_config()
    name: str = cfg["corpus"]["licence"]["name"]
    return name


def _build_front_matter(
    meeting_id: str,
    series: str,
    letter: str,
    speakers: Mapping[str, str],
    turns: int,
    characters: int,
    revision: str,
) -> str:
    """Hand-written, plain ``key: value`` front matter -- no YAML dependency (see module
    docstring)."""
    lines = [
        "---",
        f"meeting_id: {meeting_id}",
        f"series: {series}",
        f"letter: {letter}",
        f"source: {_source_archive_stem()}",
        f"licence: {_licence_name()}",
        f"renderer: afg.corpus.render@{revision}",
        "speakers:",
    ]
    for agent in sorted(speakers):
        lines.append(f"  {agent}: {speakers[agent]}")
    lines.append(f"turns: {turns}")
    lines.append(f"characters: {characters}")
    lines.append("---")
    return "\n".join(lines)


def parse_front_matter(markdown_text: str) -> tuple[dict[str, object], str]:
    """Parse a rendered transcript's front matter back into a dict, plus the body that
    follows it.

    The front matter is plain ``key: value`` lines (see module docstring); ``speakers``
    is the one nested mapping, indented two spaces, parsed into a ``dict[str, str]``.
    Every other value is returned as its raw string -- this project does not add a YAML
    dependency to infer types, and callers that need an int (e.g. ``turns``) convert it
    themselves.

    Raises:
        ValueError: if the opening or closing ``---`` marker is missing.
    """
    lines = markdown_text.split("\n")
    if not lines or lines[0] != "---":
        raise ValueError("Missing front matter opening '---'.")

    fields: dict[str, object] = {}
    i = 1
    while i < len(lines) and lines[i] != "---":
        line = lines[i]
        if line == "speakers:":
            speakers: dict[str, str] = {}
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                key, _, value = lines[i].strip().partition(": ")
                speakers[key] = value
                i += 1
            fields["speakers"] = speakers
            continue
        key, _, value = line.partition(": ")
        fields[key] = value
        i += 1

    if i >= len(lines):
        raise ValueError("Missing front matter closing '---'.")

    body_start = i + 1
    if body_start < len(lines) and lines[body_start] == "":
        body_start += 1
    body = "\n".join(lines[body_start:])
    return fields, body


@dataclass(frozen=True, slots=True)
class MeetingArtifacts:
    """One meeting's rendered ``.md`` text and ``.jsonl`` lines, plus the stats needed
    for the manifest row -- everything :func:`write_meeting_artifacts` needs to freeze
    to disk."""

    meeting_id: str
    series: str
    letter: str
    speakers: dict[str, str]
    markdown: str
    jsonl_lines: list[str]
    turn_count: int
    dialogue_act_count: int
    character_count: int


def render_meeting_artifacts(
    ami_root: Path, meeting_id: str, revision: str
) -> MeetingArtifacts | None:
    """Render one meeting's ``.md`` text and ``.jsonl`` lines from
    :mod:`afg.corpus.transcripts`'s segment-level and dialogue-act-level rendering.

    Returns ``None`` when the meeting has no renderable turns (mirrors
    :func:`afg.corpus.transcripts.render_meeting_transcript`'s empty-list-on-missing-data
    behaviour) -- callers should skip such a meeting rather than write empty files for it.
    """
    turns = render_meeting_transcript(ami_root, meeting_id)
    if not turns:
        return None
    acts = render_meeting_dialogue_acts(ami_root, meeting_id)

    acts_by_speaker: dict[str, list[DialogueActTurn]] = {}
    for act in acts:
        acts_by_speaker.setdefault(act.speaker_id, []).append(act)

    speakers: dict[str, str] = {}
    for turn in turns:
        speakers.setdefault(turn.speaker_id, turn.role_label)

    body_parts: list[str] = []
    jsonl_lines: list[str] = []
    pos = 0
    for index, turn in enumerate(turns):
        if index > 0:
            body_parts.append("\n\n")
            pos += 2

        prefix = f"{turn.role_label}: "
        body_parts.append(prefix)
        pos += len(prefix)
        char_start = pos

        body_parts.append(turn.text)
        pos += len(turn.text)
        char_end = pos

        overlapping = [
            act.dialogue_act_id
            for act in acts_by_speaker.get(turn.speaker_id, [])
            if act.word_start_index <= turn.word_end_index
            and turn.word_start_index <= act.word_end_index
        ]

        record = {
            "meeting_id": meeting_id,
            "turn_index": index,
            "speaker": turn.speaker_id,
            "role": turn.role_label,
            "start": turn.start_time,
            "end": turn.end_time,
            "char_start": char_start,
            "char_end": char_end,
            "dialogue_act_ids": overlapping,
            "text": turn.text,
        }
        jsonl_lines.append(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )

    body = "".join(body_parts)
    series, letter = meeting_id[:-1], meeting_id[-1]
    front_matter = _build_front_matter(
        meeting_id, series, letter, speakers, len(turns), len(body), revision
    )
    markdown = front_matter + "\n\n" + body

    return MeetingArtifacts(
        meeting_id=meeting_id,
        series=series,
        letter=letter,
        speakers=speakers,
        markdown=markdown,
        jsonl_lines=jsonl_lines,
        turn_count=len(turns),
        dialogue_act_count=len(acts),
        character_count=len(body),
    )


def write_meeting_artifacts(artifacts: MeetingArtifacts, out_dir: Path) -> tuple[Path, Path]:
    """Write one meeting's ``.md`` and ``.jsonl`` files to ``out_dir``. Always
    overwrites; refusing to overwrite an existing non-empty output directory is the
    CLI's ``--force`` gate, not this function's concern."""
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{artifacts.meeting_id}.md"
    jsonl_path = out_dir / f"{artifacts.meeting_id}.jsonl"
    md_path.write_text(artifacts.markdown, encoding="utf-8")
    jsonl_text = "\n".join(artifacts.jsonl_lines)
    if jsonl_text:
        jsonl_text += "\n"
    jsonl_path.write_text(jsonl_text, encoding="utf-8")
    return md_path, jsonl_path


def sha256_of_file(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes on disk -- used both to populate the
    manifest and, in tests, to verify it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ManifestRow:
    """One row of ``reports/tables/transcripts_manifest.csv``."""

    meeting_id: str
    series: str
    letter: str
    speakers: str
    turns: int
    dialogue_acts: int
    characters: int
    sha256_md: str
    sha256_jsonl: str
    renderer_revision: str
    source_archive: str


def write_manifest_csv(rows: Sequence[ManifestRow], out_dir: Path = TABLES_DIR) -> Path:
    """Write the freeze manifest to ``reports/tables/transcripts_manifest.csv``, one row
    per rendered meeting, sorted by ``meeting_id`` for a stable, diffable file.

    ``lineterminator="\n"`` is not cosmetic. ``csv.writer`` defaults to CRLF, which git
    normalizes to LF on commit -- so a manifest written here would differ from the one
    checked out, and the next render would produce a spurious diff. That would quietly
    destroy the reproducibility evidence this file exists to provide. It also matches the
    other tracked tables under ``reports/tables/``, which are all LF.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / MANIFEST_CSV_NAME
    with out_path.open("w", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            [
                "meeting_id",
                "series",
                "letter",
                "speakers",
                "turns",
                "dialogue_acts",
                "characters",
                "sha256_md",
                "sha256_jsonl",
                "renderer_revision",
                "source_archive",
            ]
        )
        for row in sorted(rows, key=lambda r: r.meeting_id):
            writer.writerow(
                [
                    row.meeting_id,
                    row.series,
                    row.letter,
                    row.speakers,
                    row.turns,
                    row.dialogue_acts,
                    row.characters,
                    row.sha256_md,
                    row.sha256_jsonl,
                    row.renderer_revision,
                    row.source_archive,
                ]
            )
    logger.info("Wrote transcripts manifest to %s", out_path)
    return out_path


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Aggregate result of one ``render_meetings`` call, for the CLI's summary."""

    meeting_ids: tuple[str, ...]
    total_turns: int
    total_characters: int
    renderer_revision: str
    out_dir: Path
    manifest_path: Path


def render_meetings(
    ami_root: Path,
    meeting_ids: Sequence[str],
    out_dir: Path,
    manifest_dir: Path = TABLES_DIR,
) -> RenderResult:
    """Render every meeting in ``meeting_ids`` to ``<out_dir>/<meeting_id>.{md,jsonl}``
    and write the manifest to ``<manifest_dir>/transcripts_manifest.csv``.

    Rendering twice over an unchanged corpus and an unchanged renderer MUST produce
    byte-identical files and therefore an empty ``git diff`` on the manifest -- there are
    no timestamps anywhere in either artifact, by design.

    A meeting with no renderable turns is skipped (logged, not raised) and does not
    appear in the manifest.
    """
    revision = renderer_revision()
    rows: list[ManifestRow] = []
    total_turns = 0
    total_characters = 0

    for meeting_id in meeting_ids:
        artifacts = render_meeting_artifacts(ami_root, meeting_id, revision)
        if artifacts is None:
            logger.info("Skipping %s: no renderable turns.", meeting_id)
            continue
        md_path, jsonl_path = write_meeting_artifacts(artifacts, out_dir)

        speakers_str = ";".join(f"{k}:{v}" for k, v in sorted(artifacts.speakers.items()))
        rows.append(
            ManifestRow(
                meeting_id=artifacts.meeting_id,
                series=artifacts.series,
                letter=artifacts.letter,
                speakers=speakers_str,
                turns=artifacts.turn_count,
                dialogue_acts=artifacts.dialogue_act_count,
                characters=artifacts.character_count,
                sha256_md=sha256_of_file(md_path),
                sha256_jsonl=sha256_of_file(jsonl_path),
                renderer_revision=revision,
                source_archive=_source_archive_stem(),
            )
        )
        total_turns += artifacts.turn_count
        total_characters += artifacts.character_count

    manifest_path = write_manifest_csv(rows, out_dir=manifest_dir)

    return RenderResult(
        meeting_ids=tuple(sorted(row.meeting_id for row in rows)),
        total_turns=total_turns,
        total_characters=total_characters,
        renderer_revision=revision,
        out_dir=out_dir,
        manifest_path=manifest_path,
    )
