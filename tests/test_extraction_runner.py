"""Tests for repeated-run variance reporting (thesis section 5.8)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from afg.domain.decision import Decision, DecisionStatus, EvidenceSpan
from afg.extraction.protocol import ExtractionResult
from afg.extraction.runner import run_repeated


@dataclass
class _FakeExtractor:
    """Returns a different number of decisions on each call, to exercise variance math."""

    decision_counts: list[int] = field(default_factory=lambda: [2, 3, 2])
    _call_index: int = 0

    def extract(self, meeting_id: str, transcript: str) -> ExtractionResult:
        count = self.decision_counts[self._call_index % len(self.decision_counts)]
        self._call_index += 1
        decisions = tuple(
            Decision(
                id=f"{meeting_id}-d{i}",
                series_id=meeting_id[:-1],
                meeting_id=meeting_id,
                decision_object="object",
                content="content",
                status=DecisionStatus.ACCEPTED,
                evidence=EvidenceSpan(meeting_id=meeting_id, dialogue_act_ids=("d1",)),
            )
            for i in range(count)
        )
        return ExtractionResult(decisions=decisions)


class TestRunRepeated:
    def test_runs_exactly_n_times(self) -> None:
        extractor = _FakeExtractor(decision_counts=[1, 1, 1])
        results, _ = run_repeated(extractor, "ES2015a", "transcript", n_runs=3)
        assert len(results) == 3

    def test_reports_mean_and_stdev(self) -> None:
        extractor = _FakeExtractor(decision_counts=[2, 4, 6])
        _, variance = run_repeated(extractor, "ES2015a", "transcript", n_runs=3)

        assert variance.mean_decision_count == pytest.approx(4.0)
        assert variance.stdev_decision_count > 0.0
        assert variance.decision_counts == (2, 4, 6)

    def test_below_minimum_runs_raises(self) -> None:
        extractor = _FakeExtractor()
        with pytest.raises(ValueError, match="minimum"):
            run_repeated(extractor, "ES2015a", "transcript", n_runs=2)

    def test_single_identical_run_has_zero_stdev(self) -> None:
        extractor = _FakeExtractor(decision_counts=[3, 3, 3])
        _, variance = run_repeated(extractor, "ES2015a", "transcript", n_runs=3)
        assert variance.stdev_decision_count == 0.0
