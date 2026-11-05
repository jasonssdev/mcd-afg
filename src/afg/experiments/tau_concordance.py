"""Judge-person concordance on a sample of the tau-calibration judgments (ADR 0012).

The same-decision judge fixed the "judge" criterion for tau without any person having checked
its verdicts. This module draws a small blind sample from the stored judgments, writes the
worksheet a person fills and a separate key, and scores the filled sheet against the judge.

* **Sample.** From the judged pairs (judge failures excluded), ``per_bin`` pairs of every 0.05
  similarity bin plus random extras from the rest up to ``sample_size``; the order is shuffled.
  Sizes and seed live in ``[alignment.concordance]`` of ``config/experiments.toml``, fixed before
  any label exists.
* **Sheet.** Only the pair id, the meeting, the two texts and the empty ``same`` / ``notes``
  columns. The similarity, the bin, the judge verdict and the model names stay in the **key**,
  which the person does not open.
* **Score.** Observed agreement, Cohen's kappa with a percentile bootstrap CI, the confusion
  matrix, agreement per bin and the yes-rate of the judge against the person's below and above
  ``tau_split``. No pass/fail threshold is defined: a low agreement reopens ADR 0012.

Reading stored judgments calls no model, so there is no pinned-environment guard here. Only
development series are involved (ADR 0005): the judgments were drawn from them.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from afg.evaluation.metrics import cohen_kappa
from afg.experiments.tau_calibration import Judgment
from afg.shared.config import load_experiments_config
from afg.shared.csvio import open_csv_writer, read_rows
from afg.shared.paths import EXPERIMENT_A_DIR, JUDGE_CALIBRATION_DIR

__all__ = [
    "CONCORDANCE_KEY_PATH",
    "CONCORDANCE_RESULT_PATH",
    "CONCORDANCE_SHEET_PATH",
    "SHEET_COLUMNS",
    "TAU_CALIBRATION_DIR",
    "ConcordanceConfig",
    "ConcordanceError",
    "ConcordanceSheetLabeledError",
    "concordance_tables",
    "draw_concordance_sample",
    "load_concordance_config",
    "load_concordance_result",
    "save_concordance_result",
    "score_concordance",
    "write_concordance_files",
]

TAU_CALIBRATION_DIR: Final[Path] = EXPERIMENT_A_DIR / "tau-calibration"
CONCORDANCE_SHEET_PATH: Final[Path] = JUDGE_CALIBRATION_DIR / "tau-concordancia.jss.csv"
CONCORDANCE_KEY_PATH: Final[Path] = TAU_CALIBRATION_DIR / "concordancia-key.json"
CONCORDANCE_RESULT_PATH: Final[Path] = TAU_CALIBRATION_DIR / "concordancia.json"

SHEET_COLUMNS: Final[tuple[str, ...]] = (
    "pair_id",
    "meeting_id",
    "extracted_decision",
    "reference_decision",
    "same",
    "notes",
)
_YES: Final = frozenset({"si", "sí"})
_NO: Final = frozenset({"no"})


class ConcordanceError(ValueError):
    """The sample cannot be drawn or the filled sheet cannot be scored."""


class ConcordanceSheetLabeledError(ConcordanceError):
    """Writing the sheet would erase labels a person already entered."""


@dataclass(frozen=True, slots=True)
class ConcordanceConfig:
    sample_size: int
    per_bin: int
    seed: int
    tau_split: float


def load_concordance_config() -> ConcordanceConfig:
    """Read ``[alignment.concordance]``; the single source of the pre-registered values."""
    section = load_experiments_config()["alignment"]["concordance"]
    return ConcordanceConfig(
        sample_size=int(section["sample_size"]),
        per_bin=int(section["per_bin"]),
        seed=int(section["seed"]),
        tau_split=float(section["tau_split"]),
    )


# --- sample ----------


def draw_concordance_sample(
    judgments: Iterable[Judgment], *, sample_size: int, per_bin: int, seed: int
) -> list[Judgment]:
    """``per_bin`` judged pairs of each bin plus random extras up to ``sample_size``, shuffled.

    Judge failures (``same is None``) are never drawn. The result depends on the seed and the
    pair ids only, not on the order of ``judgments``.

    Raises:
        ConcordanceError: a bin has fewer than ``per_bin`` judged pairs, or the pool cannot
            reach ``sample_size``.
    """
    judged = sorted((j for j in judgments if j.same is not None), key=lambda j: j.pair.id)
    by_bin: dict[float, list[Judgment]] = defaultdict(list)
    for j in judged:
        by_bin[j.pair.bin_low].append(j)
    rng = random.Random(f"{seed}/concordance")
    chosen: list[Judgment] = []
    for bin_low in sorted(by_bin):
        members = by_bin[bin_low]
        if len(members) < per_bin:
            raise ConcordanceError(
                f"Bin {bin_low}: only {len(members)} judged pair(s), {per_bin} needed."
            )
        chosen.extend(rng.sample(members, per_bin))
    if len(judged) < sample_size or len(chosen) > sample_size:
        raise ConcordanceError(
            f"Cannot reach a sample of {sample_size} from {len(judged)} judged pairs "
            f"({len(chosen)} stratified)."
        )
    taken = {j.pair.id for j in chosen}
    rest = [j for j in judged if j.pair.id not in taken]
    chosen.extend(rng.sample(rest, sample_size - len(chosen)))
    rng.shuffle(chosen)
    return chosen


# --- sheet and key ----------


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_concordance_files(
    sample: Sequence[Judgment],
    *,
    sheet_path: Path,
    key_path: Path,
    source_path: Path,
    seed: int,
    per_bin: int,
    force: bool = False,
) -> None:
    """Write the blind sheet and the key; refuse to erase a sheet that already has labels.

    Raises:
        ConcordanceSheetLabeledError: ``sheet_path`` has a filled ``same`` and ``force`` is off.
    """
    if sheet_path.exists() and not force:
        labeled = [r for r in read_rows(sheet_path) if r.get("same", "").strip()]
        if labeled:
            raise ConcordanceSheetLabeledError(
                f"{sheet_path.name} already has labels ({len(labeled)} pair(s)); use force."
            )
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(sheet_path, encoding="utf-8") as writer:
        writer.writerow(SHEET_COLUMNS)
        for j in sample:
            p = j.pair
            writer.writerow([p.id, p.meeting_id, p.extracted_text, p.reference_text, "", ""])
    key = {
        "seed": seed,
        "per_bin": per_bin,
        "sample_size": len(sample),
        "source": source_path.name,
        "source_sha256": _file_sha256(source_path),
        "pairs": [
            {
                "pair_id": j.pair.id,
                "bin_low": j.pair.bin_low,
                "similarity": j.pair.similarity,
                "judge_same": j.same,
            }
            for j in sample
        ],
    }
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- score ----------


def _parse_label(value: str, pair_id: str) -> bool:
    text = value.strip().lower()
    if text in _YES:
        return True
    if text in _NO:
        return False
    shown = value.strip() or "(vacío)"
    raise ConcordanceError(f"Pair {pair_id!r}: `same` must be si or no, got {shown!r}.")


def _kappa_2x2(a: int, b: int, c: int, d: int) -> float:
    """Cohen's kappa of a 2x2 table (judge rows, person columns); NaN with a single class."""
    n = a + b + c + d
    observed = (a + d) / n
    expected = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    return math.nan if expected == 1.0 else (observed - expected) / (1.0 - expected)


def _bootstrap_kappa(
    judge: Sequence[bool], person: Sequence[bool], *, n_resamples: int, seed: int, level: float
) -> dict[str, Any] | None:
    rng = random.Random(seed)
    n = len(judge)
    values: list[float] = []
    for _ in range(n_resamples):
        a = b = c = d = 0
        for _ in range(n):
            i = rng.randrange(n)
            if judge[i]:
                a, b = (a + 1, b) if person[i] else (a, b + 1)
            else:
                c, d = (c + 1, d) if person[i] else (c, d + 1)
        k = _kappa_2x2(a, b, c, d)
        if k == k:
            values.append(k)
    if not values:
        return None
    values.sort()
    alpha = 1.0 - level
    low = values[max(0, int((alpha / 2) * len(values)))]
    high = values[min(len(values) - 1, int((1 - alpha / 2) * len(values)))]
    return {
        "lower": low,
        "upper": high,
        "level": level,
        "n_resamples": n_resamples,
        "n_valid_resamples": len(values),
    }


def _rate(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def score_concordance(
    sheet_path: Path,
    key_path: Path,
    *,
    tau_split: float,
    n_resamples: int,
    seed: int,
    level: float = 0.95,
) -> dict[str, Any]:
    """Judge-person agreement from the filled sheet and the key.

    Raises:
        ConcordanceError: the sheet and the key disagree on the pair ids, or a `same` is empty
            or not si/no (the message names the pair).
    """
    key = json.loads(key_path.read_text(encoding="utf-8"))
    pairs: Mapping[str, Mapping[str, Any]] = {p["pair_id"]: p for p in key["pairs"]}
    rows = read_rows(sheet_path)
    ids = [r.get("pair_id", "") for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(pairs):
        missing = sorted(set(pairs) - set(ids))
        extra = sorted(set(ids) - set(pairs))
        raise ConcordanceError(
            f"The sheet and the key do not list the same pairs (missing {missing}, unknown "
            f"{extra}, duplicated ids: {len(ids) - len(set(ids))})."
        )
    person = [_parse_label(r.get("same", ""), r["pair_id"]) for r in rows]
    judge = [bool(pairs[i]["judge_same"]) for i in ids]
    n = len(rows)

    cells = {(j, p): 0 for j in (True, False) for p in (True, False)}
    for j, p in zip(judge, person, strict=True):
        cells[(j, p)] += 1
    agree = cells[(True, True)] + cells[(False, False)]
    kappa_2x2 = _kappa_2x2(
        cells[(True, True)], cells[(True, False)], cells[(False, True)], cells[(False, False)]
    )
    kappa = (
        None
        if kappa_2x2 != kappa_2x2  # NaN: judge and person used a single class
        else cohen_kappa(
            ["si" if v else "no" for v in judge], ["si" if v else "no" for v in person]
        )
    )

    by_bin: dict[float, list[tuple[bool, bool]]] = defaultdict(list)
    regions: dict[str, list[tuple[bool, bool]]] = {"below": [], "above": []}
    for i, j, p in zip(ids, judge, person, strict=True):
        by_bin[float(pairs[i]["bin_low"])].append((j, p))
        regions["below" if float(pairs[i]["similarity"]) < tau_split else "above"].append((j, p))

    return {
        "n": n,
        "n_agree": agree,
        "observed_agreement": agree / n,
        "kappa": kappa,
        "kappa_ci": (
            None
            if kappa is None
            else _bootstrap_kappa(judge, person, n_resamples=n_resamples, seed=seed, level=level)
        ),
        "judge_yes": sum(judge),
        "person_yes": sum(person),
        "confusion": {
            "judge_si": {
                "person_si": cells[(True, True)],
                "person_no": cells[(True, False)],
            },
            "judge_no": {
                "person_si": cells[(False, True)],
                "person_no": cells[(False, False)],
            },
        },
        "by_bin": {
            f"{b:.2f}": {
                "n": len(v),
                "n_agree": sum(j == p for j, p in v),
                "agreement": sum(j == p for j, p in v) / len(v),
            }
            for b, v in sorted(by_bin.items())
        },
        "tau_split": tau_split,
        "yes_rate_by_tau_region": {
            name: {
                "n": len(v),
                "judge_yes_rate": _rate([j for j, _ in v]),
                "person_yes_rate": _rate([p for _, p in v]),
            }
            for name, v in regions.items()
        },
        "bootstrap_seed": seed,
        "source_sha256": key.get("source_sha256"),
        "threshold": None,
    }


def save_concordance_result(path: Path, result: Mapping[str, Any]) -> None:
    """Store the score so the notebook reads it without recomputing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


_RESULT_KEYS: Final = frozenset(
    {"n", "n_agree", "observed_agreement", "kappa", "kappa_ci", "confusion", "by_bin"}
    | {"yes_rate_by_tau_region", "tau_split"}
)


def load_concordance_result(path: Path) -> dict[str, Any]:
    """Read a stored score (the inverse of :func:`save_concordance_result`).

    Raises:
        ConcordanceError: the file is not a concordance score.
    """
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not result.keys() >= _RESULT_KEYS:
        raise ConcordanceError(f"{path} is not a concordance score.")
    return result


def concordance_tables(result: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Plain rows (confusion matrix, agreement per bin, yes-rates by region) for display."""
    confusion = result["confusion"]
    return {
        "confusion": [
            {
                "juez": f"juez {label}",
                "persona sí": confusion[key]["person_si"],
                "persona no": confusion[key]["person_no"],
            }
            for label, key in (("sí", "judge_si"), ("no", "judge_no"))
        ],
        "by_bin": [
            {"bin": float(b), "n": v["n"], "n_agree": v["n_agree"], "agreement": v["agreement"]}
            for b, v in sorted(result["by_bin"].items(), key=lambda kv: float(kv[0]))
        ],
        "by_region": [
            {"region": name, **result["yes_rate_by_tau_region"][name]}
            for name in ("below", "above")
        ],
    }
