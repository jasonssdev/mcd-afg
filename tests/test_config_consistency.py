"""Cross-file consistency of the TOML configuration (drift detectors, no code reads them)."""

from __future__ import annotations

from afg.shared.config import load_annotation_config, load_corpus_config


def test_oe1_lists_agree_with_the_annotation_assignment() -> None:
    oe1 = load_corpus_config()["oe1"]
    annotation = load_annotation_config()["annotation"]

    series = set(oe1["series"])
    control = set(oe1["control_series"])
    held_out = set(oe1["held_out"])
    ineligible = set(oe1["ineligible"])

    # The control series are exactly the double-annotated phase-2 series.
    assert control == set(annotation["phase2_series"])
    # ... and they are evaluation data, never development data.
    assert control <= set(oe1["evaluation_series"])
    assert not control & set(oe1["development_series"])
    # Held-out and ineligible series are outside the annotation sample and never assigned.
    assert not held_out & series
    assert not ineligible & series
    assert not held_out & ineligible

    assigned = set(annotation["phase1_series"]) | set(annotation["phase2_series"])
    for person in annotation["annotators"]:
        assigned |= set(person["phase3_series"])
    assert assigned <= series
    assert not assigned & (held_out | ineligible)
    assert set(annotation["recall_sample"]["series"]) <= series
