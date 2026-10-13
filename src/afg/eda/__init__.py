"""Computation layer for the AFG2 exploratory data analysis (notebook ``03``).

Every figure the EDA notebook shows comes from this package (CONTRIBUTING 7.1); the notebook
imports, calls and plots. Functions return pandas ``DataFrame`` s or frozen dataclasses and
never print.

Submodules:

- :mod:`afg.eda.tables` -- the five analysis levels (series 14, meeting 56, speaker-meeting
  224, decision 343, pair 3,071) and the readers that feed them.
- :mod:`afg.eda.dictionary` -- variable registry and the data dictionary built from it.
- :mod:`afg.eda.quality` -- data dictionary, key and business-rule checks, missingness.
- :mod:`afg.eda.stats` -- descriptive statistics, outliers, group comparison, correlation.
- :mod:`afg.eda.multivariate` -- standardised PCA and silhouette-scanned clustering.
- :mod:`afg.eda.temporal` -- per-position aggregates and monotonic-trend tests.

ADR 0005: only ids and numeric features leave this package; no decision or transcript text.
"""

from __future__ import annotations

from afg.eda.dictionary import VARIABLES, VariableSpec, table_dictionary
from afg.eda.multivariate import ClusterScanResult, PcaResult, cluster_scan, pca_standardized
from afg.eda.quality import (
    VALID_ROLES,
    consistency_checks,
    data_dictionary,
    missingness_matrix,
    missingness_mechanism,
    missingness_summary,
    record_missingness,
)
from afg.eda.stats import (
    Chi2Result,
    KruskalResult,
    chi2_independence,
    contingency_table,
    correlation_table,
    describe_categorical,
    describe_numeric,
    iqr_outliers,
    kruskal_by_group,
    mosaic_rectangles,
    multivariate_outliers,
    outlier_summary,
    rate_by_bin,
    variance_inflation_factors,
    zscore_outliers,
)
from afg.eda.tables import (
    DEFAULT_CONTEXT_TOKENS,
    EdaTables,
    add_pair_features,
    build_decision_table,
    build_meeting_table,
    build_pair_table,
    build_series_table,
    build_speaker_table,
    duration_coherence,
    load_eda_tables,
    read_meeting_metadata,
    read_speaker_metadata,
    read_transcripts,
    turn_length_distribution,
)
from afg.eda.temporal import monotonic_trend, position_aggregates

__all__ = [
    "DEFAULT_CONTEXT_TOKENS",
    "VALID_ROLES",
    "VARIABLES",
    "Chi2Result",
    "ClusterScanResult",
    "EdaTables",
    "KruskalResult",
    "PcaResult",
    "VariableSpec",
    "add_pair_features",
    "build_decision_table",
    "build_meeting_table",
    "build_pair_table",
    "build_series_table",
    "build_speaker_table",
    "chi2_independence",
    "cluster_scan",
    "consistency_checks",
    "contingency_table",
    "correlation_table",
    "data_dictionary",
    "describe_categorical",
    "describe_numeric",
    "duration_coherence",
    "iqr_outliers",
    "kruskal_by_group",
    "load_eda_tables",
    "missingness_matrix",
    "missingness_mechanism",
    "missingness_summary",
    "monotonic_trend",
    "mosaic_rectangles",
    "multivariate_outliers",
    "outlier_summary",
    "pca_standardized",
    "position_aggregates",
    "rate_by_bin",
    "read_meeting_metadata",
    "read_speaker_metadata",
    "read_transcripts",
    "record_missingness",
    "table_dictionary",
    "turn_length_distribution",
    "variance_inflation_factors",
    "zscore_outliers",
]
