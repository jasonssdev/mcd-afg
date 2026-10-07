"""The two answer prompts C1 shares with OpenKOS, copied byte for byte (ADR 0006).

C2 and C3 answer through ``openkos query``, which makes two model calls: a sufficiency
check (``answer/sufficiency``) and the answer synthesis (``answer/system``). C1 answers
with the same two prompts so that the conditions differ only in what they retrieve
(thesis section 5.3). The files under ``prompts/answer/`` are copies of
``src/openkos/prompts/answer/`` at openkos commit ``473b3fbb`` and are never edited: their
wording speaks of "concepts" and a "compiled bundle", and that mismatch with transcript
chunks is a declared limitation, not something to fix here.

Loading mirrors ``openkos.llm.prompts``: the file is read as bytes and decoded as UTF-8
with no newline translation (``.gitattributes`` marks the folder ``-text``), and each
``{{name}}`` placeholder is filled strictly -- a missing or an extra argument raises.
The placeholder values are OpenKOS's own constants from ``openkos.retrieval.answer``.
"""

from __future__ import annotations

import hashlib
import re
from importlib import resources

PINNED_RAW_SHA256 = {
    "system": "9cbf11e8ac9f8220253b233f1475b5cea9716b86b5868ce78ae31b235917119c",
    "sufficiency": "afc4644b27500c2cd69ea6c28919275d5447baaf7ce8ff938e9de7add7936f56",
}

# openkos.retrieval.answer: _ATTRIBUTION_KEYWORD, _ATTRIBUTION_NONE, _SUFFICIENCY_NONE.
ATTRIBUTION_KEYWORD = "USED"
ATTRIBUTION_NONE = "none"
SUFFICIENCY_NONE = "NONE"

_PLACEHOLDER_RE = re.compile(r"\{\{([a-z0-9_]+)\}\}")


def read_raw_prompt(name: str) -> str:
    """Return the prompt file ``prompts/answer/<name>.md`` exactly as stored."""
    if name not in PINNED_RAW_SHA256:
        raise ValueError(
            f"unknown answer prompt {name!r}; expected one of {sorted(PINNED_RAW_SHA256)}"
        )
    path = resources.files("afg.conditions") / "prompts" / "answer" / f"{name}.md"
    return path.read_bytes().decode("utf-8")


def render_prompt(name: str, **placeholders: str) -> str:
    """Fill every ``{{name}}`` of the prompt, raising if the arguments do not match exactly."""
    text = read_raw_prompt(name)
    wanted = set(_PLACEHOLDER_RE.findall(text))
    if wanted != set(placeholders):
        raise ValueError(
            f"prompt {name!r}: placeholders {sorted(wanted)} do not match arguments "
            f"{sorted(placeholders)}"
        )
    return _PLACEHOLDER_RE.sub(lambda match: placeholders[match.group(1)], text)


def system_prompt() -> str:
    """The synthesis prompt, filled exactly as ``openkos query`` fills it."""
    return render_prompt(
        "system", attribution_keyword=ATTRIBUTION_KEYWORD, attribution_none=ATTRIBUTION_NONE
    )


def sufficiency_prompt() -> str:
    """The sufficiency-check prompt, filled exactly as ``openkos query`` fills it."""
    return render_prompt("sufficiency", sufficiency_none=SUFFICIENCY_NONE)


def sent_prompt_sha256(text: str) -> str:
    """Full SHA-256 hex of the prompt bytes as sent, the scheme of ``openkos query --json``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
