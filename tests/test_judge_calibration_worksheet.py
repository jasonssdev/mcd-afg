"""Tests for the pre-filled question worksheet of the judge calibration (issue #82).

The person writing the questions only picks rows and fills four columns; the evidence is
resolved by the machine. Nothing here reads the AMI corpus: the evidence resolver is injected.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import QuestionStratum
from afg.evaluation.judge_calibration_set import DevelopmentSplitError
from afg.evaluation.judge_calibration_worksheet import (
    COLUMNS,
    HARD_MIN_SELECTED,
    HUMAN_COLUMNS,
    MIN_SELECTED,
    ResolvedActs,
    WorksheetError,
    WorksheetNotEmptyError,
    build_worksheet_rows,
    load_worksheet,
    parse_stratum,
    validate_worksheet,
    worksheet_questions,
    write_worksheet,
)

DECISION_HEADER = (
    "decision_id,meeting_id,source_sentence_id,sentence_text,evidence_text,final_status,"
    "final_object,final_content\n"
)
RELATION_HEADER = (
    "pair_id,earlier_decision_id,later_decision_id,earlier_text,later_text,final_relation\n"
)


def _acts(meeting: str, *numbers: int) -> tuple[str, ...]:
    return tuple(f"{meeting}.A.dialog-act.x.{n}" for n in numbers)


def resolver(meeting_id: str, sentence_id: str) -> ResolvedActs:
    """d01 -> acts 1,2; d02 -> act 5; any 'none' sentence -> nothing; 'part' -> 1 + 1 dropped."""
    if sentence_id.endswith(".none"):
        return ResolvedActs(ids=(), dropped=0)
    if sentence_id.endswith(".part"):
        return ResolvedActs(ids=_acts(meeting_id, 1), dropped=1)
    if sentence_id.endswith(".s2"):
        return ResolvedActs(ids=_acts(meeting_id, 5), dropped=0)
    return ResolvedActs(ids=_acts(meeting_id, 1, 2), dropped=0)


@pytest.fixture
def sources(tmp_path: Path) -> tuple[Path, Path]:
    decisions = tmp_path / "decisions.csv"
    decisions.write_text(
        DECISION_HEADER
        + "ES2015a.d01,ES2015a,ES2015a.e.s1,Price is 25.,A: 25 euros,decision,precio,fijar 25\n"
        + "ES2015a.d02,ES2015a,ES2015a.e.s2,Remote.,A: remote,decision,producto,control remoto\n"
        + "ES2015b.d01,ES2015b,ES2015b.e.s1,Single function.,A: only tv,decision,uso,solo tv\n"
        + "ES2015b.d02,ES2015b,ES2015b.e.none,Orphan.,,decision,x,huerfana\n"
        + "ES2015b.d03,ES2015b,ES2015b.e.part,Partial.,A: p,decision,x,parcial\n"
        + "ES2015b.d04,ES2015b,ES2015b.e.s1,Two things.,,compuesta,,\n"
        + "ES2015b.d05,ES2015b,ES2015b.e.s1,Maybe.,,no_decision,,\n",
        encoding="utf-8",
    )
    relations = tmp_path / "relations.csv"
    relations.write_text(
        RELATION_HEADER
        + "ES2015.p001,ES2015a.d01,ES2015b.d01,Price is 25.,Single function.,refina\n"
        + "ES2015.p002,ES2015a.d02,ES2015b.d01,Remote.,Single function.,\n",
        encoding="utf-8",
    )
    return decisions, relations


def _rows(sources: tuple[Path, Path]) -> list[dict[str, str]]:
    return build_worksheet_rows(*sources, resolve_acts=resolver)


def _by_origin(rows: Sequence[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {r["origen"]: r for r in rows if r["origen"] != "E4"}


class TestBuild:
    def test_only_decisions_whose_final_status_is_decision(
        self, sources: tuple[Path, Path]
    ) -> None:
        origins = [r["origen"] for r in _rows(sources)]
        assert [o for o in origins if o.startswith("ES2015a.d") or o.startswith("ES2015b.d")] == [
            "ES2015a.d01",
            "ES2015a.d02",
            "ES2015b.d01",
            "ES2015b.d02",
            "ES2015b.d03",
        ]

    def test_pairs_need_a_final_relation(self, sources: tuple[Path, Path]) -> None:
        origins = [r["origen"] for r in _rows(sources)]
        assert "ES2015.p001" in origins and "ES2015.p002" not in origins

    def test_six_blank_e4_rows_without_evidence(self, sources: tuple[Path, Path]) -> None:
        e4 = [r for r in _rows(sources) if r["origen"] == "E4"]
        assert len(e4) == 6
        assert all(r["reference_evidence"] == "" and r["aviso_evidencia"] == "" for r in e4)

    def test_human_columns_start_empty_and_rows_are_numbered(
        self, sources: tuple[Path, Path]
    ) -> None:
        rows = _rows(sources)
        assert [r["fila"] for r in rows] == [str(i) for i in range(1, len(rows) + 1)]
        assert all(r[c] == "" for r in rows for c in HUMAN_COLUMNS)

    def test_decision_row_carries_text_agreed_content_and_resolved_evidence(
        self, sources: tuple[Path, Path]
    ) -> None:
        row = _by_origin(_rows(sources))["ES2015a.d01"]
        assert row["reunion"] == "ES2015a"
        assert row["decision"] == "Price is 25."
        assert row["contenido_acordado"] == "fijar 25"
        assert row["evidencia_texto"] == "A: 25 euros"
        assert (
            row["reference_evidence"] == "ES2015a:ES2015a.A.dialog-act.x.1;ES2015a.A.dialog-act.x.2"
        )
        assert row["aviso_evidencia"] == ""

    def test_unresolvable_evidence_is_left_empty_and_flagged(
        self, sources: tuple[Path, Path]
    ) -> None:
        row = _by_origin(_rows(sources))["ES2015b.d02"]
        assert row["reference_evidence"] == ""
        assert "sin evidencia" in row["aviso_evidencia"]

    def test_partially_resolved_evidence_is_flagged_but_kept(
        self, sources: tuple[Path, Path]
    ) -> None:
        row = _by_origin(_rows(sources))["ES2015b.d03"]
        assert row["reference_evidence"] == "ES2015b:ES2015b.A.dialog-act.x.1"
        assert "parcial" in row["aviso_evidencia"]

    def test_pair_row_has_both_texts_the_relation_and_the_union_of_evidence(
        self, sources: tuple[Path, Path]
    ) -> None:
        row = _by_origin(_rows(sources))["ES2015.p001"]
        assert row["reunion"] == "ES2015a -> ES2015b"
        assert row["relacion"] == "refina"
        assert row["decision"] == "Price is 25."
        assert row["decision_posterior"] == "Single function."
        assert row["contenido_acordado"] == "fijar 25"
        assert row["contenido_posterior"] == "solo tv"
        assert row["reference_evidence"] == (
            "ES2015a:ES2015a.A.dialog-act.x.1;ES2015a.A.dialog-act.x.2"
            "|ES2015b:ES2015b.A.dialog-act.x.1;ES2015b.A.dialog-act.x.2"
        )

    def test_pair_evidence_merges_spans_of_the_same_meeting(self, tmp_path: Path) -> None:
        decisions = tmp_path / "d.csv"
        decisions.write_text(
            DECISION_HEADER
            + "ES2015a.d01,ES2015a,ES2015a.e.s1,A.,,decision,o,a\n"
            + "ES2015a.d02,ES2015a,ES2015a.e.s2,B.,,decision,o,b\n",
            encoding="utf-8",
        )
        relations = tmp_path / "r.csv"
        relations.write_text(
            RELATION_HEADER + "ES2015.p001,ES2015a.d01,ES2015a.d02,A.,B.,refina\n",
            encoding="utf-8",
        )
        (row,) = [
            r
            for r in build_worksheet_rows(decisions, relations, resolve_acts=resolver)
            if r["origen"] == "ES2015.p001"
        ]
        assert row["reference_evidence"] == (
            "ES2015a:ES2015a.A.dialog-act.x.1;ES2015a.A.dialog-act.x.2;ES2015a.A.dialog-act.x.5"
        )

    def test_pair_with_an_unknown_decision_is_flagged_not_invented(self, tmp_path: Path) -> None:
        decisions = tmp_path / "d.csv"
        decisions.write_text(DECISION_HEADER, encoding="utf-8")
        relations = tmp_path / "r.csv"
        relations.write_text(
            RELATION_HEADER + "ES2015.p001,ES2015a.d01,ES2015b.d01,A.,B.,refina\n",
            encoding="utf-8",
        )
        (row,) = [
            r
            for r in build_worksheet_rows(decisions, relations, resolve_acts=resolver)
            if r["origen"] == "ES2015.p001"
        ]
        assert row["reference_evidence"] == ""
        assert row["aviso_evidencia"] != ""


class TestFile:
    def test_written_without_bom_with_lf_and_the_declared_columns(
        self, tmp_path: Path, sources: tuple[Path, Path]
    ) -> None:
        path = tmp_path / "ES2015.preguntas.csv"
        write_worksheet(path, _rows(sources))
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
        assert tuple(next(csv.reader(path.read_text(encoding="utf-8").splitlines()))) == COLUMNS
        assert tuple(COLUMNS[:4]) == HUMAN_COLUMNS

    def test_read_tolerates_a_bom(self, tmp_path: Path, sources: tuple[Path, Path]) -> None:
        path = tmp_path / "w.csv"
        write_worksheet(path, _rows(sources))
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        assert len(load_worksheet(path)) == len(_rows(sources))

    def test_regenerating_an_untouched_worksheet_is_allowed(
        self, tmp_path: Path, sources: tuple[Path, Path]
    ) -> None:
        path = tmp_path / "w.csv"
        write_worksheet(path, _rows(sources))
        write_worksheet(path, _rows(sources))

    def test_refuses_to_overwrite_a_worksheet_with_human_work(
        self, tmp_path: Path, sources: tuple[Path, Path]
    ) -> None:
        path = tmp_path / "w.csv"
        rows = _rows(sources)
        write_worksheet(path, rows)
        filled = load_worksheet(path)
        filled[0]["pregunta"] = "What is the price?"
        write_worksheet(path, filled)
        before = path.read_bytes()
        with pytest.raises(WorksheetNotEmptyError):
            write_worksheet(path, rows)
        assert path.read_bytes() == before

    def test_force_overwrites_human_work(self, tmp_path: Path, sources: tuple[Path, Path]) -> None:
        path = tmp_path / "w.csv"
        rows = _rows(sources)
        filled = [dict(r) for r in rows]
        filled[0]["usar"] = "si"
        write_worksheet(path, filled)
        write_worksheet(path, rows, force=True)
        assert all(r["usar"] == "" for r in load_worksheet(path))

    def test_missing_columns_are_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "w.csv"
        path.write_text("usar,pregunta\nsi,q\n", encoding="utf-8")
        with pytest.raises(WorksheetError, match="faltan columnas"):
            load_worksheet(path)


def _row(fila: int, **cells: str) -> dict[str, str]:
    base = dict.fromkeys(COLUMNS, "")
    base.update(fila=str(fila), origen=f"ES2015a.d{fila:02d}", reunion="ES2015a")
    base["reference_evidence"] = "ES2015a:ES2015a.A.dialog-act.x.1"
    base.update(cells)
    return base


def _selected(fila: int, stratum: str = "E1", **cells: str) -> dict[str, str]:
    values = {
        "usar": "si",
        "stratum": stratum,
        "pregunta": "What is the price?",
        "respuesta_referencia": "25 euros.",
    }
    values.update(cells)
    return _row(fila, **values)


def _valid_set() -> list[dict[str, str]]:
    rows = [_selected(i, "E1") for i in range(1, 9)]
    rows += [_selected(i, "E2") for i in range(9, 14)]
    rows += [_selected(i, "E3") for i in range(14, 17)]
    rows += [
        _selected(i, "E4", respuesta_referencia="", reference_evidence="", origen="E4")
        for i in range(17, 17 + MIN_SELECTED - 16)
    ]
    return rows


class TestParseStratum:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("E1", QuestionStratum.E1_POINT_FACT),
            (" e2 ", QuestionStratum.E2_CURRENT_STATE),
            ("E3", QuestionStratum.E3_EVOLUTION),
            ("e4", QuestionStratum.E4_UNANSWERABLE),
            ("E3_evolution", QuestionStratum.E3_EVOLUTION),
        ],
    )
    def test_shorthand_and_full_names(self, text: str, expected: QuestionStratum) -> None:
        assert parse_stratum(text) is expected

    def test_unknown_value_is_none(self) -> None:
        assert parse_stratum("E5") is None and parse_stratum("") is None


class TestValidate:
    def test_a_complete_selection_has_no_errors_and_counts_strata(self) -> None:
        report = validate_worksheet(_valid_set())
        assert report.errors == ()
        assert report.n_selected == MIN_SELECTED
        assert report.by_stratum["E1_point_fact"] == 8
        assert report.by_stratum["E4_unanswerable"] == MIN_SELECTED - 16
        assert any("E1" in line for line in report.summary_lines())

    def test_nothing_selected_yet(self) -> None:
        report = validate_worksheet([_row(1), _row(2)])
        assert any("no hay ninguna fila" in e for e in report.errors)

    def test_fewer_than_the_hard_minimum_is_an_error(self) -> None:
        report = validate_worksheet(_valid_set()[: HARD_MIN_SELECTED - 1])
        assert any(f"mínimo es {HARD_MIN_SELECTED}" in e for e in report.errors)

    def test_between_the_hard_minimum_and_the_target_is_only_a_warning(self) -> None:
        rows = _valid_set()[: MIN_SELECTED - 1]
        report = validate_worksheet(rows)
        assert report.errors == ()
        assert report.ok
        assert any(f"recomendado {MIN_SELECTED}" in w for w in report.warnings)
        assert len(worksheet_questions(rows)) == MIN_SELECTED - 1

    def test_the_target_has_no_size_warning(self) -> None:
        assert validate_worksheet(_valid_set()).warnings == ()

    def test_missing_stratum(self) -> None:
        rows = _valid_set()
        rows[0]["stratum"] = ""
        assert any("fila 1" in e and "stratum" in e for e in validate_worksheet(rows).errors)

    def test_unknown_stratum(self) -> None:
        rows = _valid_set()
        rows[0]["stratum"] = "E9"
        assert any("fila 1" in e and "E9" in e for e in validate_worksheet(rows).errors)

    def test_missing_question(self) -> None:
        rows = _valid_set()
        rows[1]["pregunta"] = " "
        assert any("fila 2" in e and "pregunta" in e for e in validate_worksheet(rows).errors)

    def test_e4_with_reference_answer(self) -> None:
        rows = _valid_set()
        rows[-1]["respuesta_referencia"] = "Nobody knows."
        assert any(
            "E4" in e and "respuesta_referencia" in e for e in validate_worksheet(rows).errors
        )

    def test_answerable_without_reference_answer(self) -> None:
        rows = _valid_set()
        rows[2]["respuesta_referencia"] = ""
        assert any(
            "fila 3" in e and "respuesta_referencia" in e for e in validate_worksheet(rows).errors
        )

    def test_answerable_without_evidence_mentions_the_warning_column(self) -> None:
        rows = _valid_set()
        rows[3]["reference_evidence"] = ""
        rows[3]["aviso_evidencia"] = "sin evidencia"
        errors = validate_worksheet(rows).errors
        assert any("fila 4" in e and "evidencia" in e for e in errors)

    def test_malformed_evidence(self) -> None:
        rows = _valid_set()
        rows[4]["reference_evidence"] = "no-colon"
        assert any(
            "fila 5" in e and "reference_evidence" in e for e in validate_worksheet(rows).errors
        )

    def test_no_e4_question(self) -> None:
        rows = [_selected(i, "E1") for i in range(1, MIN_SELECTED + 1)]
        assert any("E4" in e and "ninguna" in e for e in validate_worksheet(rows).errors)

    def test_unrecognized_usar_value(self) -> None:
        rows = _valid_set()
        rows[0]["usar"] = "quizás"
        assert any("fila 1" in e and "usar" in e for e in validate_worksheet(rows).errors)

    def test_question_written_but_row_not_selected_is_only_a_warning(self) -> None:
        rows = _valid_set()
        rows[0]["usar"] = ""
        report = validate_worksheet(rows)
        assert any("fila 1" in w for w in report.warnings)

    def test_unselected_rows_are_not_validated(self) -> None:
        rows = [*_valid_set(), _row(99, stratum="zzz")]
        assert validate_worksheet(rows).errors == ()


class TestQuestions:
    def test_selected_rows_become_calibration_questions(self) -> None:
        questions = worksheet_questions(_valid_set())
        assert len(questions) == MIN_SELECTED
        first = questions[0]
        assert first.id == "ES2015.q001"
        assert first.series_id == "ES2015"
        assert first.stratum is QuestionStratum.E1_POINT_FACT
        assert first.question == "What is the price?"
        assert first.reference_answer == "25 euros."
        assert first.reference_evidence == (
            EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("ES2015a.A.dialog-act.x.1",)),
        )

    def test_e4_questions_carry_no_reference_or_evidence(self) -> None:
        last = worksheet_questions(_valid_set())[-1]
        assert last.stratum is QuestionStratum.E4_UNANSWERABLE
        assert last.reference_answer is None and last.reference_evidence == ()

    def test_unselected_rows_are_left_out(self) -> None:
        rows = [*_valid_set(), _row(99, pregunta="draft only")]
        assert len(worksheet_questions(rows)) == MIN_SELECTED

    def test_invalid_worksheet_is_refused_with_the_first_problem(self) -> None:
        rows = _valid_set()
        rows[0]["stratum"] = ""
        with pytest.raises(WorksheetError, match="fila 1"):
            worksheet_questions(rows)

    def test_series_outside_the_calibration_series_is_refused(self) -> None:
        rows = _valid_set()
        rows[0]["reunion"] = "IS1004a"
        rows[0]["reference_evidence"] = "IS1004a:IS1004a.A.dialog-act.x.1"
        with pytest.raises(DevelopmentSplitError):
            worksheet_questions(rows)


class TestActResolver:
    def test_orders_by_transcript_and_drops_acts_missing_from_it(self, tmp_path: Path) -> None:
        import json

        from afg.evaluation.judge_calibration_worksheet import make_act_resolver

        ami = tmp_path / "ami"
        (ami / "extractive").mkdir(parents=True)
        (ami / "extractive" / "ES2015a.summlink.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<nite:root xmlns:nite="http://nite.sourceforge.net/">'
            + "".join(
                f'<summlink><nite:pointer role="extractive" '
                f'href="ES2015a.A.dialog-act.xml#id(ES2015a.A.dialog-act.x.{n})"/>'
                f'<nite:pointer role="abstractive" href="ES2015a.abssumm.xml#id(ES2015a.e.s.1)"/>'
                f"</summlink>"
                for n in (30, 10, 99)
            )
            + "</nite:root>",
            encoding="utf-8",
        )
        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        with (transcripts / "ES2015a.jsonl").open("w", encoding="utf-8") as handle:
            for turn, n in enumerate((10, 20, 30)):
                handle.write(
                    json.dumps(
                        {
                            "meeting_id": "ES2015a",
                            "turn_index": turn,
                            "speaker": "A",
                            "role": "PM",
                            "text": "t",
                            "start": 0.0,
                            "end": 1.0,
                            "char_start": 0,
                            "char_end": 1,
                            "dialogue_act_ids": [f"ES2015a.A.dialog-act.x.{n}"],
                        }
                    )
                    + "\n"
                )
        resolve = make_act_resolver(ami, transcripts)

        found = resolve("ES2015a", "ES2015a.e.s.1")

        assert found.ids == ("ES2015a.A.dialog-act.x.10", "ES2015a.A.dialog-act.x.30")
        assert found.dropped == 1
        assert resolve("ES2015a", "ES2015a.e.s.404") == ResolvedActs(ids=(), dropped=0)
