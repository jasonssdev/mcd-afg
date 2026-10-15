"""Derive the OpenKOS run settings from the project configuration.

Models, seed and temperature come from ``[shared_budget]`` of ``config/experiments.toml``
(the same source the Experiment B runner reads), so the three conditions cannot drift. Only
the executable is a runtime setting (``AFG_OPENKOS_EXECUTABLE``, default ``openkos`` on
``PATH``), because it depends on the machine.
"""

from __future__ import annotations

from afg.extraction.openkos.workspace import OpenKosRunSettings
from afg.shared.config import Settings, get_settings, load_experiments_config


def openkos_run_settings(app_settings: Settings | None = None) -> OpenKosRunSettings:
    """Build :class:`OpenKosRunSettings` from ``config/experiments.toml`` and the environment."""
    budget = load_experiments_config()["shared_budget"]
    resolved = app_settings if app_settings is not None else get_settings()
    return OpenKosRunSettings(
        executable=resolved.openkos_executable,
        generative_model=str(budget["generative_model"]),
        embedding_model=str(budget["embedding_model"]),
        base_seed=int(budget["seed"]),
        temperature=float(budget["temperature"]),
    )
