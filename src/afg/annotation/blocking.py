"""Candidate cross-meeting decision pair generation for human adjudication (thesis
section 3 OE1, manual de anotacion secciones 4 y 5).

This module never assigns a relation label. It only decides which cross-meeting decision
pairs are worth a human annotator's time (Tarea B of the manual) and, separately, which
rejected pairs go into the recall sample (Tarea C).

## Why the overlap coefficient, not Jaccard

``overlap(A, B) = |A intersection B| / min(|A|, |B|)`` is used to score candidate pairs,
never Jaccard (``|A intersection B| / |A union B|``). This is a measured decision, pinned
by the pilot's ground-truth pair and enforced by a regression test in
``tests/test_blocking.py``:

- Pair ``IS1004c.elana.s.29`` (the long sentence listing base station, scroll wheels,
  turbo button, on/off button) versus ``IS1004d.elana.s.22`` (*"For pricing reasons they
  eliminate the turbo button."*).
- After tokenisation and stopword removal: ``|A| = 14``, ``|B| = 5``, intersection
  ``= {"button", "turbo"}``.
- Jaccard = 2/17 = 0.118 -- below any sane threshold, so the pair is LOST.
- Overlap = 2/5 = 0.400 -- at the default threshold of 0.30, the pair is CAUGHT.

The reason is structural, not a tuning artefact: a reversal or replacement is almost
always a SHORT later sentence pointing back at a LONG earlier one (the earlier sentence
accumulates context across a whole meeting; the later one often just names the object and
what changed). Jaccard divides by the union, which penalises exactly that length
asymmetry -- the shorter set's few tokens get diluted by the longer set's many
non-overlapping ones. A Jaccard-based blocker is therefore systematically blind to
reversals, i.e. blind to the whole E3 (evolution) question stratum this thesis measures
against. The overlap coefficient instead divides by the smaller set, so a short sentence
that is almost entirely contained in a long one still scores high.

## Operating point (threshold 0.30, min_overlap_tokens 2) -- measured, bounded on both sides

Scoring by the coefficient alone is not enough: dividing by the minimum set size means a
SHORT decision sentence inflates trivially. ES2002 has a median of 3.5 content tokens and a
minimum of 2; a single shared token against a 2-token sentence already scores 0.5, clearing
any sane threshold. Run over the 14 selected OE1 series (``config/corpus.toml``
``[oe1].series``, 3,071 cross-meeting pairs total) with only the coefficient thresholded at
0.30, the blocker selects 712 pairs (23.2%) -- about 18 hours of human adjudication, far
beyond budget. The fix is a second, absolute constraint alongside the coefficient: a pair is
a candidate only when it clears ``threshold`` AND its intersection has at least
``min_overlap_tokens`` tokens.

Measured sensitivity (all 14 series, 3,071 pairs; the turbo-button pair --
``IS1004c.elana.s.29`` vs ``IS1004d.elana.s.22``, score 0.400, intersection exactly
``{"button", "turbo"}`` so ``|A & B| = 2`` -- is the recall control, see
:class:`TestTurboButtonRegression` in ``tests/test_blocking.py``):

| threshold | min_overlap_tokens | candidates |    %  | turbo survives? |
|-----------|---------------------|------------|-------|------------------|
|      0.30 | 1 (old behaviour)   |        712 | 23.2% | yes              |
| **0.30**  | **2 (new default)** |     **92** | **3.0%** | **yes**       |
|      0.40 | 2                   |         74 |  2.4% | yes              |
|      0.50 | 2                   |         53 |  1.7% | **NO**           |
|      0.30 | 3                   |         29 |  0.9% | **NO**           |

The operating point is bounded on BOTH sides, not just tightened arbitrarily:

- ``threshold`` must stay <= 0.40 and ``min_overlap_tokens`` must stay <= 2, or the blocker
  loses the one reversal pair verified by hand (the turbo-button pair above) -- pushing
  either knob further shrinks the candidate set but starts discarding true positives.
- Loosening either knob below the default reopens the short-sentence inflation problem this
  operating point exists to fix (712 pairs, 23.2%, over budget).

The default (threshold 0.30, min_overlap_tokens 2) is therefore not an arbitrary choice: it
is the tightest pair of constraints that still keeps the one verified reversal, and the
loosest pair that still brings the candidate set within budget (92 pairs, 3.0%).
"""

from __future__ import annotations

import random
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from afg.annotation.linking import chronological_candidate_pairs
from afg.corpus.layers import AnnotationLayer, discover_layer_files
from afg.corpus.nxt import get_attr_by_local_name, iter_elements, parse_xml
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.shared.csvio import open_csv_writer

# Blocker version, bumped whenever STOPWORDS, the tokenisation rule, or the default
# operating point (threshold, min_overlap_tokens) changes. A previously generated candidate
# set (any `data/processed/relations/*.candidates.csv` or `*.recall-sample.csv`) is only
# comparable to a fresh run when `blocker_version` matches: changing STOPWORDS, the
# tokenisation rule, or the operating point invalidates every candidate set generated under
# the old version and requires regenerating them (`afg gold candidates`,
# `afg gold recall-sample`) for every series before annotation resumes.
#
# 1.1 changed the default operating point from (threshold=0.30, min_overlap_tokens=1) to
# (threshold=0.30, min_overlap_tokens=2) -- see the module docstring for the measured
# evidence. The operating point is part of the version because it changes which pairs clear
# blocking exactly as much as a STOPWORDS or tokenisation change would.
BLOCKER_VERSION = "1.1"

# Explicit, versioned stopword list -- this is the exact list used by the pilot that
# produced the turbo-button ground truth above. Do not "improve" it (e.g. with a stemmer
# or a longer general-English list) without bumping BLOCKER_VERSION: doing so silently
# changes which pairs clear the threshold and breaks comparability with any candidate set
# already generated and annotated under this version.
_STOPWORDS_SOURCE = (
    "the a an will be is are to of and or for on in it they them this that with as not no "
    "thus far have has been used using use should can cannot but"
)
STOPWORDS: frozenset[str] = frozenset(_STOPWORDS_SOURCE.split())

_TOKEN_RE = re.compile(r"[a-z]+")
_MIN_TOKEN_LENGTH = 3


def tokenize(text: str) -> frozenset[str]:
    """Lowercase ``text``, keep letters-only tokens of length >= 3, drop stopwords."""
    return frozenset(
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= _MIN_TOKEN_LENGTH and token not in STOPWORDS
    )


def overlap_coefficient(a: frozenset[str], b: frozenset[str]) -> float:
    """Overlap coefficient ``|A intersection B| / min(|A|, |B|)``.

    This is the blocking score this module uses in production (see the module docstring
    for why, over Jaccard). Returns 0.0 when either set is empty, rather than raising, so
    a decision with no content tokens (e.g. only stopwords) never causes a ZeroDivisionError
    -- it simply never clears a positive threshold.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity ``|A intersection B| / |A union B|``.

    NOT used for production blocking. Kept only so the regression test in
    ``tests/test_blocking.py`` can demonstrate, on the real turbo-button pilot pair, why a
    Jaccard-based blocker loses reversal pairs that the overlap coefficient catches -- see
    the module docstring. Do not switch ``generate_candidates`` to use this.
    """
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


class CandidatePair(BaseModel):
    """One candidate cross-meeting decision pair, scored but not yet adjudicated.

    Direction convention (manual de anotacion section 4): ``later_decision_id`` is
    ``source`` and ``earlier_decision_id`` is ``target`` once a human assigns a relation --
    this module never assigns one, but it always orders the pair chronologically so that
    convention is unambiguous downstream.
    """

    model_config = ConfigDict(frozen=True)

    pair_id: str
    earlier_decision_id: str
    later_decision_id: str
    earlier_meeting_id: str
    later_meeting_id: str
    earlier_text: str
    later_text: str
    blocker_score: float
    blocker_version: str


def _decision_text(decision: Decision) -> str:
    """Text a decision is blocked on: its object and content, combined."""
    return f"{decision.decision_object} {decision.content}".strip()


def _scored_pairs(
    decisions: Sequence[Decision],
) -> list[tuple[Decision, Decision, float, int]]:
    """Every cross-meeting pair in ``decisions``, scored by overlap coefficient.

    Reuses :func:`afg.annotation.linking.chronological_candidate_pairs` for the eligible
    pair universe (same series, cross-meeting, direction enforced structurally), so this
    module never re-derives or risks disagreeing with the chronology/leakage rule. Returns
    ``(earlier, later, score, overlap_tokens)`` quadruples, where ``overlap_tokens`` is
    ``len(A & B)``; this is the single computation both :func:`generate_candidates` and
    :func:`rejected_pairs` filter, so together they partition the full pair space exactly.
    """
    scored: list[tuple[Decision, Decision, float, int]] = []
    for source, target in chronological_candidate_pairs(list(decisions)):
        target_tokens = tokenize(_decision_text(target))
        source_tokens = tokenize(_decision_text(source))
        score = overlap_coefficient(target_tokens, source_tokens)
        overlap_tokens = len(target_tokens & source_tokens)
        scored.append((target, source, score, overlap_tokens))
    return scored


def _build_candidate_pairs(
    triples: list[tuple[Decision, Decision, float]], *, id_infix: str
) -> list[CandidatePair]:
    """Sort ``triples`` and assign pair ids, shared by candidates and rejected pairs.

    Sorted by ``(earlier_meeting_id, later_meeting_id, -blocker_score)`` as required by the
    manual. ``id_infix`` (``"p"`` for candidates, ``"r"`` for rejected) keeps the two id
    spaces disjoint so a candidate and a rejected pair never collide.
    """
    def _sort_key(triple: tuple[Decision, Decision, float]) -> tuple[str, str, float]:
        earlier, later, score = triple
        return (earlier.meeting_id, later.meeting_id, -score)

    ordered = sorted(triples, key=_sort_key)
    counters: dict[str, int] = {}
    pairs: list[CandidatePair] = []
    for earlier, later, score in ordered:
        counters[earlier.series_id] = counters.get(earlier.series_id, 0) + 1
        pair_id = f"{earlier.series_id}.{id_infix}{counters[earlier.series_id]:03d}"
        pairs.append(
            CandidatePair(
                pair_id=pair_id,
                earlier_decision_id=earlier.id,
                later_decision_id=later.id,
                earlier_meeting_id=earlier.meeting_id,
                later_meeting_id=later.meeting_id,
                earlier_text=_decision_text(earlier),
                later_text=_decision_text(later),
                blocker_score=score,
                blocker_version=BLOCKER_VERSION,
            )
        )
    return pairs


def _clears_operating_point(
    quad: tuple[Decision, Decision, float, int], *, threshold: float, min_overlap_tokens: int
) -> bool:
    """Both constraints of the operating point (see module docstring): the overlap
    coefficient must clear ``threshold`` AND the absolute intersection size must clear
    ``min_overlap_tokens``. Neither alone is the rule -- both are required together."""
    _, _, score, overlap_tokens = quad
    return score >= threshold and overlap_tokens >= min_overlap_tokens


def generate_candidates(
    decisions: Sequence[Decision], *, threshold: float = 0.30, min_overlap_tokens: int = 2
) -> list[CandidatePair]:
    """Cross-meeting decision pairs whose overlap coefficient clears ``threshold`` AND whose
    absolute token intersection clears ``min_overlap_tokens``.

    These are the pairs a human adjudicates in Tarea B. Always ordered chronologically
    (earlier first), per the manual's direction convention. See the module docstring for why
    the operating point needs both an absolute and a relative constraint.
    """
    above = [
        (earlier, later, score)
        for earlier, later, score, overlap_tokens in _scored_pairs(decisions)
        if _clears_operating_point(
            (earlier, later, score, overlap_tokens),
            threshold=threshold,
            min_overlap_tokens=min_overlap_tokens,
        )
    ]
    return _build_candidate_pairs(above, id_infix="p")


def rejected_pairs(
    decisions: Sequence[Decision], *, threshold: float = 0.30, min_overlap_tokens: int = 2
) -> list[CandidatePair]:
    """The complement of :func:`generate_candidates`: pairs the blocker rejected.

    Feeds the Tarea C recall sample. Together with :func:`generate_candidates`, these two
    functions partition the full cross-meeting pair space for ``decisions`` exactly.
    """
    below = [
        (earlier, later, score)
        for earlier, later, score, overlap_tokens in _scored_pairs(decisions)
        if not _clears_operating_point(
            (earlier, later, score, overlap_tokens),
            threshold=threshold,
            min_overlap_tokens=min_overlap_tokens,
        )
    ]
    return _build_candidate_pairs(below, id_infix="r")


def sample_rejected(
    decisions: Sequence[Decision],
    *,
    n: int,
    seed: int,
    threshold: float = 0.30,
    min_overlap_tokens: int = 2,
) -> list[CandidatePair]:
    """Deterministic random sample of ``n`` rejected pairs, for the Tarea C recall sample.

    Uses ``random.Random(seed)`` seeded independently of any global RNG state, so the same
    seed, the same input decisions, and the same :data:`BLOCKER_VERSION` always produce the
    same sample -- required to report the recall figure (manual section 5) reproducibly.
    Returns every rejected pair, unsampled, if ``n`` is at least the population size.
    """
    population = rejected_pairs(
        decisions, threshold=threshold, min_overlap_tokens=min_overlap_tokens
    )
    if n >= len(population):
        return population
    return random.Random(seed).sample(population, k=n)


# --- provisional adapter: raw abstractive DECISIONS sentences ---------------------------


def decisions_from_abstractive(ami_root: Path, series_id: str) -> list[Decision]:
    """Provisional decision source: one :class:`Decision` per raw abstractive DECISIONS
    sentence for ``series_id``, so candidate pairs can be generated TODAY.

    This is NOT the P3 gold decision source. ``afg.annotation.goldset.build_gold_decisions``
    (P3, still ``NotImplementedError``) will eventually normalise decisions with a real
    object/content split and dialogue-act-linked evidence via ``summlink``. Until then,
    this function reads the ``<decisions>`` section's ``<sentence>`` children of each
    ``abstractive/<meeting>.abssumm.xml`` file directly (see
    ``afg.corpus.inventory._count_abstractive_decision_sentences`` for the same, already
    verified, parsing approach) and wraps each raw sentence as a :class:`Decision`:

    - ``id`` is the sentence's namespaced ``nite:id`` (e.g. ``"IS1004c.elana.s.29"``).
    - ``decision_object`` is left empty: raw abstractive sentences are not segmented into
      object/content, that segmentation is P3's job.
    - ``content`` is the sentence's full raw text.
    - ``evidence.dialogue_act_ids`` holds only the sentence's own id as a placeholder --
      it is NOT a verified link to supporting dialogue acts (that link is ``summlink``,
      P3's job too).

    Candidates generated from these raw sentences are NOT the final gold input: they are
    good enough to exercise and measure the blocker (P2) now, but the real Tarea B/C input
    must be regenerated from P3's normalised decisions once ``build_gold_decisions`` lands.
    """
    decisions: list[Decision] = []
    for layer_file in discover_layer_files(ami_root, AnnotationLayer.ABSTRACTIVE_SUMMARY):
        meeting_id = layer_file.meeting_id
        if meeting_id[:-1] != series_id:
            continue
        root = parse_xml(layer_file.path)
        for decisions_el in iter_elements(root, "decisions"):
            for sentence_el in decisions_el:
                tag = sentence_el.tag
                is_sentence = isinstance(tag, str) and tag.split("}")[-1] == "sentence"
                if not is_sentence:
                    continue
                sentence_id = get_attr_by_local_name(sentence_el, "id")
                text = (sentence_el.text or "").strip()
                if not sentence_id or not text:
                    continue
                decisions.append(
                    Decision(
                        id=sentence_id,
                        series_id=series_id,
                        meeting_id=meeting_id,
                        decision_object="",
                        content=text,
                        status=DecisionStatus.ACCEPTED,
                        evidence=EvidenceSpan(
                            meeting_id=meeting_id, dialogue_act_ids=(sentence_id,)
                        ),
                        annotator=None,
                    )
                )
    decisions.sort(key=lambda d: d.id)
    return decisions


# --- CSV output ---------------------------------------------------------------------------

_CSV_COLUMNS = (
    "pair_id",
    "earlier_decision_id",
    "later_decision_id",
    "earlier_text",
    "later_text",
    "blocker_score",
    "relation",
    "direction_ok",
    "confidence",
    "annotator",
    "notes",
)


def write_candidate_pairs_csv(pairs: list[CandidatePair], out_path: Path) -> Path:
    """Write ``pairs`` to ``out_path`` with the manual's section-4/5 columns.

    The last five columns (``relation``, ``direction_ok``, ``confidence``, ``annotator``,
    ``notes``) are always empty: they are for the human annotator to fill during Tarea B
    or Tarea C, never machine-populated here.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(out_path, encoding="utf-8") as writer:
        writer.writerow(_CSV_COLUMNS)
        for pair in pairs:
            writer.writerow(
                [
                    pair.pair_id,
                    pair.earlier_decision_id,
                    pair.later_decision_id,
                    pair.earlier_text,
                    pair.later_text,
                    pair.blocker_score,
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
    return out_path
