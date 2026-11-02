"""Guard that refuses to run a command when the model environment differs from the pinned one.

``config/experiments.toml`` ``[pinned_environment]`` fixes the Ollama and OpenKOS versions and the
content digest of every model. A command that calls models runs :func:`check_pinned_environment`
before its first call: any difference (model missing, digest changed, version changed, model
without a pin, probe unavailable) stops it with every mismatch listed. There is no bypass; a
changed pin is a reviewed edit of the config. The returned record goes into the manifest of the
run (``pinned_environment_ok`` and ``pinned_environment``).

OpenKOS is only checked (and recorded) when the command runs it; Ollama is always checked.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from afg.experiments.provenance import ProvenanceProbe, _digest_of, _with_tag
from afg.shared.config import load_experiments_config

SECTION = "pinned_environment"


@dataclass(frozen=True, slots=True)
class PinnedEnvironment:
    """The fixed versions and model digests (keys are the model names of the config)."""

    model_digests: Mapping[str, str]
    ollama_version: str
    openkos_version: str


class PinnedEnvironmentError(Exception):
    """The installed environment differs from the pinned one; ``mismatches`` lists every case."""

    def __init__(self, mismatches: Sequence[str]) -> None:
        self.mismatches = tuple(mismatches)
        super().__init__(
            "El entorno no coincide con `[pinned_environment]` de config/experiments.toml; "
            "no se llamó a ningún modelo:\n" + "\n".join(f"  - {m}" for m in self.mismatches)
        )


def load_pinned_environment(config: Mapping[str, Any] | None = None) -> PinnedEnvironment:
    """The ``[pinned_environment]`` section of the experiments config.

    Raises:
        ValueError: the section or one of its keys is missing or malformed.
    """
    loaded = load_experiments_config() if config is None else config
    section: Any = loaded.get(SECTION)
    try:
        digests: Mapping[str, Any] = section["model_digests"]
        return PinnedEnvironment(
            model_digests={str(k): str(v) for k, v in digests.items()},
            ollama_version=str(section["ollama_version"]),
            openkos_version=str(section["openkos_version"]),
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(
            f"Falta o está mal formada la sección [{SECTION}] de config/experiments.toml "
            "(ollama_version, openkos_version y [pinned_environment.model_digests])."
        ) from exc


def check_pinned_environment(
    probe: ProvenanceProbe,
    *,
    models: Sequence[str],
    needs_openkos: bool,
    pins: PinnedEnvironment | None = None,
) -> dict[str, Any]:
    """Compare the installed environment with the pins; return the manifest record.

    ``models`` are the models the command will call. Raises :class:`PinnedEnvironmentError`
    listing every mismatch.
    """
    pinned = pins if pins is not None else load_pinned_environment()
    pin_by_tag = {_with_tag(name): digest for name, digest in pinned.model_digests.items()}
    installed = probe.model_digests()
    mismatches: list[str] = []
    recorded: dict[str, str] = {}

    for model in dict.fromkeys(models):
        expected = pin_by_tag.get(_with_tag(model))
        if expected is None:
            mismatches.append(f"modelo {model}: sin huella fijada en [{SECTION}.model_digests]")
            continue
        recorded[model] = expected
        if installed is None:
            mismatches.append(f"modelo {model}: no se pudo consultar Ollama")
            continue
        found = _digest_of(model, installed)
        if found is None:
            mismatches.append(f"modelo {model}: no está instalado (huella fijada {expected})")
        elif found != expected:
            mismatches.append(f"modelo {model}: huella instalada {found}, fijada {expected}")

    ollama = probe.ollama_version()
    if ollama != pinned.ollama_version:
        mismatches.append(
            f"versión de Ollama: instalada {ollama or 'no legible'}, fijada {pinned.ollama_version}"
        )
    if needs_openkos:
        openkos = probe.openkos_version()
        if openkos != pinned.openkos_version:
            mismatches.append(
                f"versión de OpenKOS: instalada {openkos or 'no legible'}, fijada "
                f"{pinned.openkos_version}"
            )
    if mismatches:
        raise PinnedEnvironmentError(mismatches)
    return {
        "pinned_environment_ok": True,
        "pinned_environment": {
            "ollama_version": pinned.ollama_version,
            "openkos_version": pinned.openkos_version if needs_openkos else None,
            "model_digests": recorded,
        },
    }
