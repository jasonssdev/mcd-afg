"""Everything that talks to the OpenKOS instrument (ADR 0003, ADR 0006).

OpenKOS is reached only through its command line, and its version is not pinned: each run
records the version it executed against. Modules:

* :mod:`~afg.extraction.openkos.commands` -- the injectable command runner.
* :mod:`~afg.extraction.openkos.capabilities` -- what the installed executable supports.
* :mod:`~afg.extraction.openkos.workspace` -- one fresh workspace per (series, run).
* :mod:`~afg.extraction.openkos.evidence` -- maps an evidence quote to dialogue act ids.

TODO(T4): reading the compiled bundle back into :class:`~afg.domain.decision.Decision`
objects and an :class:`~afg.extraction.protocol.ExtractionResult` waits for the OpenKOS
release that defines the bundle layout. :func:`run_series_workspace` returns the workspace
path and manifest that reader will consume.
"""
