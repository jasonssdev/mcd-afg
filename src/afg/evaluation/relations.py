"""Scoring of machine temporal relations against the gold relations (OE2, H2 and H3; ADR 0016).

Gold: the pairs of a series' Task-B candidates file, ``<ID>.candidates.adjudicated.csv``
(``final_relation`` / ``final_direction_ok``) or, for a single-annotator series, the series'
only ``<ID>.candidates.<ini>.csv`` (``relation`` / ``direction_ok``; ``<ini>`` = annotator
initials, issue #229). The adjudicated file wins; two single files are ambiguous. Machine: the
verdicts of ``openkos revisions`` (:mod:`afg.extraction.openkos.revisions`). The two sides name
decisions differently, so a machine decision is mapped to a gold decision by the decision
alignment of Experiment A (ADR 0011, ADR 0012) and a :class:`RelationCase` carries that mapping.

Definitions
-----------

* A **link** is any relation other than ``no_relacionada`` and ``introduce``. ``introduce`` (the
  later decision raises a new object) is not a link, the same class as ``no_relacionada``. The
  machine verdict ``unrelated`` is not a link either.
* **Existence**: a machine link is a true positive when both its decisions are aligned and the
  mapped pair is a gold link; a false positive otherwise (the pair is a gold non-link, is not a
  gold candidate, or one of its decisions is not aligned); a gold link without a true positive
  is a false negative. Gold candidates come from the lexical blocker, so a pair it did not
  propose is treated as having no link; the blocker's own recall is measured separately.
* **Type**: over gold links. Principal view: ``revierte`` and ``reemplaza`` are one class
  (OpenKOS's ``reverses`` covers both). Strict view: ``reverses`` is ``revierte`` only.
* **Direction**: the machine's later decision (from event dates, never from the model) must be
  the gold later decision (the CSV's ``later`` when ``direction_ok`` is ``si``, its ``earlier``
  when ``no``). Principal view: an unknown direction is an error. Sensitivity view: pairs with an
  unknown direction leave the denominator. The share of unknown directions is reported apart.

Scopes (every accuracy is reported for each):

* ``end_to_end``: denominator is every gold link; one whose decisions are not aligned, or that
  the machine did not link, counts as missed.
* ``conditional``: denominator is the gold links whose two decisions are aligned.
* ``among_detected``: denominator is the true positives of existence (the literal "accuracy over
  matched linked pairs").

Cases are pooled by summing counts (micro). Proportions carry a Wilson interval
(:func:`afg.evaluation.metrics.wilson_interval`); with so few gold relations (9 in development)
the intervals are wide and the figures are descriptive.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from afg.domain.relation import RelationType
from afg.evaluation.metrics import precision_recall_f1, wilson_interval
from afg.evaluation.reference import SeriesFile, resolve_series_file
from afg.extraction.openkos.revisions import MachineRelation
from afg.shared.csvio import open_csv_reader
from afg.shared.paths import GOLD_RELATIONS_DIR

_NON_LINKS = frozenset({RelationType.INTRODUCE, RelationType.NO_RELACIONADA})
_REVERSAL_CLASS = frozenset({RelationType.REVIERTE, RelationType.REEMPLAZA})
_DIRECTION_OK = "si"
EVOLUTION_RELATIONS = frozenset(
    {RelationType.REFINA, RelationType.REVIERTE, RelationType.REEMPLAZA}
)
"""Labels of a decision that evolves: the relations an E3 question can be about."""


@dataclass(frozen=True, slots=True)
class GoldPair:
    """One adjudicated candidate pair, ordered as the CSV orders it."""

    earlier_decision_id: str
    later_decision_id: str
    relation: RelationType
    direction_ok: bool

    @property
    def is_link(self) -> bool:
        return self.relation not in _NON_LINKS

    @property
    def true_later(self) -> str:
        """The decision that really acts on the other (swapped when ``direction_ok`` is ``no``)."""
        return self.later_decision_id if self.direction_ok else self.earlier_decision_id

    @property
    def true_earlier(self) -> str:
        return self.earlier_decision_id if self.direction_ok else self.later_decision_id


def gold_source(series_id: str, relations_dir: Path = GOLD_RELATIONS_DIR) -> SeriesFile:
    """The candidates file that is the gold of ``series_id`` and its kind.

    Raises:
        FileNotFoundError: no ``.candidates.adjudicated.csv`` and no ``.candidates.<ini>.csv``.
        AmbiguousReferenceError: no adjudication and two or more single-annotator files.
    """
    return resolve_series_file(series_id, relations_dir, "candidates")


def load_gold_pairs(
    series_id: str, *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> tuple[GoldPair, ...]:
    """The gold pairs of ``series_id`` (:func:`gold_source`: adjudicated, else the single file).

    Rows without a relation (not yet adjudicated) are skipped; ``no_relacionada`` and
    ``introduce`` rows are kept because they are the gold non-links.

    Raises:
        FileNotFoundError: neither kind of file exists.
        AmbiguousReferenceError: two or more single-annotator files and no adjudication.
    """
    source = gold_source(series_id, relations_dir)
    path = source.path
    if source.kind == "adjudicated":
        relation_col, direction_col = "final_relation", "final_direction_ok"
    else:
        relation_col, direction_col = "relation", "direction_ok"
    pairs: list[GoldPair] = []
    with open_csv_reader(path) as handle:
        for row in csv.DictReader(handle):
            relation = (row.get(relation_col) or "").strip()
            earlier = (row.get("earlier_decision_id") or "").strip()
            later = (row.get("later_decision_id") or "").strip()
            if not (relation and earlier and later):
                continue
            direction = (row.get(direction_col) or "").strip()
            pairs.append(
                GoldPair(earlier, later, RelationType(relation), direction == _DIRECTION_OK)
            )
    return tuple(pairs)


def load_gold_pair_labels(
    series_id: str, *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> tuple[tuple[str, str], ...]:
    """``(pair_id, relation)`` of every labelled row of the gold of ``series_id``.

    The file is the one :func:`gold_source` resolves (adjudicated, else the single-annotator
    file), so the label column is ``final_relation`` or ``relation`` accordingly. Rows without
    a relation are skipped.

    Raises:
        FileNotFoundError: neither kind of file exists.
        AmbiguousReferenceError: two or more single-annotator files and no adjudication.
    """
    source = gold_source(series_id, relations_dir)
    relation_col = "final_relation" if source.kind == "adjudicated" else "relation"
    labels: list[tuple[str, str]] = []
    with open_csv_reader(source.path) as handle:
        for row in csv.DictReader(handle):
            relation = (row.get(relation_col) or "").strip()
            pair_id = (row.get("pair_id") or "").strip()
            if relation and pair_id:
                labels.append((pair_id, relation))
    return tuple(labels)


def count_evolution_relations(labels: Iterable[tuple[str, str]]) -> int:
    """Distinct pair ids whose relation is ``refina``, ``revierte`` or ``reemplaza``.

    ``labels`` are ``(pair_id, relation)`` rows. A pair id counts once however many rows carry
    it. Pure: it reads nothing, so the rule is testable without disk.
    """
    evolution = {r.value for r in EVOLUTION_RELATIONS}
    return len({pair_id for pair_id, relation in labels if relation.strip() in evolution})


def available_evolution_relations(
    series_ids: Iterable[str], *, relations_dir: Path = GOLD_RELATIONS_DIR
) -> int:
    """Evolution relations in the gold of ``series_ids`` (:func:`count_evolution_relations`)."""
    return count_evolution_relations(
        label
        for series_id in series_ids
        for label in load_gold_pair_labels(series_id, relations_dir=relations_dir)
    )


@dataclass(frozen=True, slots=True)
class RelationCase:
    """One (series, run): its gold pairs, its machine relations and the decision mapping.

    ``mapping`` sends an OpenKOS decision id to the gold decision id it is aligned with.
    """

    label: str
    gold: tuple[GoldPair, ...]
    machine: tuple[MachineRelation, ...]
    mapping: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Proportion:
    """``successes`` out of ``trials`` with its Wilson interval (``None`` when no trials)."""

    successes: int
    trials: int
    rate: float | None
    lower: float | None
    upper: float | None

    @classmethod
    def of(cls, successes: int, trials: int) -> Proportion:
        if trials == 0:
            return cls(successes, 0, None, None, None)
        interval = wilson_interval(successes, trials)
        return cls(successes, trials, interval.point_estimate, interval.lower, interval.upper)


@dataclass(frozen=True, slots=True)
class ExistenceScore:
    """Link existence: precision, recall and F1 of the machine links."""

    tp: int
    fp: int
    fn: int
    precision: Proportion
    recall: Proportion
    f1: float | None
    fp_breakdown: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class AccuracyViews:
    """One accuracy over its three denominators (module docstring)."""

    end_to_end: Proportion
    conditional: Proportion
    among_detected: Proportion


@dataclass(frozen=True, slots=True)
class RelationScore:
    """Every figure of ADR 0016 for one or several pooled cases."""

    n_gold_pairs: int
    n_gold_links: int
    n_gold_links_aligned: int
    n_machine_relations: int
    n_machine_links: int
    n_machine_links_aligned: int
    existence_end_to_end: ExistenceScore
    existence_conditional: ExistenceScore
    type_principal: AccuracyViews
    type_strict: AccuracyViews
    direction_principal: AccuracyViews
    direction_unknown_excluded: AccuracyViews
    unknown_direction: Proportion

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class _GoldLinkOutcome:
    """What happened to one gold link: found or not, and how well when found."""

    aligned: bool
    found: bool = False
    type_merged_ok: bool = False
    type_strict_ok: bool = False
    direction_known: bool = False
    direction_ok: bool = False


@dataclass(slots=True)
class _Tally:
    n_gold_pairs: int = 0
    n_machine_relations: int = 0
    n_machine_links: int = 0
    n_machine_links_aligned: int = 0
    fp_not_candidate: int = 0
    fp_gold_no_link: int = 0
    fp_unaligned: int = 0
    outcomes: list[_GoldLinkOutcome] = field(default_factory=list)


def _type_class(relation: RelationType, *, merged: bool) -> RelationType:
    return RelationType.REVIERTE if merged and relation in _REVERSAL_CLASS else relation


def _tally_case(case: RelationCase, tally: _Tally) -> None:
    aligned_gold = set(case.mapping.values())
    by_pair = {frozenset((g.earlier_decision_id, g.later_decision_id)): g for g in case.gold}
    outcome_of: dict[frozenset[str], _GoldLinkOutcome] = {}
    for pair, listed in by_pair.items():
        if listed.is_link:
            outcome = _GoldLinkOutcome(
                aligned=listed.earlier_decision_id in aligned_gold
                and listed.later_decision_id in aligned_gold
            )
            outcome_of[pair] = outcome
            tally.outcomes.append(outcome)

    tally.n_gold_pairs += len(by_pair)
    tally.n_machine_relations += len(case.machine)
    for found in case.machine:
        if not found.is_link:
            continue
        tally.n_machine_links += 1
        mapped = [case.mapping.get(i) for i in found.decision_ids]
        if None in mapped:
            tally.fp_unaligned += 1
            continue
        tally.n_machine_links_aligned += 1
        pair = frozenset(i for i in mapped if i is not None)
        gold = by_pair.get(pair)
        if gold is None:
            tally.fp_not_candidate += 1
        elif not gold.is_link:
            tally.fp_gold_no_link += 1
        else:
            hit = outcome_of[pair]
            hit.found = True
            hit.type_merged_ok = _type_class(found.relation, merged=True) == _type_class(
                gold.relation, merged=True
            )
            hit.type_strict_ok = found.relation == gold.relation
            hit.direction_known = found.source_decision_id is not None
            hit.direction_ok = (
                found.source_decision_id is not None
                and case.mapping.get(found.source_decision_id) == gold.true_later
            )


def _existence(tally: _Tally, *, conditional: bool) -> ExistenceScore:
    gold_links = [o for o in tally.outcomes if o.aligned or not conditional]
    tp = sum(o.found for o in gold_links)
    fn = len(gold_links) - tp
    fp_unaligned = 0 if conditional else tally.fp_unaligned
    fp = tally.fp_not_candidate + tally.fp_gold_no_link + fp_unaligned
    _, _, f1 = precision_recall_f1(tp, fp, fn)
    return ExistenceScore(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=Proportion.of(tp, tp + fp),
        recall=Proportion.of(tp, tp + fn),
        f1=f1 if (tp + fp + fn) else None,
        fp_breakdown={
            "gold_no_link": tally.fp_gold_no_link,
            "not_candidate": tally.fp_not_candidate,
            "unaligned": fp_unaligned,
        },
    )


def _views(tally: _Tally, *, ok: str, known: str | None = None) -> AccuracyViews:
    """An accuracy over the three denominators; ``known`` drops detected pairs it marks False."""

    def keep(o: _GoldLinkOutcome) -> bool:
        return known is None or not o.found or bool(getattr(o, known))

    def over(outcomes: Sequence[_GoldLinkOutcome]) -> Proportion:
        kept = [o for o in outcomes if keep(o)]
        return Proportion.of(sum(bool(o.found and getattr(o, ok)) for o in kept), len(kept))

    detected = [o for o in tally.outcomes if o.found]
    return AccuracyViews(
        end_to_end=over(tally.outcomes),
        conditional=over([o for o in tally.outcomes if o.aligned]),
        among_detected=over(detected),
    )


def score_relations(cases: Sequence[RelationCase]) -> RelationScore:
    """Score and pool ``cases`` (one per series and run) by summing their counts."""
    tally = _Tally()
    for case in cases:
        _tally_case(case, tally)
    detected = [o for o in tally.outcomes if o.found]
    return RelationScore(
        n_gold_pairs=tally.n_gold_pairs,
        n_gold_links=len(tally.outcomes),
        n_gold_links_aligned=sum(o.aligned for o in tally.outcomes),
        n_machine_relations=tally.n_machine_relations,
        n_machine_links=tally.n_machine_links,
        n_machine_links_aligned=tally.n_machine_links_aligned,
        existence_end_to_end=_existence(tally, conditional=False),
        existence_conditional=_existence(tally, conditional=True),
        type_principal=_views(tally, ok="type_merged_ok"),
        type_strict=_views(tally, ok="type_strict_ok"),
        direction_principal=_views(tally, ok="direction_ok"),
        direction_unknown_excluded=_views(tally, ok="direction_ok", known="direction_known"),
        unknown_direction=Proportion.of(
            sum(not o.direction_known for o in detected), len(detected)
        ),
    )
