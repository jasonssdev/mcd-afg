"""Tests for the OE1 candidate-pair blocker (thesis section 3 OE1, manual section 4/5).

Three kinds of coverage:

- Pure unit tests of the maths (overlap/Jaccard, cross-meeting-only, ordering,
  determinism, partitioning) that need no corpus and always run.
- The turbo-button regression test: the entire reason this module scores pairs with the
  overlap coefficient instead of Jaccard. Skipped when the corpus is absent.
- Corpus-backed candidate counts for ES2015 and IS1004, measured against the real
  download. Skipped when the corpus is absent.
"""

from __future__ import annotations

import pytest

from afg.annotation.blocking import (
    BLOCKER_VERSION,
    STOPWORDS,
    CandidatePair,
    decisions_from_abstractive,
    generate_candidates,
    jaccard,
    overlap_coefficient,
    rejected_pairs,
    sample_rejected,
    tokenize,
)
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.shared.config import load_corpus_config
from afg.shared.paths import AMI_DIR

_corpus_present = AMI_DIR.exists() and any(
    p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".") for p in AMI_DIR.rglob("*")
)

requires_corpus = pytest.mark.skipif(
    not _corpus_present, reason="AMI corpus not downloaded at data/raw/ami/"
)


def _decision(
    id_: str, meeting_id: str, content: str, *, series_id: str = "ES2015"
) -> Decision:
    return Decision(
        id=id_,
        series_id=series_id,
        meeting_id=meeting_id,
        decision_object="",
        content=content,
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=(id_,)),
    )


class TestTokenize:
    def test_lowercases_and_keeps_letters_only(self) -> None:
        assert tokenize("Turbo-Button 2000!") == frozenset({"turbo", "button"})

    def test_drops_short_tokens(self) -> None:
        # "tv" and "on" are both below the 3-char minimum.
        assert "tv" not in tokenize("turn on the tv")
        assert "on" not in tokenize("turn on the tv")

    def test_drops_stopwords(self) -> None:
        assert tokenize("the a an will be is are") == frozenset()

    def test_empty_string(self) -> None:
        assert tokenize("") == frozenset()

    def test_stopwords_is_versioned_and_frozen(self) -> None:
        assert isinstance(STOPWORDS, frozenset)
        assert "the" in STOPWORDS
        assert BLOCKER_VERSION == "1.1"


class TestOverlapCoefficient:
    def test_matches_manual_definition(self) -> None:
        a = frozenset({"turbo", "button", "base", "station"})
        b = frozenset({"turbo", "button"})
        assert overlap_coefficient(a, b) == pytest.approx(1.0)

    def test_symmetric(self) -> None:
        a = frozenset({"turbo", "button", "base"})
        b = frozenset({"button", "device"})
        assert overlap_coefficient(a, b) == overlap_coefficient(b, a)

    def test_empty_set_a_is_zero(self) -> None:
        assert overlap_coefficient(frozenset(), frozenset({"turbo"})) == 0.0

    def test_empty_set_b_is_zero(self) -> None:
        assert overlap_coefficient(frozenset({"turbo"}), frozenset()) == 0.0

    def test_both_empty_is_zero(self) -> None:
        assert overlap_coefficient(frozenset(), frozenset()) == 0.0

    def test_disjoint_sets_is_zero(self) -> None:
        assert overlap_coefficient(frozenset({"a"}), frozenset({"b"})) == 0.0


class TestJaccard:
    def test_matches_definition(self) -> None:
        a = frozenset({"turbo", "button", "base", "station"})
        b = frozenset({"turbo", "button"})
        assert jaccard(a, b) == pytest.approx(2 / 4)

    def test_both_empty_is_zero(self) -> None:
        assert jaccard(frozenset(), frozenset()) == 0.0

    def test_disjoint_sets_is_zero(self) -> None:
        assert jaccard(frozenset({"a"}), frozenset({"b"})) == 0.0

    def test_underestimates_relative_to_overlap_for_asymmetric_sets(self) -> None:
        # Structural claim from the module docstring: for a short set nearly contained in
        # a long one, Jaccard is always <= overlap coefficient.
        long_set = frozenset({"base", "station", "scroll", "wheels", "turbo", "button", "device"})
        short_set = frozenset({"turbo", "button"})
        assert jaccard(long_set, short_set) < overlap_coefficient(long_set, short_set)


class TestGenerateCandidatesUnit:
    def test_cross_meeting_only(self) -> None:
        same_words = "turbo button base station"
        d1 = _decision("d1", "ES2015a", same_words)
        d2 = _decision("d2", "ES2015a", same_words)  # same meeting as d1

        assert generate_candidates([d1, d2], threshold=0.30) == []

    def test_no_pairs_across_series(self) -> None:
        d1 = _decision("d1", "ES2015a", "turbo button base station", series_id="ES2015")
        d2 = _decision("d2", "IS1004a", "turbo button base station", series_id="IS1004")

        assert generate_candidates([d1, d2], threshold=0.30) == []

    def test_below_threshold_excluded(self) -> None:
        d1 = _decision("d1", "ES2015a", "base station scroll wheels device casing")
        d2 = _decision("d2", "ES2015b", "completely unrelated marketing budget topic")

        assert generate_candidates([d1, d2], threshold=0.30) == []

    def test_chronological_ordering_always_earlier_first(self) -> None:
        earlier = _decision("d1", "ES2015a", "turbo button base station")
        later = _decision("d2", "ES2015c", "turbo button")

        [pair] = generate_candidates([earlier, later], threshold=0.30)

        assert pair.earlier_decision_id == "d1"
        assert pair.later_decision_id == "d2"
        assert pair.earlier_meeting_id == "ES2015a"
        assert pair.later_meeting_id == "ES2015c"

    def test_pair_carries_blocker_version(self) -> None:
        earlier = _decision("d1", "ES2015a", "turbo button base station")
        later = _decision("d2", "ES2015c", "turbo button")

        [pair] = generate_candidates([earlier, later], threshold=0.30)

        assert pair.blocker_version == BLOCKER_VERSION
        assert isinstance(pair, CandidatePair)


class TestRejectedPairsPartitionExactly:
    def test_candidates_and_rejected_partition_the_pair_space(self) -> None:
        decisions = [
            _decision("d1", "ES2015a", "turbo button base station"),
            _decision("d2", "ES2015b", "turbo button"),
            _decision("d3", "ES2015c", "completely unrelated budget marketing topic"),
            _decision("d4", "ES2015d", "another unrelated logo design discussion"),
        ]

        candidates = generate_candidates(decisions, threshold=0.30)
        rejected = rejected_pairs(decisions, threshold=0.30)

        candidate_ids = {(p.earlier_decision_id, p.later_decision_id) for p in candidates}
        rejected_ids = {(p.earlier_decision_id, p.later_decision_id) for p in rejected}

        # Disjoint.
        assert candidate_ids & rejected_ids == set()

        # C(4, 2) = 6 cross-meeting pairs total (all four meetings are distinct).
        assert len(candidate_ids) + len(rejected_ids) == 6


class TestMinOverlapTokensParameter:
    """Unit coverage for the second, absolute constraint added in 1.1 (see module
    docstring: threshold alone lets short sentences inflate the coefficient)."""

    def test_partition_holds_with_min_overlap_tokens(self) -> None:
        decisions = [
            _decision("d1", "ES2015a", "turbo button base station"),
            _decision("d2", "ES2015b", "turbo button"),
            _decision("d3", "ES2015c", "completely unrelated budget marketing topic"),
            _decision("d4", "ES2015d", "another unrelated logo design discussion"),
        ]

        candidates = generate_candidates(decisions, threshold=0.30, min_overlap_tokens=2)
        rejected = rejected_pairs(decisions, threshold=0.30, min_overlap_tokens=2)

        candidate_ids = {(p.earlier_decision_id, p.later_decision_id) for p in candidates}
        rejected_ids = {(p.earlier_decision_id, p.later_decision_id) for p in rejected}

        assert candidate_ids & rejected_ids == set()
        # C(4, 2) = 6 cross-meeting pairs total (all four meetings are distinct).
        assert len(candidate_ids) + len(rejected_ids) == 6

    def test_min_overlap_tokens_zero_reproduces_pre_1_1_behaviour(self) -> None:
        decisions = [
            _decision("d1", "ES2015a", "turbo button base station"),
            _decision("d2", "ES2015b", "turbo button"),
            _decision("d3", "ES2015c", "completely unrelated budget marketing topic"),
            _decision("d4", "ES2015d", "another unrelated logo design discussion"),
        ]

        old_behaviour = generate_candidates(decisions, threshold=0.30, min_overlap_tokens=0)
        pre_1_1 = generate_candidates(decisions, threshold=0.30, min_overlap_tokens=1)

        assert old_behaviour == pre_1_1

    def test_min_overlap_tokens_one_reproduces_pre_1_1_behaviour(self) -> None:
        # A pair whose coefficient clears 0.30 on a single shared token: at min_overlap=1
        # (equivalent to the old, unconstrained rule) it is a candidate.
        d1 = _decision("d1", "ES2015a", "turbo")
        d2 = _decision("d2", "ES2015b", "turbo")

        [pair] = generate_candidates([d1, d2], threshold=0.30, min_overlap_tokens=1)
        assert pair.earlier_decision_id == "d1"
        assert pair.later_decision_id == "d2"

    def test_high_coefficient_single_shared_token_rejected_at_default(self) -> None:
        # overlap_coefficient({"turbo"}, {"turbo"}) == 1.0, well above threshold, but the
        # intersection has only 1 token -- below the new default min_overlap_tokens=2.
        d1 = _decision("d1", "ES2015a", "turbo")
        d2 = _decision("d2", "ES2015b", "turbo")

        assert generate_candidates([d1, d2], threshold=0.30) == []
        [rejected] = rejected_pairs([d1, d2], threshold=0.30)
        assert rejected.blocker_score == pytest.approx(1.0)


class TestSampleRejectedDeterminism:
    _NAMES_SOURCE = (
        "zeus thor odin loki freya hera apollo athena artemis hermes poseidon demeter "
        "hades persephone dionysus hestia ares nike pan iris"
    )
    _NAMES = _NAMES_SOURCE.split()

    def _many_rejected_decisions(self) -> list[Decision]:
        # Each decision has one unique token (a name) plus one shared token ("keyword"),
        # so every cross-meeting pair overlaps at only 0.5 and is rejected at the
        # (deliberately very high) threshold below -- giving a large, genuinely-rejected
        # population to sample from.
        return [
            _decision(f"d{i}", f"ES2015{letter}", f"{self._NAMES[i]} keyword")
            for i, letter in enumerate("abcd" * 5)
        ]

    def test_same_seed_gives_same_sample(self) -> None:
        decisions = self._many_rejected_decisions()

        sample_1 = sample_rejected(decisions, n=5, seed=42, threshold=0.99)
        sample_2 = sample_rejected(decisions, n=5, seed=42, threshold=0.99)

        assert sample_1 == sample_2

    def test_different_seed_can_give_different_sample(self) -> None:
        decisions = self._many_rejected_decisions()

        sample_a = sample_rejected(decisions, n=5, seed=1, threshold=0.99)
        sample_b = sample_rejected(decisions, n=5, seed=2, threshold=0.99)

        assert sample_a != sample_b

    def test_n_larger_than_population_returns_everything(self) -> None:
        decisions = self._many_rejected_decisions()
        rejected = rejected_pairs(decisions, threshold=0.99)

        sample = sample_rejected(decisions, n=len(rejected) + 100, seed=42, threshold=0.99)

        assert len(sample) == len(rejected)


# --- corpus-backed tests ------------------------------------------------------------------


@requires_corpus
class TestTurboButtonRegression:
    """The reason this module exists: overlap catches the pilot's ground-truth reversal
    pair; Jaccard loses it. See the module docstring for the full argument."""

    def test_turbo_button_pair_survives_overlap_but_not_jaccard(self) -> None:
        decisions = decisions_from_abstractive(AMI_DIR, "IS1004")
        by_id = {d.id: d for d in decisions}

        earlier = by_id["IS1004c.elana.s.29"]
        later = by_id["IS1004d.elana.s.22"]

        a = tokenize(earlier.content)
        b = tokenize(later.content)

        assert len(a) == 14
        assert len(b) == 5
        assert a & b == {"button", "turbo"}
        assert jaccard(a, b) == pytest.approx(0.118, abs=0.001)
        assert overlap_coefficient(a, b) == pytest.approx(0.400, abs=0.001)

        # The real assertion: at the overlap threshold of 0.30, the pair IS a candidate...
        candidates = generate_candidates(decisions, threshold=0.30)
        candidate_ids = {(c.earlier_decision_id, c.later_decision_id) for c in candidates}
        assert ("IS1004c.elana.s.29", "IS1004d.elana.s.22") in candidate_ids

        # ...but a Jaccard-based rule at a comparable 0.18 threshold would have lost it.
        assert jaccard(a, b) < 0.18

    def test_turbo_button_pair_survives_at_default_but_is_lost_past_either_bound(
        self,
    ) -> None:
        """Boundary test pinning BOTH sides of the operating point (module docstring
        table). This is the test that stops someone tightening the blocker into
        uselessness: the turbo-button pair (score 0.400, |A & B| = 2) is the one verified
        reversal this module must never silently stop catching.
        """
        decisions = decisions_from_abstractive(AMI_DIR, "IS1004")
        turbo_pair = ("IS1004c.elana.s.29", "IS1004d.elana.s.22")

        def _candidate_ids(*, threshold: float, min_overlap_tokens: int) -> set[tuple[str, str]]:
            candidates = generate_candidates(
                decisions, threshold=threshold, min_overlap_tokens=min_overlap_tokens
            )
            return {(c.earlier_decision_id, c.later_decision_id) for c in candidates}

        # Survives at the new default operating point (threshold=0.30, min_overlap_tokens=2).
        assert turbo_pair in _candidate_ids(threshold=0.30, min_overlap_tokens=2)

        # Lost if min_overlap_tokens is tightened past 2 (|A & B| == 2 exactly).
        assert turbo_pair not in _candidate_ids(threshold=0.30, min_overlap_tokens=3)

        # Lost if threshold is tightened past 0.40 (score == 0.400 exactly).
        assert turbo_pair not in _candidate_ids(threshold=0.50, min_overlap_tokens=2)


@requires_corpus
class TestCorpusBackedCandidateCounts:
    """Ground truth measured against data/raw/ami/. Do not derive these numbers from the
    code under test -- they are the independent check (manual section 5: the recall figure
    this module exists to make reportable)."""

    def test_es2015_candidate_count_min_overlap_tokens_1(self) -> None:
        # Pre-1.1 behaviour (min_overlap_tokens=1, i.e. no absolute constraint), retained
        # as documentation of the operating point this thesis moved away from and why.
        decisions = decisions_from_abstractive(AMI_DIR, "ES2015")
        total_pairs = len(
            rejected_pairs(decisions, threshold=0.30, min_overlap_tokens=1)
        ) + len(generate_candidates(decisions, threshold=0.30, min_overlap_tokens=1))
        candidates = generate_candidates(decisions, threshold=0.30, min_overlap_tokens=1)

        assert total_pairs == 311
        assert len(candidates) == 18

    def test_es2015_candidate_count_at_new_default(self) -> None:
        decisions = decisions_from_abstractive(AMI_DIR, "ES2015")
        candidates = generate_candidates(decisions, threshold=0.30)  # default min_overlap=2

        assert len(candidates) == 3

    def test_is1004_candidate_count_min_overlap_tokens_1(self) -> None:
        # Pre-1.1 behaviour (min_overlap_tokens=1), retained as documentation.
        decisions = decisions_from_abstractive(AMI_DIR, "IS1004")
        total_pairs = len(
            rejected_pairs(decisions, threshold=0.30, min_overlap_tokens=1)
        ) + len(generate_candidates(decisions, threshold=0.30, min_overlap_tokens=1))
        candidates = generate_candidates(decisions, threshold=0.30, min_overlap_tokens=1)

        assert total_pairs == 188
        assert len(candidates) == 10

    def test_is1004_candidate_count_at_new_default(self) -> None:
        decisions = decisions_from_abstractive(AMI_DIR, "IS1004")
        candidates = generate_candidates(decisions, threshold=0.30)  # default min_overlap=2

        assert len(candidates) == 4

    def test_total_candidates_across_oe1_series_at_new_default(self) -> None:
        """The headline number this whole change exists to hit: 92 candidates across the
        14 selected OE1 series at the new default operating point (threshold=0.30,
        min_overlap_tokens=2) -- down from 712 (23.2%) at the pre-1.1 operating point."""
        corpus_config = load_corpus_config()
        series_ids = corpus_config["oe1"]["series"]

        total = 0
        for series_id in series_ids:
            decisions = decisions_from_abstractive(AMI_DIR, series_id)
            total += len(generate_candidates(decisions, threshold=0.30))

        assert total == 92
