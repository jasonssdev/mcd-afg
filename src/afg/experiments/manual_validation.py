"""Manual validation of the automatic alignment (protocol step 3, issue #240).

The alignment protocol (``docs/protocols/alignment.md``, step 3) contrasts the automatic
alignment against a manual matching on a sample of at least 100 pairs and reports the
:func:`~afg.evaluation.alignment.concordance`. This module builds that sample from a stored
Experiment A run, writes the blind worksheet a person fills and a separate key, and scores the
filled sheet.

* **Pair.** A *candidate pair* is an extracted decision and a reference decision of the same
  meeting (the primary ``origin_meetings`` alignment scope). The automatic alignment keeps a
  pair when the Hungarian assignment at the main tau selects it; the person answers, for each
  sampled pair, whether both texts are the same decision.
* **Sample.** ``sample_size`` pairs (``manual_validation_sample_size``), ``matched_share`` of them
  drawn from the automatic matches and the rest from same-meeting pairs the automatic alignment
  does not keep but whose similarity is at least ``similarity_floor`` (the near misses). The order
  is shuffled. Size, share, floor and seed live in ``config/experiments.toml`` and are fixed
  before any label exists.
* **Pooling.** A run may list several series (the formal evaluation run lists eleven). The
  candidate pairs of all of them form one pool and the sample is drawn from it, each row carrying
  its ``serie``; a pool smaller than ``sample_size`` is refused, never shrunk.
* **Sheet.** Only the pair id, the series, the meeting, the two texts and the empty ``same`` /
  ``notes`` columns. The similarity and the automatic decision stay in the **key**.
* **Score.** The concordance of the two matched-pair sets inside the sample (Jaccard, as
  ``concordance`` defines it), the observed agreement, the confusion matrix and, per stratum,
  how many pairs the person confirmed. No pass/fail threshold is defined.

Reading a stored run and its reference calls no model; only the similarity function given by the
caller embeds texts. The sheet lives under ``data/processed`` and the key under
``data/interim`` (gitignored), so the person who fills the sheet cannot read the key.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np

from afg.domain.decision import Decision
from afg.evaluation.alignment import concordance
from afg.evaluation.alignment_analysis import scored_matches
from afg.evaluation.metrics import cohen_kappa
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import SimilarityFn, pair_text
from afg.experiments.extraction_runs import RECORDS_FILENAME
from afg.shared.config import load_experiments_config
from afg.shared.csvio import open_csv_writer, read_rows
from afg.shared.paths import INTERIM_DIR, PROCESSED_DIR

__all__ = [
    "SHEET_COLUMNS",
    "VALIDATION_DIR",
    "VALIDATION_KEY_DIR",
    "CandidatePair",
    "ManualValidationError",
    "ManualValidationSheetLabeledError",
    "ValidationConfig",
    "candidate_pairs",
    "draw_validation_sample",
    "load_run_decisions",
    "load_validation_config",
    "score_validation",
    "source_sha256",
    "write_validation_files",
]

VALIDATION_DIR: Final[Path] = PROCESSED_DIR / "alignment-validation"
VALIDATION_KEY_DIR: Final[Path] = INTERIM_DIR / "alignment-validation"
SHEET_COLUMNS: Final[tuple[str, ...]] = (
    "pair_id",
    "serie",
    "meeting_id",
    "extracted_decision",
    "reference_decision",
    "same",
    "notes",
)
_YES: Final = frozenset({"si", "sí"})
_NO: Final = frozenset({"no"})


class ManualValidationError(ValueError):
    """The sample cannot be drawn or the filled sheet cannot be scored."""


class ManualValidationSheetLabeledError(ManualValidationError):
    """Writing the sheet would erase labels a person already entered."""


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    sample_size: int
    matched_share: float
    seed: int
    similarity_floor: float


def load_validation_config() -> ValidationConfig:
    """Read ``[alignment]`` and ``[alignment.manual_validation]``: the pre-registered values."""
    section = load_experiments_config()["alignment"]
    params = section["manual_validation"]
    return ValidationConfig(
        sample_size=int(section["manual_validation_sample_size"]),
        matched_share=float(params["matched_share"]),
        seed=int(params["seed"]),
        similarity_floor=float(params["similarity_floor"]),
    )


# --- stored run ----------


def source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_run_decisions(run_dir: Path, *, series: str, run: int) -> list[Decision]:
    """The decisions of one repetition of one series in ``extracciones.jsonl``.

    Raises:
        ManualValidationError: the run directory has no record for that series and repetition.
    """
    path = run_dir / RECORDS_FILENAME
    if not path.is_file():
        raise ManualValidationError(f"No existe {path}.")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("series_id") == series and int(record["run"]) == run:
            return [Decision.model_validate(d) for d in record.get("decisions", [])]
    raise ManualValidationError(f"{path.parent.name}: no hay registro de {series} corrida {run}.")


# --- candidate pairs ----------


@dataclass(frozen=True, slots=True)
class CandidatePair:
    """One (extracted, reference) pair of the same meeting and whether the scorer keeps it."""

    pair_id: str
    meeting_id: str
    predicted_meeting: str
    predicted_id: str
    reference_id: str
    predicted_index: int
    reference_index: int
    extracted_text: str
    reference_text: str
    similarity: float
    auto_match: bool
    serie: str = ""


def _pair_id(predicted_id: str, reference_id: str) -> str:
    return "v-" + hashlib.sha1(f"{predicted_id}|{reference_id}".encode()).hexdigest()[:10]


def candidate_pairs(
    reference: Sequence[ReferenceDecision],
    predicted: Sequence[Decision],
    similarity: SimilarityFn,
    *,
    tau: float,
    floor: float,
) -> list[CandidatePair]:
    """Same-meeting pairs: those the Hungarian assignment keeps at ``tau`` and those at ``floor``.

    Only ``ACCEPTED`` extracted decisions are considered, as the scorer does. The automatic
    matches come from :func:`~afg.evaluation.alignment_analysis.scored_matches` (primary scope),
    so they are exactly the pairs counted as true positives.
    """
    accepted = [d for d in predicted if d.is_decision]
    if not accepted or not reference:
        return []
    matrix = np.asarray(
        similarity(
            [pair_text(d.decision_object, d.content) for d in accepted],
            [pair_text(r.decision_object, r.content) for r in reference],
        ),
        dtype=float,
    )
    kept = scored_matches(reference, accepted, lambda _p, _r: matrix, tau=tau)
    p_index = {id(d): i for i, d in enumerate(accepted)}
    r_index = {id(r): j for j, r in enumerate(reference)}
    automatic = {(p_index[id(m.predicted)], r_index[id(m.reference)]) for m in kept}
    pairs = []
    for i, d in enumerate(accepted):
        for j, r in enumerate(reference):
            if r.meeting_id not in d.origin_meetings:
                continue
            is_auto = (i, j) in automatic
            if not is_auto and matrix[i, j] < floor:
                continue
            pairs.append(
                CandidatePair(
                    pair_id=_pair_id(d.id, r.decision_id),
                    meeting_id=r.meeting_id,
                    predicted_meeting=d.meeting_id,
                    predicted_id=d.id,
                    reference_id=r.decision_id,
                    predicted_index=i,
                    reference_index=j,
                    extracted_text=pair_text(d.decision_object, d.content),
                    reference_text=pair_text(r.decision_object, r.content),
                    similarity=float(matrix[i, j]),
                    auto_match=is_auto,
                )
            )
    return pairs


# --- sample ----------


def draw_validation_sample(
    pairs: Sequence[CandidatePair], *, sample_size: int, matched_share: float, seed: int
) -> list[CandidatePair]:
    """``matched_share`` of the sample from the automatic matches, the rest from the others.

    When a stratum is short the other one fills the sample. The result depends on the seed and
    the pair ids only, not on the order of ``pairs``.

    Raises:
        ManualValidationError: fewer than ``sample_size`` candidate pairs.
    """
    if len(pairs) < sample_size:
        raise ManualValidationError(
            f"Solo hay {len(pairs)} pares candidatos y la muestra pide {sample_size}; "
            "la muestra no se reduce."
        )
    ordered = sorted(pairs, key=lambda p: p.pair_id)
    matched = [p for p in ordered if p.auto_match]
    others = [p for p in ordered if not p.auto_match]
    n_matched = min(round(sample_size * matched_share), len(matched))
    n_others = sample_size - n_matched
    if n_others > len(others):
        n_others = len(others)
        n_matched = sample_size - n_others
    rng = random.Random(f"{seed}/manual-validation")
    chosen = rng.sample(matched, n_matched) + rng.sample(others, n_others)
    rng.shuffle(chosen)
    return chosen


# --- sheet and key ----------


def write_validation_files(
    sample: Sequence[CandidatePair],
    *,
    sheet_path: Path,
    key_path: Path,
    source: Mapping[str, Any],
    tau: float,
    seed: int,
    force: bool = False,
) -> None:
    """Write the blind sheet and the key; refuse to erase a sheet that already has labels.

    Raises:
        ManualValidationSheetLabeledError: ``sheet_path`` has labels and ``force`` is off.
    """
    if sheet_path.exists() and not force:
        labeled = [r for r in read_rows(sheet_path) if r.get("same", "").strip()]
        if labeled:
            raise ManualValidationSheetLabeledError(
                f"{sheet_path.name} ya tiene etiquetas ({len(labeled)} par(es)); usa --force."
            )
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    with open_csv_writer(sheet_path, encoding="utf-8") as writer:
        writer.writerow(SHEET_COLUMNS)
        for p in sample:
            writer.writerow(
                [p.pair_id, p.serie, p.meeting_id, p.extracted_text, p.reference_text, "", ""]
            )
    key = {
        "tau": tau,
        "seed": seed,
        "sample_size": len(sample),
        "source": dict(source),
        "pairs": [
            {
                "pair_id": p.pair_id,
                "serie": p.serie,
                "predicted_id": p.predicted_id,
                "reference_id": p.reference_id,
                "predicted_index": p.predicted_index,
                "reference_index": p.reference_index,
                "similarity": p.similarity,
                "auto_match": p.auto_match,
            }
            for p in sample
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
    raise ManualValidationError(f"Par {pair_id!r}: `same` debe ser si o no, no {shown!r}.")


def score_validation(sheet_path: Path, key_path: Path) -> dict[str, Any]:
    """Concordance between the automatic alignment and the manual matching of the sample.

    Raises:
        ManualValidationError: the sheet and the key disagree on the pair ids, or a `same` is
            empty or not si/no (the message names the pair).
    """
    key = json.loads(key_path.read_text(encoding="utf-8"))
    pairs: Mapping[str, Mapping[str, Any]] = {p["pair_id"]: p for p in key["pairs"]}
    rows = read_rows(sheet_path)
    ids = [r.get("pair_id", "") for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(pairs):
        raise ManualValidationError(
            "La hoja y la clave no listan los mismos pares "
            f"(faltan {sorted(set(pairs) - set(ids))}, sobran {sorted(set(ids) - set(pairs))})."
        )
    manual = [_parse_label(r.get("same", ""), r["pair_id"]) for r in rows]
    auto = [bool(pairs[i]["auto_match"]) for i in ids]

    def edge(i: str) -> tuple[str, int, int]:
        return (
            str(pairs[i].get("serie", "")),
            int(pairs[i]["predicted_index"]),
            int(pairs[i]["reference_index"]),
        )

    auto_set = {edge(i) for i, a in zip(ids, auto, strict=True) if a}
    manual_set = {edge(i) for i, m in zip(ids, manual, strict=True) if m}
    cells = {(a, m): 0 for a in (True, False) for m in (True, False)}
    for a, m in zip(auto, manual, strict=True):
        cells[(a, m)] += 1
    n = len(rows)
    agree = cells[(True, True)] + cells[(False, False)]
    kappa = (
        cohen_kappa(["si" if v else "no" for v in auto], ["si" if v else "no" for v in manual])
        if len(set(auto)) > 1 and len(set(manual)) > 1
        else None
    )
    yes_ids = [i for i, m in zip(ids, manual, strict=True) if m]
    shared = 0
    for field in ("predicted_id", "reference_id"):
        values = [pairs[i][field] for i in yes_ids]
        shared += sum(1 for i in yes_ids if values.count(pairs[i][field]) > 1)
    return {
        "n": n,
        "n_auto": sum(auto),
        "n_manual": sum(manual),
        "concordance": concordance(auto_set, manual_set),
        "n_agree": agree,
        "observed_agreement": agree / n,
        "kappa": kappa,
        "confusion": {
            "auto_si": {
                "manual_si": cells[(True, True)],
                "manual_no": cells[(True, False)],
            },
            "auto_no": {
                "manual_si": cells[(False, True)],
                "manual_no": cells[(False, False)],
            },
        },
        "automatic_confirmed": {
            "n": cells[(True, True)] + cells[(True, False)],
            "n_manual_yes": cells[(True, True)],
        },
        "automatic_missed": {
            "n": cells[(False, True)] + cells[(False, False)],
            "n_manual_yes": cells[(False, True)],
        },
        "n_manual_shared_decision": shared,
        "tau": key.get("tau"),
        "source": key.get("source"),
        "threshold": None,
        "key": key,
    }
