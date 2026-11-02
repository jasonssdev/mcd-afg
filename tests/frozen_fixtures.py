"""Build a tiny frozen transcript (``.md`` + ``.jsonl``) with the real offset convention.

``write_frozen_meeting`` lays turns out exactly like :func:`afg.corpus.render
.render_meeting_artifacts`: front matter, a blank line, then ``ROLE: text`` blocks separated
by a blank line; ``char_start``/``char_end`` locate each turn's text inside the BODY (front
matter excluded), after the ``ROLE: `` prefix.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_frozen_meeting(
    directory: Path,
    meeting_id: str,
    turns: list[tuple[str, tuple[str, ...]]],
    *,
    role: str = "PM",
) -> str:
    """Write ``<meeting_id>.md`` and ``.jsonl`` for ``turns`` (text, acts); return the body."""
    parts: list[str] = []
    rows: list[str] = []
    pos = 0
    for index, (text, acts) in enumerate(turns):
        if index:
            parts.append("\n\n")
            pos += 2
        prefix = f"{role}: "
        parts.append(prefix)
        pos += len(prefix)
        start = pos
        parts.append(text)
        pos += len(text)
        rows.append(
            json.dumps(
                {
                    "meeting_id": meeting_id,
                    "turn_index": index,
                    "speaker": "A",
                    "role": role,
                    "text": text,
                    "start": None,
                    "end": None,
                    "char_start": start,
                    "char_end": pos,
                    "dialogue_act_ids": list(acts),
                }
            )
        )
    body = "".join(parts)
    front = (
        f"---\nmeeting_id: {meeting_id}\nseries: {meeting_id[:-1]}\nturns: {len(turns)}\n---\n\n"
    )
    (directory / f"{meeting_id}.md").write_text(front + body, encoding="utf-8")
    (directory / f"{meeting_id}.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return body
