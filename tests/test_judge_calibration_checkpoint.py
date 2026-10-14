"""Tests for per-candidate checkpoints of the judge calibration (issue #82)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from afg.domain.question import QuestionStratum
from afg.evaluation.judge_calibration import CandidateMetrics, FieldAgreement
from afg.evaluation.judge_calibration_checkpoint import CandidateCheckpoints, calibration_key
from afg.evaluation.judge_calibration_runner import CandidateRun
from afg.evaluation.judge_calibration_set import CalibrationItem
from afg.evaluation.metrics import BootstrapCI
from tests.test_judge_calibration_runner import THRESHOLDS, _items


def _run(model: str = "judge:1") -> CandidateRun:
    return CandidateRun(
        metrics=CandidateMetrics(
            model=model,
            kappa_correct=BootstrapCI(0.8, 0.7, 0.9, 0.95, 1000),
            position_consistency=0.95,
            seed_consistency=0.99,
            e4_accuracy=0.9,
            json_valid_rate=1.0,
            verbosity_flip_rate=0.05,
            latency_seconds=1.5,
        ),
        evidence_supported=FieldAgreement(kappa=0.6, accuracy=0.8, n=10),
        calls=65,
        failures=1,
    )


def _key(items: list[CalibrationItem] | None = None, **overrides: object) -> str:
    args: dict[str, object] = {
        "items": items if items is not None else _items(),
        "excerpts": {item.id: "" for item in _items()},
        "thresholds": THRESHOLDS,
        "model": "judge:1",
        "generative_model": "qwen3:8b",
        "think": None,
    }
    args.update(overrides)
    return calibration_key(**args)  # type: ignore[arg-type]


class TestKey:
    def test_same_inputs_same_key(self) -> None:
        assert _key() == _key()

    def test_a_changed_human_label_changes_the_key(self) -> None:
        items = _items()
        items[0] = items[0].model_copy(update={"correct": not items[0].correct})
        assert _key(items) != _key()

    def test_a_changed_answer_changes_the_key(self) -> None:
        items = _items()
        items[1] = items[1].model_copy(update={"answer_text": "different"})
        assert _key(items) != _key()

    def test_item_order_does_not_matter(self) -> None:
        assert _key(list(reversed(_items()))) == _key()

    def test_a_changed_excerpt_changes_the_key(self) -> None:
        excerpts = {item.id: "" for item in _items()}
        excerpts["i0"] = "another passage"
        assert _key(excerpts=excerpts) != _key()

    def test_thresholds_model_think_and_generator_change_the_key(self) -> None:
        other = replace(THRESHOLDS, min_kappa_correct=0.5)
        assert _key(thresholds=other) != _key()
        assert _key(model="judge:2") != _key()
        assert _key(think="low") != _key()
        assert _key(generative_model="other") != _key()

    def test_a_different_stratum_changes_the_key(self) -> None:
        items = _items()
        items[0] = items[0].model_copy(update={"stratum": QuestionStratum.E2_CURRENT_STATE})
        assert _key(items) != _key()


class TestStore:
    def test_roundtrip_of_a_finished_candidate(self, tmp_path: Path) -> None:
        store = CandidateCheckpoints(tmp_path / "cand", key_for=lambda model: "k1")
        store.save("judge:1", _run())
        assert store.load("judge:1") == _run()
        assert any((tmp_path / "cand").iterdir())

    def test_roundtrip_without_evidence_agreement(self, tmp_path: Path) -> None:
        store = CandidateCheckpoints(tmp_path, key_for=lambda model: "k1")
        run = CandidateRun(metrics=_run().metrics, evidence_supported=None, calls=3, failures=0)
        store.save("judge:1", run)
        assert store.load("judge:1") == run

    def test_a_result_for_other_inputs_is_never_reused(self, tmp_path: Path) -> None:
        CandidateCheckpoints(tmp_path, key_for=lambda model: "old").save("judge:1", _run())
        assert CandidateCheckpoints(tmp_path, key_for=lambda model: "new").load("judge:1") is None

    def test_missing_or_corrupt_files_mean_not_done(self, tmp_path: Path) -> None:
        store = CandidateCheckpoints(tmp_path, key_for=lambda model: "k")
        assert store.load("judge:1") is None
        store.save("judge:1", _run())
        (next(tmp_path.iterdir())).write_text("not json", encoding="utf-8")
        assert store.load("judge:1") is None

    def test_models_with_slashes_and_colons_get_safe_distinct_files(self, tmp_path: Path) -> None:
        store = CandidateCheckpoints(tmp_path, key_for=lambda model: "k")
        store.save("atla/selene-mini:q8_0", _run("atla/selene-mini:q8_0"))
        store.save("gpt-oss:20b", _run("gpt-oss:20b"))
        assert {p.parent for p in tmp_path.iterdir()} == {tmp_path}
        assert store.load("atla/selene-mini:q8_0") == _run("atla/selene-mini:q8_0")
        assert store.load("gpt-oss:20b") == _run("gpt-oss:20b")
