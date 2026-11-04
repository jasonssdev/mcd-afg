"""Tests for the semantic-channel measurement (``afg.annotation.semantic_channel``).

Everything is synthetic: hand-made decisions, hand-made vectors and fake embedders. No
Ollama, no AMI corpus and no real annotation file are needed.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.annotation.recall import SeriesRecallCounts, estimate_recall
from afg.annotation.semantic_channel import (
    DEFAULT_THRESHOLDS,
    PairRecord,
    cosine_similarity,
    embed_texts,
    evaluate_channel,
    false_negative_diagnosis,
    lexical_sensitivity,
    read_gold_labels,
    read_recall_sample_labels,
    score_pairs,
    threshold_grid,
    threshold_table,
)
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.metrics import wilson_interval

NO_REL = "no_relacionada"
REL = "refina"


def _decision(id_: str, meeting_id: str, content: str, series_id: str = "ES2015") -> Decision:
    return Decision(
        id=id_,
        series_id=series_id,
        meeting_id=meeting_id,
        decision_object="",
        content=content,
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=(f"{meeting_id}.s.{id_}",)),
    )


# Meeting a holds one decision; meeting b holds four. Against the a decision:
#   b1 shares three tokens (lexical candidate, cosine ~ 0.995),
#   b2 shares nothing and points elsewhere (cosine 0),
#   b3 shares nothing but is close in meaning (cosine 0.8),
#   b4 shares one token only (rejected by min_overlap_tokens=2; cosine 0).
DECISIONS = [
    _decision("A1", "ES2015a", "remote control battery"),
    _decision("B1", "ES2015b", "remote control battery solar"),
    _decision("B2", "ES2015b", "fruit shape banana"),
    _decision("B3", "ES2015b", "device casing rubber"),
    _decision("B4", "ES2015b", "remote speaker"),
]
VECTORS: dict[str, list[float]] = {
    "remote control battery": [1.0, 0.0],
    "remote control battery solar": [1.0, 0.1],
    "fruit shape banana": [0.0, 1.0],
    "device casing rubber": [0.8, 0.6],
    "remote speaker": [0.0, 1.0],
}
LABELS: dict[tuple[str, str], str] = {
    ("A1", "B1"): REL,  # kept relation (candidate)
    ("A1", "B2"): NO_REL,  # sampled rejected, no relation
    ("A1", "B3"): REL,  # sampled rejected, false negative
    # ("A1", "B4") is rejected and NOT sampled.
}


def _records() -> list[PairRecord]:
    return score_pairs(DECISIONS, VECTORS, LABELS)


def _by_pair(records: Sequence[PairRecord]) -> dict[tuple[str, str], PairRecord]:
    return {(r.earlier_id, r.later_id): r for r in records}


class TestCosineSimilarity:
    def test_identical_and_orthogonal(self) -> None:
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)
        assert cosine_similarity([1.0, 0.0], [0.0, 3.0]) == 0.0

    def test_scale_invariant(self) -> None:
        assert cosine_similarity([1.0, 1.0], [5.0, 5.0]) == pytest.approx(1.0)

    def test_zero_vector_is_zero_not_an_error(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="length"):
            cosine_similarity([1.0], [1.0, 2.0])


class TestThresholdGrid:
    def test_default_grid_is_050_to_090_in_steps_of_005(self) -> None:
        assert threshold_grid(0.50, 0.90, 0.05) == DEFAULT_THRESHOLDS
        assert len(DEFAULT_THRESHOLDS) == 9
        assert DEFAULT_THRESHOLDS[0] == 0.5
        assert DEFAULT_THRESHOLDS[-1] == 0.9
        assert 0.75 in DEFAULT_THRESHOLDS  # no float drift

    def test_custom_grid(self) -> None:
        assert threshold_grid(0.2, 0.3, 0.05) == (0.2, 0.25, 0.3)

    def test_rejects_non_positive_step(self) -> None:
        with pytest.raises(ValueError, match="step"):
            threshold_grid(0.5, 0.9, 0.0)


class TestScorePairs:
    def test_every_cross_meeting_pair_is_scored(self) -> None:
        assert len(_records()) == 4

    def test_lexical_flag_matches_the_blocker(self) -> None:
        by_pair = _by_pair(_records())
        assert by_pair[("A1", "B1")].lexical_candidate is True
        assert by_pair[("A1", "B2")].lexical_candidate is False
        assert by_pair[("A1", "B4")].lexical_candidate is False  # one shared token only

    def test_lexical_diagnostics(self) -> None:
        by_pair = _by_pair(_records())
        assert by_pair[("A1", "B1")].shared_tokens == 3
        assert by_pair[("A1", "B1")].overlap_score == pytest.approx(1.0)
        assert by_pair[("A1", "B4")].shared_tokens == 1
        assert by_pair[("A1", "B4")].overlap_score == pytest.approx(0.5)
        assert by_pair[("A1", "B2")].shared_tokens == 0

    def test_cosine_comes_from_the_decision_text_vectors(self) -> None:
        by_pair = _by_pair(_records())
        assert by_pair[("A1", "B3")].cosine == pytest.approx(0.8)
        assert by_pair[("A1", "B2")].cosine == 0.0
        assert by_pair[("A1", "B1")].cosine == pytest.approx(0.995, abs=1e-3)

    def test_labels_are_attached_and_missing_ones_are_none(self) -> None:
        by_pair = _by_pair(_records())
        assert by_pair[("A1", "B3")].label == REL
        assert by_pair[("A1", "B4")].label is None

    def test_role_properties(self) -> None:
        by_pair = _by_pair(_records())
        assert by_pair[("A1", "B1")].is_kept_relation
        assert by_pair[("A1", "B3")].is_false_negative
        assert by_pair[("A1", "B2")].is_sampled_no_relation
        unsampled = by_pair[("A1", "B4")]
        assert not (
            unsampled.is_kept_relation
            or unsampled.is_false_negative
            or unsampled.is_sampled_no_relation
        )

    def test_missing_vector_raises(self) -> None:
        with pytest.raises(KeyError):
            score_pairs(DECISIONS, {}, LABELS)

    def test_empty_decisions_give_no_records(self) -> None:
        assert score_pairs([], VECTORS, LABELS) == []


class TestEvaluateChannel:
    def test_counts_at_a_mid_threshold(self) -> None:
        row = evaluate_channel(_records(), lambda r: r.cosine >= 0.75, name="cos", parameter=0.75)
        assert (row.fn_caught, row.fn_total) == (1, 1)
        assert (row.kept_caught_all, row.kept_total_all) == (1, 1)
        assert (row.kept_caught_sampled, row.kept_total_sampled) == (1, 1)
        assert (row.false_alarms, row.sampled_no_relation) == (0, 1)
        assert row.new_pairs == 1  # only B3: B1 is already a lexical candidate
        assert row.new_pairs_by_series == {"ES2015": 1}
        assert row.lexical_candidates == 1
        assert row.candidates_total == 2

    def test_nothing_caught_when_the_threshold_is_above_every_cosine(self) -> None:
        row = evaluate_channel(_records(), lambda r: r.cosine >= 0.99, name="cos", parameter=0.99)
        assert row.fn_caught == 0
        assert row.new_pairs == 0
        assert row.candidates_total == 1
        assert row.new_pairs_by_series == {"ES2015": 0}
        assert row.union_recall == pytest.approx(row.lexical_recall)

    def test_false_alarm_rate_uses_wilson(self) -> None:
        row = evaluate_channel(_records(), lambda r: r.cosine >= 0.0, name="all", parameter=0.0)
        assert (row.false_alarms, row.sampled_no_relation) == (1, 1)
        ci = wilson_interval(1, 1)
        assert row.false_alarm_rate == 1.0
        assert row.false_alarm_lower == pytest.approx(ci.lower)
        assert row.false_alarm_upper == pytest.approx(ci.upper)

    def test_union_recall_follows_the_stratified_logic(self) -> None:
        # Rejected population 3 (B2, B3, B4), sample of 2 with 1 false negative, 1 kept relation.
        records = _records()
        row = evaluate_channel(records, lambda r: r.cosine >= 0.75, name="cos", parameter=0.75)
        assert row.lexical_recall == pytest.approx(1 / (1 + 1.5))
        # The channel catches the one false negative: caught = 3 * 1/2, nothing left missed.
        assert row.union_recall == pytest.approx(1.0)
        assert row.union_recall_lower is not None and row.union_recall_upper is not None
        assert row.union_recall_lower < 1.0  # the Wilson bound keeps the residual uncertainty
        assert row.union_recall_upper == pytest.approx(1.0)

    def test_lexical_recall_equals_the_recall_module(self) -> None:
        row = evaluate_channel(_records(), lambda r: False, name="none", parameter=None)
        reference = estimate_recall(
            [
                SeriesRecallCounts(
                    series_id="ES2015",
                    n_sampled=2,
                    n_false_negative=1,
                    rejected_population=3,
                    kept_relations=1,
                )
            ]
        )
        assert row.lexical_recall == pytest.approx(reference.recall)
        assert row.union_recall == pytest.approx(reference.recall)

    def test_union_is_none_without_any_sampled_series(self) -> None:
        unlabeled = score_pairs(DECISIONS, VECTORS, {})
        row = evaluate_channel(unlabeled, lambda r: r.cosine >= 0.5, name="cos", parameter=0.5)
        assert row.union_recall is None
        assert row.lexical_recall is None
        assert row.false_alarm_rate is None
        assert row.new_pairs == 1  # B3 (0.8); B2 and B4 have cosine 0

    def test_empty_series_list(self) -> None:
        row = evaluate_channel([], lambda r: True, name="cos", parameter=0.5)
        assert row.new_pairs == 0
        assert row.candidates_total == 0
        assert row.new_pairs_by_series == {}
        assert row.union_recall is None

    def test_per_series_new_pairs_cover_series_without_new_pairs(self) -> None:
        other = [
            _decision("C1", "TS3005a", "alpha beta gamma", "TS3005"),
            _decision("C2", "TS3005b", "delta epsilon zeta", "TS3005"),
        ]
        vectors = {**VECTORS, "alpha beta gamma": [1.0, 0.0], "delta epsilon zeta": [0.0, 1.0]}
        records = score_pairs(DECISIONS, vectors, LABELS) + score_pairs(other, vectors, {})
        row = evaluate_channel(records, lambda r: r.cosine >= 0.75, name="cos", parameter=0.75)
        assert row.new_pairs_by_series == {"ES2015": 1, "TS3005": 0}
        assert row.new_pairs == 1


class TestThresholdTable:
    def test_one_row_per_threshold_in_order(self) -> None:
        rows = threshold_table(_records(), (0.5, 0.75, 0.9))
        assert [r.parameter for r in rows] == [0.5, 0.75, 0.9]

    def test_false_negatives_caught_never_increase_with_the_threshold(self) -> None:
        rows = threshold_table(_records(), DEFAULT_THRESHOLDS)
        caught = [r.fn_caught for r in rows]
        assert caught == sorted(caught, reverse=True)
        new = [r.new_pairs for r in rows]
        assert new == sorted(new, reverse=True)

    def test_grid_values_around_the_synthetic_cosine(self) -> None:
        rows = {r.parameter: r for r in threshold_table(_records(), (0.75, 0.85))}
        assert rows[0.75].fn_caught == 1
        assert rows[0.85].fn_caught == 0
        assert rows[0.85].kept_caught_all == 1  # B1 at 0.995 still passes

    def test_empty_records(self) -> None:
        rows = threshold_table([], (0.5,))
        assert rows[0].new_pairs == 0


class TestLexicalSensitivity:
    def test_loosening_min_overlap_adds_the_one_token_pair(self) -> None:
        rows = lexical_sensitivity(_records(), [(0.30, 1)])
        assert len(rows) == 1
        row = rows[0]
        assert row.new_pairs == 1  # B4
        assert row.fn_caught == 0  # the false negative (B3) shares no token
        assert row.candidates_total == 2
        assert "0.30" in row.name

    def test_a_looser_threshold_catches_nothing_without_overlap(self) -> None:
        rows = lexical_sensitivity(_records(), [(0.0, 0)])
        assert rows[0].new_pairs == 3  # every rejected pair
        assert rows[0].fn_caught == 1


class TestFalseNegativeDiagnosis:
    def test_one_row_per_false_negative_with_aggregate_fields_only(self) -> None:
        rows = false_negative_diagnosis(_records())
        assert len(rows) == 1
        row = rows[0]
        assert (row.series_id, row.earlier_id, row.later_id) == ("ES2015", "A1", "B3")
        assert row.shared_tokens == 0
        assert row.overlap_class == "zero_overlap"
        assert row.cosine == pytest.approx(0.8)
        # B3 has the highest cosine among the series' rejected pairs: rank share 1/3.
        assert row.cosine_rank_share == pytest.approx(1 / 3)
        assert not hasattr(row, "earlier_text")

    def test_partial_overlap_is_a_near_miss(self) -> None:
        labels = {**LABELS, ("A1", "B4"): REL}
        rows = false_negative_diagnosis(score_pairs(DECISIONS, VECTORS, labels))
        by_later = {r.later_id: r for r in rows}
        assert by_later["B4"].overlap_class == "partial_overlap"
        assert by_later["B4"].shared_tokens == 1

    def test_no_false_negatives(self) -> None:
        assert false_negative_diagnosis(score_pairs(DECISIONS, VECTORS, {})) == []


class _CountingEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(t)), 1.0] for t in texts]


class TestEmbedTexts:
    def test_embeds_unique_texts_once(self, tmp_path: Path) -> None:
        embedder = _CountingEmbedder()
        vectors = embed_texts(["aa", "bbb", "aa"], embedder, tmp_path / "c.json", model="m")
        assert vectors == {"aa": [2.0, 1.0], "bbb": [3.0, 1.0]}
        assert embedder.calls == [["aa", "bbb"]]

    def test_second_call_reads_the_cache(self, tmp_path: Path) -> None:
        cache = tmp_path / "c.json"
        embed_texts(["aa", "bbb"], _CountingEmbedder(), cache, model="m")
        second = _CountingEmbedder()
        vectors = embed_texts(["bbb", "aa"], second, cache, model="m")
        assert second.calls == []
        assert vectors["aa"] == [2.0, 1.0]

    def test_only_missing_texts_are_embedded(self, tmp_path: Path) -> None:
        cache = tmp_path / "c.json"
        embed_texts(["aa"], _CountingEmbedder(), cache, model="m")
        second = _CountingEmbedder()
        vectors = embed_texts(["aa", "cccc"], second, cache, model="m")
        assert second.calls == [["cccc"]]
        assert set(vectors) == {"aa", "cccc"}

    def test_cache_of_another_model_is_not_reused(self, tmp_path: Path) -> None:
        cache = tmp_path / "c.json"
        embed_texts(["aa"], _CountingEmbedder(), cache, model="m1")
        second = _CountingEmbedder()
        embed_texts(["aa"], second, cache, model="m2")
        assert second.calls == [["aa"]]

    def test_no_texts_means_no_call_and_no_file(self, tmp_path: Path) -> None:
        embedder = _CountingEmbedder()
        assert embed_texts([], embedder, tmp_path / "c.json", model="m") == {}
        assert embedder.calls == []

    def test_wrong_number_of_vectors_raises(self, tmp_path: Path) -> None:
        class Broken:
            def embed(self, texts: Sequence[str]) -> list[list[float]]:
                return [[1.0]]

        with pytest.raises(ValueError, match="vectors"):
            embed_texts(["a", "b"], Broken(), tmp_path / "c.json", model="m")

    def test_cosine_of_cached_vectors_is_finite(self, tmp_path: Path) -> None:
        vectors = embed_texts(["aa", "bbb"], _CountingEmbedder(), tmp_path / "c.json", model="m")
        assert math.isfinite(cosine_similarity(vectors["aa"], vectors["bbb"]))


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class TestLabelReaders:
    def test_recall_sample_labels(self, tmp_path: Path) -> None:
        _write_csv(
            tmp_path / "ES2015.recall-sample.gv.csv",
            ["pair_id", "earlier_decision_id", "later_decision_id", "relation"],
            [["ES2015.r001", "A1", "B2", NO_REL], ["ES2015.r002", "A1", "B3", REL]],
        )
        labels = read_recall_sample_labels("ES2015", "gv", relations_dir=tmp_path)
        assert labels == {("A1", "B2"): NO_REL, ("A1", "B3"): REL}

    def test_missing_recall_sample_gives_no_labels(self, tmp_path: Path) -> None:
        assert read_recall_sample_labels("ES2015", "gv", relations_dir=tmp_path) == {}

    def test_gold_labels_from_an_adjudicated_file(self, tmp_path: Path) -> None:
        _write_csv(
            tmp_path / "ES2015.candidates.adjudicated.csv",
            [
                "pair_id",
                "earlier_decision_id",
                "later_decision_id",
                "final_relation",
                "final_direction_ok",
            ],
            [
                ["ES2015.p001", "A1", "B1", REL, "si"],
                ["ES2015.p002", "A1", "B4", NO_REL, "si"],
            ],
        )
        labels = read_gold_labels("ES2015", relations_dir=tmp_path)
        assert labels == {("A1", "B1"): REL, ("A1", "B4"): NO_REL}

    def test_series_without_gold_gives_no_labels(self, tmp_path: Path) -> None:
        assert read_gold_labels("ES2015", relations_dir=tmp_path) == {}
