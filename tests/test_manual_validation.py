"""Tests for alignment-protocol step 3: automatic alignment vs manual matching (issue #240)."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.evaluation.alignment import concordance
from afg.evaluation.reference import ReferenceDecision
from afg.experiments.manual_validation import (
    SHEET_COLUMNS,
    ManualValidationError,
    ManualValidationSheetLabeledError,
    candidate_pairs,
    draw_validation_sample,
    load_run_decisions,
    load_validation_config,
    score_validation,
    write_validation_files,
)

MEETINGS = ("ES2015a", "ES2015b")
PER_MEETING = 10
TAU = 0.70


def _index(text: str) -> int:
    match = re.match(r"d(\d+)", text)
    assert match, text
    return int(match.group(1))


def fake_similarity(predicted: Sequence[str], reference: Sequence[str]) -> np.ndarray:
    """0.95 when the indexes are equal, otherwise 0.60 minus 0.02 per index of distance."""
    out = np.zeros((len(predicted), len(reference)))
    for i, p in enumerate(predicted):
        for j, r in enumerate(reference):
            gap = abs(_index(p) - _index(r))
            out[i, j] = 0.95 if gap == 0 else max(0.0, 0.60 - 0.02 * gap)
    return out


def _predicted(
    meeting: str, i: int, *, status: DecisionStatus = DecisionStatus.ACCEPTED
) -> Decision:
    return Decision(
        id=f"decisions/{meeting}-{i}",
        series_id="ES2015",
        meeting_id=meeting,
        decision_object=f"d{i}",
        content=f"predicted {meeting} {i}",
        status=status,
        evidence=EvidenceSpan(meeting_id=meeting, dialogue_act_ids=(f"{meeting}.a{i}",)),
    )


def _reference(meeting: str, i: int) -> ReferenceDecision:
    return ReferenceDecision(
        decision_id=f"{meeting}.r{i:02d}",
        series_id="ES2015",
        meeting_id=meeting,
        decision_object=f"d{i}",
        content=f"reference {meeting} {i}",
        evidence=None,
        evidence_method="none",
        role=None,
    )


def _world() -> tuple[list[Decision], list[ReferenceDecision]]:
    predicted = [_predicted(m, i) for m in MEETINGS for i in range(PER_MEETING)]
    reference = [_reference(m, i) for m in MEETINGS for i in range(PER_MEETING)]
    return predicted, reference


def _pairs() -> list[Any]:
    predicted, reference = _world()
    return candidate_pairs(reference, predicted, fake_similarity, tau=TAU, floor=0.5)


def _draw(pairs: list[Any], *, size: int = 30, share: float = 0.5, seed: int = 42) -> list[Any]:
    return draw_validation_sample(pairs, sample_size=size, matched_share=share, seed=seed)


# --- config ----------


def test_config_is_pre_registered() -> None:
    cfg = load_validation_config()
    assert cfg.sample_size == 100
    assert 0.0 < cfg.matched_share < 1.0
    assert isinstance(cfg.seed, int)
    assert 0.0 < cfg.similarity_floor < 0.70


# --- candidate pairs ----------


def test_candidates_are_same_meeting_pairs_and_flag_the_automatic_matches() -> None:
    pairs = _pairs()
    assert all(p.predicted_meeting == p.meeting_id for p in pairs)
    matched = [p for p in pairs if p.auto_match]
    assert len(matched) == len(MEETINGS) * PER_MEETING
    assert all(_index(p.extracted_text) == _index(p.reference_text) for p in matched)
    assert all(p.similarity >= TAU for p in matched)
    # Non-matched candidates respect the floor and never include a match twice.
    assert all(p.similarity >= 0.5 for p in pairs)
    assert len({(p.predicted_id, p.reference_id) for p in pairs}) == len(pairs)


def test_candidates_ignore_non_decisions() -> None:
    predicted, reference = _world()
    predicted.append(_predicted("ES2015a", 3, status=DecisionStatus.OPEN_PROPOSAL))
    pairs = candidate_pairs(reference, predicted, fake_similarity, tau=TAU, floor=0.5)
    assert len(pairs) == len(_pairs())


# --- sample ----------


def test_sample_has_size_and_strata_and_unique_ids() -> None:
    sample = _draw(_pairs())
    assert len(sample) == 30
    assert len({p.pair_id for p in sample}) == 30
    assert sum(p.auto_match for p in sample) == 15


def test_sample_is_deterministic_and_independent_of_input_order() -> None:
    pairs = _pairs()
    a = [p.pair_id for p in _draw(pairs)]
    assert a == [p.pair_id for p in _draw(list(reversed(pairs)))]
    assert a != [p.pair_id for p in _draw(pairs, seed=7)]


def test_sample_order_is_shuffled_not_grouped_by_stratum() -> None:
    flags = [p.auto_match for p in _draw(_pairs())]
    assert flags != sorted(flags) and flags != sorted(flags, reverse=True)


def test_sample_fills_from_the_other_stratum_when_one_is_short() -> None:
    pairs = _pairs()
    sample = _draw(pairs, size=30, share=0.9)  # 27 asked, only 20 automatic matches exist
    assert len(sample) == 30
    assert sum(p.auto_match for p in sample) == 20


def test_sample_refuses_when_the_pool_is_too_small() -> None:
    with pytest.raises(ManualValidationError):
        _draw(_pairs(), size=10_000)


# --- sheet and key ----------


def _write(tmp_path: Path, *, force: bool = False) -> dict[str, Any]:
    sample = _draw(_pairs())
    sheet, key = tmp_path / "sheet.csv", tmp_path / "key.json"
    write_validation_files(
        sample,
        sheet_path=sheet,
        key_path=key,
        source={"run_name": "r", "series": "ES2015", "run": 0, "sha256": "abc"},
        tau=TAU,
        seed=42,
        force=force,
    )
    return {"sample": sample, "sheet": sheet, "key": key}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_sheet_is_blind_and_unlabeled(tmp_path: Path) -> None:
    out = _write(tmp_path)
    rows = _rows(out["sheet"])
    assert tuple(rows[0]) == SHEET_COLUMNS
    assert len(rows) == 30
    assert all(r["same"] == "" and r["notes"] == "" for r in rows)
    assert [r["pair_id"] for r in rows] == [p.pair_id for p in out["sample"]]
    text = out["sheet"].read_text(encoding="utf-8")
    assert "0.95" not in text and "auto" not in text.lower().replace("automat", "")


def test_key_holds_the_hidden_fields(tmp_path: Path) -> None:
    out = _write(tmp_path)
    key = json.loads(out["key"].read_text(encoding="utf-8"))
    assert key["tau"] == TAU and key["seed"] == 42 and key["sample_size"] == 30
    assert key["source"]["sha256"] == "abc"
    assert [p["pair_id"] for p in key["pairs"]] == [p.pair_id for p in out["sample"]]
    assert {"auto_match", "similarity", "predicted_index", "reference_index"} <= set(
        key["pairs"][0]
    )


def test_writer_refuses_to_erase_labels_unless_forced(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {p.pair_id: "si" for p in out["sample"]})
    with pytest.raises(ManualValidationSheetLabeledError):
        _write(tmp_path)
    _write(tmp_path, force=True)
    assert all(r["same"] == "" for r in _rows(out["sheet"]))


# --- score ----------


def _label(path: Path, human: dict[str, str]) -> None:
    rows = _rows(path)
    for r in rows:
        r["same"] = human[r["pair_id"]]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_perfect_agreement_scores_one(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {p.pair_id: "si" if p.auto_match else "no" for p in out["sample"]})
    result = score_validation(out["sheet"], out["key"])
    assert result["concordance"] == 1.0
    assert result["observed_agreement"] == 1.0
    assert result["n"] == 30 and result["n_auto"] == 15 and result["n_manual"] == 15


def test_concordance_is_the_jaccard_of_the_matched_sets(tmp_path: Path) -> None:
    out = _write(tmp_path)
    auto = [p for p in out["sample"] if p.auto_match]
    other = [p for p in out["sample"] if not p.auto_match]
    # The person rejects 3 automatic matches and accepts 2 pairs the machine left out.
    yes = {p.pair_id for p in auto[3:]} | {p.pair_id for p in other[:2]}
    _label(out["sheet"], {p.pair_id: "si" if p.pair_id in yes else "no" for p in out["sample"]})
    result = score_validation(out["sheet"], out["key"])
    expected = concordance(
        {(p.predicted_index, p.reference_index) for p in auto},
        {(p.predicted_index, p.reference_index) for p in out["sample"] if p.pair_id in yes},
    )
    assert result["concordance"] == pytest.approx(expected) == pytest.approx(12 / 17)
    assert result["confusion"] == {
        "auto_si": {"manual_si": 12, "manual_no": 3},
        "auto_no": {"manual_si": 2, "manual_no": 13},
    }
    assert result["observed_agreement"] == pytest.approx(25 / 30)
    assert result["automatic_confirmed"] == {"n": 15, "n_manual_yes": 12}
    assert result["automatic_missed"] == {"n": 15, "n_manual_yes": 2}


def test_score_rejects_empty_or_invalid_labels(tmp_path: Path) -> None:
    out = _write(tmp_path)
    with pytest.raises(ManualValidationError, match=r"si o no"):
        score_validation(out["sheet"], out["key"])
    _label(out["sheet"], {p.pair_id: "quizás" for p in out["sample"]})
    with pytest.raises(ManualValidationError):
        score_validation(out["sheet"], out["key"])


def test_score_rejects_a_sheet_that_does_not_match_the_key(tmp_path: Path) -> None:
    out = _write(tmp_path)
    rows = _rows(out["sheet"])[:-1]
    with out["sheet"].open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for r in rows:
            r["same"] = "si"
            writer.writerow(r)
    with pytest.raises(ManualValidationError):
        score_validation(out["sheet"], out["key"])


def test_score_counts_manual_matches_that_break_one_to_one(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {p.pair_id: "si" for p in out["sample"]})
    result = score_validation(out["sheet"], out["key"])
    assert result["n_manual_shared_decision"] > 0


# --- stored run ----------


def _write_run(root: Path) -> Path:
    run_dir = root / "es2015-test"
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(json.dumps({"series": "ES2015"}), encoding="utf-8")
    predicted, _ = _world()
    records = [
        {
            "series_id": "ES2015",
            "run": r,
            "decisions": [d.model_dump(mode="json") for d in predicted[: 5 + r]],
        }
        for r in (0, 1)
    ]
    (run_dir / "extracciones.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    return run_dir


def test_load_run_decisions_reads_one_run_of_one_series(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path)
    assert len(load_run_decisions(run_dir, series="ES2015", run=0)) == 5
    assert len(load_run_decisions(run_dir, series="ES2015", run=1)) == 6
    with pytest.raises(ManualValidationError):
        load_run_decisions(run_dir, series="ES2015", run=9)
    with pytest.raises(ManualValidationError):
        load_run_decisions(run_dir, series="TS3009", run=0)


# --- CLI ----------


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    runs = tmp_path / "experiment-a"
    runs.mkdir()
    _write_run(runs)
    _, reference = _world()
    # The stored run only holds the first decisions: store all of them for the CLI test.
    predicted, _ = _world()
    records = [
        {
            "series_id": "ES2015",
            "run": 0,
            "decisions": [d.model_dump(mode="json") for d in predicted],
        }
    ]
    (runs / "es2015-test" / "extracciones.jsonl").write_text(
        json.dumps(records[0]) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(afg_cli, "EXPERIMENT_A_DIR", runs)
    monkeypatch.setattr(afg_cli, "make_alignment_similarity", lambda: fake_similarity)
    monkeypatch.setattr(afg_cli, "load_series_reference", lambda *a, **k: _FakeReference(reference))
    monkeypatch.setattr(afg_cli, "require_pinned_environment", lambda *a, **k: {})
    monkeypatch.setattr(afg_cli, "configured_embedding_model", lambda: "fake")
    return {
        "sheet": tmp_path / "hoja.csv",
        "key": tmp_path / "clave.json",
        "out": tmp_path / "res.json",
    }


class _FakeReference:
    def __init__(self, decisions: list[ReferenceDecision]) -> None:
        self.decisions = decisions
        self.source_kind = "adjudicated"


def _cli(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["experiment", *args])


def test_cli_sheet_then_score(cli_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(afg_cli, "load_validation_config", lambda: _small_config(), raising=False)
    sheet, key, out = (str(cli_env[k]) for k in ("sheet", "key", "out"))
    result = _cli("a-validacion-hoja", "--run-name", "es2015-test", "--hoja", sheet, "--clave", key)
    assert result.exit_code == 0, result.output
    stored = json.loads(cli_env["key"].read_text(encoding="utf-8"))
    _label(
        cli_env["sheet"],
        {p["pair_id"]: "si" if p["auto_match"] else "no" for p in stored["pairs"]},
    )
    result = _cli("a-validacion-puntaje", "--hoja", sheet, "--clave", key, "--salida", out)
    assert result.exit_code == 0, result.output
    assert json.loads(cli_env["out"].read_text(encoding="utf-8"))["concordance"] == 1.0


def test_cli_sheet_refuses_to_erase_labels(
    cli_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(afg_cli, "load_validation_config", lambda: _small_config(), raising=False)
    args = ("a-validacion-hoja", "--run-name", "es2015-test", "--hoja", str(cli_env["sheet"]),
            "--clave", str(cli_env["key"]))  # fmt: skip
    assert _cli(*args).exit_code == 0
    stored = json.loads(cli_env["key"].read_text(encoding="utf-8"))
    _label(cli_env["sheet"], {p["pair_id"]: "si" for p in stored["pairs"]})
    before = cli_env["sheet"].read_bytes()
    assert _cli(*args).exit_code == 1
    assert cli_env["sheet"].read_bytes() == before


def test_cli_refuses_an_evaluation_series(
    cli_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _cli("a-validacion-hoja", "--run-name", "es2015-test", "--serie", "ES2008")
    assert result.exit_code == 1


def test_cli_help_is_in_spanish() -> None:
    out = CliRunner().invoke(afg_cli.app, ["experiment", "a-validacion-hoja", "--help"]).output
    assert "paso 3" in out.lower()


def _small_config() -> Any:
    from afg.experiments.manual_validation import ValidationConfig

    return ValidationConfig(sample_size=30, matched_share=0.5, seed=42, similarity_floor=0.5)
