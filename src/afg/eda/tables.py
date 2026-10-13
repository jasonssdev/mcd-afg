"""The five analysis-level tables of the AFG2 exploratory data analysis.

==============  =====================================  ==========
Level           Grain                                  Rows (OE1)
==============  =====================================  ==========
``series``      one AMI series                         14
``meeting``     one meeting                            56
``speaker``     one speaker in one meeting             224
``decision``    one abstractive DECISIONS sentence     343
``pair``        one cross-meeting decision pair        3,071
==============  =====================================  ==========

Design rules
------------
* Reuse, do not re-derive: decisions come from
  :func:`afg.annotation.blocking.decisions_from_abstractive`, tokens from
  :func:`afg.annotation.blocking.tokenize`, pairs and the operating point from
  :func:`afg.annotation.blocking.generate_candidates`, evidence from the audit layer.
* ADR 0005: the tables carry ids and numeric/boolean features only. No decision sentence and
  no transcript text ever reaches a returned table (transcripts are reduced to counts while
  being read), so a notebook built on them reports aggregates of the evaluation series
  without reading their content.
* Every builder is a pure function of already-loaded inputs (tested on synthetic data); only
  the ``read_*`` functions and :func:`load_eda_tables` touch the filesystem.

Token approximation
-------------------
The context-window question needs a model-token count, which the project does not have a
tokenizer for. ``approx_tokens = ceil(1.3 * n_words)`` is used (about 1.3 sub-word tokens per
English word is the usual rule of thumb for BPE vocabularies); ``approx_tokens_chars =
ceil(n_characters / 4)`` is kept beside it as a cross-check. Both count spoken text only: the
role label and line breaks that the rendered transcript adds per turn are excluded, so
treat the fit flag as optimistic by a few percent. It is an estimate, never a measurement.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from afg.annotation.blocking import (
    decisions_from_abstractive,
    generate_candidates,
    source_sentence_id,
    tokenize,
)
from afg.audit.decisions import NON_DECISION_MARKERS, site_prefix
from afg.audit.evidence import _decision_evidence_map, _dialogue_act_speaker_letter
from afg.corpus.nxt import find_by_local_name, get_attr, iter_elements, parse_xml
from afg.corpus.participants import load_native_language_records
from afg.domain.decision import Decision
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR, TRANSCRIPTS_DIR

DEFAULT_CONTEXT_TOKENS = 12288
"""The OpenKOS workspace default context window, in tokens."""
TOKENS_PER_WORD = 1.3
POSITION_LETTERS: tuple[str, ...] = ("a", "b", "c", "d")


def _position(meeting_id: str) -> tuple[str, int]:
    letter = meeting_id[-1]
    return letter, POSITION_LETTERS.index(letter) + 1


def _split_map() -> dict[str, str]:
    oe1 = load_corpus_config()["oe1"]
    mapping = {s: "development" for s in oe1["development_series"]}
    mapping.update({s: "evaluation" for s in oe1["evaluation_series"]})
    return mapping


# --- readers (filesystem) -------------------------------------------------------------------


def _parse_date(date_only: str | None) -> pd.Timestamp:
    """AMI writes ``dateOnly`` with a four-digit year (``29-10-2004``) in some series and a
    two-digit one (``13-12-04``) in others."""
    for fmt in ("%d-%m-%Y", "%d-%m-%y"):
        try:
            return pd.Timestamp(datetime.strptime(date_only or "", fmt))
        except ValueError:
            continue
    return pd.NaT


def _parse_start(date_only: str | None, start_time: str | None) -> pd.Timestamp:
    """Date plus ``startTime`` (``10h46``); NaT when either is missing (``startTime`` is an
    empty string for many meetings)."""
    day = _parse_date(date_only)
    try:
        clock = datetime.strptime(start_time or "", "%Hh%M")
    except ValueError:
        return pd.NaT
    if pd.isna(day):
        return pd.NaT
    return day + pd.Timedelta(hours=clock.hour, minutes=clock.minute)


def read_meeting_metadata(ami_root: Path, meeting_ids: Iterable[str]) -> pd.DataFrame:
    """``meeting_id``, ``duration_seconds``, ``recording_date`` and ``start`` from
    ``corpusResources/meetings.xml`` (attributes ``duration``, ``dateOnly``, ``startTime``).

    ``start`` is the date plus the clock time and is NaT whenever ``startTime`` is empty
    (32 of the 56 OE1 meetings); ``recording_date`` survives in that case. Meetings absent
    from the file get NaN/NaT, never a guessed value.
    """
    root = parse_xml(ami_root / "corpusResources" / "meetings.xml")
    found: dict[str, tuple[float, pd.Timestamp, pd.Timestamp]] = {}
    for element in find_by_local_name(root, "meeting"):
        observation = get_attr(element, "observation")
        if not observation:
            continue
        raw = get_attr(element, "duration")
        date_only, start_time = get_attr(element, "dateOnly"), get_attr(element, "startTime")
        found[observation] = (
            float(raw) if raw else float("nan"),
            _parse_date(date_only),
            _parse_start(date_only, start_time),
        )
    blank = (float("nan"), pd.NaT, pd.NaT)
    rows = [
        {
            "meeting_id": m,
            "duration_seconds": found.get(m, blank)[0],
            "recording_date": found.get(m, blank)[1],
            "start": found.get(m, blank)[2],
        }
        for m in meeting_ids
    ]
    out = pd.DataFrame(rows, columns=["meeting_id", "duration_seconds", "recording_date", "start"])
    out["recording_date"] = pd.to_datetime(out["recording_date"])
    out["start"] = pd.to_datetime(out["start"])
    return out


def read_speaker_metadata(ami_root: Path, meeting_ids: Iterable[str]) -> pd.DataFrame:
    """One row per speaker of each meeting: ``meeting_id``, ``speaker`` (NXT agent letter),
    ``role``, ``participant_id`` (``global_name``), ``native_language`` (NaN when
    ``participants.xml`` does not know the participant) and ``native_status``
    (``native`` / ``non_native`` / ``unknown``)."""
    wanted = set(meeting_ids)
    languages = {r.participant_id: r for r in load_native_language_records(ami_root)}
    root = parse_xml(ami_root / "corpusResources" / "meetings.xml")
    rows: list[dict[str, object]] = []
    for meeting_el in find_by_local_name(root, "meeting"):
        observation = get_attr(meeting_el, "observation")
        if observation not in wanted:
            continue
        for speaker_el in iter_elements(meeting_el, "speaker"):
            participant = get_attr(speaker_el, "global_name")
            record = languages.get(participant) if participant else None
            rows.append(
                {
                    "meeting_id": observation,
                    "speaker": get_attr(speaker_el, "nxt_agent"),
                    "role": get_attr(speaker_el, "role"),
                    "participant_id": participant,
                    "native_language": record.native_language if record else None,
                    "native_status": record.native_speaker_status.value if record else "unknown",
                }
            )
    columns = [
        "meeting_id",
        "speaker",
        "role",
        "participant_id",
        "native_language",
        "native_status",
    ]
    return pd.DataFrame(rows, columns=columns)


def read_transcripts(
    transcripts_dir: Path, meeting_ids: Iterable[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reduce the frozen ``<meeting>.jsonl`` transcripts to numbers.

    Returns ``(turns, act_ids)``. ``turns`` has one row per turn: ``meeting_id``,
    ``turn_index``, ``speaker``, ``role``, ``start``, ``end``, ``duration`` (seconds),
    ``n_words`` (whitespace tokens), ``n_chars`` and ``n_dialogue_acts``. ``act_ids`` has the
    distinct dialogue-act ids per meeting (``meeting_id``, ``dialogue_act_id``). The turn
    text is dropped here and never returned. Meetings with no file are simply absent.
    """
    turn_rows: list[dict[str, object]] = []
    act_rows: list[dict[str, str]] = []
    for meeting_id in meeting_ids:
        path = transcripts_dir / f"{meeting_id}.jsonl"
        if not path.exists():
            continue
        seen: set[str] = set()
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                turn = json.loads(line)
                text = turn.get("text", "")
                acts = turn.get("dialogue_act_ids", [])
                start, end = turn.get("start"), turn.get("end")
                turn_rows.append(
                    {
                        "meeting_id": meeting_id,
                        "turn_index": turn.get("turn_index"),
                        "speaker": turn.get("speaker"),
                        "role": turn.get("role"),
                        "start": start,
                        "end": end,
                        "duration": (end - start)
                        if start is not None and end is not None
                        else None,
                        "n_words": len(text.split()),
                        "n_chars": len(text),
                        "n_dialogue_acts": len(acts),
                    }
                )
                seen.update(acts)
        act_rows.extend({"meeting_id": meeting_id, "dialogue_act_id": a} for a in sorted(seen))
    turns = pd.DataFrame(
        turn_rows,
        columns=[
            "meeting_id",
            "turn_index",
            "speaker",
            "role",
            "start",
            "end",
            "duration",
            "n_words",
            "n_chars",
            "n_dialogue_acts",
        ],
    )
    return turns, pd.DataFrame(act_rows, columns=["meeting_id", "dialogue_act_id"])


def turn_length_distribution(
    turns: pd.DataFrame, *, by: str | None = None, column: str = "n_words"
) -> pd.DataFrame:
    """Distribution of turn length (``column``, words by default), overall or per ``by``.

    Columns: the ``by`` key (when given), ``n_turns``, ``mean``, ``std``, ``min``, ``q1``,
    ``median``, ``q3``, ``p90``, ``p99``, ``max`` and ``share_single_word`` (turns of length
    1: back-channels such as "yeah" or "okay").
    """

    def summarise(values: pd.Series) -> dict[str, float]:
        return {
            "n_turns": int(values.count()),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if values.count() > 1 else float("nan"),
            "min": float(values.min()),
            "q1": float(values.quantile(0.25)),
            "median": float(values.median()),
            "q3": float(values.quantile(0.75)),
            "p90": float(values.quantile(0.90)),
            "p99": float(values.quantile(0.99)),
            "max": float(values.max()),
            "share_single_word": float((values == 1).mean()),
        }

    if by is None:
        return pd.DataFrame([summarise(turns[column])])
    rows = [{by: key, **summarise(part[column])} for key, part in turns.groupby(by, sort=True)]
    return pd.DataFrame(rows)


# --- decision and pair levels (pure) ---------------------------------------------------------


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def build_decision_table(
    decisions: Sequence[Decision],
    evidence_by_sentence: Mapping[str, Sequence[str]],
    role_lookup: Mapping[tuple[str, str], str],
    split_by_series: Mapping[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The decision-level table and the long evidence table.

    ``evidence_by_sentence`` maps an abstractive sentence id to the dialogue-act ids that
    summlink attaches to it; ``role_lookup`` maps ``(meeting_id, speaker_letter)`` to a role.

    Decision columns: ``decision_id``, ``sentence_id``, ``series_id``, ``meeting_id``,
    ``position``, ``position_index``, ``site``, ``split``, ``n_tokens`` / ``n_chars`` (the
    blocker's tokenisation), ``n_evidence_acts``, ``anchored`` (at least one act),
    ``has_non_decision_marker`` (any of :data:`NON_DECISION_MARKERS`; a hint, precision
    unmeasured), ``n_evidence_roles``, ``evidence_role`` (most frequent role among the
    evidence acts, ``"mixed"`` on a tie, NaN without evidence), ``exact_duplicate`` and
    ``near_duplicate``.

    Duplicates are searched within a series and flag every member of a duplicate group.
    *Exact*: equal after lower-casing and collapsing whitespace. *Near*: equal non-empty
    blocker token sets (overlap coefficient 1.0 both ways); exact duplicates are near
    duplicates too.

    Evidence columns: ``decision_id``, ``meeting_id``, ``dialogue_act_id``, ``act_meeting_id``,
    ``speaker``, ``role`` (NaN when the letter has no role).
    """
    rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    keys: list[tuple[str, str, frozenset[str]]] = []
    for d in decisions:
        sentence_id = source_sentence_id(d)
        acts = list(evidence_by_sentence.get(sentence_id, ()))
        tokens = tokenize(d.content)
        roles: list[str] = []
        for act in acts:
            letter = _dialogue_act_speaker_letter(act)
            role = role_lookup.get((d.meeting_id, letter)) if letter else None
            if role:
                roles.append(role)
            evidence_rows.append(
                {
                    "decision_id": d.id,
                    "meeting_id": d.meeting_id,
                    "dialogue_act_id": act,
                    "act_meeting_id": act.split(".")[0],
                    "speaker": letter,
                    "role": role,
                }
            )
        position, position_index = _position(d.meeting_id)
        counts = Counter(roles).most_common()
        if not counts:
            evidence_role: str | float = float("nan")
        elif len(counts) > 1 and counts[0][1] == counts[1][1]:
            evidence_role = "mixed"
        else:
            evidence_role = counts[0][0]
        lowered = d.content.lower()
        rows.append(
            {
                "decision_id": d.id,
                "sentence_id": sentence_id,
                "series_id": d.series_id,
                "meeting_id": d.meeting_id,
                "position": position,
                "position_index": position_index,
                "site": site_prefix(d.series_id),
                "split": split_by_series.get(d.series_id, "unassigned"),
                "n_tokens": len(tokens),
                "n_chars": len(d.content),
                "n_evidence_acts": len(acts),
                "anchored": len(acts) > 0,
                "has_non_decision_marker": any(m in lowered for m in NON_DECISION_MARKERS),
                "n_evidence_roles": len(set(roles)),
                "evidence_role": evidence_role,
            }
        )
        keys.append((d.series_id, _normalise(d.content), tokens))

    table = pd.DataFrame(rows)
    if table.empty:
        table = pd.DataFrame(columns=[*_DECISION_COLUMNS])
    exact = Counter((s, t) for s, t, _ in keys)
    near = Counter((s, tok) for s, _, tok in keys if tok)
    table["exact_duplicate"] = [exact[(s, t)] > 1 for s, t, _ in keys]
    table["near_duplicate"] = [bool(tok) and near[(s, tok)] > 1 for s, _, tok in keys]
    evidence = pd.DataFrame(
        evidence_rows,
        columns=[
            "decision_id",
            "meeting_id",
            "dialogue_act_id",
            "act_meeting_id",
            "speaker",
            "role",
        ],
    )
    return table, evidence


_DECISION_COLUMNS = (
    "decision_id",
    "sentence_id",
    "series_id",
    "meeting_id",
    "position",
    "position_index",
    "site",
    "split",
    "n_tokens",
    "n_chars",
    "n_evidence_acts",
    "anchored",
    "has_non_decision_marker",
    "n_evidence_roles",
    "evidence_role",
)


def build_pair_table(
    decisions: Sequence[Decision], split_by_series: Mapping[str, str]
) -> pd.DataFrame:
    """Every cross-meeting pair of decisions within a series, scored by the blocker.

    Columns: ``pair_id``, ``series_id``, ``site``, ``split``, ``earlier_decision_id``,
    ``later_decision_id``, ``earlier_meeting_id``, ``later_meeting_id``, ``meeting_distance``
    (1-3), ``n_tokens_earlier``, ``n_tokens_later``, ``shared_tokens`` (``|A and B|``),
    ``overlap`` (overlap coefficient) and ``is_candidate`` (clears the blocker defaults:
    overlap >= 0.30 and at least 2 shared tokens). The pair universe is
    ``generate_candidates(threshold=0, min_overlap_tokens=0)``; pair texts are used only to
    count tokens and are not returned.
    """
    candidate_keys = {
        (c.earlier_decision_id, c.later_decision_id) for c in generate_candidates(decisions)
    }
    rows: list[dict[str, object]] = []
    for pair in generate_candidates(decisions, threshold=0.0, min_overlap_tokens=0):
        earlier, later = tokenize(pair.earlier_text), tokenize(pair.later_text)
        series_id = pair.earlier_meeting_id[:-1]
        rows.append(
            {
                "pair_id": pair.pair_id,
                "series_id": series_id,
                "site": site_prefix(series_id),
                "split": split_by_series.get(series_id, "unassigned"),
                "earlier_decision_id": pair.earlier_decision_id,
                "later_decision_id": pair.later_decision_id,
                "earlier_meeting_id": pair.earlier_meeting_id,
                "later_meeting_id": pair.later_meeting_id,
                "meeting_distance": _position(pair.later_meeting_id)[1]
                - _position(pair.earlier_meeting_id)[1],
                "n_tokens_earlier": len(earlier),
                "n_tokens_later": len(later),
                "shared_tokens": len(earlier & later),
                "overlap": pair.blocker_score,
                "is_candidate": (pair.earlier_decision_id, pair.later_decision_id)
                in candidate_keys,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "pair_id",
            "series_id",
            "site",
            "split",
            "earlier_decision_id",
            "later_decision_id",
            "earlier_meeting_id",
            "later_meeting_id",
            "meeting_distance",
            "n_tokens_earlier",
            "n_tokens_later",
            "shared_tokens",
            "overlap",
            "is_candidate",
        ],
    )


# --- meeting, speaker and series levels (pure) ------------------------------------------------


def build_meeting_table(
    meeting_ids: Sequence[str],
    metadata: pd.DataFrame,
    turns: pd.DataFrame,
    act_ids: pd.DataFrame,
    decision_table: pd.DataFrame,
    split_by_series: Mapping[str, str],
    *,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    tokens_per_word: float = TOKENS_PER_WORD,
) -> pd.DataFrame:
    """One row per meeting in ``meeting_ids``.

    Columns: ``meeting_id``, ``series_id``, ``site``, ``split``, ``position`` (a-d),
    ``position_index`` (1-4), ``recording_date``, ``start``, ``duration_seconds``,
    ``n_speakers`` (who spoke),
    ``n_turns``, ``n_dialogue_acts`` (distinct ids in the transcript), ``n_characters``,
    ``n_words``, ``n_decisions``, ``n_anchored_decisions``, ``approx_tokens``,
    ``approx_tokens_chars``, ``context_ratio`` (``approx_tokens / context_tokens``) and
    ``fits_context`` (``approx_tokens <= context_tokens``). A meeting without a transcript
    has zero counts. See the module docstring for the token approximation.
    """
    by_meeting = turns.groupby("meeting_id")
    n_turns = by_meeting.size()
    n_words = by_meeting["n_words"].sum()
    n_chars = by_meeting["n_chars"].sum()
    n_speakers = by_meeting["speaker"].nunique()
    acts = act_ids.groupby("meeting_id").size()
    decisions_by = decision_table.groupby("meeting_id")
    n_decisions = decisions_by.size()
    n_anchored = decisions_by["anchored"].sum()
    meta = metadata.set_index("meeting_id")

    rows: list[dict[str, object]] = []
    for meeting_id in meeting_ids:
        series_id = meeting_id[:-1]
        position, position_index = _position(meeting_id)
        words = int(n_words.get(meeting_id, 0))
        chars = int(n_chars.get(meeting_id, 0))
        approx = math.ceil(tokens_per_word * words)
        rows.append(
            {
                "meeting_id": meeting_id,
                "series_id": series_id,
                "site": site_prefix(series_id),
                "split": split_by_series.get(series_id, "unassigned"),
                "position": position,
                "position_index": position_index,
                "recording_date": meta["recording_date"].get(meeting_id, pd.NaT),
                "start": meta["start"].get(meeting_id, pd.NaT),
                "duration_seconds": meta["duration_seconds"].get(meeting_id, float("nan")),
                "n_speakers": int(n_speakers.get(meeting_id, 0)),
                "n_turns": int(n_turns.get(meeting_id, 0)),
                "n_dialogue_acts": int(acts.get(meeting_id, 0)),
                "n_characters": chars,
                "n_words": words,
                "n_decisions": int(n_decisions.get(meeting_id, 0)),
                "n_anchored_decisions": int(n_anchored.get(meeting_id, 0)),
                "approx_tokens": approx,
                "approx_tokens_chars": math.ceil(chars / 4),
                "context_ratio": approx / context_tokens,
                "fits_context": approx <= context_tokens,
            }
        )
    out = pd.DataFrame(rows)
    out["recording_date"] = pd.to_datetime(out["recording_date"])
    out["start"] = pd.to_datetime(out["start"])
    return out


def build_speaker_table(
    speaker_metadata: pd.DataFrame, turns: pd.DataFrame, evidence: pd.DataFrame
) -> pd.DataFrame:
    """One row per speaker of each meeting (the roster in ``meetings.xml``).

    Columns: ``meeting_id``, ``speaker``, ``role``, ``participant_id``, ``native_language``,
    ``native_status``, ``n_turns``, ``n_words``, ``n_chars``, ``talk_seconds``,
    ``talk_share`` (share of the meeting's words; NaN if nobody spoke) and
    ``n_decision_acts`` (summlink evidence acts of that speaker supporting decisions of the
    meeting: the per-speaker version of :func:`afg.audit.role_authorship`).
    """
    spoken = (
        turns.groupby(["meeting_id", "speaker"])
        .agg(
            n_turns=("turn_index", "size"),
            n_words=("n_words", "sum"),
            n_chars=("n_chars", "sum"),
            talk_seconds=("duration", "sum"),
        )
        .reset_index()
    )
    attributed = (
        evidence.groupby(["meeting_id", "speaker"]).size().rename("n_decision_acts").reset_index()
    )
    table = speaker_metadata.merge(spoken, on=["meeting_id", "speaker"], how="left").merge(
        attributed, on=["meeting_id", "speaker"], how="left"
    )
    for column in ("n_turns", "n_words", "n_chars", "n_decision_acts"):
        table[column] = table[column].fillna(0).astype(int)
    table["talk_seconds"] = table["talk_seconds"].fillna(0.0)
    totals = table.groupby("meeting_id")["n_words"].transform("sum")
    table["talk_share"] = np.where(totals > 0, table["n_words"] / totals.where(totals > 0), np.nan)
    return table


def build_series_table(
    meetings: pd.DataFrame,
    decisions: pd.DataFrame,
    pairs: pd.DataFrame,
    split_by_series: Mapping[str, str],
) -> pd.DataFrame:
    """One row per series, aggregated from the finer levels.

    Columns: ``series_id``, ``site``, ``split``, ``n_meetings``, ``n_decisions``,
    ``n_cross_meeting_pairs``, ``n_candidates`` (blocker defaults), ``candidate_rate``
    (candidates / pairs; NaN with no pairs), ``anchoring_rate``, ``median_decision_tokens``,
    ``total_turns``, ``total_characters``, ``total_words`` and ``total_duration_seconds``.
    """
    rows: list[dict[str, object]] = []
    for series_id in sorted(meetings["series_id"].unique()):
        m = meetings[meetings["series_id"] == series_id]
        d = decisions[decisions["series_id"] == series_id]
        p = pairs[pairs["series_id"] == series_id]
        n_pairs, n_candidates = len(p), int(p["is_candidate"].sum())
        rows.append(
            {
                "series_id": series_id,
                "site": site_prefix(series_id),
                "split": split_by_series.get(series_id, "unassigned"),
                "n_meetings": len(m),
                "n_decisions": len(d),
                "n_cross_meeting_pairs": n_pairs,
                "n_candidates": n_candidates,
                "candidate_rate": n_candidates / n_pairs if n_pairs else float("nan"),
                "anchoring_rate": float(d["anchored"].mean()) if len(d) else float("nan"),
                "median_decision_tokens": float(d["n_tokens"].median()) if len(d) else float("nan"),
                "total_turns": int(m["n_turns"].sum()),
                "total_characters": int(m["n_characters"].sum()),
                "total_words": int(m["n_words"].sum()),
                "total_duration_seconds": float(m["duration_seconds"].sum()),
            }
        )
    return pd.DataFrame(rows)


# --- orchestration ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EdaTables:
    """All analysis levels plus the auxiliary tables the quality checks need.

    ``turns`` is the turn-level table (numbers only), ``evidence`` the long
    decision-to-dialogue-act table and ``act_ids`` the dialogue acts that exist in the frozen
    transcripts.
    """

    series: pd.DataFrame
    meeting: pd.DataFrame
    speaker_meeting: pd.DataFrame
    decision: pd.DataFrame
    pair: pd.DataFrame
    turns: pd.DataFrame
    evidence: pd.DataFrame
    act_ids: pd.DataFrame


def load_eda_tables(
    ami_root: Path = AMI_DIR,
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    series: Sequence[str] | None = None,
    *,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
) -> EdaTables:
    """Read the corpus once and build every level.

    ``series`` defaults to the 14 OE1 series of ``config/corpus.toml``. ``context_tokens``
    is the window the meeting table compares each transcript against.
    """
    series_ids = list(series if series is not None else load_corpus_config()["oe1"]["series"])
    split = _split_map()
    meeting_ids = [f"{s}{letter}" for s in series_ids for letter in POSITION_LETTERS]

    decisions: list[Decision] = []
    for series_id in series_ids:
        decisions.extend(decisions_from_abstractive(ami_root, series_id))
    evidence_map: dict[str, list[str]] = {}
    for series_id in series_ids:
        sentence_ids = {source_sentence_id(d) for d in decisions if d.series_id == series_id}
        evidence_map.update(_decision_evidence_map(ami_root, series_id, sentence_ids))

    metadata = read_meeting_metadata(ami_root, meeting_ids)
    speaker_meta = read_speaker_metadata(ami_root, meeting_ids)
    turns, act_ids = read_transcripts(transcripts_dir, meeting_ids)
    roles = {
        (m, s): r
        for m, s, r in zip(
            speaker_meta["meeting_id"], speaker_meta["speaker"], speaker_meta["role"], strict=True
        )
    }
    decision_table, evidence = build_decision_table(decisions, evidence_map, roles, split)
    pair_table = build_pair_table(decisions, split)
    meeting_table = build_meeting_table(
        meeting_ids, metadata, turns, act_ids, decision_table, split, context_tokens=context_tokens
    )
    return EdaTables(
        series=build_series_table(meeting_table, decision_table, pair_table, split),
        meeting=meeting_table,
        speaker_meeting=build_speaker_table(speaker_meta, turns, evidence),
        decision=decision_table,
        pair=pair_table,
        turns=turns,
        evidence=evidence,
        act_ids=act_ids,
    )
