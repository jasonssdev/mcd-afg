"""``entregada``: a complete, valid series whose files are on ``main`` and unchanged."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest

from afg.annotation.progress import (
    NextKind,
    SeriesState,
    annotator_status,
    is_delivered,
)
from afg.annotation.workspace import (
    WorkspacePaths,
    load_annotation_plan,
    prepare_annotator_workspace,
)
from tests import test_cli_gold_estado as _base
from tests.test_cli_gold_estado import _config, _fill_candidates, _fill_decisions, _use

env = _base.env  # reuse the temporary-workspace fixture

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "commit.gpgsign", "false")
    return root


def _commit(repo: Path, message: str = "x") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


class TestIsDelivered:
    def test_committed_and_unchanged_on_main(self, repo: Path) -> None:
        a, b = repo / "sub" / "a.csv", repo / "sub" / "b.csv"
        a.parent.mkdir()
        a.write_text("1\n", encoding="utf-8")
        b.write_text("2\n", encoding="utf-8")
        _commit(repo)

        assert is_delivered([a, b], ref="main") is True

    def test_not_on_main(self, repo: Path) -> None:
        a = repo / "a.csv"
        a.write_text("1\n", encoding="utf-8")
        _commit(repo)
        b = repo / "b.csv"
        b.write_text("2\n", encoding="utf-8")

        assert is_delivered([a, b]) is False

    def test_modified_locally(self, repo: Path) -> None:
        a = repo / "a.csv"
        a.write_text("1\n", encoding="utf-8")
        _commit(repo)
        a.write_text("changed\n", encoding="utf-8")

        assert is_delivered([a]) is False

    def test_on_another_branch_only(self, repo: Path) -> None:
        (repo / "seed").write_text("s", encoding="utf-8")
        _commit(repo)
        _git(repo, "switch", "-c", "feature")
        a = repo / "a.csv"
        a.write_text("1\n", encoding="utf-8")
        _commit(repo)

        assert is_delivered([a]) is False

    def test_not_a_repository(self, tmp_path: Path) -> None:
        a = tmp_path / "a.csv"
        a.write_text("1\n", encoding="utf-8")

        assert is_delivered([a]) is False

    def test_missing_ref(self, repo: Path) -> None:
        a = repo / "a.csv"
        a.write_text("1\n", encoding="utf-8")
        _commit(repo)

        assert is_delivered([a], ref="nope") is False

    def test_missing_directory_or_empty(self, tmp_path: Path) -> None:
        assert is_delivered([tmp_path / "gone" / "a.csv"]) is False
        assert is_delivered([]) is False

    def test_git_missing(self, repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        a = repo / "a.csv"
        a.write_text("1\n", encoding="utf-8")
        _commit(repo)
        monkeypatch.setenv("PATH", "")

        assert is_delivered([a]) is False


def _ready_status(
    env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch, *, delivered: bool | None
) -> tuple[object, Path, Path]:
    _use(monkeypatch, ["ES1"])
    plan = load_annotation_plan(_config(["ES1"]))
    prepare_annotator_workspace(plan, "gv", paths=env)
    dec = env.decisions_dir / "ES1.decisions.gv.csv"
    cand = env.relations_dir / "ES1.candidates.gv.csv"
    _fill_decisions(dec, "gv")
    _fill_candidates(cand, "gv")
    seen: list[list[Path]] = []

    def fake(paths: Iterable[Path]) -> bool:
        seen.append(list(paths))
        return bool(delivered)

    if delivered is None:
        status = annotator_status(plan, "gv", paths=env)
    else:
        status = annotator_status(plan, "gv", paths=env, delivered=fake)
    return status, dec, cand


class TestDeliveredState:
    def test_default_outside_git_is_ready(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        status, _, _ = _ready_status(env, monkeypatch, delivered=None)
        assert status.series[0].state is SeriesState.READY  # type: ignore[attr-defined]

    def test_complete_and_delivered(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        status, _, _ = _ready_status(env, monkeypatch, delivered=True)
        assert status.series[0].state is SeriesState.DELIVERED  # type: ignore[attr-defined]
        assert SeriesState.DELIVERED.value == "entregada"

    def test_complete_not_delivered(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        status, _, _ = _ready_status(env, monkeypatch, delivered=False)
        assert status.series[0].state is SeriesState.READY  # type: ignore[attr-defined]

    def test_checks_both_target_files(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        _fill_decisions(env.decisions_dir / "ES1.decisions.gv.csv", "gv")
        _fill_candidates(env.relations_dir / "ES1.candidates.gv.csv", "gv")
        seen: list[list[Path]] = []

        def spy(paths: Iterable[Path]) -> bool:
            seen.append(sorted(paths))
            return True

        annotator_status(plan, "gv", paths=env, delivered=spy)

        assert seen == [
            sorted(
                [
                    env.decisions_dir / "ES1.decisions.gv.csv",
                    env.relations_dir / "ES1.candidates.gv.csv",
                ]
            )
        ]

    def test_incomplete_is_never_delivered(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        _fill_decisions(env.decisions_dir / "ES1.decisions.gv.csv", "gv", count=1)

        status = annotator_status(plan, "gv", paths=env, delivered=lambda _p: True)

        assert status.series[0].state is SeriesState.IN_PROGRESS

    def test_adjudicated_takes_precedence(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1"])
        plan = load_annotation_plan(_config(["ES1"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        _fill_decisions(env.decisions_dir / "ES1.decisions.gv.csv", "gv")
        _fill_candidates(env.relations_dir / "ES1.candidates.gv.csv", "gv")
        (env.decisions_dir / "ES1.decisions.adjudicated.csv").write_text("x", encoding="utf-8")
        (env.relations_dir / "ES1.candidates.adjudicated.csv").write_text("x", encoding="utf-8")

        status = annotator_status(plan, "gv", paths=env, delivered=lambda _p: True)

        assert status.series[0].state is SeriesState.ADJUDICATED

    def test_next_action_is_not_deliver(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ready, _, _ = _ready_status(env, monkeypatch, delivered=False)
        assert ready.next_action.kind is NextKind.DELIVER  # type: ignore[attr-defined]

        delivered, _, _ = _ready_status(env, monkeypatch, delivered=True)
        action = delivered.next_action  # type: ignore[attr-defined]
        assert action.kind is not NextKind.DELIVER
        assert action.kind is NextKind.WAIT or action.kind is NextKind.NOTHING
        assert "Entrega" not in action.message

    def test_recall_gating_treats_delivered_as_closed(
        self, env: WorkspacePaths, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use(monkeypatch, ["ES1", "ES3"])
        plan = load_annotation_plan(_config(["ES1", "ES3"]))
        prepare_annotator_workspace(plan, "gv", paths=env)
        _fill_decisions(env.decisions_dir / "ES3.decisions.gv.csv", "gv")
        _fill_candidates(env.relations_dir / "ES3.candidates.gv.csv", "gv")

        status = annotator_status(plan, "gv", paths=env, delivered=lambda _p: True)

        recall = {r.series_id: r.state for r in status.recall}
        assert recall["ES3"] is SeriesState.TO_START
