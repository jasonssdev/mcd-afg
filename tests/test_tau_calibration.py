"""Tests for the inputs that fix tau: null control, judged pair sample and the two rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.judge import JudgeConfigurationError
from afg.evaluation.reference import ReferenceDecision
from afg.experiments.model_screen import PassRun, curve_summary, score_curve
from afg.experiments.tau_calibration import (
    Judgment,
    JudgmentStore,
    MatchedPair,
    bin_table,
    coverage_by_tau,
    digest_of,
    examples_by_region,
    judge_sample,
    load_stored_judgments,
    matched_pairs,
    null_coverage,
    null_curve_points,
    prompt_sha256,
    propose_tau,
    reference_shift_table,
    same_decision_prompt,
    stratified_sample,
    tau_judge,
    tau_null,
)


def _partition(series: str) -> str:
    return "development" if series in {"ES2015", "TS3009"} else "evaluation"


def _decision(i: int, meeting: str, text: str) -> Decision:
    obj, content = text.split(": ", 1)
    return Decision(
        id=f"m/{meeting}/{i}",
        series_id=meeting[:-1],
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        status=DecisionStatus.ACCEPTED,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"{meeting}#pass-{i}",)),
    )


def _run(model: str, series: str, run: int, texts: list[tuple[str, str]]) -> PassRun:
    decisions = tuple(_decision(i, m, t) for i, (m, t) in enumerate(texts))
    return PassRun(
        model=model,
        series=series,
        run=run,
        decisions=decisions,
        meetings=tuple(sorted({m for m, _ in texts})),
        failures=(),
        wall_s=1.0,
    )


def _ref(i: int, meeting: str, text: str) -> ReferenceDecision:
    obj, content = text.split(": ", 1)
    return ReferenceDecision(
        decision_id=f"{meeting}.d{i}",
        series_id=meeting[:-1],
        meeting_id=meeting,
        decision_object=obj,
        content=content,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"da.{i}",)),
        evidence_method="sentence_id",
        role="PM",
        roles=("PM",),
    )


def _table_similarity(table: dict[tuple[str, str], float], default: float = 0.1):
    def similarity(predicted, reference):
        return np.array([[table.get((p, r), default) for r in reference] for p in predicted])

    return similarity


# --- null control -------------------------------------------------------------------------


def test_null_curve_points_score_each_run_against_the_other_series_reference() -> None:
    runs = [
        _run("m", "ES2015", 0, [("ES2015a", "price: 25 euros")]),
        _run("m", "TS3009", 0, [("TS3009a", "case: rubber")]),
    ]
    references = {
        "ES2015": [_ref(1, "ES2015a", "price: 25 euros")],
        "TS3009": [_ref(1, "TS3009a", "case: rubber")],
    }
    similarity = _table_similarity(
        {
            ("price: 25 euros", "case: rubber"): 0.7,  # ES2015 output vs TS3009 reference
            ("case: rubber", "price: 25 euros"): 0.4,  # TS3009 output vs ES2015 reference
        }
    )

    points = null_curve_points(
        runs, references, similarity, taus=[0.5, 0.6], partition_of=_partition
    )

    got = {(p.series, p.tau): p.recall for p in points}
    # The point is attributed to the series whose reference was used.
    assert got == {
        ("TS3009", 0.5): 1.0,
        ("TS3009", 0.6): 1.0,
        ("ES2015", 0.5): 0.0,
        ("ES2015", 0.6): 0.0,
    }


def test_null_curve_points_refuse_a_series_without_a_counterpart() -> None:
    run = _run("m", "ES2015", 0, [("ES2015a", "a: b")])
    with pytest.raises(ValueError, match="ES2016"):
        null_curve_points(
            [_run("m", "ES2016", 0, [("ES2016a", "a: b")])],
            {"ES2016": []},
            _table_similarity({}),
            taus=[0.5],
            partition_of=_partition,
        )
    assert run.series == "ES2015"


def _points(recalls: dict[float, list[float]]):
    from afg.experiments.model_screen import CurvePoint

    return [
        CurvePoint("m", "ES2015", i, tau, 0, 1, 1, 0.0, r, 0.0)
        for tau, values in recalls.items()
        for i, r in enumerate(values)
    ]


def test_null_coverage_reports_mean_and_worst_cell_per_tau() -> None:
    from afg.experiments.model_screen import CurvePoint

    points = [
        CurvePoint("a", "ES2015", 0, 0.5, 0, 1, 1, 0.0, 0.4, 0.0),
        CurvePoint("a", "ES2015", 1, 0.5, 0, 1, 1, 0.0, 0.2, 0.0),
        CurvePoint("b", "TS3009", 0, 0.5, 0, 1, 1, 0.0, 0.0, 0.0),
    ]
    frame = null_coverage(points)
    row = frame.iloc[0]
    assert row.tau == 0.5
    assert row.runs == 3
    assert row.recall_mean == pytest.approx(0.2)  # mean over every run
    assert row.recall_worst_cell == pytest.approx(0.3)  # (model, series) mean, the largest


def test_coverage_by_tau_is_the_same_summary_for_real_points() -> None:
    frame = coverage_by_tau(_points({0.5: [0.8, 0.6], 0.6: [0.3]}))
    assert frame.recall_mean.tolist() == pytest.approx([0.7, 0.3])
    assert frame.runs.tolist() == [2, 1]


def test_tau_null_is_the_smallest_grid_value_at_or_under_the_ceiling() -> None:
    frame = null_coverage(_points({0.5: [0.8], 0.6: [0.3], 0.7: [0.05], 0.8: [0.0]}))
    assert tau_null(frame) == 0.7  # 0.05 counts: the rule is "<= 0.05"


def test_tau_null_is_none_when_the_ceiling_is_never_reached() -> None:
    assert tau_null(null_coverage(_points({0.5: [0.8], 0.6: [0.3]}))) is None


# --- matched pairs and the stratified sample ----------------------------------------------


def test_matched_pairs_are_the_scorers_hungarian_matches_above_the_floor() -> None:
    runs = [
        _run(
            "m", "ES2015", 0, [("ES2015a", "x: one"), ("ES2015a", "y: two"), ("ES2015b", "z: far")]
        )
    ]
    references = {
        "ES2015": [_ref(1, "ES2015a", "p: one"), _ref(2, "ES2015a", "q: two")],
    }
    similarity = _table_similarity(
        {
            ("x: one", "p: one"): 0.80,
            ("x: one", "q: two"): 0.78,  # greedy would take 0.80 and 0.78 for x twice
            ("y: two", "p: one"): 0.79,
            ("y: two", "q: two"): 0.60,
            ("z: far", "p: one"): 0.99,  # other meeting: masked by the scope
        }
    )

    pairs = matched_pairs(runs, references, similarity, tau=0.5)

    got = {(p.extracted_text, p.reference_text): p.similarity for p in pairs}
    # Optimal total: x-q (0.78) + y-p (0.79) = 1.57 > x-p (0.80) + y-q (0.60) = 1.40.
    assert got == {("x: one", "q: two"): 0.78, ("y: two", "p: one"): 0.79}
    assert {p.reference_id for p in pairs} == {"ES2015a.d1", "ES2015a.d2"}
    assert all(p.model == "m" and p.series == "ES2015" and p.run == 0 for p in pairs)
    assert all(p.meeting_id == "ES2015a" for p in pairs)


def _pair(i: int, sim: float, model: str = "qwen3:8b") -> MatchedPair:
    return MatchedPair(
        model=model,
        series="ES2015",
        run=0,
        meeting_id="ES2015a",
        reference_id=f"ES2015a.d{i}",
        extracted_text=f"obj{i}: extracted {i}",
        reference_text=f"obj{i}: reference {i}",
        similarity=sim,
    )


def test_stratified_sample_takes_up_to_n_per_bin_in_the_half_open_range() -> None:
    pool = (
        [_pair(i, 0.50 + 0.001 * i) for i in range(40)]  # bin 0.50: 40 available
        + [_pair(100 + i, 0.62) for i in range(3)]  # bin 0.60: 3 available
        + [_pair(200, 0.90), _pair(201, 0.95), _pair(202, 0.49)]  # outside [0.50, 0.90)
    )

    sample = stratified_sample(pool, seed=7, per_bin=25)

    counts = pd.Series([p.bin_low for p in sample.pairs]).value_counts().to_dict()
    assert counts == {0.5: 25, 0.6: 3}
    assert sample.available == {0.5: 40, 0.6: 3}
    assert all(0.50 <= p.similarity < 0.90 for p in sample.pairs)
    assert sample.seed == 7


def test_stratified_sample_is_deterministic_for_a_seed_and_changes_with_it() -> None:
    pool = [_pair(i, 0.55) for i in range(60)]
    first = stratified_sample(pool, seed=1, per_bin=10)
    again = stratified_sample(list(reversed(pool)), seed=1, per_bin=10)
    other = stratified_sample(pool, seed=2, per_bin=10)
    assert [p.id for p in first.pairs] == [p.id for p in again.pairs]
    assert [p.id for p in first.pairs] != [p.id for p in other.pairs]


def test_stratified_sample_never_repeats_identical_text_pairs() -> None:
    a = _pair(1, 0.62, model="qwen3:8b")
    b = _pair(1, 0.62, model="qwen3.6:27b")  # same texts, another model
    c = _pair(2, 0.62)
    sample = stratified_sample([a, b, c], seed=1, per_bin=25)
    assert len(sample.pairs) == 2
    assert sample.available == {0.6: 2}
    merged = next(p for p in sample.pairs if p.reference_id == "ES2015a.d1")
    assert merged.models == ("qwen3.6:27b", "qwen3:8b")
    assert merged.occurrences == 2


def test_stratified_sample_survives_floating_point_edges_of_a_bin() -> None:
    sample = stratified_sample([_pair(1, 0.6), _pair(2, 0.65), _pair(3, 0.8999999)], seed=1)
    assert sorted(p.bin_low for p in sample.pairs) == [0.6, 0.65, 0.85]


# --- judge --------------------------------------------------------------------------------


class _FakeBackend:
    def __init__(self, answers: dict[str, str] | None = None, default: str | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._answers = answers or {}
        self._default = default

    def complete(self, system, user, *, model, seed, temperature, format_schema):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "model": model,
                "seed": seed,
                "temperature": temperature,
                "schema": format_schema,
            }
        )
        for needle, answer in self._answers.items():
            if needle in user:
                return answer
        assert self._default is not None
        return self._default


def _yes(rationale: str = "same") -> str:
    return json.dumps({"same_decision": True, "rationale": rationale})


def _no(rationale: str = "different") -> str:
    return json.dumps({"same_decision": False, "rationale": rationale})


def test_prompt_is_versioned_and_hashed() -> None:
    text = same_decision_prompt()
    assert "same decision" in text.lower()
    assert len(prompt_sha256()) == 64
    assert prompt_sha256() == prompt_sha256()


def test_judge_sample_records_verdicts_raw_output_and_both_orders(tmp_path: Path) -> None:
    sample = stratified_sample([_pair(i, 0.55) for i in range(6)], seed=3, per_bin=25)
    backend = _FakeBackend(default=_yes())

    judgments = judge_sample(
        sample.pairs,
        backend=backend,
        judge_model="gpt-oss:20b",
        model_digest="abc123",
        seed=42,
        temperature=0.0,
        think="low",
        store=JudgmentStore(tmp_path),
    )

    assert len(judgments) == 6 and all(j.same is True for j in judgments)
    assert all(j.raw_output == _yes() for j in judgments)
    assert {c["model"] for c in backend.calls} == {"gpt-oss:20b"}
    assert {c["seed"] for c in backend.calls} == {42}
    # The pair order shown to the judge is randomized, so both orders appear.
    firsts = {c["user"].index("extracted ") < c["user"].index("reference ") for c in backend.calls}
    assert firsts == {True, False}
    meta = json.loads((tmp_path / "run.json").read_text("utf-8"))
    assert meta["judge_model"] == "gpt-oss:20b"
    assert meta["model_digest"] == "abc123"
    assert meta["prompt_sha256"] == prompt_sha256()
    assert meta["sample_seed"] == 3
    assert meta["n_pairs"] == 6


def test_judge_sample_reuses_stored_judgments_and_recalls_when_inputs_change(
    tmp_path: Path,
) -> None:
    pairs = stratified_sample([_pair(i, 0.55) for i in range(3)], seed=3).pairs
    kwargs: dict[str, Any] = dict(
        judge_model="gpt-oss:20b",
        seed=42,
        temperature=0.0,
        think="low",
        store=JudgmentStore(tmp_path),
    )
    first = _FakeBackend(default=_yes())
    judge_sample(pairs, backend=first, model_digest="d1", **kwargs)
    assert len(first.calls) == 3

    second = _FakeBackend(default=_no())
    again = judge_sample(pairs, backend=second, model_digest="d1", **kwargs)
    assert second.calls == [] and all(j.same is True for j in again)

    third = _FakeBackend(default=_no())
    changed = judge_sample(pairs, backend=third, model_digest="d2", **kwargs)  # new digest
    assert len(third.calls) == 3 and all(j.same is False for j in changed)


def test_judge_sample_keeps_a_malformed_output_as_a_failure(tmp_path: Path) -> None:
    pairs = stratified_sample([_pair(1, 0.55), _pair(2, 0.57)], seed=3).pairs
    backend = _FakeBackend(answers={"extracted 1": "not json"}, default=_yes())
    judgments = judge_sample(
        pairs,
        backend=backend,
        judge_model="gpt-oss:20b",
        model_digest="d",
        seed=42,
        temperature=0.0,
        think="low",
        store=JudgmentStore(tmp_path),
    )
    bad = next(j for j in judgments if "extracted 1" in j.pair.extracted_text)
    assert bad.same is None and bad.failure == "invalid_json" and bad.raw_output == "not json"


def test_judge_sample_refuses_a_judge_that_is_also_the_extractor(tmp_path: Path) -> None:
    pairs = stratified_sample([_pair(1, 0.55, model="gpt-oss:20b")], seed=3).pairs
    with pytest.raises(JudgeConfigurationError):
        judge_sample(
            pairs,
            backend=_FakeBackend(default=_yes()),
            judge_model="gpt-oss:20b",
            model_digest="d",
            seed=42,
            temperature=0.0,
            think="low",
            store=JudgmentStore(tmp_path),
        )


def test_digest_of_finds_the_model_tag() -> None:
    installed = {"gpt-oss:20b": "sha256:f38aa0c53da5aa", "qwen3:8b": "sha256:500a1f067a9f"}
    assert digest_of("gpt-oss:20b", installed) == "sha256:f38aa0c53da5aa"
    with pytest.raises(ValueError, match="gpt-oss:120b"):
        digest_of("gpt-oss:120b", installed)


# --- bins, tau_juez and the proposal --------------------------------------------------------


def _judged(bin_low: float, yes: int, no: int, fail: int = 0) -> list[Judgment]:
    out = []
    for k in range(yes + no + fail):
        pair = _pair(int(bin_low * 1000) * 100 + k, bin_low + 0.01)
        same = True if k < yes else (False if k < yes + no else None)
        out.append(
            Judgment(
                pair=stratified_sample([pair], seed=1).pairs[0],
                same=same,
                rationale="",
                raw_output="",
                failure=None if same is not None else "invalid_json",
                order="extracted_first",
                seconds=1.0,
            )
        )
    return out


def test_bin_table_counts_yes_rates_wilson_interval_and_failures() -> None:
    judgments = _judged(0.5, 1, 9) + _judged(0.6, 5, 5, fail=2)
    table = bin_table(judgments).set_index("bin_low")
    assert table.loc[0.5, ["n", "yes", "failures"]].tolist() == [10, 1, 0]
    assert table.loc[0.6, ["n", "yes", "failures"]].tolist() == [10, 5, 2]
    assert table.loc[0.5, "rate"] == pytest.approx(0.1)
    # Wilson 95% for 1/10 is about (0.018, 0.404).
    assert table.loc[0.5, "ci_low"] == pytest.approx(0.0179, abs=1e-3)
    assert table.loc[0.5, "ci_high"] == pytest.approx(0.4041, abs=1e-3)
    assert table.loc[0.5, "bin_high"] == pytest.approx(0.55)


def _rates(rates: dict[float, tuple[int, int]]) -> pd.DataFrame:
    return bin_table([j for low, (y, n) in rates.items() for j in _judged(low, y, n - y)])


def test_tau_judge_is_the_lowest_bin_from_which_every_bin_has_majority_yes() -> None:
    table = _rates(
        {0.5: (1, 10), 0.55: (4, 10), 0.6: (6, 10), 0.65: (5, 10), 0.7: (8, 10), 0.75: (9, 10)}
    )
    # 0.60 has 6/10 > 0.5 but 0.65 has exactly 0.5 (not > 0.5): the run starts at 0.70.
    assert tau_judge(table) == pytest.approx(0.70)


def test_tau_judge_starts_at_the_lowest_bin_when_all_bins_pass() -> None:
    assert tau_judge(_rates({0.5: (9, 10), 0.55: (8, 10)})) == pytest.approx(0.5)


def test_tau_judge_is_none_when_the_top_bin_is_not_a_majority() -> None:
    assert tau_judge(_rates({0.5: (9, 10), 0.85: (4, 10)})) is None


def test_tau_judge_skips_empty_bins_instead_of_failing_them() -> None:
    table = _rates({0.5: (1, 10), 0.6: (8, 10), 0.8: (9, 10)})  # 0.65, 0.7, 0.75 empty
    assert tau_judge(table) == pytest.approx(0.6)


def test_propose_tau_is_the_larger_of_the_two_and_none_if_either_is_missing() -> None:
    assert propose_tau(0.7, 0.65) == 0.7
    assert propose_tau(0.6, 0.65) == 0.65
    assert propose_tau(None, 0.65) is None
    assert propose_tau(0.6, None) is None


def test_examples_by_region_picks_the_pair_nearest_each_region_centre() -> None:
    judgments = _judged(0.5, 1, 1) + _judged(0.6, 1, 0) + _judged(0.7, 0, 1) + _judged(0.85, 1, 0)
    chosen = examples_by_region(judgments, regions=((0.50, 0.65), (0.65, 0.80), (0.80, 0.90)))
    assert [(lo, hi) for lo, hi, _ in chosen] == [(0.50, 0.65), (0.65, 0.80), (0.80, 0.90)]
    for lo, hi, j in chosen:
        assert lo <= j.pair.similarity < hi


# --- Spanish versus English reference --------------------------------------------------------


def test_reference_shift_table_puts_both_languages_side_by_side() -> None:
    runs = [_run("m", "ES2015", 0, [("ES2015a", "x: one")])]
    es = curve_summary(
        score_curve(
            runs,
            {"ES2015": [_ref(1, "ES2015a", "p: uno")]},
            _table_similarity({("x: one", "p: uno"): 0.65}),
            taus=[0.6, 0.7],
        )
    )
    en = curve_summary(
        score_curve(
            runs,
            {"ES2015": [_ref(1, "ES2015a", "p: one")]},
            _table_similarity({("x: one", "p: one"): 0.85}),
            taus=[0.6, 0.7],
        )
    )
    table = reference_shift_table(es, en, taus=[0.6, 0.7], metric="recall")
    row = table.set_index(["model", "series", "tau"])
    assert row.loc[("m", "ES2015", 0.6), ["es", "en", "shift"]].tolist() == [1.0, 1.0, 0.0]
    assert row.loc[("m", "ES2015", 0.7), ["es", "en", "shift"]].tolist() == [0.0, 1.0, 1.0]


def test_stored_judgments_are_read_back_as_the_judgments_that_were_written(tmp_path: Path) -> None:
    sample = stratified_sample([_pair(i, 0.55) for i in range(4)], seed=3, per_bin=25)
    store = JudgmentStore(tmp_path)
    written = judge_sample(
        sample.pairs,
        backend=_FakeBackend(default=_yes()),
        judge_model="gpt-oss:20b",
        model_digest="abc123",
        seed=42,
        temperature=0.0,
        think="low",
        store=store,
    )

    read = load_stored_judgments(store)

    assert sorted(read, key=lambda j: j.pair.id) == sorted(written, key=lambda j: j.pair.id)
    # the stored judgments feed the same bin table without calling the judge again
    assert bin_table(read).loc[0, ["n", "yes"]].tolist() == [4, 4]


def test_stored_judgments_of_an_empty_store_are_an_empty_list(tmp_path: Path) -> None:
    assert load_stored_judgments(JudgmentStore(tmp_path)) == []
