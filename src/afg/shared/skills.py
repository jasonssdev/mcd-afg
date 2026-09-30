"""Provisioning of skill assets that are deliberately not versioned.

A skill under ``.agents/skills/<name>/`` may depend on binary assets (brand manuals, office
templates) that the repository cannot redistribute. The skill ships only a checksum list,
``assets.sha256`` (``sha256sum`` format), and each person copies the files from a locally
synced shared folder with :func:`sync_assets`. Nothing is copied unless every listed file
exists in the source and matches its hash.

:func:`link_skill` exposes a skill to tools that look for skills in another directory,
through a relative symlink whose parent directory is kept out of git via
``.git/info/exclude`` (a local file), so no tool-specific folder name is ever versioned.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

CHECKSUMS_FILE = "assets.sha256"
ASSETS_DIRNAME = "assets"
_CHUNK = 1024 * 1024
_HASH_LENGTH = 64


class SkillAssetsError(Exception):
    """A skill asset operation cannot proceed; the message says what to do next."""


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of ``path``, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    """Parse a ``sha256sum``-style file (``<hash>  <name>``) into ``{name: hash}``."""
    checksums: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        digest, sep, name = line.partition("  ")
        name = name.strip()
        if not sep or not name or len(digest) != _HASH_LENGTH:
            raise SkillAssetsError(
                f"Malformed line {number} in {path}: expected '<sha256>  <filename>'."
            )
        checksums[name] = digest.lower()
    return checksums


def _skill_paths(skill: str, skills_dir: Path) -> tuple[Path, dict[str, str]]:
    skill_dir = skills_dir / skill
    checksums_path = skill_dir / CHECKSUMS_FILE
    if not checksums_path.is_file():
        raise SkillAssetsError(
            f"Unknown skill '{skill}': {checksums_path} not found. "
            f"Available skills live under {skills_dir}."
        )
    return skill_dir, parse_checksums(checksums_path)


def _problems(directory: Path, checksums: dict[str, str]) -> list[str]:
    """Describe every listed file that is missing from, or differs in, ``directory``."""
    problems: list[str] = []
    for name, expected in checksums.items():
        candidate = directory / name
        if not candidate.is_file():
            problems.append(f"missing: {name}")
        elif sha256_of(candidate) != expected:
            problems.append(f"hash mismatch: {name}")
    return problems


def _resolve_source(skill: str, source: Path) -> Path:
    if not source.is_dir():
        raise SkillAssetsError(f"Source directory does not exist: {source}")
    nested = source / skill
    return nested if nested.is_dir() else source


def sync_assets(skill: str, source: Path, skills_dir: Path) -> list[str]:
    """Copy the skill's assets from ``source`` after verifying all of them.

    Files are looked up in ``<source>/<skill>/`` when that folder exists, else directly in
    ``<source>/``. Returns the names copied (already-correct files are skipped, so a second
    run returns an empty list). Raises :class:`SkillAssetsError` before copying anything if
    a file is missing or its hash differs.
    """
    skill_dir, checksums = _skill_paths(skill, skills_dir)
    origin = _resolve_source(skill, source)
    problems = _problems(origin, checksums)
    if problems:
        listing = "\n  ".join(problems)
        raise SkillAssetsError(
            f"Cannot install assets for '{skill}' from {origin}:\n  {listing}\n"
            "Check that the shared folder is fully synced and up to date."
        )
    target = skill_dir / ASSETS_DIRNAME
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name, expected in checksums.items():
        destination = target / name
        if destination.is_file() and sha256_of(destination) == expected:
            continue
        shutil.copyfile(origin / name, destination)
        copied.append(name)
    return copied


def verify_installed(skill: str, skills_dir: Path) -> None:
    """Check the installed assets of a skill against ``assets.sha256``."""
    skill_dir, checksums = _skill_paths(skill, skills_dir)
    problems = _problems(skill_dir / ASSETS_DIRNAME, checksums)
    if problems:
        listing = "\n  ".join(problems)
        raise SkillAssetsError(
            f"Assets of '{skill}' are incomplete or altered:\n  {listing}\n"
            "Run `make skill-assets` to install them."
        )


def _exclude_file(repo_root: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "info/exclude"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SkillAssetsError(
            f"Cannot locate .git/info/exclude for {repo_root}; is it a git repository?"
        ) from error
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else repo_root / path


def _ensure_excluded(dest_dir: Path, repo_root: Path) -> None:
    try:
        relative = dest_dir.relative_to(repo_root)
    except ValueError:
        return  # outside the repository: nothing to exclude
    entry = "/" + relative.as_posix().strip("/") + "/"
    exclude = _exclude_file(repo_root)
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    if entry in existing:
        return
    prefix = "\n" if existing and not exclude.read_text(encoding="utf-8").endswith("\n") else ""
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{entry}\n")


def link_skill(skill: str, dest_dir: Path, skills_dir: Path, repo_root: Path) -> Path:
    """Create ``<dest_dir>/<skill>`` as a relative symlink to the skill directory.

    When ``dest_dir`` is inside ``repo_root`` it is added to ``.git/info/exclude`` (if not
    already there). An existing symlink is replaced; any other existing path is refused.
    """
    skill_dir, _ = _skill_paths(skill, skills_dir)
    skill_dir = skill_dir.resolve()
    dest = dest_dir.resolve()
    if dest == skills_dir.resolve():
        raise SkillAssetsError("The destination is the skills directory itself; pick another.")
    link = dest / skill
    if link.exists() and not link.is_symlink():
        raise SkillAssetsError(f"{link} exists and is not a symlink; refusing to overwrite it.")
    dest.mkdir(parents=True, exist_ok=True)
    _ensure_excluded(dest, repo_root.resolve())
    if link.is_symlink():
        link.unlink()
    link.symlink_to(os.path.relpath(skill_dir, dest))
    return link
