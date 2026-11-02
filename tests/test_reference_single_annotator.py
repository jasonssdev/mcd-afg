"""Tests for the single-annotator reference of Experiment A (issue #229)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.evaluation.reference import (
    AmbiguousReferenceError,
    NotAdjudicatedError,
    load_reference,
    load_series_reference,
    reference_kind,
    resolve_reference,
    resolve_series_file,
)
from afg.evaluation.translation import (
    TRANSLATION_COLUMNS,
    TranslationError,
    validate_translation,
    write_translation_template,
)
from tests.test_reference import HEADER, MEETING, _row, _write_csv, transcripts  # noqa: F401

SERIES = "ES2015"
SINGLE_HEADER = [
    "decision_id",
    "meeting_id",
    "source_sentence_id",
    "sentence_text",
    "evidence_da_count",
    "evidence_text",
    "status",
    "decision_object",
    "decision_content",
    "annotator",
    "notes",
    "machine_flags",
]


def _single_row(decision_id: str, status: str, **extra: str) -> dict[str, str]:
    base = {
        "decision_id": decision_id,
        "meeting_id": decision_id.split(".")[0],
        "source_sentence_id": f"{MEETING}.x.s.1",
        "status": status,
        "decision_object": f"object of {decision_id}",
        "decision_content": f"content of {decision_id}",
        "annotator": "gv",
    }
    return {**base, **extra}


def _single(
    directory: Path, initials: str = "gv", rows: list[dict[str, str]] | None = None
) -> Path:
    rows = rows or [
        _single_row("ES2015a.d01", "decision"),
        _single_row("ES2015a.d02", "no_decision"),
    ]
    return _write_csv(directory / f"{SERIES}.decisions.{initials}.csv", rows, SINGLE_HEADER)


def _adjudicated(directory: Path) -> Path:
    return _write_csv(
        directory / f"{SERIES}.decisions.adjudicated.csv",
        [_row("ES2015a.d01", "decision", final_object="adj", final_content="adj")],
        HEADER,
    )


def test_adjudicated_wins_over_single_files(tmp_path: Path) -> None:
    adjudicated = _adjudicated(tmp_path)
    _single(tmp_path, "gv")
    _single(tmp_path, "gm")

    source = resolve_reference(SERIES, tmp_path)

    assert source.path == adjudicated
    assert source.kind == "adjudicated"


def test_exactly_one_single_file_is_the_reference(tmp_path: Path) -> None:
    single = _single(tmp_path, "gm")
    (tmp_path / f"{SERIES}.decisions.csv").write_text("machine base", encoding="utf-8")
    (tmp_path / f"{SERIES}.reference-en.csv").write_text("translation", encoding="utf-8")

    source = resolve_reference(SERIES, tmp_path)

    assert source.path == single
    assert source.kind == "single:gm"


def test_two_single_files_without_adjudication_are_ambiguous_and_named(tmp_path: Path) -> None:
    _single(tmp_path, "gv")
    _single(tmp_path, "gm")

    with pytest.raises(AmbiguousReferenceError, match=r"decisions\.gm\.csv.*decisions\.gv\.csv"):
        resolve_reference(SERIES, tmp_path)
    assert issubclass(AmbiguousReferenceError, NotAdjudicatedError)


def test_no_file_names_what_was_expected(tmp_path: Path) -> None:
    (tmp_path / f"{SERIES}.decisions.csv").write_text("machine base", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match=r"decisions\.adjudicated\.csv.*decisions\.<"):
        resolve_reference(SERIES, tmp_path)


def test_other_series_and_non_initials_files_are_not_candidates(tmp_path: Path) -> None:
    (tmp_path / "TS3009.decisions.gv.csv").write_text("x", encoding="utf-8")
    (tmp_path / f"{SERIES}.decisions.recall-sample.csv").write_text("x", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        resolve_reference(SERIES, tmp_path)


def test_generic_resolver_serves_the_relation_candidates(tmp_path: Path) -> None:
    (tmp_path / f"{SERIES}.candidates.gm.csv").write_text("x", encoding="utf-8")
    (tmp_path / f"{SERIES}.candidates.csv").write_text("x", encoding="utf-8")

    source = resolve_series_file(SERIES, tmp_path, "candidates")

    assert (source.path.name, source.kind) == (f"{SERIES}.candidates.gm.csv", "single:gm")


def test_reference_kind_from_the_file_name() -> None:
    assert reference_kind(Path("a/ES2015.decisions.adjudicated.csv")) == "adjudicated"
    assert reference_kind(Path("a/IS1004.decisions.gv.csv")) == "single:gv"


def test_single_file_loads_with_the_adjudicated_rules(tmp_path: Path, transcripts: Path) -> None:  # noqa: F811
    path = _single(
        tmp_path,
        rows=[
            _single_row("ES2015a.d01", "decision"),
            _single_row("ES2015a.d02", "no_decision"),
            _single_row("ES2015a.d03", "compuesta"),
            _single_row("ES2015a.d03-1", "decision", annotator=""),
            _single_row("ES2015a.d03-2", "descartar"),
        ],
    )

    reference = load_reference(
        path, sentence_acts={f"{MEETING}.x.s.1": ["da.1"]}, transcripts_dir=transcripts
    )

    assert [d.decision_id for d in reference.decisions] == ["ES2015a.d01", "ES2015a.d03-1"]
    assert reference.decisions[0].decision_object == "object of ES2015a.d01"
    assert reference.decisions[0].content == "content of ES2015a.d01"
    assert reference.decisions[0].adjudicator == "gv"
    assert reference.decisions[1].adjudicator == "gv"  # blank annotator -> the initials
    assert reference.excluded == {"no_decision": 1, "compuesta": 1, "descartar": 1}
    assert reference.source_kind == "single:gv"


def test_adjudicated_reference_reports_its_kind(tmp_path: Path, transcripts: Path) -> None:  # noqa: F811
    path = _adjudicated(tmp_path)

    reference = load_reference(path, sentence_acts={}, transcripts_dir=transcripts)

    assert reference.source_kind == "adjudicated"


def test_single_file_with_an_incomplete_status_still_raises(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    path = _single(tmp_path, rows=[_single_row("ES2015a.d01", "")])

    with pytest.raises(NotAdjudicatedError, match=r"ES2015a\.d01"):
        load_reference(path, sentence_acts={}, transcripts_dir=transcripts)


def test_single_decision_without_object_or_content_raises(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    path = _single(tmp_path, rows=[_single_row("ES2015a.d01", "decision", decision_content="")])

    with pytest.raises(NotAdjudicatedError, match=r"ES2015a\.d01"):
        load_reference(path, sentence_acts={}, transcripts_dir=transcripts)


def test_series_loader_uses_the_single_file(tmp_path: Path, transcripts: Path) -> None:  # noqa: F811
    _single(tmp_path, "gm")

    reference = load_series_reference(
        SERIES, decisions_dir=tmp_path, ami_root=tmp_path, transcripts_dir=transcripts
    )

    assert reference.source_kind == "single:gm"
    assert len(reference.decisions) == 1


def test_series_loader_without_any_file_still_says_adjudicated(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="adjudicated"):
        load_series_reference(SERIES, decisions_dir=tmp_path, ami_root=tmp_path)


def test_translation_template_validation_and_english_load_from_the_single_file(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    _single(tmp_path)

    template = write_translation_template(SERIES, decisions_dir=tmp_path)

    with template.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["decision_id"] for r in rows] == ["ES2015a.d01"]
    assert rows[0]["final_object"] == "object of ES2015a.d01"
    assert validate_translation(SERIES, decisions_dir=tmp_path)  # English still empty

    rows[0]["object_en"], rows[0]["content_en"] = "obj", "cont"
    with template.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TRANSLATION_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    assert validate_translation(SERIES, decisions_dir=tmp_path) == []

    english = load_series_reference(
        SERIES,
        decisions_dir=tmp_path,
        ami_root=tmp_path,
        transcripts_dir=transcripts,
        language="en",
    )
    assert english.decisions[0].decision_object == "obj"
    assert english.decisions[0].content == "cont"


def test_translation_goes_stale_when_the_single_file_changes(tmp_path: Path) -> None:
    _single(tmp_path)
    template = write_translation_template(SERIES, decisions_dir=tmp_path)
    with template.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["object_en"] = row["content_en"] = "ok"
    with template.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TRANSLATION_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    _single(tmp_path, rows=[_single_row("ES2015a.d01", "decision", decision_content="otro")])

    assert any(
        "desactualizada" in issue for issue in validate_translation(SERIES, decisions_dir=tmp_path)
    )


def test_english_load_without_translation_raises_translation_error(
    tmp_path: Path,
    transcripts: Path,  # noqa: F811
) -> None:
    _single(tmp_path)

    with pytest.raises(TranslationError, match="reference-en"):
        load_series_reference(
            SERIES,
            decisions_dir=tmp_path,
            ami_root=tmp_path,
            transcripts_dir=transcripts,
            language="en",
        )


def test_translation_template_without_any_reference_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_translation_template(SERIES, decisions_dir=tmp_path)


def test_cli_translation_template_from_the_single_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _single(tmp_path)
    monkeypatch.setattr(afg_cli, "GOLD_DECISIONS_DIR", tmp_path)

    result = CliRunner().invoke(afg_cli.app, ["gold", "translation-template", "--series", SERIES])

    assert result.exit_code == 0, result.output
    assert (tmp_path / f"{SERIES}.reference-en.csv").is_file()
