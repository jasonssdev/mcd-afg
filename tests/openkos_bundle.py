"""Builders of OpenKOS v0.5.5 bundle files and frozen AMI transcripts for the adapter tests.

The decision file layout is the one OpenKOS v0.5.5 writes for a ``Decision`` concept (see
``tests/test_openkos_bundle_reader.py`` for the source lines); the frontmatter is dumped with
the same YAML settings as ``python-frontmatter`` (sorted keys, block style, 80 columns), so a
long description folds over two lines exactly as in a real bundle.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import yaml


def decision_file(
    *,
    title: str,
    subject: str,
    value: str,
    quotes: Sequence[tuple[str, str]],
) -> str:
    """One ``bundle/decisions/<slug>.md`` text.

    ``quotes`` is ``[(source_slug, evidence), ...]``: the first one is the creating source, the
    others are sources the decision was attached to (``## Update from`` sections).
    """
    description = f"{subject}: {value}"
    provenance = [f"sources/{slug}" for slug, _ in quotes]
    metadata: dict[str, object] = {
        "type": "Decision",
        "title": title,
        "description": description,
        "tags": [],
        "generated": {"by": "openkos 0.5.5", "at": "2004-11-23T09:00:00Z"},
        "status": "stable",
        "version": len(quotes),
        "freshness": "snapshot",
        "sensitivity": "private",
        "provenance": provenance,
        "sources": [{"id": ref, "resource": f"/{ref}.md"} for ref in provenance],
    }
    head = f"# {title}\n\n{description}\n\n{value}\n\n> {quotes[0][1]}"
    for slug, evidence in quotes[1:]:
        head += f"\n\n## Update from {slug.upper()} (sources/{slug})\n\n{value}\n\n> {evidence}"
    related = "\n".join(
        f"- [{ref}](/{ref}.md) — source this was extracted from" for ref in provenance
    )
    body = f"{head}\n\n## Related\n\n{related}\n"
    frontmatter = yaml.safe_dump(
        metadata, default_flow_style=False, allow_unicode=True, sort_keys=True
    )
    return f"---\n{frontmatter}---\n\n{body}\n"


def concept_file(
    *,
    title: str,
    description: str,
    turns: Sequence[str],
    provenance: Sequence[str],
    type_: str = "Concept",
) -> str:
    """One non-decision, non-source bundle file (concept, event, project, person).

    Same layout OpenKOS v0.5.5 writes: ``# title``, the description, then the transcript
    excerpt as ``ROLE: text`` turns separated by blank lines, then ``## Related``.
    ``provenance`` holds source slugs (``es2015b``).
    """
    refs = [f"sources/{slug}" for slug in provenance]
    metadata: dict[str, object] = {
        "type": type_,
        "title": title,
        "description": description,
        "tags": [],
        "generated": {"by": "openkos/0.5.5", "at": "2004-11-23T09:00:00Z"},
        "status": "stable",
        "version": 1,
        "freshness": "snapshot",
        "sensitivity": "private",
        "provenance": refs,
        "sources": [{"id": ref, "resource": f"/{ref}.md"} for ref in refs],
    }
    related = "\n".join(f"- [{ref}](/{ref}.md) — source this was extracted from" for ref in refs)
    body = f"# {title}\n\n{description}\n\n" + "\n\n".join(turns)
    frontmatter = yaml.safe_dump(
        metadata, default_flow_style=False, allow_unicode=True, sort_keys=True
    )
    return f"---\n{frontmatter}---\n\n{body}\n\n## Related\n\n{related}\n"


def source_file(slug: str, transcript: str) -> str:
    """One ``bundle/sources/<slug>.md``: the whole transcript under ``## Source content``."""
    metadata = {"type": "Source", "title": slug.upper(), "resource": f"raw/{slug}.md"}
    frontmatter = yaml.safe_dump(metadata, default_flow_style=False, sort_keys=True)
    return f"---\n{frontmatter}---\n\n# {slug.upper()}\n\n## Source content\n\n{transcript}\n"


def write_bundle_file(bundle_dir: Path, folder: str, name: str, text: str) -> Path:
    path = bundle_dir / folder / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_decision(bundle_dir: Path, name: str, text: str) -> Path:
    path = bundle_dir / "decisions" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_meeting(
    transcripts_dir: Path, meeting_id: str, rows: Sequence[tuple[str, str, tuple[str, ...]]]
) -> None:
    """Write ``<meeting>.md`` and ``<meeting>.jsonl`` in the frozen-transcript layout."""
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    body = ""
    lines: list[str] = []
    for index, (role, text, acts) in enumerate(rows):
        prefix = f"{role}: "
        start = len(body) + len(prefix)
        body += prefix + text
        lines.append(
            json.dumps(
                {
                    "meeting_id": meeting_id,
                    "turn_index": index,
                    "speaker": role,
                    "role": role,
                    "text": text,
                    "start": None,
                    "end": None,
                    "char_start": start,
                    "char_end": start + len(text),
                    "dialogue_act_ids": list(acts),
                }
            )
        )
        body += "\n\n"
    front = f"---\nmeeting_id: {meeting_id}\nseries: {meeting_id[:-1]}\n---\n\n"
    (transcripts_dir / f"{meeting_id}.md").write_text(front + body.rstrip("\n"), encoding="utf-8")
    (transcripts_dir / f"{meeting_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
