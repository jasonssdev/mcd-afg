"""The freeze record and the gate that ties evaluation series to it.

The freeze ADR fixes everything a formal run reads. This module keeps that
decision as one small machine-readable file, ``config/freeze.json``, and makes the code obey it:

- :func:`write_freeze_record` writes the record (used once, by ``afg freeze write``, when the
  ADR is closed). It stores the ADR id, the code commit, the SHA-256 of
  ``config/experiments.toml``, of the question bank and of three reference files per series
  (decisions as resolved, relations as resolved, and ``<SERIES>.reference-en.csv``), and the
  ``[pinned_environment]`` values.
- The frozen transcripts (``data/interim/transcripts``, gitignored) are recorded as one manifest
  hash (sorted relative paths and per-file SHA-256, hashed together) plus the file count, so a
  difference names the count and the hash, not hundreds of files. ``config/corpus.toml`` and
  ``config/annotation.toml`` are hashed like ``config/experiments.toml``. Regenerate the
  transcripts with ``afg corpus transcripts --force`` (needs the AMI corpus); the hash must then
  equal the frozen one.
- :func:`freeze_differences` compares the current files with the record and lists every
  difference.
- :func:`gate_partition` is the gate of the commands that read evaluation series. Development
  series pass without a record; evaluation series pass only when the record exists and nothing
  differs; any other series is refused. It runs before the first model call. The live
  environment check (model digests, Ollama and OpenKOS versions) stays in
  :func:`afg.experiments.pinned_environment.check_pinned_environment`, which every command runs
  next with ``[pinned_environment]`` of the config; this gate guarantees that config is the
  frozen one, so the machine is compared with the frozen pins.

JSON, not TOML, because the file is written and read by code only: a person edits nothing in
it, and the standard library writes JSON deterministically (sorted keys) but not TOML.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afg.evaluation.reference import resolve_reference
from afg.evaluation.relations import gold_source
from afg.experiments.pinned_environment import load_pinned_environment
from afg.shared.paths import (
    CONFIG_DIR,
    ENV_PATH,
    EXPERIMENTS_CONFIG_PATH,
    GOLD_DECISIONS_DIR,
    GOLD_RELATIONS_DIR,
    PROJECT_ROOT,
    QUESTIONS_DIR,
    TRANSCRIPTS_DIR,
)

__all__ = [
    "FREEZE_PATH",
    "RESULT_AFFECTING_ENV",
    "FreezeError",
    "FreezeSources",
    "SeriesGateError",
    "build_freeze_record",
    "code_changes_since",
    "freeze_differences",
    "freeze_provenance",
    "gate_partition",
    "manifest_series",
    "read_freeze_record",
    "verify_run_against_freeze",
    "write_freeze_record",
]

FREEZE_PATH: Path = CONFIG_DIR / "freeze.json"
SCHEMA_VERSION = 2
CODE_PATHS = ("src", "pyproject.toml", "uv.lock", ".python-version")
"""What counts as code for the frozen commit: the package, its dependency pins and the Python."""
_TRANSCRIPT_SUFFIXES = frozenset({".md", ".jsonl"})
_REQUIRED_KEYS = (
    "adr",
    "code_commit",
    "experiments_config",
    "question_bank",
    "corpus_config",
    "annotation_config",
    "transcripts",
    "reference",
    "pinned_environment",
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REFERENCE_KINDS = ("decisions", "relations", "reference_en")

RESULT_AFFECTING_ENV = (
    "AFG_EMBEDDING_MODEL",
    "AFG_GENERATIVE_MODEL",
    "AFG_JUDGE_MODEL",
    "AFG_OPENKOS_EXECUTABLE",
    "AFG_SEED",
)
"""``Settings`` variables that change what a run computes; evaluation series refuse them."""

CodeChanges = Callable[[str], list[str]]


class FreezeError(Exception):
    """The record cannot be written or read."""


class SeriesGateError(Exception):
    """The series cannot run; the message says why and lists every difference."""


@dataclass(frozen=True, slots=True)
class FreezeSources:
    """Where the frozen files live; ``root`` makes the recorded paths relative."""

    root: Path = PROJECT_ROOT
    config_path: Path = EXPERIMENTS_CONFIG_PATH
    decisions_dir: Path = GOLD_DECISIONS_DIR
    relations_dir: Path = GOLD_RELATIONS_DIR
    question_bank_path: Path = QUESTIONS_DIR / "banco-preguntas.csv"
    transcripts_dir: Path = TRANSCRIPTS_DIR
    corpus_config_path: Path = CONFIG_DIR / "corpus.toml"
    annotation_config_path: Path = CONFIG_DIR / "annotation.toml"

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def digest(self, path: Path) -> dict[str, str]:
        return {
            "path": self.relative(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def transcripts(self) -> dict[str, Any]:
        """Manifest of the transcripts: path, file count and one hash over all of them.

        The hash covers the sorted relative paths with the SHA-256 of each ``.md``/``.jsonl``
        file, so adding, removing, renaming or editing any file changes it.
        """
        files = (
            sorted(
                p
                for p in self.transcripts_dir.rglob("*")
                if p.is_file() and p.suffix in _TRANSCRIPT_SUFFIXES
            )
            if self.transcripts_dir.is_dir()
            else []
        )
        manifest = hashlib.sha256()
        for path in files:
            name = path.relative_to(self.transcripts_dir).as_posix()
            manifest.update(f"{name}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n".encode())
        return {
            "path": self.relative(self.transcripts_dir),
            "count": len(files),
            "sha256": manifest.hexdigest(),
        }


def _reference_paths(series: str, sources: FreezeSources) -> dict[str, Path]:
    """The three reference files of ``series`` as they resolve today (existence of the
    translation is checked when it is read or hashed).

    Raises:
        FileNotFoundError: no decisions or relations reference.
        ValueError: more than one single-annotator file and no adjudication.
    """
    return {
        "decisions": resolve_reference(series, sources.decisions_dir).path,
        "relations": gold_source(series, sources.relations_dir).path,
        "reference_en": sources.decisions_dir / f"{series}.reference-en.csv",
    }


def _pins(config_path: Path) -> dict[str, Any]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    pins = load_pinned_environment(config)
    return {
        "ollama_version": pins.ollama_version,
        "openkos_version": pins.openkos_version,
        "model_digests": dict(sorted(pins.model_digests.items())),
    }


def build_freeze_record(
    sources: FreezeSources, *, series: Iterable[str], adr: str, commit: str
) -> dict[str, Any]:
    """The record for ``series`` as the files are now.

    Raises:
        FreezeError: ``commit`` is not a full hash, a reference file is missing or ambiguous,
            or a frozen file or the pins cannot be read.
    """
    if not _COMMIT.match(commit):
        raise FreezeError(f"commit debe ser el hash completo de 40 caracteres, no {commit!r}.")
    reference: dict[str, Any] = {}
    problems: list[str] = []
    for name in sorted(set(series)):
        try:
            reference[name] = {
                kind: sources.digest(path) for kind, path in _reference_paths(name, sources).items()
            }
        except (OSError, ValueError) as exc:
            problems.append(f"{name}: {exc}")
    if problems:
        raise FreezeError(
            "No se puede congelar; la referencia está incompleta:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )
    transcripts = sources.transcripts()
    if transcripts["count"] == 0:
        raise FreezeError(
            f"No se puede congelar: no hay transcripciones en {transcripts['path']}. "
            "Se generan con `afg corpus transcripts`."
        )
    try:
        return {
            "schema_version": SCHEMA_VERSION,
            "adr": adr,
            "code_commit": commit,
            "experiments_config": sources.digest(sources.config_path),
            "question_bank": sources.digest(sources.question_bank_path),
            "corpus_config": sources.digest(sources.corpus_config_path),
            "annotation_config": sources.digest(sources.annotation_config_path),
            "transcripts": transcripts,
            "reference": reference,
            "pinned_environment": _pins(sources.config_path),
        }
    except (OSError, ValueError) as exc:
        raise FreezeError(f"No se puede congelar: {exc}") from exc


def write_freeze_record(
    path: Path, sources: FreezeSources, *, series: Iterable[str], adr: str, commit: str
) -> dict[str, Any]:
    """Write the record to ``path``; an existing record is never overwritten.

    Raises:
        FreezeError: the record exists (a frozen decision changes only with a new ADR) or
            cannot be built.
    """
    if path.exists():
        raise FreezeError(
            f"Ya existe {path.name}: lo congelado no se cambia sin un ADR nuevo. "
            "Si el registro es un borrador sin fusionar, bórralo y vuelve a escribirlo."
        )
    record = build_freeze_record(sources, series=series, adr=adr, commit=commit)
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def read_freeze_record(path: Path) -> dict[str, Any]:
    """The record at ``path``.

    Raises:
        FreezeError: the file is missing, is not JSON or lacks a required key.
    """
    if not path.is_file():
        raise FreezeError(f"no existe el registro de congelamiento {path.name} ({path})")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        missing = [key for key in _REQUIRED_KEYS if key not in record]
        if missing:
            raise FreezeError(
                f"El registro de congelamiento {path.name} está mal formado: falta "
                f"{', '.join(missing)} (un registro de esquema anterior no sirve; se escribe "
                "de nuevo con el ADR de congelamiento vigente)."
            )
        record["reference"].items()
        record["pinned_environment"]["model_digests"]
        record["transcripts"]["count"]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise FreezeError(f"El registro de congelamiento {path.name} está mal formado.") from exc
    return record


def freeze_provenance(path: Path = FREEZE_PATH) -> dict[str, Any] | None:
    """``{adr, code_commit, sha256}`` of the record at ``path`` for a run manifest.

    ``None`` when there is no record (development runs before the freeze). The hash is of the
    file bytes, so it identifies the exact record a run was made under.
    """
    if not path.is_file():
        return None
    raw = path.read_bytes()
    try:
        record = json.loads(raw)
    except ValueError:
        record = {}
    return {
        "adr": record.get("adr"),
        "code_commit": record.get("code_commit"),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def code_changes_since(
    commit: str, root: Path = PROJECT_ROOT, *, until: str | None = None
) -> list[str]:
    """Code files (``src``, ``pyproject.toml``, ``uv.lock``) that differ from ``commit``.

    Compares the working tree, so uncommitted edits count, or the commit ``until`` when given.
    An unknown commit or no git raises :class:`FreezeError`.
    """
    span = [commit] if until is None else [commit, until]
    try:
        done = subprocess.run(
            ["git", "diff", "--name-only", *span, "--", *CODE_PATHS],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise FreezeError(f"no se pudo comparar el código con el commit {commit[:7]}") from exc
    return [line for line in done.stdout.splitlines() if line]


def manifest_series(manifest: Mapping[str, Any]) -> list[str]:
    """Series of a run manifest: a list (Experiment B) or a comma-separated string (A)."""
    series = manifest.get("series") or []
    if isinstance(series, str):
        series = series.split(",")
    return [str(s).strip() for s in series if str(s).strip()]


def verify_run_against_freeze(
    manifest: Mapping[str, Any],
    record: Mapping[str, Any],
    *,
    check_questions: bool = True,
    code_changes: Callable[[str, str], list[str]] | None = None,
) -> list[str]:
    """Differences between a finished run's manifest and the freeze record (empty: it matches).

    The run must have used the frozen question bank (``check_questions``, for the runs that read
    questions), a clean git tree, and the frozen code: its commit is the frozen one or differs
    from it in no code file (``code_changes(frozen, run)``, by default ``git diff``), so a later
    commit that only adds the record itself or docs still matches.
    """
    found: list[str] = []
    if check_questions:
        frozen_bank = record["question_bank"]["sha256"]
        used = manifest.get("questions_sha256")
        if used != frozen_bank:
            found.append(
                f"banco de preguntas: la corrida usó la huella {used or 'desconocida'}, "
                f"congelada {frozen_bank}"
            )
    if manifest.get("git_dirty") is not False:
        found.append(
            "árbol de trabajo: la corrida se hizo con cambios sin confirmar o no registró "
            f"su estado (git_dirty = {manifest.get('git_dirty')})"
        )
    frozen = str(record["code_commit"])
    commit = manifest.get("git_commit")
    if commit != frozen:
        if not commit:
            found.append(f"código: la corrida no registró su commit, congelado {frozen[:7]}")
        else:
            try:
                changed = (code_changes or (lambda a, b: code_changes_since(a, until=b)))(
                    frozen, str(commit)
                )
            except FreezeError as exc:
                found.append(f"código: {exc}")
            else:
                if changed:
                    found.append(
                        f"código: la corrida se hizo en {str(commit)[:7]}, que difiere del commit "
                        f"congelado {frozen[:7]} ({', '.join(changed)})"
                    )
    return found


def _compare(
    label: str, recorded: Mapping[str, str], current: Mapping[str, str] | None
) -> str | None:
    if current is None:
        return f"{label}: {recorded['path']} no existe (huella congelada {recorded['sha256']})"
    if current["path"] != recorded["path"]:
        return f"{label}: el archivo ahora es {current['path']}, congelado {recorded['path']}"
    if current["sha256"] != recorded["sha256"]:
        return (
            f"{label} ({recorded['path']}): huella actual {current['sha256']}, "
            f"congelada {recorded['sha256']}"
        )
    return None


def _digest_or_none(sources: FreezeSources, path: Path) -> dict[str, str] | None:
    return sources.digest(path) if path.is_file() else None


def freeze_differences(
    record: Mapping[str, Any],
    sources: FreezeSources,
    *,
    questions_path: Path | None = None,
    code_changes: CodeChanges | None = None,
) -> list[str]:
    """Every difference between the files now and the record; empty when all match.

    ``questions_path`` is the question file a command was given: its content must be the
    frozen bank (by hash, whatever its name). Without it the bank is read from where it was
    recorded.
    """
    found: list[str] = []

    def add(message: str | None) -> None:
        if message:
            found.append(message)

    for label, key, path in (
        ("config/experiments.toml", "experiments_config", sources.config_path),
        ("config/corpus.toml", "corpus_config", sources.corpus_config_path),
        ("config/annotation.toml", "annotation_config", sources.annotation_config_path),
    ):
        add(_compare(label, record[key], _digest_or_none(sources, path)))
    frozen_transcripts = record["transcripts"]
    transcripts = sources.transcripts()
    if (transcripts["count"], transcripts["sha256"]) != (
        frozen_transcripts["count"],
        frozen_transcripts["sha256"],
    ):
        found.append(
            f"transcripciones ({frozen_transcripts['path']}): {transcripts['count']} archivos, "
            f"huella actual {transcripts['sha256']}; congelados {frozen_transcripts['count']}, "
            f"huella congelada {frozen_transcripts['sha256']}. Se regeneran con "
            "`afg corpus transcripts --force`."
        )
    try:
        current_pins = _pins(sources.config_path)
    except (OSError, ValueError) as exc:
        found.append(f"[pinned_environment]: no se pudo leer ({exc})")
    else:
        frozen = record["pinned_environment"]
        for key in ("ollama_version", "openkos_version"):
            if current_pins[key] != frozen.get(key):
                found.append(
                    f"[pinned_environment] {key}: actual {current_pins[key]}, "
                    f"congelada {frozen.get(key)}"
                )
        if current_pins["model_digests"] != frozen["model_digests"]:
            for model in sorted(set(current_pins["model_digests"]) | set(frozen["model_digests"])):
                now = current_pins["model_digests"].get(model)
                then = frozen["model_digests"].get(model)
                if now != then:
                    found.append(
                        f"[pinned_environment] modelo {model}: actual {now}, congelada {then}"
                    )

    bank_path = questions_path or (sources.root / record["question_bank"]["path"])
    bank = _digest_or_none(sources, bank_path)
    if bank is not None and questions_path is not None:
        bank = {**bank, "path": record["question_bank"]["path"]}
    add(_compare("question_bank", record["question_bank"], bank))

    for series, recorded in sorted(record["reference"].items()):
        try:
            paths = _reference_paths(series, sources)
        except (OSError, ValueError) as exc:
            found.append(f"{series}: la referencia ya no se resuelve ({exc})")
            continue
        for kind in _REFERENCE_KINDS:
            add(_compare(f"{series} {kind}", recorded[kind], _digest_or_none(sources, paths[kind])))

    commit = str(record["code_commit"])
    try:
        changed = (code_changes or (lambda c: code_changes_since(c, sources.root)))(commit)
    except FreezeError as exc:
        found.append(f"código: {exc}")
    else:
        if changed:
            found.append(
                f"código: cambió desde el commit congelado {commit[:7]} ({', '.join(changed)})"
            )
    return found


def _env_file_names(env_file: Path) -> set[str]:
    """Upper-cased variable names set in a dotenv file (a missing file sets none)."""
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    names = set()
    for line in lines:
        line = line.strip().removeprefix("export ").strip()
        if line and not line.startswith("#") and "=" in line:
            names.add(line.split("=", 1)[0].strip().upper())
    return names


def result_overrides(
    environ: Mapping[str, str] | None = None, env_file: Path | None = None
) -> list[str]:
    """The :data:`RESULT_AFFECTING_ENV` variables set in the environment or the ``.env`` file."""
    names = {k.upper() for k in (os.environ if environ is None else environ)}
    names |= _env_file_names(ENV_PATH if env_file is None else env_file)
    return [name for name in RESULT_AFFECTING_ENV if name in names]


def gate_partition(
    series_ids: Sequence[str],
    partition_of: Callable[[str], str],
    *,
    freeze_path: Path = FREEZE_PATH,
    sources: FreezeSources | None = None,
    questions_path: Path | None = None,
    code_changes: CodeChanges | None = None,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    runs: int | None = None,
    configured_runs: int | None = None,
) -> str:
    """``development``, ``evaluation`` or ``mixed`` when every series may run; else refuse.

    Development series run without a record. A series that is neither development nor
    evaluation never runs. Evaluation series run only when ``freeze_path`` exists, every
    evaluation series is in it and nothing differs from it (:func:`freeze_differences`).
    Evaluation series also refuse the ``AFG_*`` overrides of :data:`RESULT_AFFECTING_ENV`
    (environment or ``.env``) and a ``--runs`` different from ``configured_runs``.

    Raises:
        SeriesGateError: the message says why and lists every difference.
    """
    sources = sources or FreezeSources()
    partitions = {s: partition_of(s) for s in series_ids}
    unassigned = [s for s, p in partitions.items() if p not in ("development", "evaluation")]
    if unassigned:
        raise SeriesGateError(
            f"{', '.join(unassigned)} no pertenece a la partición de desarrollo ni a la de "
            "evaluación de config/corpus.toml; no se llamó a ningún modelo."
        )
    evaluation = [s for s, p in partitions.items() if p == "evaluation"]
    if not evaluation:
        return "development"
    names = ", ".join(evaluation)
    overrides = result_overrides(environ, env_file)
    if overrides:
        raise SeriesGateError(
            f"{names}: serie(s) de evaluación; no corren con variables {', '.join(overrides)} "
            "definidas (entorno o .env): cambian lo que se calcula y el congelamiento no las "
            "cubre. Quítalas; no se llamó a ningún modelo."
        )
    if runs is not None and configured_runs is not None and runs != configured_runs:
        raise SeriesGateError(
            f"{names}: serie(s) de evaluación; --runs {runs} difiere de runs_per_config = "
            f"{configured_runs} de config/experiments.toml. Quita --runs; no se llamó a ningún "
            "modelo."
        )
    try:
        record = read_freeze_record(freeze_path)
    except FreezeError as exc:
        raise SeriesGateError(
            f"{names}: serie(s) de evaluación; solo corren con el registro del ADR de "
            f"congelamiento y {exc}; no se llamó a ningún modelo."
        ) from exc
    problems = freeze_differences(
        record, sources, questions_path=questions_path, code_changes=code_changes
    )
    problems += [
        f"{s}: la serie no está en el registro de congelamiento"
        for s in evaluation
        if s not in record["reference"]
    ]
    if problems:
        raise SeriesGateError(
            f"{names}: serie(s) de evaluación; lo actual no coincide con el congelamiento "
            f"(ADR {record['adr']}, {freeze_path.name}); no se llamó a ningún modelo:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )
    return "evaluation" if len(evaluation) == len(partitions) else "mixed"
