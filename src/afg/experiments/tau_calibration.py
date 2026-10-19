"""Inputs to fix the alignment threshold tau (issue #142): null control and a judged sample.

tau is not fixed by ADR 0011. With the English reference (protocol v2.0) this module offers
the two pre-registered criteria, stated before any result was seen (``odd/tasks``
feature document):

* **Criterion A (null control).** The output of one series is scored against the reference of
  the other, meeting by meeting, in both directions (notebook 15, section 6.2). ``tau_null`` is
  the smallest value of the grid whose mean null recall is at most 0.05.
* **Criterion B (judge).** The pairs the scorer matches, with similarity in [0.50, 0.90), are
  sampled by 0.05 bins (up to 25 per bin, fixed seed, no identical text pair twice) and a judge of
  another family answers "do both texts describe the same decision?". ``tau_judge`` is the lowest
  bin lower bound from which the share of "yes" is above 0.5 in that bin and in all higher ones.

The proposal is ``max(tau_null, tau_judge)``; the full curve is still reported and the decision
belongs to the author of the thesis.

Pairs are those of :func:`afg.evaluation.alignment_analysis.scored_matches`, i.e. the Hungarian
assignment inside the primary ``origin_meetings`` scope, computed at the lowest tau of the sample
range so every pair that any larger tau could count is a candidate. Only development series are
read (ADR 0005): the guards of :mod:`afg.experiments.model_screen` apply.

The judge backend is injected (:class:`afg.evaluation.judge.JudgeBackend`); every judgment is
written to disk with its raw output, so a rerun never calls the judge again for the same inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Final, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError

from afg.evaluation.alignment_analysis import scored_matches
from afg.evaluation.judge import (
    JudgeBackend,
    require_distinct_model_families,
)
from afg.evaluation.metrics import wilson_interval
from afg.evaluation.reference import ReferenceDecision
from afg.evaluation.scoring import SimilarityFn, pair_text
from afg.experiments.model_screen import (
    CurvePoint,
    PassRun,
    relabel_series,
    score_curve,
)

__all__ = [
    "Judgment",
    "JudgmentStore",
    "MatchedPair",
    "Sample",
    "SamplePair",
    "bin_table",
    "coverage_by_tau",
    "digest_of",
    "examples_by_region",
    "installed_digests",
    "judge_sample",
    "matched_pairs",
    "null_coverage",
    "null_curve_points",
    "prompt_sha256",
    "propose_tau",
    "reference_shift_table",
    "same_decision_prompt",
    "stratified_sample",
    "tau_judge",
    "tau_null",
]

PROMPT_VERSION: Final = "same-decision-v1"
PROMPT_RESOURCE: Final = "same_decision_v1.md"
NULL_COVERAGE_CEILING: Final = 0.05
"""Criterion A: the null recall must be at most this."""
SAMPLE_LOW: Final = 0.50
SAMPLE_HIGH: Final = 0.90
BIN_WIDTH: Final = 0.05
PER_BIN: Final = 25
MAJORITY: Final = 0.5
"""Criterion B: the share of "yes" must be strictly above this."""

_COUNTERPART: Final = {"ES2015": "TS3009", "TS3009": "ES2015"}
Order = Literal["extracted_first", "reference_first"]


# --- criterion A: null control ----------


def null_curve_points(
    runs: Iterable[PassRun],
    references: Mapping[str, Sequence[ReferenceDecision]],
    similarity: SimilarityFn,
    *,
    taus: Sequence[float],
    partition_of: Callable[[str], str] | None = None,
) -> list[CurvePoint]:
    """Score each run against the reference of the OTHER series (ES2015 <-> TS3009).

    Each point is attributed to the series whose reference was used. The meetings keep their
    letter (:func:`~afg.experiments.model_screen.relabel_series`).

    Raises:
        ValueError: a run belongs to a series without a counterpart, or to a series that is
            not a development series (ADR 0005).
    """
    moved = []
    for run in runs:
        if run.series not in _COUNTERPART:
            raise ValueError(f"Null control: series {run.series} has no counterpart series.")
        moved.append(relabel_series(run, _COUNTERPART[run.series], partition_of=partition_of))
    return score_curve(moved, references, similarity, taus=taus)


def coverage_by_tau(points: Iterable[CurvePoint]) -> pd.DataFrame:
    """Per tau: runs, mean recall over every run and the largest (model, series) mean recall."""
    by_tau: dict[float, list[CurvePoint]] = defaultdict(list)
    for p in points:
        by_tau[round(p.tau, 10)].append(p)
    rows = []
    for tau, group in sorted(by_tau.items()):
        cells: dict[tuple[str, str], list[float]] = defaultdict(list)
        for p in group:
            cells[(p.model, p.series)].append(p.recall)
        rows.append(
            {
                "tau": tau,
                "runs": len(group),
                "recall_mean": sum(p.recall for p in group) / len(group),
                "recall_worst_cell": max(sum(v) / len(v) for v in cells.values()),
            }
        )
    return pd.DataFrame(rows, columns=["tau", "runs", "recall_mean", "recall_worst_cell"])


null_coverage = coverage_by_tau
"""The same summary; it is the null control when ``points`` come from ``null_curve_points``."""


def tau_null(coverage: pd.DataFrame, *, ceiling: float = NULL_COVERAGE_CEILING) -> float | None:
    """Criterion A: the smallest tau of the grid whose mean null recall is at most ``ceiling``."""
    for _, row in coverage.sort_values("tau").iterrows():
        if row.recall_mean <= ceiling + 1e-12:
            return float(row.tau)
    return None


# --- matched pairs and the stratified sample ----------


@dataclass(frozen=True, slots=True)
class MatchedPair:
    """One pair the scorer matches: an extracted decision and its reference decision."""

    model: str
    series: str
    run: int
    meeting_id: str
    reference_id: str
    extracted_text: str
    reference_text: str
    similarity: float


def matched_pairs(
    runs: Iterable[PassRun],
    references: Mapping[str, Sequence[ReferenceDecision]],
    similarity: SimilarityFn,
    *,
    tau: float = SAMPLE_LOW,
) -> list[MatchedPair]:
    """The pairs the scorer's Hungarian assignment keeps at ``tau`` (primary scope), per run."""
    pairs = []
    for run in runs:
        for m in scored_matches(references[run.series], run.decisions, similarity, tau=tau):
            pairs.append(
                MatchedPair(
                    model=run.model,
                    series=run.series,
                    run=run.run,
                    meeting_id=m.reference.meeting_id,
                    reference_id=m.reference.decision_id,
                    extracted_text=pair_text(m.predicted.decision_object, m.predicted.content),
                    reference_text=pair_text(m.reference.decision_object, m.reference.content),
                    similarity=m.similarity,
                )
            )
    return pairs


@dataclass(frozen=True, slots=True)
class SamplePair:
    """A distinct (extracted text, reference text) pair of the sample.

    ``models`` lists every extractor that produced the pair and ``occurrences`` how many matched
    pairs of the pool it stands for; the provenance fields are those of its first occurrence.
    """

    id: str
    bin_low: float
    similarity: float
    extracted_text: str
    reference_text: str
    reference_id: str
    series: str
    meeting_id: str
    models: tuple[str, ...]
    occurrences: int
    order: Order
    sample_seed: int


@dataclass(frozen=True, slots=True)
class Sample:
    pairs: tuple[SamplePair, ...]
    available: dict[float, int]
    """Distinct text pairs available per bin (before taking at most ``per_bin``)."""
    seed: int
    per_bin: int


def bin_low_of(similarity: float, *, width: float = BIN_WIDTH) -> float:
    """Lower bound of the ``width``-wide bin of ``similarity`` (robust to float noise)."""
    return round(math.floor(similarity / width + 1e-9) * width, 10)


def _pair_id(extracted: str, reference: str) -> str:
    return hashlib.sha256(f"{extracted}\x1f{reference}".encode()).hexdigest()[:12]


def stratified_sample(
    pool: Iterable[MatchedPair],
    *,
    seed: int,
    per_bin: int = PER_BIN,
    low: float = SAMPLE_LOW,
    high: float = SAMPLE_HIGH,
) -> Sample:
    """Distinct text pairs with similarity in ``[low, high)``, up to ``per_bin`` per 0.05 bin.

    Identical (extracted text, reference text) pairs are merged first. Each bin is drawn with
    its own generator seeded from ``seed`` and the bin, and every pair gets a random
    presentation order from the same seed, so the result does not depend on the pool order.
    """
    ordered = sorted(
        (p for p in pool if low <= p.similarity < high),
        key=lambda p: (p.extracted_text, p.reference_text, p.model, p.series, p.run),
    )
    merged: dict[str, list[MatchedPair]] = {}
    for p in ordered:
        merged.setdefault(_pair_id(p.extracted_text, p.reference_text), []).append(p)
    by_bin: dict[float, list[str]] = defaultdict(list)
    for pid, group in merged.items():
        by_bin[bin_low_of(group[0].similarity)].append(pid)

    chosen: list[SamplePair] = []
    for bin_low, ids in sorted(by_bin.items()):
        ids = sorted(ids)
        picked = random.Random(f"{seed}/{bin_low}").sample(ids, min(per_bin, len(ids)))
        for pid in sorted(picked):
            group = merged[pid]
            first = group[0]
            order: Order = (
                "extracted_first"
                if random.Random(f"{seed}/order/{pid}").random() < 0.5
                else "reference_first"
            )
            chosen.append(
                SamplePair(
                    id=pid,
                    bin_low=bin_low,
                    similarity=first.similarity,
                    extracted_text=first.extracted_text,
                    reference_text=first.reference_text,
                    reference_id=first.reference_id,
                    series=first.series,
                    meeting_id=first.meeting_id,
                    models=tuple(sorted({g.model for g in group})),
                    occurrences=len(group),
                    order=order,
                    sample_seed=seed,
                )
            )
    return Sample(
        pairs=tuple(chosen),
        available={b: len(v) for b, v in sorted(by_bin.items())},
        seed=seed,
        per_bin=per_bin,
    )


# --- the judge ----------


class _SameDecisionOutput(BaseModel):
    """The JSON object the judge must return; also the Ollama ``format`` schema."""

    model_config = ConfigDict(extra="forbid", strict=True)

    same_decision: bool
    rationale: str


@dataclass(frozen=True, slots=True)
class Judgment:
    """The judge's answer on one pair; ``same`` is ``None`` when the output was unusable."""

    pair: SamplePair
    same: bool | None
    rationale: str
    raw_output: str
    failure: str | None
    order: Order
    seconds: float


def same_decision_prompt() -> str:
    """The judge instructions (``prompts/same_decision_v1.md``)."""
    return (resources.files("afg.evaluation") / "prompts" / PROMPT_RESOURCE).read_bytes().decode()


def prompt_sha256() -> str:
    """SHA-256 of the judge instructions, recorded with every run."""
    return hashlib.sha256(same_decision_prompt().encode("utf-8")).hexdigest()


def _user_prompt(pair: SamplePair) -> str:
    first, second = (
        (pair.extracted_text, pair.reference_text)
        if pair.order == "extracted_first"
        else (pair.reference_text, pair.extracted_text)
    )
    return f"Text A:\n{first}\n\nText B:\n{second}"


def installed_digests(host: str | None = None) -> dict[str, str]:
    """Digest of every model installed in the local Ollama server, by tag."""
    import ollama

    from afg.conditions.c1_retrieval import resolve_ollama_host

    client = ollama.Client(host=host or resolve_ollama_host())
    return {str(m.model): str(m.digest) for m in client.list().models}


def digest_of(model: str, installed: Mapping[str, str]) -> str:
    """The digest of ``model`` (untagged means ``:latest``)."""
    wanted = model if ":" in model.rsplit("/", 1)[-1] else f"{model}:latest"
    for name, digest in installed.items():
        if name == wanted:
            return digest
    raise ValueError(f"Model {model!r} is not installed (found {sorted(installed)}).")


class JudgmentStore:
    """Raw judgments (``judgments.jsonl``) and the run description (``run.json``) in a folder."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    @property
    def judgments_path(self) -> Path:
        return self.directory / "judgments.jsonl"

    @property
    def meta_path(self) -> Path:
        return self.directory / "run.json"

    def load(self) -> dict[str, dict[str, Any]]:
        """Stored records by pair id; the latest record of an id wins."""
        records: dict[str, dict[str, Any]] = {}
        if self.judgments_path.is_file():
            for line in self.judgments_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    records[record["id"]] = record
        return records

    def append(self, record: Mapping[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.judgments_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def write_meta(self, meta: Mapping[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )


def _key(pair: SamplePair, settings: Mapping[str, Any]) -> str:
    payload = {
        "id": pair.id,
        "extracted": pair.extracted_text,
        "reference": pair.reference_text,
        "order": pair.order,
        **settings,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _parse(raw: str) -> tuple[bool | None, str, str | None]:
    try:
        parsed = _SameDecisionOutput.model_validate(json.loads(raw))
    except json.JSONDecodeError:
        return None, "", "invalid_json"
    except ValidationError:
        return None, "", "schema_violation"
    return parsed.same_decision, parsed.rationale, None


def judge_sample(
    pairs: Sequence[SamplePair],
    *,
    backend: JudgeBackend,
    judge_model: str,
    model_digest: str,
    seed: int,
    temperature: float,
    think: bool | str | None,
    store: JudgmentStore,
    clock: Callable[[], float] = time.perf_counter,
    progress: Callable[[int, int], None] | None = None,
) -> list[Judgment]:
    """Ask the judge about each pair, reusing the stored answer when every input is the same.

    The judge/extractor family guard runs first, for every extractor in the sample. An output
    that is not valid JSON or does not match the schema is kept as a failure (``same`` is
    ``None``) with its raw text; backend errors propagate. Each answer is appended to the store
    as soon as it arrives, so an interruption loses nothing.
    """
    for pair in pairs:
        for extractor in pair.models:
            require_distinct_model_families(judge_model, extractor, must_differ=True)
    settings = {
        "prompt_sha256": prompt_sha256(),
        "judge_model": judge_model,
        "model_digest": model_digest,
        "seed": seed,
        "temperature": temperature,
        "think": think,
    }
    stored = store.load()
    judgments: list[Judgment] = []
    for n, pair in enumerate(pairs, start=1):
        key = _key(pair, settings)
        record = stored.get(pair.id)
        if record is None or record["key"] != key:
            started = clock()
            raw = backend.complete(
                same_decision_prompt(),
                _user_prompt(pair),
                model=judge_model,
                seed=seed,
                temperature=temperature,
                format_schema=_SameDecisionOutput.model_json_schema(),
            )
            seconds = clock() - started
            same, rationale, failure = _parse(raw)
            record = {
                "id": pair.id,
                "key": key,
                "same": same,
                "rationale": rationale,
                "failure": failure,
                "raw_output": raw,
                "order": pair.order,
                "seconds": seconds,
                "pair": asdict(pair),
            }
            store.append(record)
        judgments.append(
            Judgment(
                pair=pair,
                same=record["same"],
                rationale=record["rationale"],
                raw_output=record["raw_output"],
                failure=record["failure"],
                order=record["order"],
                seconds=float(record["seconds"]),
            )
        )
        if progress is not None:
            progress(n, len(pairs))
    store.write_meta(
        {
            "prompt_version": PROMPT_VERSION,
            **settings,
            "sample_seed": pairs[0].sample_seed if pairs else None,
            "n_pairs": len(pairs),
            "n_failures": sum(1 for j in judgments if j.same is None),
            "judge_seconds_total": sum(j.seconds for j in judgments),
        }
    )
    return judgments


# --- criterion B and the proposal ----------


def bin_table(judgments: Iterable[Judgment], *, confidence_level: float = 0.95) -> pd.DataFrame:
    """Per bin with judgments: usable answers ``n``, ``yes``, rate, Wilson interval, failures."""
    by_bin: dict[float, list[Judgment]] = defaultdict(list)
    for j in judgments:
        by_bin[j.pair.bin_low].append(j)
    rows = []
    for low, group in sorted(by_bin.items()):
        answered = [j for j in group if j.same is not None]
        yes = sum(1 for j in answered if j.same)
        row: dict[str, Any] = {
            "bin_low": low,
            "bin_high": round(low + BIN_WIDTH, 10),
            "n": len(answered),
            "yes": yes,
            "rate": yes / len(answered) if answered else float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "failures": len(group) - len(answered),
        }
        if answered:
            ci = wilson_interval(yes, len(answered), confidence_level)
            row["ci_low"], row["ci_high"] = ci.lower, ci.upper
        rows.append(row)
    return pd.DataFrame(
        rows,
        columns=["bin_low", "bin_high", "n", "yes", "rate", "ci_low", "ci_high", "failures"],
    )


def tau_judge(table: pd.DataFrame) -> float | None:
    """Criterion B: lowest bin lower bound from which every bin has more than half "yes".

    Bins without usable answers carry no evidence and are skipped. ``None`` when not even the
    top bin has a majority of "yes".
    """
    found: float | None = None
    for _, row in table[table.n > 0].sort_values("bin_low", ascending=False).iterrows():
        if row.rate > MAJORITY:
            found = float(row.bin_low)
        else:
            break
    return found


def propose_tau(tau_nulo: float | None, tau_juez: float | None) -> float | None:
    """``max(tau_nulo, tau_juez)``; ``None`` when either criterion found no value."""
    if tau_nulo is None or tau_juez is None:
        return None
    return max(tau_nulo, tau_juez)


def examples_by_region(
    judgments: Iterable[Judgment], *, regions: Sequence[tuple[float, float]]
) -> list[tuple[float, float, Judgment]]:
    """For each ``[lo, hi)`` region, the answered judgment nearest to the region's centre."""
    answered = sorted((j for j in judgments if j.same is not None), key=lambda j: j.pair.id)
    chosen = []
    for lo, hi in regions:
        inside = [j for j in answered if lo <= j.pair.similarity < hi]
        if inside:
            centre = (lo + hi) / 2
            chosen.append((lo, hi, min(inside, key=lambda j: abs(j.pair.similarity - centre))))
    return chosen


# --- Spanish versus English reference ----------


def reference_shift_table(
    spanish: pd.DataFrame,
    english: pd.DataFrame,
    *,
    taus: Sequence[float],
    metric: Literal["recall", "precision", "f1"] = "recall",
) -> pd.DataFrame:
    """Mean ``metric`` per (model, series, tau) with each reference language and the shift."""
    column = f"{metric}_mean"
    keys = ["model", "series", "tau"]

    def pick(frame: pd.DataFrame, name: str) -> pd.DataFrame:
        wanted = frame[[any(abs(t - x) < 1e-9 for x in taus) for t in frame["tau"]]]
        return wanted[[*keys, column]].rename(columns={column: name})

    merged = pick(spanish, "es").merge(pick(english, "en"), on=keys, how="inner")
    merged["shift"] = merged["en"] - merged["es"]
    return merged.sort_values(keys).reset_index(drop=True)
