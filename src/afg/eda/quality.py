"""Data dictionary, missingness diagnostics and business-rule checks.

Missingness: this project never imputes (decision D3), so the diagnostics here exist to
*describe and argue* the mechanism, not to repair it. :func:`missingness_mechanism` can
reject MCAR by showing that missingness depends on an observed covariate (that is MAR, or
MNAR with an observed proxy); failing to reject MCAR is not proof of it. MNAR (missingness
depends on the unobserved value itself) cannot be tested from the data and has to be argued
from how the value is produced.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations

import pandas as pd
from scipy import stats as sps

from afg.eda.stats import chi2_independence, contingency_table

VALID_ROLES: frozenset[str] = frozenset({"PM", "ID", "ME", "UI"})
_TEXT_MEAN_LENGTH = 60
_ID_NAME = re.compile(r"(^id$|_id$)")


# --- data dictionary ------------------------------------------------------------------------


def _infer_kind(name: str, series: pd.Series) -> str:
    if _ID_NAME.search(name):
        return "identifier"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "temporal"
    if pd.api.types.is_bool_dtype(series):
        return "categorical"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    lengths = series.dropna().astype(str).str.len()
    if len(lengths) and lengths.mean() > _TEXT_MEAN_LENGTH:
        return "text"
    return "categorical"


def data_dictionary(
    df: pd.DataFrame,
    descriptions: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
    domains: Mapping[str, str] | None = None,
    kinds: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """One row per column of ``df``.

    Columns: ``variable``, ``description``, ``dtype``, ``kind`` (``numeric``,
    ``categorical``, ``temporal``, ``text`` or ``identifier``; inferred from the dtype and
    the name unless overridden in ``kinds``), ``unit``, ``valid_domain``, ``n_missing``,
    ``n_unique`` and ``example`` (first non-missing value). Metadata absent from the
    mappings is left blank rather than guessed.
    """
    descriptions, units, domains, kinds = (
        descriptions or {},
        units or {},
        domains or {},
        kinds or {},
    )
    rows: list[dict[str, object]] = []
    for name in df.columns:
        column = df[name]
        present = column.dropna()
        rows.append(
            {
                "variable": name,
                "description": descriptions.get(name, ""),
                "dtype": str(column.dtype),
                "kind": kinds.get(name) or _infer_kind(name, column),
                "unit": units.get(name, ""),
                "valid_domain": domains.get(name, ""),
                "n_missing": int(column.isna().sum()),
                "n_unique": int(column.nunique(dropna=True)),
                "example": str(present.iloc[0]) if len(present) else "",
            }
        )
    return pd.DataFrame(rows)


# --- missingness ----------------------------------------------------------------------------


def missingness_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per variable: ``variable``, ``n_present``, ``n_missing``, ``share_missing``."""
    missing = df.isna().sum()
    n = len(df)
    return pd.DataFrame(
        {
            "variable": list(df.columns),
            "n_present": [n - int(m) for m in missing],
            "n_missing": [int(m) for m in missing],
            "share_missing": [int(m) / n if n else float("nan") for m in missing],
        }
    )


def record_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Per record (index kept): ``n_missing`` and ``share_missing`` across the columns."""
    counts = df.isna().sum(axis=1).astype(int)
    width = df.shape[1]
    return pd.DataFrame(
        {"n_missing": counts, "share_missing": counts / width if width else float("nan")}
    )


def missingness_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Boolean frame, ``True`` where the value is missing (ready for a heatmap)."""
    return df.isna().astype(bool)


def missingness_mechanism(
    indicator: pd.Series, covariates: pd.DataFrame, *, alpha: float = 0.05
) -> pd.DataFrame:
    """Test whether a missingness ``indicator`` (``True`` = missing) depends on observed
    ``covariates``.

    Numeric covariates use a two-sided Mann-Whitney U test (effect: rank-biserial
    correlation, positive when the missing group has larger values); categorical and boolean
    ones use chi-square (Fisher exact for a small 2x2) with Cramer's V. Columns:
    ``covariate``, ``test``, ``statistic``, ``p_value``, ``effect_name``, ``effect_size``,
    ``n``, ``associated`` (``p < alpha``). A constant indicator yields NaN. Many covariates
    mean many tests: read ``associated`` as a screening, not as a corrected conclusion.
    """
    flags = indicator.astype(bool)
    nan = float("nan")
    rows: list[dict[str, object]] = []
    for name in covariates.columns:
        values = covariates.loc[flags.index, name]
        usable = values.notna()
        group = flags[usable]
        values = values[usable]
        row: dict[str, object] = {
            "covariate": name,
            "test": "none",
            "statistic": nan,
            "p_value": nan,
            "effect_name": "",
            "effect_size": nan,
            "n": int(usable.sum()),
        }
        if group.nunique() == 2:
            numeric = pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(
                values
            )
            if numeric:
                a = values[group].to_numpy(dtype=float)
                b = values[~group].to_numpy(dtype=float)
                u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
                row.update(
                    test="mann_whitney",
                    statistic=float(u),
                    p_value=float(p),
                    effect_name="rank_biserial",
                    effect_size=float(2 * u / (len(a) * len(b)) - 1),
                )
            else:
                table = contingency_table(
                    pd.DataFrame({"x": values.astype(str), "m": group}), "x", "m"
                )
                result = chi2_independence(table)
                row.update(
                    test=result.test,
                    statistic=result.statistic,
                    p_value=result.p_value,
                    effect_name="cramers_v",
                    effect_size=result.cramers_v,
                )
        p_value = row["p_value"]
        row["associated"] = bool(isinstance(p_value, float) and p_value < alpha)
        rows.append(row)
    return pd.DataFrame(rows)


# --- keys and business rules ----------------------------------------------------------------


def _show(items: Iterable[object], limit: int = 5) -> str:
    listed = [str(i) for i in items]
    more = f" (+{len(listed) - limit} más)" if len(listed) > limit else ""
    return ", ".join(listed[:limit]) + more


def _result(
    check: str, description: str, violations: Sequence[object], ok_detail: str = "sin violaciones"
) -> dict[str, object]:
    return {
        "check": check,
        "description": description,
        "passed": len(violations) == 0,
        "n_violations": len(violations),
        "detail": ok_detail if not violations else _show(violations),
    }


def consistency_checks(
    meetings: pd.DataFrame,
    speakers: pd.DataFrame,
    decisions: pd.DataFrame,
    pairs: pd.DataFrame,
    *,
    evidence: pd.DataFrame | None = None,
    act_ids: pd.DataFrame | None = None,
    meetings_per_series: int = 4,
) -> pd.DataFrame:
    """Key-consistency and business-rule checks over the EDA tables.

    Returns one row per check: ``check``, ``description`` (Spanish), ``passed``,
    ``n_violations`` and ``detail`` (the first offending keys; ids only, never text).
    The checks needing optional inputs are skipped, not failed, when those are absent:
    ``evidence`` (columns ``decision_id``, ``dialogue_act_id``) and ``act_ids`` (columns
    ``meeting_id``, ``dialogue_act_id``, the acts that exist in the frozen transcripts);
    the chronology check needs a ``start`` column in ``meetings``; the duplicate-sentence
    checks need the ``exact_duplicate`` / ``near_duplicate`` flags of the decision table.

    Duplicate sentences are defined within a series: *exact* means identical text after
    lower-casing and whitespace collapsing; *near* means an identical set of blocker tokens
    (:func:`afg.annotation.blocking.tokenize`), i.e. overlap coefficient 1.0 in both
    directions. Both count every decision involved in a duplicate, not only the extra copies.
    """
    rows: list[dict[str, object]] = []

    per_series = meetings.groupby("series_id")["meeting_id"].nunique()
    rows.append(
        _result(
            "meetings_per_series",
            f"Cada serie tiene exactamente {meetings_per_series} reuniones",
            [s for s, n in per_series.items() if n != meetings_per_series],
        )
    )
    expected_letters = {"a", "b", "c", "d"}
    bad_positions = [
        s
        for s, part in meetings.groupby("series_id")
        if set(part["position"]) != expected_letters
        or part.sort_values("position")["position_index"].tolist() != sorted(part["position_index"])
    ]
    rows.append(
        _result(
            "positions_abcd",
            "Las posiciones de cada serie son a, b, c, d y su índice es creciente",
            bad_positions,
        )
    )
    if "start" in meetings.columns:
        verifiable = [
            (s, part) for s, part in meetings.groupby("series_id") if part["start"].notna().all()
        ]
        unordered = [
            s
            for s, part in verifiable
            if not part.sort_values("position_index")["start"].is_monotonic_increasing
            or part["start"].duplicated().any()
        ]
        result = _result(
            "chronological_order",
            "El inicio real crece de a a d en las series que registran la hora de inicio",
            unordered,
            ok_detail=f"{len(verifiable)} de {meetings['series_id'].nunique()} series con "
            "hora de inicio completa; sin violaciones entre ellas",
        )
        rows.append(result)
    if "recording_date" in meetings.columns:
        backwards_dates = [
            s
            for s, part in meetings.groupby("series_id")
            if not part.sort_values("position_index")["recording_date"]
            .dropna()
            .is_monotonic_increasing
        ]
        rows.append(
            _result(
                "date_order",
                "La fecha de grabación no retrocede de a a d (la hora puede faltar)",
                backwards_dates,
            )
        )

    rows.append(
        _result(
            "valid_roles",
            "Todo hablante tiene un rol dentro de {PM, ID, ME, UI}",
            [
                f"{m}:{s}={r}"
                for m, s, r in zip(
                    speakers["meeting_id"], speakers["speaker"], speakers["role"], strict=True
                )
                if r not in VALID_ROLES
            ],
        )
    )
    role_counts = speakers.groupby(["meeting_id", "role"]).size()
    rows.append(
        _result(
            "one_speaker_per_role",
            "Ningún rol se repite dentro de una reunión",
            [f"{m}:{r}" for (m, r), n in role_counts.items() if n > 1],
        )
    )
    speaker_counts = speakers.groupby(["meeting_id", "speaker"]).size()
    rows.append(
        _result(
            "unique_speaker_rows",
            "Cada par (reunión, hablante) aparece una sola vez",
            [f"{m}:{s}" for (m, s), n in speaker_counts.items() if n > 1],
        )
    )

    meeting_ids = set(meetings["meeting_id"])
    rows.append(
        _result(
            "unique_meeting_ids",
            "Los identificadores de reunión son únicos",
            meetings.loc[meetings["meeting_id"].duplicated(), "meeting_id"].tolist(),
        )
    )
    rows.append(
        _result(
            "decision_meeting_exists",
            "Toda decisión pertenece a una reunión existente",
            decisions.loc[~decisions["meeting_id"].isin(meeting_ids), "decision_id"].tolist(),
        )
    )
    rows.append(
        _result(
            "unique_decision_ids",
            "Los identificadores de decisión son únicos",
            decisions.loc[decisions["decision_id"].duplicated(), "decision_id"].tolist(),
        )
    )

    decision_ids = set(decisions["decision_id"])
    missing_ends = pairs[
        ~pairs["earlier_decision_id"].isin(decision_ids)
        | ~pairs["later_decision_id"].isin(decision_ids)
    ]
    rows.append(
        _result(
            "pair_decisions_exist",
            "Las dos decisiones de cada par existen",
            [
                f"{a}->{b}"
                for a, b in zip(
                    missing_ends["earlier_decision_id"],
                    missing_ends["later_decision_id"],
                    strict=True,
                )
            ],
        )
    )
    order = dict(zip(meetings["meeting_id"], meetings["position_index"], strict=True))
    series_of = dict(zip(meetings["meeting_id"], meetings["series_id"], strict=True))
    backwards = [
        f"{a}->{b}"
        for a, b in zip(pairs["earlier_meeting_id"], pairs["later_meeting_id"], strict=True)
        if a not in order or b not in order or series_of[a] != series_of[b] or order[a] >= order[b]
    ]
    rows.append(
        _result(
            "pair_earlier_precedes_later",
            "En cada par la decisión anterior precede a la posterior, en la misma serie",
            backwards,
        )
    )
    key = pairs["earlier_decision_id"] + "|" + pairs["later_decision_id"]
    rows.append(
        _result(
            "unique_pairs",
            "Ningún par de decisiones está repetido",
            key[key.duplicated()].tolist(),
        )
    )
    expected = 0
    for _, part in decisions.groupby("series_id"):
        sizes = part.groupby("meeting_id").size().tolist()
        expected += sum(a * b for a, b in combinations(sizes, 2))
    rows.append(
        {
            "check": "pair_count_matches_decisions",
            "description": "El número de pares es el de pares entre reuniones distintas implícito "
            "en el conteo de decisiones por reunión",
            "passed": expected == len(pairs),
            "n_violations": abs(expected - len(pairs)),
            "detail": f"esperados {expected}, presentes {len(pairs)}",
        }
    )

    if evidence is not None and act_ids is not None:
        known = set(act_ids["dialogue_act_id"])
        unresolved = evidence.loc[~evidence["dialogue_act_id"].isin(known)]
        rows.append(
            _result(
                "evidence_acts_resolve",
                "Todo acto de diálogo citado como evidencia existe en las transcripciones",
                [
                    f"{d}:{a}"
                    for d, a in zip(
                        unresolved["decision_id"], unresolved["dialogue_act_id"], strict=True
                    )
                ],
            )
        )
    for flag, label in (("exact_duplicate", "exactas"), ("near_duplicate", "casi idénticas")):
        if flag in decisions.columns:
            rows.append(
                _result(
                    f"{flag}_sentences",
                    f"Sin oraciones de decisión {label} dentro de una serie",
                    decisions.loc[decisions[flag].astype(bool), "decision_id"].tolist(),
                )
            )

    out = pd.DataFrame(rows, columns=["check", "description", "passed", "n_violations", "detail"])
    out["n_violations"] = out["n_violations"].astype(int)
    out["passed"] = out["passed"].astype(bool)
    return out


__all__ = [
    "VALID_ROLES",
    "consistency_checks",
    "data_dictionary",
    "missingness_matrix",
    "missingness_mechanism",
    "missingness_summary",
    "record_missingness",
]
