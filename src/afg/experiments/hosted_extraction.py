"""Configuration and preflight of the hosted-extractor extension of Experiment A (ADR 0026).

``config/hosted_extraction.toml`` lists the paid models, the shared OpenKOS settings and the
comparison parameters. It lives apart from ``config/experiments.toml`` on purpose: that file is
hashed by ``config/freeze.json``. Nothing here calls a model; the preflight only reads local
state (the executable, its version, the environment and the local Ollama model list).

The API key is read by OpenKOS itself from ``OPENKOS_OPENAI_API_KEY``. This module only checks
that the variable is set; it never reads its value into a message, a file or a manifest.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from afg.extraction.openkos.capabilities import parse_version
from afg.extraction.openkos.commands import CommandRunner
from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.shared.paths import CONFIG_DIR, PROJECT_ROOT

__all__ = [
    "API_KEY_ENV",
    "EXECUTABLE_ENV",
    "HOSTED_ADR",
    "HOSTED_CONFIG_PATH",
    "BridgeSpec",
    "ComparisonSpec",
    "HostedConfig",
    "HostedConfigError",
    "HostedPreflightError",
    "LocalBaselineSpec",
    "ModelPrice",
    "ModelSpec",
    "bridge_run_settings",
    "hosted_manifest",
    "hosted_run_name",
    "hosted_run_settings",
    "load_hosted_config",
    "preflight",
    "resolve_executable",
]

HOSTED_CONFIG_PATH: Path = CONFIG_DIR / "hosted_extraction.toml"
API_KEY_ENV = "OPENKOS_OPENAI_API_KEY"
EXECUTABLE_ENV = "AFG_HOSTED_OPENKOS_EXECUTABLE"
HOSTED_ADR = "0026"
HOSTED_BACKEND = "openai-compatible"
BRIDGE_BACKEND = "ollama"


class HostedConfigError(ValueError):
    """The hosted configuration or a request against it is invalid."""


class HostedPreflightError(RuntimeError):
    """A precondition of a hosted run is not met; raised before any model call."""


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """One paid model: its label (the run-name suffix), provider, API model id and endpoint."""

    label: str
    provider: str
    model: str
    base_url: str


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """Public price of a model: USD per million tokens, with its date and source page."""

    input_usd_per_mtok: float
    output_usd_per_mtok: float
    prices_date: str
    pricing_url: str


@dataclass(frozen=True, slots=True)
class BridgeSpec:
    """The continuity check: ``qwen3:8b`` on OpenKOS 0.7.2, local Ollama backend (historical).

    ``openkos_version`` is the version the stored bridge run was made with; the bridge is only
    re-run when it equals ``HostedConfig.required_version``.
    """

    run_name: str
    series: tuple[str, ...]
    runs: int
    openkos_version: str


@dataclass(frozen=True, slots=True)
class LocalBaselineSpec:
    """The secondary baseline (ADR 0026 amendment): bridge settings, every evaluation series."""

    run_name: str
    model: str
    series_partition: str
    runs: int


@dataclass(frozen=True, slots=True)
class ComparisonSpec:
    """Parameters of the paired comparison (ADR 0026, decision 7)."""

    tau: float
    sensitivity_taus: tuple[float, ...]
    bootstrap_resamples: int
    bootstrap_seed: int
    family_alpha: float
    precision_margin: float


@dataclass(frozen=True, slots=True)
class HostedConfig:
    """``config/hosted_extraction.toml`` as typed values."""

    required_version: str
    ollama_version: str
    """Ollama server version of every local run of the extension (ADR 0026, fourth amendment)."""
    executable: str
    series_partition: str
    runs_per_model: int
    reasoning_effort: str
    max_generation_tokens: int
    evidence_quote: bool
    embedding_base_url: str
    embedding_model: str
    baseline_run_name: str
    baseline_model: str
    bridge: BridgeSpec
    local_baseline: LocalBaselineSpec
    comparison: ComparisonSpec
    models: Mapping[str, ModelSpec]
    prices: Mapping[str, ModelPrice]
    dashboard_usd: Mapping[str, float]


def _load_prices(raw: Mapping[str, Any], models: Mapping[str, ModelSpec]) -> dict[str, ModelPrice]:
    """The ``[prices.<label>]`` tables; an absent table means the price is still unset."""
    prices: dict[str, ModelPrice] = {}
    for label, entry in raw.items():
        if label not in models:
            raise HostedConfigError(f"[prices.{label}] names a model that is not in [models].")
        missing = [
            key
            for key in ("input_usd_per_mtok", "output_usd_per_mtok", "prices_date", "pricing_url")
            if key not in entry
        ]
        if missing:
            raise HostedConfigError(f"[prices.{label}] lacks {', '.join(missing)}.")
        price = ModelPrice(
            input_usd_per_mtok=float(entry["input_usd_per_mtok"]),
            output_usd_per_mtok=float(entry["output_usd_per_mtok"]),
            prices_date=str(entry["prices_date"]),
            pricing_url=str(entry["pricing_url"]),
        )
        if price.input_usd_per_mtok < 0 or price.output_usd_per_mtok < 0:
            raise HostedConfigError(f"[prices.{label}] has a negative price.")
        prices[label] = price
    return prices


def load_hosted_config(path: Path | None = None) -> HostedConfig:
    """Read the hosted configuration (default ``config/hosted_extraction.toml``)."""
    with (path or HOSTED_CONFIG_PATH).open("rb") as handle:
        raw: dict[str, Any] = tomllib.load(handle)
    shared, comparison, bridge = raw["shared"], raw["comparison"], raw["bridge"]
    local = raw["local_baseline"]
    providers = raw["providers"]
    models = {
        label: ModelSpec(
            label=label,
            provider=str(spec["provider"]),
            model=str(spec["model"]),
            base_url=str(providers[spec["provider"]]["base_url"]),
        )
        for label, spec in raw["models"].items()
    }
    return HostedConfig(
        required_version=str(raw["openkos"]["required_version"]),
        ollama_version=str(raw["ollama"]["required_version"]),
        executable=str(raw["openkos"]["executable"]),
        series_partition=str(shared["series_partition"]),
        runs_per_model=int(shared["runs_per_model"]),
        reasoning_effort=str(shared["reasoning_effort"]),
        max_generation_tokens=int(shared["max_generation_tokens"]),
        evidence_quote=bool(shared["evidence_quote"]),
        embedding_base_url=str(shared["embedding_base_url"]),
        embedding_model=str(shared["embedding_model"]),
        baseline_run_name=str(raw["baseline"]["run_name"]),
        baseline_model=str(raw["baseline"]["model"]),
        bridge=BridgeSpec(
            run_name=str(bridge["run_name"]),
            series=tuple(str(s) for s in bridge["series"]),
            runs=int(bridge["runs"]),
            openkos_version=str(bridge["openkos_version"]),
        ),
        local_baseline=LocalBaselineSpec(
            run_name=str(local["run_name"]),
            model=str(local["model"]),
            series_partition=str(local["series_partition"]),
            runs=int(local["runs"]),
        ),
        comparison=ComparisonSpec(
            tau=float(comparison["tau"]),
            sensitivity_taus=tuple(float(t) for t in comparison["sensitivity_taus"]),
            bootstrap_resamples=int(comparison["bootstrap_resamples"]),
            bootstrap_seed=int(comparison["bootstrap_seed"]),
            family_alpha=float(comparison["family_alpha"]),
            precision_margin=float(comparison["precision_margin"]),
        ),
        models=models,
        prices=_load_prices(raw.get("prices", {}), models),
        dashboard_usd={str(k): float(v) for k, v in raw.get("dashboard_usd", {}).items()},
    )


def hosted_run_name(label: str, *, pilot: bool = False) -> str:
    """Run folder of a model: ``experimento-a-hosted-<label>`` (pilot: ``...-piloto-<label>``)."""
    return f"experimento-a-{'piloto' if pilot else 'hosted'}-{label}"


def resolve_executable(config: HostedConfig, env: Mapping[str, str]) -> str:
    """The extension executable: ``AFG_HOSTED_OPENKOS_EXECUTABLE``, else the configured path."""
    override = env.get(EXECUTABLE_ENV)
    if override:
        return override
    path = Path(config.executable)
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def hosted_run_settings(config: HostedConfig, label: str, *, executable: str) -> OpenKosRunSettings:
    """OpenKOS settings of a paid model: provider keys set, seed and temperature unset."""
    spec = config.models.get(label)
    if spec is None:
        raise HostedConfigError(
            f"Unknown model label {label!r}; valid labels: {', '.join(config.models)}."
        )
    return OpenKosRunSettings(
        executable=executable,
        generative_model=spec.model,
        embedding_model=config.embedding_model,
        base_seed=None,
        temperature=None,
        backend=HOSTED_BACKEND,
        base_url=spec.base_url,
        embedding_base_url=config.embedding_base_url,
        reasoning_effort=config.reasoning_effort,
        max_generation_tokens=config.max_generation_tokens,
        evidence_quote=config.evidence_quote,
    )


def bridge_run_settings(formal: OpenKosRunSettings, *, executable: str) -> OpenKosRunSettings:
    """The formal settings (model, seed, temperature) on ``executable``, Ollama backend."""
    return replace(formal, executable=executable, backend=BRIDGE_BACKEND)


def hosted_manifest(
    config: HostedConfig,
    *,
    run_name: str,
    label: str | None,
    series_ids: Sequence[str],
    n_runs: int,
    settings: OpenKosRunSettings,
    pilot: bool,
    git_commit: str | None,
    git_dirty: bool | None,
    ollama_version: str | None,
    local_model_digests: Mapping[str, str] | None = None,
    local_baseline: bool = False,
) -> dict[str, Any]:
    """The opening manifest of a hosted (bridge or secondary-baseline) run directory.

    Same layout as an ``a-batch`` manifest, so ``a-report`` reads it unchanged, plus the ADR 0026
    markers: ``extension`` (which makes the report descriptive-only), provider, model, endpoint
    and OpenKOS version. It never holds the API key and records no freeze (the run is not frozen).
    """
    spec = config.models[label] if label is not None else None
    return {
        "schema_version": 1,
        "run_name": run_name,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "series": ",".join(series_ids),
        "partition": config.series_partition,
        "runs": n_runs,
        "extension": "hosted",
        "adr": HOSTED_ADR,
        "pilot": pilot,
        "bridge": label is None and not local_baseline,
        "local_baseline": local_baseline,
        "model_label": label,
        "ollama_version": ollama_version,
        "provider": spec.provider if spec else "ollama",
        "baseline_run_name": config.baseline_run_name,
        "openkos": {
            "executable": settings.executable,
            "required_version": config.required_version,
            "generative_model": settings.generative_model,
            "embedding_model": settings.embedding_model,
            "backend": settings.backend,
            "base_url": settings.base_url,
            "embedding_base_url": settings.embedding_base_url,
            "reasoning_effort": settings.reasoning_effort,
            "max_generation_tokens": settings.max_generation_tokens,
            "evidence_quote": settings.evidence_quote,
            "seed": settings.base_seed,
            "temperature": settings.temperature,
            "versions": [],
            "local_model_digests": dict(local_model_digests or {}),
        },
        "freeze": None,
        "status": "running",
    }


def _tagged(name: str) -> str:
    last = name.rsplit("/", 1)[-1]
    return name if ":" in last else f"{name}:latest"


def preflight(
    config: HostedConfig,
    *,
    label: str | None,
    executable: str,
    runner: CommandRunner,
    env: Mapping[str, str],
    ollama_models: Callable[[], Mapping[str, str] | None],
    ollama_version: Callable[[], str | None],
    executable_exists: Callable[[str], bool],
    bridge_model: str | None = None,
) -> None:
    """Check everything a run needs before the first model call.

    ``label`` is a paid model, or ``None`` for the bridge (then ``bridge_model`` is the local
    generative model it needs). Raises :class:`HostedPreflightError` naming what is missing;
    the API key is only ever named by its variable, never shown.
    """
    if label is not None and label not in config.models:
        raise HostedConfigError(
            f"Unknown model label {label!r}; valid labels: {', '.join(config.models)}."
        )
    if not executable_exists(executable):
        raise HostedPreflightError(
            f"The OpenKOS {config.required_version} executable was not found at {executable}. "
            f"Install it apart from the frozen one, or set {EXECUTABLE_ENV}."
        )
    try:
        done = runner.run([executable, "--version"])
    except OSError as exc:
        raise HostedPreflightError(f"{executable} could not be run: {exc}") from exc
    version = parse_version(done.stdout) if done.returncode == 0 else None
    if version != config.required_version:
        raise HostedPreflightError(
            f"{executable} reports OpenKOS {version or 'unknown'}; this extension needs "
            f"{config.required_version} (ADR {HOSTED_ADR})."
        )
    if label is not None and not env.get(API_KEY_ENV):
        raise HostedPreflightError(
            f"The environment variable {API_KEY_ENV} is not set. Export the key of the provider "
            f"of {label!r} before the run; it is never written to a file."
        )
    served = ollama_version()
    if served != config.ollama_version:
        raise HostedPreflightError(
            f"The local server reports Ollama {served or 'unknown'}; this extension needs "
            f"{config.ollama_version} (ADR {HOSTED_ADR}, fourth amendment)."
        )
    installed = ollama_models()
    if installed is None:
        raise HostedPreflightError(
            "The local Ollama did not answer: embeddings (and the bridge model) need it."
        )
    have = {_tagged(name) for name in installed}
    needed = [config.embedding_model, *([bridge_model] if bridge_model else [])]
    missing = [name for name in needed if _tagged(name) not in have]
    if missing:
        raise HostedPreflightError(
            f"Ollama lacks {', '.join(missing)}; pull what is missing before the run."
        )
