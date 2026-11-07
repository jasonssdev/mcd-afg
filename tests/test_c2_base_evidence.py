"""Tests for the compiled-base evidence behind the OE4 labels of C2 E1 failures. No network."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from afg.domain.decision import EvidenceSpan
from afg.domain.question import Question, QuestionStratum
from afg.experiments.c2_base_evidence import (
    ETAPA_VALUES,
    WORKSHEET_COLUMNS,
    WorksheetLabeledError,
    bundle_dir_for,
    bundle_resolver,
    count_stages,
    oe4_worksheet_rows,
    rank_bundle_objects,
    read_worksheet_rows,
    rule_attributed_failures,
    stage_shares,
    write_oe4_worksheet,
)


def _write(bundle: Path, concept_id: str, body: str, *, front: str = "title: T") -> None:
    path = bundle / f"{concept_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front}\n---\n\n# T\n\n{body}\n", encoding="utf-8")


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    _write(root, "decisions/price", "The selling price is twenty Euros.")
    _write(root, "concepts/market", "A market for young adults.")
    _write(root, "events/talk", "Price talk and market.")
    _write(root, "sources/es2015a", "Price twenty Euros market young adults for the remote.")
    _write(root, "sources/es2015b", "Unrelated chatter about animals.")
    return root


REFERENCE = "Selling price twenty Euros"


def test_objects_ranked_by_coverage_with_kind(bundle: Path) -> None:
    evidence = rank_bundle_objects(REFERENCE, bundle)
    assert [o.object_id for o in evidence.objects] == [
        "decisions/price",
        "events/talk",
        "concepts/market",
    ]
    assert [o.kind for o in evidence.objects] == ["decisions", "other", "concepts"]
    assert evidence.objects[0].coverage == 1.0
    assert evidence.objects[1].coverage == pytest.approx(0.25)  # only "price" of 4 terms


def test_sources_are_kept_apart_from_objects(bundle: Path) -> None:
    evidence = rank_bundle_objects(REFERENCE, bundle)
    assert all(o.kind != "sources" for o in evidence.objects)
    assert evidence.sources[0].object_id == "sources/es2015a"
    assert evidence.sources[0].coverage == pytest.approx(0.75)  # "selling" is absent


def test_meeting_id_limits_the_sources(bundle: Path) -> None:
    evidence = rank_bundle_objects(REFERENCE, bundle, meeting_id="ES2015b")
    assert [s.object_id for s in evidence.sources] == ["sources/es2015b"]


def test_retrieved_flag_follows_the_given_ids(bundle: Path) -> None:
    evidence = rank_bundle_objects(REFERENCE, bundle, retrieved_ids=["events/talk"])
    flags = {o.object_id: o.retrieved for o in evidence.objects}
    assert flags == {"decisions/price": False, "events/talk": True, "concepts/market": False}


def test_front_matter_does_not_count(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(root, "decisions/d", "nothing relevant", front="description: selling price twenty")
    (root / "sources").mkdir()
    evidence = rank_bundle_objects(REFERENCE, root)
    assert evidence.objects[0].coverage == 0.0


def test_lexical_proxy_does_not_see_numerals(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write(root, "decisions/d", "Selling price is 25 Euros")
    evidence = rank_bundle_objects("Twenty-five Euros", root)
    assert evidence.objects[0].coverage < 1.0  # "25" vs "twenty-five" is the known caveat


def test_missing_bundle_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rank_bundle_objects(REFERENCE, tmp_path / "nope")


def test_bundle_dir_for_follows_extraction_series_and_run(tmp_path: Path) -> None:
    assert bundle_dir_for("extr", "ES2015", 1, base_dir=tmp_path) == (
        tmp_path / "extr" / "ES2015" / "run-1" / "bundle"
    )


def test_bundle_resolver_accepts_several_series_and_rejects_others(tmp_path: Path) -> None:
    manifest = {"c2_extraction": "extr", "series": ["ES2015", "IS1003"]}
    resolve = bundle_resolver(manifest, base_dir=tmp_path)
    assert resolve("IS1003", 0) == tmp_path / "extr" / "IS1003" / "run-0" / "bundle"
    with pytest.raises(ValueError, match="TS3009"):
        resolve("TS3009", 0)
    with pytest.raises(ValueError, match="c2_extraction"):
        bundle_resolver({"series": ["ES2015"]}, base_dir=tmp_path)


def test_worksheet_reads_the_bundle_of_each_series(tmp_path: Path) -> None:
    manifest = {"c2_extraction": "extr", "series": ["ES2015", "IS1003"]}
    _write(
        bundle_dir_for("extr", "ES2015", 0, base_dir=tmp_path),
        "decisions/es-price",
        "The selling price is twenty Euros.",
    )
    _write(
        bundle_dir_for("extr", "IS1003", 0, base_dir=tmp_path),
        "decisions/is-price",
        "The selling price is twenty Euros.",
    )
    questions = {
        "ES2015.q1": _question("ES2015.q1", REFERENCE, QuestionStratum.E1_POINT_FACT),
        "IS1003.q1": _question("IS1003.q1", REFERENCE, QuestionStratum.E1_POINT_FACT).model_copy(
            update={"series_id": "IS1003"}
        ),
    }
    records = [
        _record("ES2015.q1", "E1_point_fact", ["concepts/market"], correct=False),
        _record("IS1003.q1", "E1_point_fact", ["concepts/market"], correct=False),
    ]
    rows = oe4_worksheet_rows(records, questions, bundle_resolver(manifest, base_dir=tmp_path))
    assert {r["pregunta_id"]: r["mejor_objeto"] for r in rows} == {
        "ES2015.q1": "decisions/es-price",
        "IS1003.q1": "decisions/is-price",
    }


def _question(qid: str, reference: str, stratum: QuestionStratum) -> Question:
    return Question(
        id=qid,
        series_id="ES2015",
        stratum=stratum,
        text=f"text {qid}",
        reference_answer=reference,
        reference_evidence=(EvidenceSpan(meeting_id="ES2015a", dialogue_act_ids=("a1",)),),
    )


def _record(
    qid: str,
    stratum: str,
    ids: list[str],
    *,
    correct: bool,
    condition: str = "C2",
    run: int = 0,
    text: str | None = None,
) -> dict[str, Any]:
    blocks = [
        {"index": i, "concept_id": c, "text": f"[concept_id: {c} — T]\n# T\n\nmarket"}
        for i, c in enumerate(ids, start=1)
    ]
    return {
        "question_id": qid,
        "condition": condition,
        "run": run,
        "stratum": stratum,
        "verdict": {"correct": correct},
        "answer": {"text": text or f"answer {qid}", "abstained": False},
        "trace": {"outcome": "answered", "context_blocks": blocks},
    }


@pytest.fixture
def scenario() -> tuple[list[dict[str, Any]], dict[str, Question]]:
    questions = {
        "ES2015.q1": _question("ES2015.q1", REFERENCE, QuestionStratum.E1_POINT_FACT),
        "ES2015.q2": _question("ES2015.q2", "young adults market", QuestionStratum.E1_POINT_FACT),
        "ES2015.q3": _question("ES2015.q3", REFERENCE, QuestionStratum.E1_POINT_FACT),
        "ES2015.q4": _question("ES2015.q4", REFERENCE, QuestionStratum.E2_CURRENT_STATE),
    }
    records = [
        _record("ES2015.q1", "E1_point_fact", ["concepts/market"], correct=False),
        # q2: the whole reference is visible in the retrieved text -> synthesis by rule, skipped
        _record("ES2015.q2", "E1_point_fact", ["concepts/market"], correct=False),
        _record("ES2015.q3", "E1_point_fact", ["concepts/market"], correct=True),
        _record("ES2015.q4", "E2_current_state", ["concepts/market"], correct=False),
    ]
    records[1]["trace"]["context_blocks"][0]["text"] += " young adults"
    return records, questions


def test_worksheet_lists_only_unlabeled_e1_failures(
    bundle: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    records, questions = scenario
    rows = oe4_worksheet_rows(records, questions, bundle)
    assert [r["pregunta_id"] for r in rows] == ["ES2015.q1"]
    row = rows[0]
    assert set(row) == set(WORKSHEET_COLUMNS)
    assert row["respuesta_referencia"] == REFERENCE
    assert row["respuesta_c2"] == "answer ES2015.q1"
    assert row["mejor_objeto"] == "decisions/price"
    assert row["mejor_objeto_recuperado"] == "no"
    assert "decisions/price (1.00, no recuperado)" in row["objetos_de_la_base"]
    assert row["mejor_fuente"] == "sources/es2015a (0.75)"
    assert row["pista_automatica"]


def test_worksheet_carries_the_object_texts_so_it_is_self_contained(
    bundle: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    records, questions = scenario
    (row,) = oe4_worksheet_rows(records, questions, bundle)
    assert row["mejor_objeto_texto"].endswith("The selling price is twenty Euros.")
    parts = row["objetos_de_la_base_texto"].split(" || ")
    assert [p.split(": ", 1)[0] for p in parts] == [
        "decisions/price",
        "events/talk",
        "concepts/market",
    ]
    assert "The selling price is twenty Euros." in parts[0]
    assert "Price talk and market." in parts[1]
    assert "---" not in row["mejor_objeto_texto"]  # front matter is not shown
    assert row["mejor_fuente_fragmento"] == "Price twenty Euros market young adults for the remote."


def test_worksheet_texts_are_empty_without_objects_and_sources(
    tmp_path: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    records, questions = scenario
    empty = tmp_path / "empty"
    empty.mkdir()
    (row,) = oe4_worksheet_rows(records, questions, empty)
    assert row["mejor_objeto_texto"] == ""
    assert row["objetos_de_la_base_texto"] == ""
    assert row["mejor_fuente_fragmento"] == ""


def test_source_fragment_is_the_passage_with_most_coverage_and_is_capped(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    filler = "Unrelated chatter about animals.\n\n" * 3
    _write(root, "sources/es2015a", filler + "Selling price twenty Euros. " + "x " * 400 + "\n")
    (root / "decisions").mkdir()
    records = [_record("ES2015.q1", "E1_point_fact", ["concepts/market"], correct=False)]
    questions = {"ES2015.q1": _question("ES2015.q1", REFERENCE, QuestionStratum.E1_POINT_FACT)}
    (row,) = oe4_worksheet_rows(records, questions, root)
    fragment = row["mejor_fuente_fragmento"]
    assert fragment.startswith("Selling price twenty Euros.")
    assert len(fragment) <= 600


def test_worksheet_keeps_one_row_per_question_and_run_of_c2_only(
    bundle: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    _, questions = scenario
    records = [
        _record("ES2015.q1", "E1_point_fact", ["concepts/market"], correct=False, run=run, **kw)
        for run in (0, 1)
        for kw in (
            {"condition": "C2", "text": f"c2 run {run}"},
            {"condition": "C1", "text": f"c1 run {run}"},
        )
    ]
    rows = oe4_worksheet_rows(records, questions, bundle)
    assert [(r["pregunta_id"], r["corrida"]) for r in rows] == [
        ("ES2015.q1", "0"),
        ("ES2015.q1", "1"),
    ]
    assert [r["respuesta_c2"] for r in rows] == ["c2 run 0", "c2 run 1"]


def test_worksheet_can_include_failures_the_rule_attributes(
    bundle: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    records, questions = scenario
    rows = oe4_worksheet_rows(records, questions, bundle, include_rule_attributed=True)
    assert [r["pregunta_id"] for r in rows] == ["ES2015.q1", "ES2015.q2"]
    assert all(r["etapa_humana"] == "" and r["nota"] == "" for r in rows)


def test_worksheet_never_fills_the_label(
    bundle: Path, scenario: tuple[list[dict[str, Any]], dict[str, Question]]
) -> None:
    records, questions = scenario
    for row in oe4_worksheet_rows(records, questions, bundle):
        assert row["etapa_humana"] == ""
        assert row["nota"] == ""
    assert ETAPA_VALUES == ("extraccion", "recuperacion", "sintesis")


def test_write_refuses_to_erase_labels(tmp_path: Path) -> None:
    path = tmp_path / "hoja.csv"
    blank = {c: "" for c in WORKSHEET_COLUMNS}
    write_oe4_worksheet(path, [{**blank, "pregunta_id": "ES2015.q1"}])
    labeled = path.read_text(encoding="utf-8").replace(",,\n", ",extraccion,\n", 1)
    path.write_text(labeled, encoding="utf-8")
    with pytest.raises(WorksheetLabeledError):
        write_oe4_worksheet(path, [{**blank, "pregunta_id": "ES2015.q1"}])
    write_oe4_worksheet(path, [{**blank, "pregunta_id": "ES2015.q1"}], force=True)
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(WORKSHEET_COLUMNS)


def test_worksheet_round_trips_through_the_reader(tmp_path: Path) -> None:
    path = tmp_path / "hoja.csv"
    blank = {c: "" for c in WORKSHEET_COLUMNS}
    row = {**blank, "pregunta_id": "ES2015.q1", "respuesta_c2": 'dice "sí", y más'}
    write_oe4_worksheet(path, [row])
    assert read_worksheet_rows(path) == [row]


def test_count_stages_adds_rule_stages_to_human_labels() -> None:
    sheet = [
        {"pregunta_id": "ES2015.q1", "etapa_humana": "recuperacion"},
        {"pregunta_id": "ES2015.q2", "etapa_humana": " extraccion "},
        {"pregunta_id": "ES2015.q3", "etapa_humana": "recuperacion"},
    ]
    assert count_stages(["sintesis"], sheet) == {
        "extraccion": 1,
        "recuperacion": 2,
        "sintesis": 1,
    }


def test_count_stages_rejects_unlabeled_or_unknown_rows() -> None:
    with pytest.raises(ValueError, match=r"ES2015\.q1"):
        count_stages([], [{"pregunta_id": "ES2015.q1", "etapa_humana": ""}])
    with pytest.raises(ValueError, match=r"ES2015\.q2"):
        count_stages([], [{"pregunta_id": "ES2015.q2", "etapa_humana": "otra"}])


def test_stage_shares_gives_count_and_fraction_per_stage_in_the_given_order() -> None:
    shares = stage_shares({"recuperacion": 4, "extraccion": 3, "sintesis": 2})
    assert list(shares.index) == ["recuperacion", "extraccion", "sintesis"]
    assert list(shares["cases"]) == [4, 3, 2]
    assert shares.loc["recuperacion", "share"] == pytest.approx(4 / 9)
    assert shares["share"].sum() == pytest.approx(1.0)


def test_stage_shares_of_no_failures_is_all_zero_not_a_division_error() -> None:
    shares = stage_shares({"recuperacion": 0, "extraccion": 0, "sintesis": 0})
    assert list(shares["share"]) == [0.0, 0.0, 0.0]


def test_rule_attributed_failures_are_the_e1_failures_the_worksheet_leaves_out(
    scenario: tuple[list[dict[str, Any]], dict[str, Question]],
) -> None:
    records, questions = scenario
    second_run = [{**r, "run": 1} for r in records if r["question_id"] == "ES2015.q2"]
    c1_noise = [{**records[1], "condition": "C1"}]
    found = rule_attributed_failures([*records, *second_run, *c1_noise], questions)
    assert found == [("ES2015.q2", 0), ("ES2015.q2", 1)]
