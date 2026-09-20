"""Build OE1 gold decisions from existing AMI annotation layers.

Thesis section 3 (OE1): the reused base is the abstractive summary's DECISIONS headers,
linked to dialogue acts through the extractive summary (Hsueh & Moore's operationalization,
preserved for comparability with the literature), plus the Decision Discussion
Segmentation layer.

``build_gold_decisions`` walks the following evidence chain, verified against a real
extracted copy of ``ami_public_manual_1.6.2`` (manual de anotacion secciones 2, 3, 6):

1. ``abstractive/<meeting>.abssumm.xml`` -- the ``<sentence>`` children of the
   ``<decisions>`` section are the raw decision sentences.
2. ``extractive/<meeting>.summlink.xml`` -- each ``<summlink>`` pairs an ``abstractive``
   pointer (a decision sentence) with an ``extractive`` pointer (a dialogue act). One
   sentence may have zero, one, or many summlinks.
3. ``dialogueActs/<meeting>.<speaker>.dialog-act.xml`` -- each ``<dact>`` has two hrefs;
   the one ending in ``.words.xml`` is the word span that constitutes the dialogue act's
   transcript.
4. ``words/<meeting>.<speaker>.words.xml`` -- the word span is an inclusive index range,
   in document order, over that speaker's word file. ``<w>`` elements carry text;
   ``<vocalsound>``, ``<disfmarker>``, ``<pause>``, ``<gap>``, and ``<nonvocalsound>``
   carry none and are rendered literally as ``<tagname>``.

CRITICAL: read this before touching ``machine_flags`` or the five human columns.

``build_gold_decisions`` produces the Task-A *working file* a human annotator edits, not a
finished gold set. Two things about its output are non-negotiable (manual section 2, "La
regla de oro"):

* ``status``, ``decision_object``, ``decision_content``, ``annotator``, and ``notes`` are
  ALWAYS written as the empty string by this function. Prefilling any of them -- even with
  a plausible-looking default -- would let the machine quietly make the human's call, which
  is exactly what the manual forbids: a human annotator must read ``evidence_text`` and
  decide, every time, including (especially) when the evidence contradicts the abstractive
  sentence.
* ``machine_flags`` is a triage HINT, never a verdict. It never writes to, or substitutes
  for, ``status``. A row with no flags is not "approved"; a row with a flag is not
  "rejected". Both still require full human review.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from afg.annotation.blocking import tokenize
from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.nxt import get_attr_by_local_name, get_href_targets, iter_elements, parse_xml
from afg.domain.decision import DecisionStatus

# --- Task-A row -----------------------------------------------------------------------

_EVIDENCE_MAX_CHARS = 2000
_TRUNCATION_SUFFIX = " […truncated]"

_CSV_COLUMNS = (
    "decision_id",
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_da_count",
    "evidence_text",
    "status",
    "decision_object",
    "decision_content",
    "annotator",
    "notes",
    "machine_flags",
)


@dataclass(frozen=True, slots=True)
class GoldDecisionRow:
    """One row of the Task-A working file (``<series>.decisions.csv``).

    The machine-populated columns only. ``status``, ``decision_object``,
    ``decision_content``, ``annotator``, and ``notes`` are not modeled here at all -- they
    are always written empty by :func:`write_gold_decisions_csv`, precisely so nothing in
    this module can ever accidentally populate them.
    """

    decision_id: str
    meeting_id: str
    source_sentence_id: str
    sentence_text: str
    evidence_da_count: int
    evidence_text: str
    machine_flags: str


def classify_decision_status(*, explicit: bool, accepted: bool, anchored: bool) -> DecisionStatus:
    """Apply the thesis section 5.2 three-condition test.

    A candidate is a decision proper (:attr:`DecisionStatus.ACCEPTED`) only if all three
    conditions hold. This function does not decide *which* of the three non-decision
    statuses applies when the candidate fails -- that requires the discourse context
    (was it an open proposal, an open question, or an opinion), which is a human judgment
    made during annotation, not derivable from three booleans alone. Callers with only
    these three booleans and a failing candidate should record :attr:`DecisionStatus.
    OPEN_PROPOSAL` as the conservative default and let a human annotator refine it.
    """
    if explicit and accepted and anchored:
        return DecisionStatus.ACCEPTED
    return DecisionStatus.OPEN_PROPOSAL


# --- NITE href parsing ------------------------------------------------------------------

_HREF_FRAGMENT_RE = re.compile(
    r"^(?P<file>[^#]+)#id\((?P<first>[^)]+)\)(?:\.\.id\((?P<last>[^)]+)\))?$"
)


def parse_nite_href(href: str) -> tuple[str, str, str | None]:
    """Split a NITE href into ``(filename, first_id, last_id)``.

    Handles both forms seen in the corpus: ``file.xml#id(a)`` (a single element, so
    ``last_id`` is ``None``) and ``file.xml#id(a)..id(b)`` (an inclusive index range, in
    document order, within ``file.xml``).

    Raises:
        ValueError: if ``href`` does not match either form.
    """
    match = _HREF_FRAGMENT_RE.match(href)
    if not match:
        raise ValueError(f"Unrecognized NITE href fragment: {href!r}")
    return match.group("file"), match.group("first"), match.group("last")


def _local_tag(element: etree._Element) -> str:
    tag = element.tag
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


# Word-level elements that carry no text of their own; rendered literally as "<tagname>"
# (manual section 3, step 4).
_NO_TEXT_WORD_TAGS = frozenset({"vocalsound", "disfmarker", "pause", "gap", "nonvocalsound"})


def render_word_element(element: etree._Element) -> str:
    """Render one ``words/`` child element as its transcript token.

    ``<w>`` elements render as their text content. The non-lexical event tags
    (``vocalsound``, ``disfmarker``, ``pause``, ``gap``, ``nonvocalsound``) carry no text
    and render literally as ``<tagname>``, angle brackets included -- this is what the
    manual's worked example (``IS1004c.A.dialog-act.dharshi.203``) shows for
    ``<disfmarker>``. Any other, unanticipated tag falls back to its own text if present,
    else to the same literal ``<tagname>`` rendering, rather than raising.
    """
    tag = _local_tag(element)
    if tag == "w":
        return (element.text or "").strip()
    if tag in _NO_TEXT_WORD_TAGS:
        return f"<{tag}>"
    text = (element.text or "").strip()
    return text if text else f"<{tag}>"


def resolve_word_span(
    elements: list[etree._Element],
    id_to_index: dict[str, int],
    first_id: str,
    last_id: str | None,
) -> list[etree._Element]:
    """Resolve a ``first_id[..last_id]`` NITE range into the elements it covers.

    ``elements`` and ``id_to_index`` describe one speaker's word file in document order
    (see :func:`_load_words_file`). Returns an empty list, rather than raising, when either
    id is not found in this file -- an evidence chain that cannot be resolved should
    degrade to "no evidence text", not crash the whole build.
    """
    start = id_to_index.get(first_id)
    if start is None:
        return []
    end = id_to_index.get(last_id) if last_id is not None else start
    if end is None:
        return []
    if end < start:
        start, end = end, start
    return elements[start : end + 1]


# --- corpus file access, cached per build_gold_decisions call ---------------------------


@dataclass(slots=True)
class _CorpusCache:
    """Per-call cache of parsed ``words/`` and ``dialogueActs/`` files.

    Each series build touches the same handful of words/dialogue-act files many times over
    (once per resolved dialogue act); this avoids re-parsing the same XML file repeatedly.
    """

    words_paths_by_name: dict[str, Path]
    dact_paths_by_name: dict[str, Path]
    _words_cache: dict[str, tuple[list[etree._Element], dict[str, int]]] = field(
        default_factory=dict
    )
    _dact_cache: dict[str, dict[str, etree._Element]] = field(default_factory=dict)

    def words_file(self, filename: str) -> tuple[list[etree._Element], dict[str, int]]:
        if filename not in self._words_cache:
            path = self.words_paths_by_name.get(filename)
            if path is None:
                self._words_cache[filename] = ([], {})
            else:
                root = parse_xml(path)
                elements = list(root)
                id_to_index = {
                    element_id: index
                    for index, el in enumerate(elements)
                    if (element_id := get_attr_by_local_name(el, "id")) is not None
                }
                self._words_cache[filename] = (elements, id_to_index)
        return self._words_cache[filename]

    def dact_by_id(self, filename: str) -> dict[str, etree._Element]:
        if filename not in self._dact_cache:
            path = self.dact_paths_by_name.get(filename)
            if path is None:
                self._dact_cache[filename] = {}
            else:
                root = parse_xml(path)
                self._dact_cache[filename] = {
                    dact_id: el
                    for el in iter_elements(root, "dact")
                    if (dact_id := get_attr_by_local_name(el, "id")) is not None
                }
        return self._dact_cache[filename]


def _build_corpus_cache(ami_root: Path) -> _CorpusCache:
    words_paths = {
        f.path.name: f.path for f in discover_layer_files(ami_root, AnnotationLayer.WORDS)
    }
    dact_paths = {
        f.path.name: f.path
        for f in discover_layer_files(ami_root, AnnotationLayer.DIALOGUE_ACTS)
    }
    return _CorpusCache(words_paths_by_name=words_paths, dact_paths_by_name=dact_paths)


def _resolve_dialogue_act(href: str, cache: _CorpusCache) -> tuple[str, str] | None:
    """Resolve one ``extractive`` summlink href to ``(speaker, rendered_text)``.

    Returns ``None`` when any link in the chain (dact id, its ``.words.xml`` pointer, or
    the word span itself) cannot be resolved -- callers treat that dialogue act as
    contributing to ``evidence_da_count`` but not to ``evidence_text``.
    """
    dact_filename, dact_id, _ = parse_nite_href(href)
    dact_el = cache.dact_by_id(dact_filename).get(dact_id)
    if dact_el is None:
        return None

    words_href = next(
        (
            target
            for target in get_href_targets(dact_el)
            if target.split("#", 1)[0].endswith(".words.xml")
        ),
        None,
    )
    if words_href is None:
        return None

    words_filename, first_id, last_id = parse_nite_href(words_href)
    elements, id_to_index = cache.words_file(words_filename)
    span = resolve_word_span(elements, id_to_index, first_id, last_id)
    if not span:
        return None

    text = " ".join(render_word_element(el) for el in span)
    # Dialogue-act filenames follow "<meeting>.<speaker>.dialog-act.xml"; the speaker
    # letter is the second '.'-delimited component (verified in nxt.py's NiteId docstring
    # for the sibling id format).
    parts = dact_filename.split(".")
    speaker = parts[1] if len(parts) > 1 else "?"
    return speaker, text


def _truncate_evidence(text: str, *, limit: int = _EVIDENCE_MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    if cut <= 0:
        cut = limit
    return text[:cut].rstrip() + _TRUNCATION_SUFFIX


def _summlinks_by_sentence(ami_root: Path, meeting_id: str) -> dict[str, list[str]]:
    """Map decision-sentence ``nite:id`` to its ordered list of extractive hrefs.

    Reads ``extractive/<meeting_id>.summlink.xml`` only (never ``*.extsumm.xml``, a
    different, unrelated layer that also lives under ``extractive/``, per manual section
    3 step 2). Order is document order within the summlink file, which is not guaranteed
    to be chronological (verified: the six summlinks for ``IS1004c.elana.s.29`` reference
    dact ids 213, 203, 220, 274, 228, 278 in that exact, non-monotonic order).
    """
    result: dict[str, list[str]] = {}
    for layer_file in discover_layer_files(ami_root, AnnotationLayer.EXTRACTIVE_SUMMARY_LINKS):
        if layer_file.meeting_id != meeting_id:
            continue
        root = parse_xml(layer_file.path)
        for summlink_el in iter_elements(root, "summlink"):
            abstractive_href: str | None = None
            extractive_href: str | None = None
            for pointer_el in summlink_el:
                role = pointer_el.get("role")
                href = pointer_el.get("href")
                if not href or not role:
                    continue
                if role == "abstractive":
                    abstractive_href = href
                elif role == "extractive":
                    extractive_href = href
            if abstractive_href is None or extractive_href is None:
                continue
            _, sentence_id, _ = parse_nite_href(abstractive_href)
            result.setdefault(sentence_id, []).append(extractive_href)
    return result


def _decision_sentences(ami_root: Path, meeting_id: str) -> list[tuple[str, str]]:
    """``(sentence_id, sentence_text)`` pairs from ``<decisions>``, in document order."""
    sentences: list[tuple[str, str]] = []
    for layer_file in discover_layer_files(ami_root, AnnotationLayer.ABSTRACTIVE_SUMMARY):
        if layer_file.meeting_id != meeting_id:
            continue
        root = parse_xml(layer_file.path)
        for decisions_el in iter_elements(root, "decisions"):
            for sentence_el in decisions_el:
                if _local_tag(sentence_el) != "sentence":
                    continue
                sentence_id = get_attr_by_local_name(sentence_el, "id")
                text = (sentence_el.text or "").strip()
                if not sentence_id or not text:
                    continue
                sentences.append((sentence_id, text))
    return sentences


# --- machine_flags heuristics -------------------------------------------------------------

_MIN_CONTENT_TOKENS = 4
_MIN_ENUMERATION_COMMAS = 2


def _looks_compound(sentence_text: str) -> bool:
    """Heuristic for ``posible_compuesta`` (manual section 2: "compuesta").

    UNMEASURED PRECISION -- this is a triage hint, not a classifier. It fires on either of
    two surface patterns that tend to co-occur with a sentence enumerating several
    decisions: (a) three or more comma-separated groups (i.e. at least two commas), the
    shape of the verified ``IS1004c.elana.s.29`` "base station, a button ..., 2 scroll
    wheels ..., a turbo button ..., and an on/off button" example; or (b) the literal
    substring ``" and "`` together with at least one comma, the shape of an enumeration
    closed by "..., and X". Neither pattern parses clause structure, so both false
    positives (a legitimately single decision with incidental commas) and false negatives
    (a compound decision with no commas at all) are expected and are the human
    annotator's to catch during Task A review.
    """
    comma_count = sentence_text.count(",")
    if comma_count >= _MIN_ENUMERATION_COMMAS:
        return True
    return " and " in sentence_text and comma_count >= 1


def _looks_short(sentence_text: str) -> bool:
    """Heuristic for ``frase_corta``: fewer than 4 content tokens.

    Reuses :func:`afg.annotation.blocking.tokenize` (lowercase, letters-only, length >= 3,
    stopwords dropped) so "content tokens" means the same thing here as it does for
    blocking -- e.g. ``"The control will be the approx."`` tokenizes to
    ``{"control", "approx"}`` (2 tokens), below the threshold.
    """
    return len(tokenize(sentence_text)) < _MIN_CONTENT_TOKENS


def machine_flags_for(*, evidence_da_count: int, sentence_text: str) -> str:
    """Compute the ``;``-separated ``machine_flags`` hint set for one decision row.

    See the module docstring: this is a triage hint, never a verdict. All three flags may
    co-occur; order is ``sin_evidencia``, ``posible_compuesta``, ``frase_corta``.
    """
    flags: list[str] = []
    if evidence_da_count == 0:
        flags.append("sin_evidencia")
    if _looks_compound(sentence_text):
        flags.append("posible_compuesta")
    if _looks_short(sentence_text):
        flags.append("frase_corta")
    return ";".join(flags)


# --- public API ---------------------------------------------------------------------------


def build_gold_decisions(ami_root: Path, series_id: str) -> list[GoldDecisionRow]:
    """Build the Task-A working file rows for ``series_id`` (manual sections 2, 3).

    Walks abstractive DECISIONS sentences -> summlink -> dialogue acts -> words (see the
    module docstring for the full chain) and returns one :class:`GoldDecisionRow` per
    decision sentence, in ``(meeting_id, document order)``.

    NEVER writes a verdict. ``status``, ``decision_object``, ``decision_content``,
    ``annotator``, and ``notes`` are not part of :class:`GoldDecisionRow` at all --
    :func:`write_gold_decisions_csv` writes them as the empty string, always. This
    function's only judgment calls are the ``machine_flags`` heuristics
    (:func:`_looks_compound`, :func:`_looks_short`) and ``sin_evidencia``, all of which are
    hints for a human triage pass, never a substitute for it.

    Returns an empty list (never raises) when the corpus or the series is missing or has
    no DECISIONS sentences -- callers (the CLI) are responsible for turning that into an
    actionable error message.
    """
    cache = _build_corpus_cache(ami_root)
    meeting_ids = sorted(
        {
            f.meeting_id
            for f in discover_layer_files(ami_root, AnnotationLayer.ABSTRACTIVE_SUMMARY)
            if f.meeting_id[:-1] == series_id
        }
    )

    rows: list[GoldDecisionRow] = []
    for meeting_id in meeting_ids:
        sentences = _decision_sentences(ami_root, meeting_id)
        if not sentences:
            continue
        summlinks = _summlinks_by_sentence(ami_root, meeting_id)

        for index, (sentence_id, sentence_text) in enumerate(sentences, start=1):
            extractive_hrefs = summlinks.get(sentence_id, [])
            evidence_parts: list[str] = []
            for href in extractive_hrefs:
                resolved = _resolve_dialogue_act(href, cache)
                if resolved is None:
                    continue
                speaker, text = resolved
                evidence_parts.append(f"{speaker}: {text}")

            evidence_text = _truncate_evidence(" | ".join(evidence_parts))
            evidence_da_count = len(extractive_hrefs)

            rows.append(
                GoldDecisionRow(
                    decision_id=f"{meeting_id}.d{index:02d}",
                    meeting_id=meeting_id,
                    source_sentence_id=sentence_id,
                    sentence_text=sentence_text,
                    evidence_da_count=evidence_da_count,
                    evidence_text=evidence_text,
                    machine_flags=machine_flags_for(
                        evidence_da_count=evidence_da_count, sentence_text=sentence_text
                    ),
                )
            )
    return rows


def write_gold_decisions_csv(rows: list[GoldDecisionRow], out_path: Path) -> Path:
    """Write ``rows`` to ``out_path`` with the manual's section-2 columns.

    ``status``, ``decision_object``, ``decision_content``, ``annotator``, and ``notes`` are
    always written as the empty string here -- this is the one place in the codebase that
    decides what goes in those columns, and the answer is always "nothing; a human fills
    this in" (see the module docstring).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_CSV_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row.decision_id,
                    row.meeting_id,
                    row.source_sentence_id,
                    row.sentence_text,
                    row.evidence_da_count,
                    row.evidence_text,
                    "",
                    "",
                    "",
                    "",
                    "",
                    row.machine_flags,
                ]
            )
    return out_path


# --- Task-A evidence finder (manual section 3.3) -------------------------------------------


class MeetingNotFoundError(RuntimeError):
    """Raised when no ``words/`` transcript files exist for the requested meeting id."""


@dataclass(frozen=True, slots=True)
class EvidenceHit:
    """One occurrence of a searched term in a meeting's transcript."""

    word_id: str
    speaker: str
    source_path: Path
    context: str


def find_term_occurrences(
    ami_root: Path, meeting_id: str, term: str, *, context_words: int = 25
) -> list[EvidenceHit]:
    """Search every speaker's ``words/<meeting_id>.<speaker>.words.xml`` for ``term``.

    This is the evidence finder assumed by manual section 3.3: the tool an annotator reaches
    for once a row's ``evidence_da_count`` is 0 and they have to find the supporting (or
    contradicting) passage themselves. Matching is case-insensitive and by whole word token
    (not substring): ``term`` must equal a ``<w>`` element's text after casefolding, so
    searching "turbo" does not also match "turbocharged". Each hit carries ``context_words``
    words of surrounding transcript on each side.

    Raises:
        MeetingNotFoundError: if no ``words/`` files exist for ``meeting_id`` at all --
            distinct from finding zero occurrences of ``term`` in a meeting that does exist.
    """
    words_files = [
        f
        for f in discover_layer_files(ami_root, AnnotationLayer.WORDS)
        if f.meeting_id == meeting_id
    ]
    if not words_files:
        raise MeetingNotFoundError(
            f"No words/ transcript files found for meeting {meeting_id!r} under {ami_root}."
        )

    term_lower = term.lower()
    hits: list[EvidenceHit] = []
    for layer_file in words_files:
        speaker = layer_file.path.name.split(".")[1] if "." in layer_file.path.name else "?"
        root = parse_xml(layer_file.path)
        elements = list(root)
        for index, element in enumerate(elements):
            if _local_tag(element) != "w":
                continue
            text = (element.text or "").strip()
            if text.lower() != term_lower:
                continue
            word_id = get_attr_by_local_name(element, "id") or ""
            start = max(0, index - context_words)
            end = min(len(elements), index + context_words + 1)
            context = " ".join(render_word_element(el) for el in elements[start:end])
            hits.append(
                EvidenceHit(
                    word_id=word_id,
                    speaker=speaker,
                    source_path=layer_file.path,
                    context=context,
                )
            )
    return hits
