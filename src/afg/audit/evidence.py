"""Summlink-anchoring and role-authorship measurements (thesis section 5.1 data audit).

``role_authorship`` is the headline finding this module exists to produce: which scenario
role (PM/ME/UI/ID) authored the dialogue acts that support each decision, resolved via
``extractive/<meeting>.summlink.xml`` (decision sentence -> dialogue act) and
``corpusResources/meetings.xml`` (dialogue-act speaker letter -> role), never guessed.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from afg.annotation.blocking import decisions_from_abstractive, source_sentence_id
from afg.audit.decisions import site_prefix
from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.nxt import find_by_local_name, get_attr, iter_elements, parse_xml
from afg.shared.paths import AMI_DIR

_POINTER_ID_RE = re.compile(r"id\(([^)]+)\)")


def _parse_summlink_file(path: Path) -> list[tuple[str, str]]:
    """Return ``(abstractive_sentence_id, extractive_dialogue_act_id)`` pairs from one
    ``*.summlink.xml`` file.

    A ``<summlink>`` element carries two ``<nite:pointer>`` children distinguished by their
    ``role`` attribute (``"abstractive"`` / ``"extractive"``); this links ALL abstractive
    sentences (abstract/actions/decisions/problems), not only DECISIONS sentences --
    callers filter to the sentence ids they care about.
    """
    root = parse_xml(path)
    pairs: list[tuple[str, str]] = []
    for summlink_el in iter_elements(root, "summlink"):
        extractive_id: str | None = None
        abstractive_id: str | None = None
        for pointer_el in summlink_el:
            tag = pointer_el.tag
            if not isinstance(tag, str) or tag.split("}")[-1] != "pointer":
                continue
            href = pointer_el.get("href")
            role = pointer_el.get("role")
            if not href or not role:
                continue
            match = _POINTER_ID_RE.search(href)
            if not match:
                continue
            if role == "extractive":
                extractive_id = match.group(1)
            elif role == "abstractive":
                abstractive_id = match.group(1)
        if extractive_id and abstractive_id:
            pairs.append((abstractive_id, extractive_id))
    return pairs


def _decision_evidence_map(
    ami_root: Path, series_id: str, decision_ids: set[str]
) -> dict[str, list[str]]:
    """Map each decision sentence id in ``decision_ids`` to its supporting dialogue-act
    ids, via every summlink file belonging to ``series_id``."""
    evidence: dict[str, list[str]] = {}
    layer_files = [
        f
        for f in discover_layer_files(ami_root, AnnotationLayer.EXTRACTIVE_SUMMARY_LINKS)
        if f.meeting_id[:-1] == series_id
    ]
    for layer_file in layer_files:
        for abstractive_id, extractive_id in _parse_summlink_file(layer_file.path):
            if abstractive_id in decision_ids:
                evidence.setdefault(abstractive_id, []).append(extractive_id)
    return evidence


def _role_lookup(ami_root: Path) -> dict[tuple[str, str], str]:
    """``(meeting_id, nxt_agent_letter) -> role code`` (e.g. ``"PM"``), read once from
    ``corpusResources/meetings.xml``. Returns an empty mapping if that file is absent."""
    meetings_path = ami_root / "corpusResources" / "meetings.xml"
    if not meetings_path.exists():
        return {}
    root = parse_xml(meetings_path)
    lookup: dict[tuple[str, str], str] = {}
    for meeting_el in find_by_local_name(root, "meeting"):
        observation = get_attr(meeting_el, "observation")
        if not observation:
            continue
        for speaker_el in iter_elements(meeting_el, "speaker"):
            agent = get_attr(speaker_el, "nxt_agent")
            role = get_attr(speaker_el, "role")
            if agent and role:
                lookup[(observation, agent)] = role
    return lookup


def _dialogue_act_speaker_letter(dialogue_act_id: str) -> str | None:
    """The speaker letter (2nd '.'-delimited component) of a dialogue-act id, e.g.
    ``"IS1004c.A.dialog-act.dharshi.8"`` -> ``"A"``."""
    parts = dialogue_act_id.split(".")
    return parts[1] if len(parts) > 1 else None


def anchoring_rates(ami_root: Path = AMI_DIR, series: Sequence[str] = ()) -> pd.DataFrame:
    """Per meeting, per series, and overall: how many decision sentences in ``series``
    have at least one summlink-linked dialogue act (anchored), how many have zero, and the
    anchoring rate.

    Columns: ``scope`` (str, one of ``"meeting"``/``"series"``/``"total"``), ``key`` (str,
    the meeting id, series id, or ``"ALL"``), ``n_decisions`` (int), ``n_anchored`` (int),
    ``n_zero_evidence`` (int), ``anchoring_rate`` (float, ``n_anchored / n_decisions``, 0.0
    when ``n_decisions`` is 0).
    """
    rows: list[dict[str, object]] = []
    total_decisions = 0
    total_anchored = 0

    for series_id in series:
        decisions = decisions_from_abstractive(ami_root, series_id)
        # Keyed by ABSTRACTIVE SENTENCE id: that is what `summlink` points at. A decision
        # id (`IS1004c.d29`) is this project's own invention and appears nowhere in AMI.
        sentence_ids = {source_sentence_id(d) for d in decisions}
        evidence = _decision_evidence_map(ami_root, series_id, sentence_ids)

        by_meeting: dict[str, int] = Counter()
        anchored_by_meeting: dict[str, int] = Counter()
        for decision in decisions:
            by_meeting[decision.meeting_id] += 1
            if evidence.get(source_sentence_id(decision)):
                anchored_by_meeting[decision.meeting_id] += 1

        for meeting_id in sorted(by_meeting):
            n = by_meeting[meeting_id]
            anchored = anchored_by_meeting.get(meeting_id, 0)
            rows.append(
                {
                    "scope": "meeting",
                    "key": meeting_id,
                    "n_decisions": n,
                    "n_anchored": anchored,
                    "n_zero_evidence": n - anchored,
                    "anchoring_rate": (anchored / n) if n else 0.0,
                }
            )

        series_n = len(decisions)
        series_anchored = sum(1 for d in decisions if evidence.get(source_sentence_id(d)))
        rows.append(
            {
                "scope": "series",
                "key": series_id,
                "n_decisions": series_n,
                "n_anchored": series_anchored,
                "n_zero_evidence": series_n - series_anchored,
                "anchoring_rate": (series_anchored / series_n) if series_n else 0.0,
            }
        )
        total_decisions += series_n
        total_anchored += series_anchored

    rows.append(
        {
            "scope": "total",
            "key": "ALL",
            "n_decisions": total_decisions,
            "n_anchored": total_anchored,
            "n_zero_evidence": total_decisions - total_anchored,
            "anchoring_rate": (total_anchored / total_decisions) if total_decisions else 0.0,
        }
    )

    df = pd.DataFrame(
        rows,
        columns=["scope", "key", "n_decisions", "n_anchored", "n_zero_evidence", "anchoring_rate"],
    )
    return df.astype(
        {
            "scope": "object",
            "key": "object",
            "n_decisions": "int64",
            "n_anchored": "int64",
            "n_zero_evidence": "int64",
            "anchoring_rate": "float64",
        }
    )


def role_authorship(ami_root: Path = AMI_DIR, series: Sequence[str] = ()) -> pd.DataFrame:
    """The headline finding: counts and shares of summlink-attributed dialogue acts by
    scenario role (PM/ME/UI/ID), overall and broken down by recording site.

    Each (decision, supporting dialogue act) pair from ``anchoring_rates``'s evidence
    resolution is one attribution event -- a decision with three supporting dialogue acts
    from three different speakers contributes three events, one per role. Columns:
    ``role`` (str, e.g. ``"PM"``), ``site`` (str, ``"ES"``/``"IS"``/``"TS"`` or ``"ALL"``
    for the cross-site aggregate), ``count`` (int), ``share`` (float, this role's count
    divided by the total count for this row's site, 0.0 when that total is 0).
    """
    role_lookup = _role_lookup(ami_root)
    role_site_counts: Counter[tuple[str, str]] = Counter()

    for series_id in series:
        decisions = decisions_from_abstractive(ami_root, series_id)
        sentence_ids = {source_sentence_id(d) for d in decisions}
        evidence = _decision_evidence_map(ami_root, series_id, sentence_ids)
        site = site_prefix(series_id)

        for decision in decisions:
            for dialogue_act_id in evidence.get(source_sentence_id(decision), []):
                agent = _dialogue_act_speaker_letter(dialogue_act_id)
                role = role_lookup.get((decision.meeting_id, agent)) if agent else None
                if role:
                    role_site_counts[(role, site)] += 1

    roles = sorted({role for role, _site in role_site_counts})
    sites = sorted({site for _role, site in role_site_counts} | {site_prefix(s) for s in series})

    rows = []
    for site in sites:
        site_total = sum(count for (_role, s), count in role_site_counts.items() if s == site)
        for role in roles:
            count = role_site_counts.get((role, site), 0)
            rows.append(
                {
                    "role": role,
                    "site": site,
                    "count": count,
                    "share": (count / site_total) if site_total else 0.0,
                }
            )

    all_total = sum(role_site_counts.values())
    for role in roles:
        count = sum(c for (r, _s), c in role_site_counts.items() if r == role)
        rows.append(
            {
                "role": role,
                "site": "ALL",
                "count": count,
                "share": (count / all_total) if all_total else 0.0,
            }
        )

    df = pd.DataFrame(rows, columns=["role", "site", "count", "share"])
    return df.astype({"role": "object", "site": "object", "count": "int64", "share": "float64"})
