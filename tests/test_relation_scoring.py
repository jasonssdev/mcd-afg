"""Tests for the scoring of machine temporal relations against the gold relations (ADR 0016)."""

from __future__ import annotations

from pathlib import Path

import pytest

from afg.domain.relation import RelationType
from afg.evaluation.relations import (
    GoldPair,
    RelationCase,
    load_gold_pairs,
    score_relations,
)
from afg.extraction.openkos.revisions import MachineRelation

R = RelationType


def gold(
    earlier: str, later: str, relation: RelationType, *, direction_ok: bool = True
) -> GoldPair:
    return GoldPair(earlier, later, relation, direction_ok)


def machine(
    a: str,
    b: str,
    verdict: str,
    *,
    later: str | None = None,
    reason: str | None = None,
) -> MachineRelation:
    """A machine relation between decisions ``m<a>`` and ``m<b>``; ``later`` is a or b."""
    ids = (f"decisions/m{a}", f"decisions/m{b}")
    source = f"decisions/m{later}" if later else None
    target = None if later is None else next(i for i in ids if i != source)
    relation = {
        "reverses": R.REVIERTE,
        "refines": R.REFINA,
        "reaffirms": R.REAFIRMA,
        "unrelated": R.NO_RELACIONADA,
    }[verdict]
    return MachineRelation(
        decision_ids=ids,
        relation=relation,
        verdict=verdict,
        confidence=0.9,
        source_decision_id=source,
        target_decision_id=target,
        direction_reason=reason or ("dated" if later else "equal"),
    )


MAPPING = {f"decisions/m{i}": f"g{i}" for i in range(1, 9)}


def case(gold_pairs, machine_relations, mapping=None, label="c"):  # type: ignore[no-untyped-def]
    return RelationCase(
        label, tuple(gold_pairs), tuple(machine_relations), MAPPING if mapping is None else mapping
    )


def test_perfect_machine_scores_one_everywhere() -> None:
    score = score_relations(
        [
            case(
                [gold("g1", "g2", R.REFINA), gold("g3", "g4", R.REAFIRMA)],
                [
                    machine("1", "2", "refines", later="2"),
                    machine("3", "4", "reaffirms", later="4"),
                ],
            )
        ]
    )

    e2e = score.existence_end_to_end
    assert (e2e.tp, e2e.fp, e2e.fn) == (2, 0, 0)
    assert e2e.precision.rate == 1.0 and e2e.recall.rate == 1.0 and e2e.f1 == 1.0
    assert score.type_principal.end_to_end.rate == 1.0
    assert score.type_strict.end_to_end.rate == 1.0
    assert score.direction_principal.end_to_end.rate == 1.0
    assert score.unknown_direction.successes == 0
    assert score.unknown_direction.trials == 2


def test_wilson_interval_accompanies_each_proportion() -> None:
    score = score_relations(
        [case([gold("g1", "g2", R.REFINA)], [machine("1", "2", "refines", later="2")])]
    )

    recall = score.existence_end_to_end.recall
    assert (recall.successes, recall.trials) == (1, 1)
    assert recall.lower is not None and recall.upper is not None
    assert 0.0 < recall.lower < 1.0 and recall.upper == pytest.approx(1.0)


def test_no_findings_means_everything_missed() -> None:
    score = score_relations([case([gold("g1", "g2", R.REFINA), gold("g3", "g4", R.REAFIRMA)], [])])

    e2e = score.existence_end_to_end
    assert (e2e.tp, e2e.fp, e2e.fn) == (0, 0, 2)
    assert e2e.precision.rate is None and e2e.precision.trials == 0
    assert e2e.recall.rate == 0.0
    assert e2e.f1 == 0.0
    assert score.type_principal.end_to_end.rate == 0.0
    assert score.type_principal.end_to_end.trials == 2
    assert score.type_principal.among_detected.rate is None
    assert score.direction_principal.among_detected.trials == 0
    assert score.unknown_direction.rate is None


def test_unrelated_verdict_is_not_a_link() -> None:
    score = score_relations(
        [case([gold("g1", "g2", R.REFINA)], [machine("1", "2", "unrelated", later="2")])]
    )

    assert score.n_machine_links == 0
    assert score.existence_end_to_end.fn == 1
    assert score.existence_end_to_end.fp == 0


def test_gold_introduce_and_no_relacionada_are_not_links() -> None:
    gold_pairs = [
        gold("g1", "g2", R.INTRODUCE),
        gold("g3", "g4", R.NO_RELACIONADA),
        gold("g5", "g6", R.REFINA),
    ]
    machine_relations = [
        machine("1", "2", "refines", later="2"),
        machine("5", "6", "refines", later="6"),
    ]

    score = score_relations([case(gold_pairs, machine_relations)])

    assert score.n_gold_pairs == 3
    assert score.n_gold_links == 1
    e2e = score.existence_end_to_end
    assert (e2e.tp, e2e.fp, e2e.fn) == (1, 1, 0)
    assert e2e.fp_breakdown == {"gold_no_link": 1, "not_candidate": 0, "unaligned": 0}


def test_machine_link_outside_gold_candidates_and_unaligned_are_false_positives() -> None:
    gold_pairs = [gold("g1", "g2", R.REFINA)]
    machine_relations = [
        machine("1", "2", "refines", later="2"),
        machine("3", "4", "refines", later="4"),  # both aligned, pair not a gold candidate
        machine("5", "9", "refines", later="9"),  # m9 has no gold counterpart
    ]

    score = score_relations([case(gold_pairs, machine_relations)])

    e2e = score.existence_end_to_end
    assert (e2e.tp, e2e.fp) == (1, 2)
    assert e2e.fp_breakdown == {"gold_no_link": 0, "not_candidate": 1, "unaligned": 1}
    conditional = score.existence_conditional
    assert (conditional.tp, conditional.fp) == (1, 1)  # the unaligned link leaves the scope
    assert conditional.fp_breakdown["unaligned"] == 0


def test_unaligned_gold_pair_counts_as_missed_end_to_end_and_is_out_of_conditional() -> None:
    gold_pairs = [
        gold("g1", "g2", R.REFINA),
        gold("g3", "g10", R.REAFIRMA),  # g10 has no machine decision
    ]
    machine_relations = [machine("1", "2", "refines", later="2")]

    score = score_relations([case(gold_pairs, machine_relations)])

    assert score.n_gold_links == 2
    assert score.n_gold_links_aligned == 1
    assert (
        score.existence_end_to_end.recall.successes,
        score.existence_end_to_end.recall.trials,
    ) == (1, 2)
    cond = score.existence_conditional
    assert (cond.recall.successes, cond.recall.trials) == (1, 1)
    assert score.type_principal.end_to_end.trials == 2
    assert score.type_principal.conditional.trials == 1
    assert score.direction_principal.conditional.trials == 1


def test_reverses_matches_reemplaza_in_the_principal_but_not_in_the_strict_view() -> None:
    gold_pairs = [gold("g1", "g2", R.REEMPLAZA), gold("g3", "g4", R.REVIERTE)]
    machine_relations = [
        machine("1", "2", "reverses", later="2"),
        machine("3", "4", "reverses", later="4"),
    ]

    score = score_relations([case(gold_pairs, machine_relations)])

    assert (
        score.type_principal.among_detected.successes,
        score.type_principal.among_detected.trials,
    ) == (2, 2)
    assert (
        score.type_strict.among_detected.successes,
        score.type_strict.among_detected.trials,
    ) == (1, 2)


def test_wrong_type_is_an_error_in_both_views() -> None:
    score = score_relations(
        [case([gold("g1", "g2", R.REAFIRMA)], [machine("1", "2", "refines", later="2")])]
    )

    assert score.type_principal.among_detected.successes == 0
    assert score.type_strict.among_detected.successes == 0
    assert score.type_principal.among_detected.trials == 1


def test_inverted_direction_is_an_error() -> None:
    score = score_relations(
        [case([gold("g1", "g2", R.REFINA)], [machine("1", "2", "refines", later="1")])]
    )

    assert score.direction_principal.among_detected.successes == 0
    assert score.direction_principal.among_detected.trials == 1
    assert score.direction_unknown_excluded.among_detected.trials == 1


def test_unknown_direction_is_an_error_in_the_principal_and_excluded_in_the_sensitivity() -> None:
    gold_pairs = [gold("g1", "g2", R.REFINA), gold("g3", "g4", R.REAFIRMA)]
    machine_relations = [
        machine("1", "2", "refines", later=None, reason="equal"),
        machine("3", "4", "reaffirms", later="4"),
    ]

    score = score_relations([case(gold_pairs, machine_relations)])

    principal = score.direction_principal
    assert (principal.among_detected.successes, principal.among_detected.trials) == (1, 2)
    assert (principal.end_to_end.successes, principal.end_to_end.trials) == (1, 2)
    excluded = score.direction_unknown_excluded
    assert (excluded.among_detected.successes, excluded.among_detected.trials) == (1, 1)
    assert (excluded.end_to_end.successes, excluded.end_to_end.trials) == (1, 1)
    assert (score.unknown_direction.successes, score.unknown_direction.trials) == (1, 2)


def test_all_unknown_direction_leaves_the_sensitivity_empty() -> None:
    machine_relations = [machine("1", "2", "refines", later=None, reason="missing")]

    score = score_relations([case([gold("g1", "g2", R.REFINA)], machine_relations)])

    assert score.direction_principal.among_detected.rate == 0.0
    assert score.direction_unknown_excluded.among_detected.trials == 0
    assert score.direction_unknown_excluded.among_detected.rate is None
    assert score.unknown_direction.rate == 1.0


def test_gold_direction_not_ok_means_the_listed_earlier_is_really_later() -> None:
    gold_pairs = [gold("g1", "g2", R.REFINA, direction_ok=False)]

    correct = score_relations([case(gold_pairs, [machine("1", "2", "refines", later="1")])])
    wrong = score_relations([case(gold_pairs, [machine("1", "2", "refines", later="2")])])

    assert correct.direction_principal.among_detected.successes == 1
    assert wrong.direction_principal.among_detected.successes == 0


def test_undetected_gold_link_counts_against_end_to_end_type_and_direction() -> None:
    gold_pairs = [gold("g1", "g2", R.REFINA), gold("g3", "g4", R.REFINA)]
    machine_relations = [machine("1", "2", "refines", later="2")]

    score = score_relations([case(gold_pairs, machine_relations)])

    assert (score.type_principal.end_to_end.successes, score.type_principal.end_to_end.trials) == (
        1,
        2,
    )
    assert (
        score.type_principal.among_detected.successes,
        score.type_principal.among_detected.trials,
    ) == (1, 1)
    assert (
        score.direction_principal.end_to_end.successes,
        score.direction_principal.end_to_end.trials,
    ) == (1, 2)


def test_cases_are_pooled_by_summing_counts() -> None:
    first = case([gold("g1", "g2", R.REFINA)], [machine("1", "2", "refines", later="2")], label="a")
    second = case([gold("g1", "g2", R.REFINA)], [], label="b")

    pooled = score_relations([first, second])

    assert (pooled.existence_end_to_end.tp, pooled.existence_end_to_end.fn) == (1, 1)
    assert pooled.n_gold_links == 2


def test_empty_input_scores_without_error() -> None:
    score = score_relations([])

    assert score.n_gold_pairs == 0
    assert score.existence_end_to_end.recall.rate is None
    assert score.existence_end_to_end.f1 is None


def test_score_serialises_to_plain_dicts() -> None:
    score = score_relations(
        [case([gold("g1", "g2", R.REFINA)], [machine("1", "2", "refines", later="2")])]
    )

    data = score.to_dict()

    assert data["existence_end_to_end"]["precision"]["successes"] == 1
    assert data["type_principal"]["end_to_end"]["rate"] == 1.0
    assert data["direction_unknown_excluded"]["conditional"]["trials"] == 1


# --- gold loading -----------------------------------------------------------------------------

ADJUDICATED = (
    "pair_id,earlier_decision_id,later_decision_id,final_relation,final_direction_ok\n"
    "ES2015.p001,ES2015a.d01,ES2015b.d01,refina,si\n"
    "ES2015.p002,ES2015c.d06,ES2015d.d04,reafirma,no\n"
    "ES2015.p003,ES2015a.d02,ES2015b.d02,no_relacionada,si\n"
    "ES2015.p004,ES2015a.d03,ES2015b.d03,introduce,si\n"
    "ES2015.p005,ES2015a.d04,ES2015b.d04,,\n"
)
SINGLE = (
    "pair_id,earlier_decision_id,later_decision_id,relation,direction_ok\n"
    "IS1004.p001,IS1004a.d01,IS1004b.d01,refina,si\n"
    "IS1004.p002,IS1004a.d01,IS1004b.d02,reemplaza,si\n"
)


def test_load_gold_pairs_reads_the_adjudicated_file_and_skips_unadjudicated_rows(
    tmp_path: Path,
) -> None:
    (tmp_path / "ES2015.candidates.adjudicated.csv").write_text(ADJUDICATED, encoding="utf-8")
    (tmp_path / "ES2015.candidates.gv.csv").write_text("garbage", encoding="utf-8")

    pairs = load_gold_pairs("ES2015", relations_dir=tmp_path)

    assert [
        (p.earlier_decision_id, p.later_decision_id, p.relation, p.direction_ok) for p in pairs
    ] == [
        ("ES2015a.d01", "ES2015b.d01", R.REFINA, True),
        ("ES2015c.d06", "ES2015d.d04", R.REAFIRMA, False),
        ("ES2015a.d02", "ES2015b.d02", R.NO_RELACIONADA, True),
        ("ES2015a.d03", "ES2015b.d03", R.INTRODUCE, True),
    ]
    assert pairs[1].true_later == "ES2015c.d06"
    assert pairs[0].is_link and not pairs[2].is_link and not pairs[3].is_link


def test_load_gold_pairs_falls_back_to_the_single_annotator_file(tmp_path: Path) -> None:
    (tmp_path / "IS1004.candidates.gv.csv").write_text(SINGLE, encoding="utf-8")

    pairs = load_gold_pairs("IS1004", relations_dir=tmp_path)

    assert [p.relation for p in pairs] == [R.REFINA, R.REEMPLAZA]


def test_load_gold_pairs_without_any_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="IS1004"):
        load_gold_pairs("IS1004", relations_dir=tmp_path)
