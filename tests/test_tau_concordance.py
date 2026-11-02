"""Tests for the judge-person concordance on the tau-calibration sample (ADR 0012)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.experiments.tau_calibration import (
    Judgment,
    JudgmentStore,
    SamplePair,
    load_stored_judgments,
)
from afg.experiments.tau_concordance import (
    SHEET_COLUMNS,
    ConcordanceError,
    ConcordanceSheetLabeledError,
    draw_concordance_sample,
    load_concordance_config,
    score_concordance,
    write_concordance_files,
)

BINS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85]


def _judgment(bin_low: float, i: int, same: bool | None = True) -> Judgment:
    pair = SamplePair(
        id=f"p{bin_low:.2f}-{i:02d}",
        bin_low=bin_low,
        similarity=bin_low + 0.01,
        extracted_text=f"ext {bin_low} {i}",
        reference_text=f"ref {bin_low} {i}",
        reference_id="ES2015d.d01",
        series="ES2015",
        meeting_id="ES2015d",
        models=("qwen3.6:27b",),
        occurrences=1,
        order="extracted_first",
        sample_seed=42,
    )
    return Judgment(
        pair=pair,
        same=same,
        rationale="r",
        raw_output="{}",
        failure=None if same is not None else "bad",
        order="extracted_first",
        seconds=1.0,
    )


def _pool(per_bin: int = 25) -> list[Judgment]:
    return [_judgment(b, i, same=(i % 2 == 0)) for b in BINS for i in range(per_bin)]


def _draw(pool: list[Judgment], seed: int = 42) -> list[Judgment]:
    return draw_concordance_sample(pool, sample_size=50, per_bin=6, seed=seed)


def test_sample_has_size_and_at_least_per_bin_in_every_bin() -> None:
    sample = _draw(_pool())
    assert len(sample) == 50
    assert len({j.pair.id for j in sample}) == 50
    counts = {b: sum(j.pair.bin_low == b for j in sample) for b in BINS}
    assert all(6 <= c <= 8 for c in counts.values())
    assert sum(counts.values()) == 50


def test_sample_is_deterministic_and_independent_of_input_order() -> None:
    pool = _pool()
    a = [j.pair.id for j in _draw(pool)]
    b = [j.pair.id for j in _draw(list(reversed(pool)))]
    assert a == b
    assert a != [j.pair.id for j in _draw(pool, seed=7)]


def test_sample_order_is_shuffled_not_grouped_by_bin() -> None:
    sample = _draw(_pool())
    bins = [j.pair.bin_low for j in sample]
    assert bins != sorted(bins)


def test_sample_excludes_judge_failures() -> None:
    pool = _pool()
    pool[0] = _judgment(0.5, 0, same=None)
    failed = pool[0].pair.id
    for seed in range(20):
        assert failed not in {j.pair.id for j in _draw(pool, seed=seed)}


def test_sample_refuses_when_the_pool_is_too_small() -> None:
    with pytest.raises(ConcordanceError):
        _draw(_pool(per_bin=3))


def _write(
    tmp_path: Path, pool: list[Judgment] | None = None, *, force: bool = False
) -> dict[str, Any]:
    sample = _draw(pool or _pool())
    source = tmp_path / "judgments.jsonl"
    source.write_text("source\n", encoding="utf-8")
    sheet, key = tmp_path / "sheet.csv", tmp_path / "key.json"
    write_concordance_files(
        sample, sheet_path=sheet, key_path=key, source_path=source, seed=42, per_bin=6, force=force
    )
    return {"sample": sample, "sheet": sheet, "key": key, "source": source}


def test_sheet_has_only_the_blind_columns_and_empty_labels(tmp_path: Path) -> None:
    out = _write(tmp_path)
    with out["sheet"].open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert tuple(rows[0]) == SHEET_COLUMNS == (
        "pair_id", "meeting_id", "extracted_decision", "reference_decision", "same", "notes",
    )  # fmt: skip
    assert len(rows) == 50
    assert all(r["same"] == "" and r["notes"] == "" for r in rows)
    text = out["sheet"].read_text(encoding="utf-8")
    assert "qwen3.6" not in text and "0.51" not in text
    assert [r["pair_id"] for r in rows] == [j.pair.id for j in out["sample"]]


def test_key_records_the_hidden_fields_and_provenance(tmp_path: Path) -> None:
    out = _write(tmp_path)
    key = json.loads(out["key"].read_text(encoding="utf-8"))
    assert key["seed"] == 42 and key["per_bin"] == 6 and key["sample_size"] == 50
    assert key["source_sha256"] == hashlib.sha256(b"source\n").hexdigest()
    first = key["pairs"][0]
    sample_first = out["sample"][0]
    assert first == {
        "pair_id": sample_first.pair.id,
        "bin_low": sample_first.pair.bin_low,
        "similarity": sample_first.pair.similarity,
        "judge_same": sample_first.same,
    }
    assert len(key["pairs"]) == 50


def test_writer_refuses_to_overwrite_a_labeled_sheet_unless_forced(tmp_path: Path) -> None:
    out = _write(tmp_path)
    text = out["sheet"].read_text(encoding="utf-8").replace(",,\n", ",si,\n", 1)
    out["sheet"].write_text(text, encoding="utf-8")
    with pytest.raises(ConcordanceSheetLabeledError):
        _write(tmp_path)
    assert out["sheet"].read_text(encoding="utf-8") == text
    _write(tmp_path, force=True)
    assert ",si," not in out["sheet"].read_text(encoding="utf-8")


def test_writer_rewrites_an_unlabeled_sheet(tmp_path: Path) -> None:
    out = _write(tmp_path)
    before = out["sheet"].read_bytes()
    _write(tmp_path)
    assert out["sheet"].read_bytes() == before


def _label(path: Path, human: dict[str, str]) -> None:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["same"] = human[r["pair_id"]]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def _score(out: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return score_concordance(
        out["sheet"], out["key"], tau_split=0.70, n_resamples=200, seed=1, **kw
    )


def test_scorer_perfect_agreement(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {j.pair.id: "si" if j.same else "no" for j in out["sample"]})
    result = _score(out)
    assert result["n"] == 50
    assert result["observed_agreement"] == 1.0
    assert result["kappa"] == pytest.approx(1.0)
    assert result["confusion"] == {
        "judge_si": {"person_si": result["judge_yes"], "person_no": 0},
        "judge_no": {"person_si": 0, "person_no": 50 - result["judge_yes"]},
    }
    assert all(v["agreement"] == 1.0 for v in result["by_bin"].values())


def test_scorer_known_disagreement_and_kappa_matches_sklearn_value(tmp_path: Path) -> None:
    from afg.evaluation.metrics import cohen_kappa

    out = _write(tmp_path)
    judge = {j.pair.id: ("si" if j.same else "no") for j in out["sample"]}
    flipped = list(judge)[:10]
    human = {k: ("no" if v == "si" else "si") if k in flipped else v for k, v in judge.items()}
    _label(out["sheet"], human)
    result = _score(out)
    assert result["observed_agreement"] == pytest.approx(40 / 50)
    ids = [j.pair.id for j in out["sample"]]
    expected = cohen_kappa([judge[i] for i in ids], [human[i] for i in ids])
    assert result["kappa"] == pytest.approx(expected)
    ci = result["kappa_ci"]
    assert ci["lower"] <= result["kappa"] <= ci["upper"] and ci["level"] == 0.95
    assert (
        result["confusion"]["judge_si"]["person_no"] + result["confusion"]["judge_no"]["person_si"]
        == 10
    )
    assert set(result["yes_rate_by_tau_region"]) == {"below", "above"}


def test_scorer_is_deterministic(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(
        out["sheet"],
        {j.pair.id: ("no" if i % 5 == 0 else "si") for i, j in enumerate(out["sample"])},
    )
    assert _score(out) == _score(out)


def test_yes_rate_by_tau_region(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {j.pair.id: "si" for j in out["sample"]})
    result = _score(out)
    region = result["yes_rate_by_tau_region"]
    assert region["below"]["person_yes_rate"] == 1.0 and region["above"]["person_yes_rate"] == 1.0
    assert region["below"]["n"] + region["above"]["n"] == 50
    assert 0.0 < region["below"]["judge_yes_rate"] < 1.0


def test_scorer_kappa_is_none_when_undefined(tmp_path: Path) -> None:
    pool = [_judgment(b, i, same=True) for b in BINS for i in range(25)]
    out = _write(tmp_path, pool)
    _label(out["sheet"], {j.pair.id: "si" for j in out["sample"]})
    result = _score(out)
    assert result["kappa"] is None and result["kappa_ci"] is None
    assert result["observed_agreement"] == 1.0


@pytest.mark.parametrize("bad", ["", "quizás", "maybe"])
def test_scorer_rejects_missing_or_invalid_labels(tmp_path: Path, bad: str) -> None:
    out = _write(tmp_path)
    human = {j.pair.id: "si" for j in out["sample"]}
    human[out["sample"][3].pair.id] = bad
    _label(out["sheet"], human)
    with pytest.raises(ConcordanceError, match=out["sample"][3].pair.id):
        _score(out)


def test_scorer_accepts_accent_and_case(tmp_path: Path) -> None:
    out = _write(tmp_path)
    judge = {j.pair.id: j.same for j in out["sample"]}
    _label(out["sheet"], {k: ("Sí" if v else "NO") for k, v in judge.items()})
    assert _score(out)["observed_agreement"] == 1.0


def test_scorer_rejects_ids_that_do_not_match_the_key(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _label(out["sheet"], {j.pair.id: "si" for j in out["sample"]})
    text = out["sheet"].read_text(encoding="utf-8")
    out["sheet"].write_text(text.replace(out["sample"][0].pair.id, "zzz", 1), encoding="utf-8")
    with pytest.raises(ConcordanceError):
        _score(out)


def test_config_is_preregistered() -> None:
    cfg = load_concordance_config()
    assert (cfg.sample_size, cfg.per_bin, cfg.seed, cfg.tau_split) == (50, 6, 42, 0.70)


def test_real_judgments_give_a_valid_sample() -> None:
    from afg.experiments.tau_concordance import TAU_CALIBRATION_DIR

    store = JudgmentStore(TAU_CALIBRATION_DIR)
    if not store.judgments_path.is_file():
        pytest.skip("no stored judgments")
    cfg = load_concordance_config()
    sample = draw_concordance_sample(
        load_stored_judgments(store),
        sample_size=cfg.sample_size,
        per_bin=cfg.per_bin,
        seed=cfg.seed,
    )
    assert len(sample) == 50 and all(j.same is not None for j in sample)


# --- CLI ----------


@pytest.fixture
def cli_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    store = JudgmentStore(tmp_path / "store")
    for j in _pool():
        p = j.pair
        store.append(
            {
                "id": p.id,
                "pair": {
                    "id": p.id, "bin_low": p.bin_low, "similarity": p.similarity,
                    "extracted_text": p.extracted_text, "reference_text": p.reference_text,
                    "reference_id": p.reference_id, "series": p.series, "meeting_id": p.meeting_id,
                    "models": list(p.models), "occurrences": 1, "order": p.order, "sample_seed": 42,
                },
                "same": j.same, "rationale": "r", "raw_output": "{}", "failure": None,
                "order": p.order, "seconds": 1.0,
            }
        )  # fmt: skip
    paths = {
        "store": tmp_path / "store",
        "sheet": tmp_path / "sheet.csv",
        "key": tmp_path / "key.json",
        "result": tmp_path / "out" / "concordancia.json",
    }
    monkeypatch.setattr(afg_cli, "TAU_CALIBRATION_DIR", paths["store"])
    monkeypatch.setattr(afg_cli, "CONCORDANCE_SHEET_PATH", paths["sheet"])
    monkeypatch.setattr(afg_cli, "CONCORDANCE_KEY_PATH", paths["key"])
    monkeypatch.setattr(afg_cli, "CONCORDANCE_RESULT_PATH", paths["result"])
    return paths


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(afg_cli.app, ["judge", *args])


def test_cli_sheet_then_score(cli_paths: dict[str, Path]) -> None:
    result = _invoke("tau-concordance-sheet")
    assert result.exit_code == 0, result.output
    assert cli_paths["sheet"].exists() and cli_paths["key"].exists()
    key = json.loads(cli_paths["key"].read_text(encoding="utf-8"))
    _label(
        cli_paths["sheet"], {p["pair_id"]: "si" if p["judge_same"] else "no" for p in key["pairs"]}
    )
    result = _invoke("tau-concordance-score")
    assert result.exit_code == 0, result.output
    saved = json.loads(cli_paths["result"].read_text(encoding="utf-8"))
    assert saved["observed_agreement"] == 1.0


def test_cli_sheet_refuses_to_erase_labels(cli_paths: dict[str, Path]) -> None:
    assert _invoke("tau-concordance-sheet").exit_code == 0
    key = json.loads(cli_paths["key"].read_text(encoding="utf-8"))
    _label(cli_paths["sheet"], {p["pair_id"]: "si" for p in key["pairs"]})
    before = cli_paths["sheet"].read_bytes()
    result = _invoke("tau-concordance-sheet")
    assert result.exit_code == 1
    assert cli_paths["sheet"].read_bytes() == before


def test_cli_score_reports_unlabeled_sheet(cli_paths: dict[str, Path]) -> None:
    assert _invoke("tau-concordance-sheet").exit_code == 0
    result = _invoke("tau-concordance-score")
    assert result.exit_code == 1
    assert not cli_paths["result"].exists()
