"""Everything that talks to the OpenKOS instrument (ADR 0003, ADR 0006).

OpenKOS is reached only through its command line, and its version is not pinned: each run
records the version it executed against. Modules:

* :mod:`~afg.extraction.openkos.commands` -- the injectable command runner.
* :mod:`~afg.extraction.openkos.capabilities` -- what the installed executable supports.
* :mod:`~afg.extraction.openkos.workspace` -- one fresh workspace per (series, run).
* :mod:`~afg.extraction.openkos.evidence` -- maps an evidence quote to dialogue act ids.
* :mod:`~afg.extraction.openkos.query` -- ``openkos query --json`` (schema v1): the call, the
  typed report and the checks C2 requires.
* :mod:`~afg.extraction.openkos.bundle_reader` -- reads ``bundle/decisions/*.md`` into
  :class:`~afg.domain.decision.Decision` objects.
"""
