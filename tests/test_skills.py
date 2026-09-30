"""Tests for skill asset provisioning (``afg skills``): sync, verify and link.

Everything runs against synthetic skills under ``tmp_path``; no real institutional file is
needed and nothing is read from the user's environment.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import afg.cli as afg_cli
from afg.shared.config import Settings
from afg.shared.skills import (
    SkillAssetsError,
    link_skill,
    parse_checksums,
    sha256_of,
    sync_assets,
    verify_installed,
)

runner = CliRunner()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_skill(skills_dir: Path, name: str, files: dict[str, bytes]) -> Path:
    skill = skills_dir / name
    (skill / "assets").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    lines = [f"{_sha(data)}  {fname}" for fname, data in sorted(files.items())]
    (skill / "assets.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return skill


def _make_source(source: Path, skill: str, files: dict[str, bytes]) -> Path:
    folder = source / skill
    folder.mkdir(parents=True)
    for fname, data in files.items():
        (folder / fname).write_bytes(data)
    return folder


FILES = {"a.pptx": b"alpha", "b.docx": b"bravo"}


# --- parse_checksums / sha256_of ---------------------------------------------------------


def test_sha256_of_matches_hashlib(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    assert sha256_of(f) == _sha(b"hello")


def test_parse_checksums_reads_sha256sum_format(tmp_path: Path) -> None:
    f = tmp_path / "assets.sha256"
    f.write_text(f"{_sha(b'1')}  one.bin\n\n{_sha(b'2')}  two.bin\n", encoding="utf-8")
    assert parse_checksums(f) == {"one.bin": _sha(b"1"), "two.bin": _sha(b"2")}


def test_parse_checksums_rejects_malformed_line(tmp_path: Path) -> None:
    f = tmp_path / "assets.sha256"
    f.write_text("not-a-checksum-line\n", encoding="utf-8")
    with pytest.raises(SkillAssetsError, match=r"assets\.sha256"):
        parse_checksums(f)


# --- sync_assets ---------------------------------------------------------------------------


def test_sync_copies_verified_files(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    source = tmp_path / "drive"
    _make_source(source, "demo", FILES)

    copied = sync_assets("demo", source, skills)

    assert sorted(copied) == ["a.pptx", "b.docx"]
    assert (skill / "assets" / "a.pptx").read_bytes() == b"alpha"


def test_sync_accepts_files_directly_in_source(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    source = tmp_path / "flat"
    source.mkdir()
    for fname, data in FILES.items():
        (source / fname).write_bytes(data)

    sync_assets("demo", source, skills)

    assert (skill / "assets" / "b.docx").read_bytes() == b"bravo"


def test_sync_is_idempotent(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill(skills, "demo", FILES)
    source = tmp_path / "drive"
    _make_source(source, "demo", FILES)

    sync_assets("demo", source, skills)
    again = sync_assets("demo", source, skills)

    assert again == []  # nothing left to copy


def test_sync_missing_file_fails_before_copying(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    source = tmp_path / "drive"
    _make_source(source, "demo", {"a.pptx": b"alpha"})

    with pytest.raises(SkillAssetsError, match=r"b\.docx"):
        sync_assets("demo", source, skills)

    assert not (skill / "assets" / "a.pptx").exists()


def test_sync_hash_mismatch_fails_before_copying(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    source = tmp_path / "drive"
    _make_source(source, "demo", {"a.pptx": b"alpha", "b.docx": b"tampered"})

    with pytest.raises(SkillAssetsError, match=r"b\.docx"):
        sync_assets("demo", source, skills)

    assert not (skill / "assets" / "a.pptx").exists()


def test_sync_missing_source_dir(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _make_skill(skills, "demo", FILES)
    with pytest.raises(SkillAssetsError, match="does not exist"):
        sync_assets("demo", tmp_path / "nope", skills)


def test_sync_unknown_skill(tmp_path: Path) -> None:
    with pytest.raises(SkillAssetsError, match="Unknown skill"):
        sync_assets("ghost", tmp_path, tmp_path / "skills")


# --- verify_installed ----------------------------------------------------------------------


def test_verify_installed_ok(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    for fname, data in FILES.items():
        (skill / "assets" / fname).write_bytes(data)
    verify_installed("demo", skills)  # does not raise


def test_verify_installed_reports_missing_and_corrupt(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skill = _make_skill(skills, "demo", FILES)
    (skill / "assets" / "a.pptx").write_bytes(b"corrupt")
    with pytest.raises(SkillAssetsError) as info:
        verify_installed("demo", skills)
    message = str(info.value)
    assert "a.pptx" in message and "b.docx" in message
    assert "make skill-assets" in message


# --- link_skill ----------------------------------------------------------------------------


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_link_creates_relative_symlink_and_excludes_dest(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    skill = _make_skill(repo / ".agents" / "skills", "demo", FILES)
    dest = repo / ".tools" / "skills"

    link = link_skill("demo", dest, repo / ".agents" / "skills", repo)

    assert link.is_symlink()
    assert not Path(link.readlink()).is_absolute()
    assert link.resolve() == skill.resolve()
    exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "/.tools/skills/" in exclude.splitlines()


def test_link_does_not_duplicate_exclude_entry(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    skills = repo / ".agents" / "skills"
    _make_skill(skills, "demo", FILES)
    _make_skill(skills, "other", FILES)
    dest = repo / ".tools" / "skills"

    link_skill("demo", dest, skills, repo)
    link_skill("other", dest, skills, repo)

    exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert exclude.splitlines().count("/.tools/skills/") == 1


def test_link_outside_repo_leaves_exclude_untouched(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    skills = repo / ".agents" / "skills"
    _make_skill(skills, "demo", FILES)
    before = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")

    link = link_skill("demo", tmp_path / "elsewhere", skills, repo)

    assert link.is_symlink()
    assert (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8") == before


def test_link_is_idempotent_for_same_target(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    skills = repo / ".agents" / "skills"
    _make_skill(skills, "demo", FILES)
    dest = repo / ".tools"
    first = link_skill("demo", dest, skills, repo)
    second = link_skill("demo", dest, skills, repo)
    assert first == second and second.is_symlink()


def test_link_refuses_to_overwrite_real_path(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    skills = repo / ".agents" / "skills"
    _make_skill(skills, "demo", FILES)
    dest = repo / ".tools"
    (dest / "demo").mkdir(parents=True)

    with pytest.raises(SkillAssetsError, match="not a symlink"):
        link_skill("demo", dest, skills, repo)


# --- CLI -----------------------------------------------------------------------------------


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    skills = tmp_path / "skills"
    monkeypatch.setattr(afg_cli, "SKILLS_DIR", skills)
    monkeypatch.setattr(afg_cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(afg_cli, "get_settings", lambda: Settings(_env_file=None))
    monkeypatch.delenv("AFG_SKILL_ASSETS_DIR", raising=False)
    _make_skill(skills, "demo", FILES)
    return tmp_path


def test_cli_sync_without_source_is_actionable(cli_env: Path) -> None:
    result = runner.invoke(afg_cli.app, ["skills", "sync-assets", "demo"])
    assert result.exit_code == 1
    assert "AFG_SKILL_ASSETS_DIR" in result.output


def test_cli_sync_and_verify_with_source_option(cli_env: Path) -> None:
    source = cli_env / "drive"
    _make_source(source, "demo", FILES)

    synced = runner.invoke(afg_cli.app, ["skills", "sync-assets", "demo", "--source", str(source)])
    assert synced.exit_code == 0, synced.output

    verified = runner.invoke(afg_cli.app, ["skills", "verify", "demo"])
    assert verified.exit_code == 0, verified.output


def test_cli_sync_uses_setting(cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = cli_env / "drive"
    _make_source(source, "demo", FILES)
    monkeypatch.setattr(
        afg_cli, "get_settings", lambda: Settings(_env_file=None, skill_assets_dir=source)
    )
    result = runner.invoke(afg_cli.app, ["skills", "sync-assets", "demo"])
    assert result.exit_code == 0, result.output


def test_cli_verify_fails_when_assets_missing(cli_env: Path) -> None:
    result = runner.invoke(afg_cli.app, ["skills", "verify", "demo"])
    assert result.exit_code == 1
    assert "make skill-assets" in result.output


def test_cli_link(cli_env: Path) -> None:
    subprocess.run(["git", "init", "-q", str(cli_env)], check=True)
    dest = cli_env / ".tools"
    result = runner.invoke(afg_cli.app, ["skills", "link", "demo", str(dest)])
    assert result.exit_code == 0, result.output
    assert (dest / "demo").is_symlink()
