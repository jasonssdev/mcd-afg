"""The answer prompt of C1, a conventional RAG (thesis section 5.3, ADR 0006 as amended).

C1 is the baseline "retrieve, then generate" system, so its prompt is a generic one rather than
OpenKOS's. The template adapts the widely used LangChain hub prompt ``rlm/rag-prompt``
("You are an assistant for question-answering tasks. Use the following pieces of retrieved
context to answer the question. If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.") in two ways: a fixed sentence to
reply with when the context lacks the answer, so abstention is detectable, and an instruction
to cite the numbered context blocks inline as ``[n]``.

The file ``prompts/c1/answer.md`` is read as bytes and decoded as UTF-8 with no newline
translation (``.gitattributes`` marks the folder ``-text``), and its SHA-256 is pinned: editing
it changes what C1 sends to the model and needs a new pin and a new run.
"""

from __future__ import annotations

import hashlib
from importlib import resources

PINNED_SHA256 = "2764df018d82e31a39a6bb46590fcd892e9f4fdfa0934cb7cb5adcbe68edbd60"

# The reply the prompt asks for when the context does not contain the answer.
ABSTENTION_SENTENCE = "I don't know."

_TRIM = "\"'`*.!? \t\n"


def answer_prompt() -> str:
    """The system prompt of C1, exactly as stored."""
    path = resources.files("afg.conditions") / "prompts" / "c1" / "answer.md"
    return path.read_bytes().decode("utf-8")


def is_abstention(reply: str) -> bool:
    """Whether ``reply`` IS the fixed sentence, modulo case, quotes and trailing punctuation."""

    def normal(text: str) -> str:
        return text.replace("\N{RIGHT SINGLE QUOTATION MARK}", "'").strip(_TRIM).casefold()

    return normal(reply) == normal(ABSTENTION_SENTENCE)


def sent_prompt_sha256(text: str) -> str:
    """Full SHA-256 hex of the prompt bytes as sent, the scheme of ``openkos query --json``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
