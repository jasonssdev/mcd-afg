"""Low-level NXT (NITE XML Toolkit) XML helpers.

AMI's manual annotations are distributed as a set of NXT-format XML files, one family of
files per annotation layer, cross-referenced by pointers rather than nested inside a
single document. This module intentionally does **not** hard-code the corpus's on-disk
layout: every path is discovered by globbing, and every field access degrades to
``None``/``[]`` rather than raising ``KeyError``/``AttributeError``, so the parser survives
minor layout differences between corpus releases.

VERIFIED at paso cero (2026-09-20) against a real extracted copy of
``ami_public_manual_1.6.2``. The per-layer subdirectory + ``<meeting_id>[.<speaker>].<layer>.xml``
convention holds, with one wrinkle worth knowing: the Decision Discussion Segmentation layer
lives one level deeper, at ``decision/manual/<meeting_id>.decision.xml``. Discovery is
``rglob``, so nesting is handled; see ``corpus/layers.py`` for the verified per-layer
patterns and their observed file counts.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from lxml import etree


class NxtParseError(RuntimeError):
    """Raised when a file that should be NXT XML fails to parse."""


@dataclass(frozen=True, slots=True)
class NiteId:
    """A parsed NITE id, e.g. ``ES2015a.B.dialogue-act.4``.

    VERIFIED (2026-09-20): the meeting id is always the first '.'-delimited component.
    The remaining components genuinely do vary by layer and often embed the annotator's
    name -- e.g. ``IS1004c.elana.s.29`` (abstractive sentence) versus
    ``IS1004c.A.dialog-act.dharshi.203`` (dialogue act, with the speaker letter second).
    Callers should still treat everything after the meeting id as opaque unless they have
    verified that specific layer's id format.
    """

    raw: str
    meeting_id: str

    @classmethod
    def parse(cls, raw: str) -> NiteId:
        meeting_id = raw.split(".", 1)[0] if "." in raw else raw
        return cls(raw=raw, meeting_id=meeting_id)


def parse_xml(path: Path) -> etree._Element:
    """Parse an XML file and return its root element.

    Raises:
        NxtParseError: if the file does not exist or is not well-formed XML. Never
            silently returns a partial tree.
    """
    if not path.exists():
        raise NxtParseError(f"Annotation file not found: {path}")
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        raise NxtParseError(f"Malformed XML in {path}: {exc}") from exc
    return tree.getroot()


def iter_elements(root: etree._Element, tag: str) -> Iterator[etree._Element]:
    """Yield every descendant element whose local tag matches ``tag``, ignoring namespaces.

    NXT files may or may not declare a namespace depending on release; matching on the
    local name rather than a hard-coded namespace URI avoids silently finding zero
    elements because of a namespace mismatch we have not verified.
    """
    for element in root.iter():
        qname = etree.QName(element.tag) if isinstance(element.tag, str) else None
        if qname is not None and qname.localname == tag:
            yield element


def find_by_local_name(root: etree._Element, local_name: str) -> list[etree._Element]:
    """Return every element with the given local tag name, namespace-agnostic."""
    return root.xpath(f"//*[local-name()='{local_name}']")


def get_attr(element: etree._Element, name: str, default: str | None = None) -> str | None:
    """Read an attribute, tolerating its absence instead of raising."""
    return element.get(name, default)


def get_attr_by_local_name(
    element: etree._Element, local_name: str, default: str | None = None
) -> str | None:
    """Read an attribute by local name, ignoring any namespace prefix.

    NXT commonly declares ids as a namespaced ``nite:id`` attribute (e.g. on
    ``corpusResources/participants.xml``'s ``<participant>`` elements). lxml's
    ``element.get("id")`` does not match that -- the namespaced attribute's internal key
    is ``"{http://nite.sourceforge.net/}id"`` -- so this checks the plain attribute first
    and falls back to matching any attribute whose local part (after a ``}``) equals
    ``local_name``, the same namespace-agnostic philosophy as :func:`find_by_local_name`.
    """
    value = element.get(local_name)
    if value is not None:
        return value
    for key, val in element.attrib.items():
        if isinstance(key, str) and key.rsplit("}", 1)[-1] == local_name:
            return val
    return default


def get_href_targets(element: etree._Element) -> list[str]:
    """Extract NITE pointer targets from a ``<nite:pointer href="...">``-style element.

    VERIFIED (2026-09-20) against ``ami_public_manual_1.6.2``. Both forms occur:
    ``filename.xml#id(single.nite.id)`` (e.g. ``summlink`` pointers) and
    ``filename.xml#id(first)..id(last)`` (e.g. ``decision`` and ``dact`` children, where the
    pair denotes an inclusive INDEX range in document order within that file).

    Two traps this helper deliberately does not hide from callers:

    * A ``dact`` element carries **two** hrefs -- one to ``da-types.xml#id(ami_da_N)``
      (the dialogue-act type) and one to ``<meeting>.<speaker>.words.xml#id(a)..id(b)``.
      Callers wanting transcript text must filter on the ``.words.xml`` filename.
    * Resolving an ``id(a)..id(b)`` range requires the target file's document order; this
      helper returns the raw href strings only and does not resolve them.
    """
    hrefs: list[str] = []
    href = element.get("href")
    if href:
        hrefs.append(href)
    for child in element.iter():
        child_href = child.get("href")
        if child_href and child_href not in hrefs:
            hrefs.append(child_href)
    return hrefs


def local_name(element: etree._Element) -> str | None:
    """Return an element's local tag name, ignoring any namespace prefix.

    Returns ``None`` for a non-element node (comments, processing instructions), whose
    ``.tag`` is a callable rather than a string -- callers iterating raw children (e.g.
    ``for el in root``) must guard against those, since ``etree.QName`` raises on them.
    """
    if not isinstance(element.tag, str):
        return None
    return etree.QName(element.tag).localname


_ID_TOKEN_RE = re.compile(r"id\(([^()]+)\)")


def parse_href_ids(href: str) -> list[str]:
    """Extract the id token(s) referenced by a NITE href, in encounter order.

    VERIFIED (2026-09-21) against both href shapes documented on :func:`get_href_targets`:
    a single-id href (``file.xml#id(x)``) yields one id; a range href
    (``file.xml#id(a)..id(b)``) yields exactly two ids -- the range's inclusive start and
    end. This function knows nothing about document order and never expands a range into
    every id it covers; that is :func:`resolve_id_range`'s job, given the target file's
    id -> document-order-index mapping.
    """
    fragment = href.split("#", 1)[-1] if "#" in href else href
    return _ID_TOKEN_RE.findall(fragment)


def href_filename(href: str) -> str:
    """Return the filename portion of a NITE href, before the ``#``.

    Needed to implement the ``dact`` filtering trap documented on
    :func:`get_href_targets`: a dialogue act's ``da-types.xml`` href must be told apart
    from its ``<meeting>.<speaker>.words.xml`` href before either is resolved.
    """
    return href.split("#", 1)[0]


def resolve_id_range(ids: Sequence[str], index_by_id: Mapping[str, int]) -> tuple[int, int] | None:
    """Resolve parsed href id(s) to an inclusive ``(start, end)`` index pair, given a
    target file's document-order ``id -> index`` mapping (e.g. built while parsing a
    ``words.xml`` file in document order, keeping every element -- including non-lexical
    ones -- so no id's index silently shifts).

    ``ids`` is what :func:`parse_href_ids` returns: one id for a single-target href, two
    for an ``id(a)..id(b)`` range. VERIFIED (2026-09-21) against ``ami_public_manual_1.6.2``:
    the range is INCLUSIVE of both endpoints, over document order -- not a two-element set
    naming only the first and last member.

    Returns ``None`` (never raises) when ``ids`` is empty or either endpoint is absent
    from ``index_by_id`` (a dangling reference) -- the caller should skip that href rather
    than guess a range from a partial match.
    """
    if not ids:
        return None
    start = index_by_id.get(ids[0])
    if start is None:
        return None
    end = index_by_id.get(ids[-1])
    if end is None:
        return None
    return (start, end) if start <= end else (end, start)


def discover_annotation_files(ami_root: Path, pattern: str) -> list[Path]:
    """Glob for annotation files under ``ami_root`` matching ``pattern``.

    Centralizing the glob here (rather than scattering ``ami_root.glob(...)`` calls across
    the codebase) means the single place that needs correcting, once the real corpus
    layout is confirmed at paso cero, is this function.
    """
    if not ami_root.exists():
        return []
    return sorted(ami_root.rglob(pattern))
