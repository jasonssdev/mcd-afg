"""``afg`` -- command-line entry point for the evaluation harness.

Every command is written to either work or fail with a clear, actionable message when the
AMI corpus has not been downloaded yet -- most commands cannot do anything useful before
paso cero (thesis section 5.0), and they say so instead of crashing with a stack trace.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from afg.annotation.blocking import (
    BLOCKER_VERSION,
    decisions_from_abstractive,
    generate_candidates,
    sample_rejected,
    write_candidate_pairs_csv,
)
from afg.annotation.linking import chronological_candidate_pairs
from afg.bibliography.audit import render_table as render_biblio_table
from afg.bibliography.audit import run_audit
from afg.bibliography.audit import write_csv as write_biblio_csv
from afg.bibliography.library import load_library
from afg.corpus.download import DownloadError, download_annotations
from afg.corpus.inventory import (
    CorpusNotDownloadedError,
    build_inventory,
)
from afg.corpus.inventory import (
    render_table as render_inventory_table,
)
from afg.corpus.inventory import (
    write_csv as write_inventory_csv,
)
from afg.corpus.participants import (
    load_native_language_records,
    load_participants,
)
from afg.corpus.participants import (
    render_table as render_participants_table,
)
from afg.corpus.participants import (
    write_csv as write_participants_csv,
)
from afg.domain.decision import Decision
from afg.shared.config import get_settings, load_corpus_config
from afg.shared.logging import configure_logging, get_logger
from afg.shared.paths import (
    AMI_DIR,
    GOLD_DECISIONS_DIR,
    GOLD_RELATIONS_DIR,
    TABLES_DIR,
    ensure_dirs,
)

console = Console()
logger = get_logger(__name__)

app = typer.Typer(
    name="afg",
    help="Evaluation harness: document RAG vs. compiled decision representations "
    "over the AMI Meeting Corpus (thesis section 5).",
    no_args_is_help=True,
)
corpus_app = typer.Typer(help="AMI corpus download and paso-cero inventory (thesis section 5.0).")
biblio_app = typer.Typer(help="Bibliography coverage and stats (bibliography/refs.bib).")
gold_app = typer.Typer(help="OE1: build the gold decision/relation set (thesis section 3).")
experiment_app = typer.Typer(help="OE2/OE3: run Experiment A / Experiment B (thesis section 3).")

app.add_typer(corpus_app, name="corpus")
app.add_typer(biblio_app, name="biblio")
app.add_typer(gold_app, name="gold")
app.add_typer(experiment_app, name="experiment")


@app.callback()
def main(log_level: str = typer.Option("INFO", help="Logging level.")) -> None:
    configure_logging(log_level)
    ensure_dirs()


# --- corpus -----------------------------------------------------------------------------


@corpus_app.command("download")
def corpus_download(
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Fetch and extract the AMI manual annotations (CC BY 4.0). Prints the licence first."""
    cfg = load_corpus_config()
    licence = cfg["corpus"]["licence"]
    console.print(
        f"[bold]Licence:[/bold] {licence['name']} "
        f"(archive published {licence['archive_published']}; the licence page states no "
        f"effective date)"
    )
    console.print(licence["note"].strip())
    console.print(f"[bold]Source:[/bold] {cfg['corpus']['annotations']['url']}")
    console.print(
        f"[bold]Approximate size:[/bold] {cfg['corpus']['annotations']['approximate_size_mb']} MB"
    )

    if not yes and not typer.confirm("Proceed with download?"):
        console.print("Aborted.")
        raise typer.Exit(code=1)

    try:
        result = download_annotations(AMI_DIR)
    except DownloadError as exc:
        console.print(f"[bold red]Download failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"Downloaded {result.bytes_downloaded} bytes, extracted to {result.extracted_to}")


@corpus_app.command("inventory")
def corpus_inventory() -> None:
    """Paso cero: verify series completeness and count decisions / candidate links."""
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    try:
        inventory = build_inventory(ami_root)
    except CorpusNotDownloadedError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    render_inventory_table(inventory, console)
    out_path = write_inventory_csv(inventory)
    console.print(f"Wrote {out_path}")


@corpus_app.command("participants")
def corpus_participants() -> None:
    """Native/non-native English + role breakdown, corpus-wide and per target series
    (thesis section 5.1 / 6.3)."""
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]AMI corpus not found at {ami_root}. "
            "Run `uv run afg corpus download` first.[/bold red]"
        )
        raise typer.Exit(code=1)

    corpus_wide = load_native_language_records(ami_root)
    series_participants = load_participants(ami_root)
    if not corpus_wide or not series_participants:
        console.print(
            "[yellow]No participants could be loaded from the corpus resources file. "
            "This is expected until the real file layout is confirmed against a "
            "downloaded corpus (see src/afg/corpus/participants.py).[/yellow]"
        )
        raise typer.Exit(code=1)

    render_participants_table(corpus_wide, series_participants, console)
    out_path = write_participants_csv(series_participants)
    console.print(f"Wrote {out_path}")


# --- bibliography -------------------------------------------------------------------------


@biblio_app.command("audit")
def biblio_audit() -> None:
    """Coverage per thesis section, unreviewed preprints, missing/duplicate DOIs."""
    audit = run_audit()
    render_biblio_table(audit, console)
    out_path = write_biblio_csv(audit)
    console.print(f"Wrote {out_path}")


@biblio_app.command("stats")
def biblio_stats() -> None:
    """Counts per thesis section and preprint/peer-reviewed split."""
    entries = load_library()
    console.print(f"Total entries: {len(entries)}")
    by_section: dict[str, int] = {}
    for entry in entries:
        for section in entry.sections:
            by_section[section] = by_section.get(section, 0) + 1
    for section in sorted(by_section):
        console.print(f"  {section}: {by_section[section]}")
    preprints = sum(1 for e in entries if e.is_preprint)
    console.print(f"Preprints (not peer reviewed): {preprints}")
    console.print(f"Peer-reviewed / standard: {len(entries) - preprints}")


# --- gold (OE1) ---------------------------------------------------------------------------


@gold_app.command("build")
def gold_build(
    series: str = typer.Option(..., "--series", help="AMI series id, e.g. IS1004."),
) -> None:
    """Build the Task-A working file for a series (manual de anotacion secciones 2, 3).

    Writes ``data/processed/decisions/<series>.decisions.csv``. IMPORTANT: this is a
    working file for a human annotator, not a finished gold set. ``machine_flags`` are
    triage hints only, never a verdict -- ``status``, ``decision_object``,
    ``decision_content``, ``annotator``, and ``notes`` are always written empty and must be
    filled in by a human (see ``afg.annotation.goldset`` module docstring).
    """
    from afg.annotation.goldset import build_gold_decisions, write_gold_decisions_csv

    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]AMI corpus not found at {ami_root}. "
            "Run `uv run afg corpus download` first.[/bold red]"
        )
        raise typer.Exit(code=1)

    rows = build_gold_decisions(ami_root, series)
    if not rows:
        console.print(
            f"[bold red]No abstractive DECISIONS sentences found for series {series!r} "
            f"under {ami_root}. Check the series id (e.g. 'IS1004') and that the corpus "
            "was extracted correctly.[/bold red]"
        )
        raise typer.Exit(code=1)

    out_path = GOLD_DECISIONS_DIR / f"{series}.decisions.csv"
    write_gold_decisions_csv(rows, out_path)

    per_meeting: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    for row in rows:
        per_meeting[row.meeting_id] = per_meeting.get(row.meeting_id, 0) + 1
        for flag in row.machine_flags.split(";"):
            if flag:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

    console.print(
        f"[bold]Series {series}[/bold]: {len(rows)} decision sentences across "
        f"{len(per_meeting)} meetings."
    )
    for meeting_id in sorted(per_meeting):
        console.print(f"  {meeting_id}: {per_meeting[meeting_id]}")

    console.print(
        "[bold]machine_flags[/bold] are triage hints, NOT a verdict -- status, "
        "decision_object, decision_content, annotator, and notes were written EMPTY for "
        "every row and must be filled in by a human annotator:"
    )
    if flag_counts:
        for flag in sorted(flag_counts):
            console.print(f"  {flag}: {flag_counts[flag]}")
    else:
        console.print("  (none raised)")

    console.print(f"Wrote {out_path}")


@gold_app.command("link")
def gold_link() -> None:
    """Generate cross-meeting relation annotation candidates (thesis sections 3, 5.1)."""
    console.print(
        "[yellow]Requires a built gold decision set (`afg gold build`) as input. "
        "Once decisions exist, use afg.annotation.linking.chronological_candidate_pairs "
        "to generate the candidate list for annotation.[/yellow]"
    )
    raise typer.Exit(code=2)


@gold_app.command("agreement")
def gold_agreement(
    series: str = typer.Option(..., "--series", help="AMI series id, e.g. IS1004."),
) -> None:
    """Compute Cohen's kappa for existence/type/direction, separately (manual section 6).

    Reads every ``data/processed/relations/<series>.candidates.<initials>.csv`` file
    (one per independent annotator) and writes ``reports/tables/<series>.agreement.csv``.
    """
    from afg.annotation.agreement import (
        AgreementInputError,
        compute_series_agreement,
        write_agreement_csv,
    )

    pattern = f"{series}.candidates.*.csv"
    paths = sorted(GOLD_RELATIONS_DIR.glob(pattern))
    if len(paths) < 2:
        console.print(
            f"[bold red]Need at least 2 annotator files matching "
            f"data/processed/relations/{pattern} (found {len(paths)}). Each annotator's "
            f"independent copy should be named <series>.candidates.<initials>.csv, per "
            "manual de anotacion section 6.[/bold red]"
        )
        raise typer.Exit(code=1)
    if len(paths) > 2:
        console.print(
            f"[yellow]Found {len(paths)} annotator files; using the first two "
            f"({paths[0].name}, {paths[1].name}) -- Cohen's kappa is pairwise.[/yellow]"
        )

    try:
        result = compute_series_agreement(paths)
    except AgreementInputError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    out_path = TABLES_DIR / f"{series}.agreement.csv"
    write_agreement_csv(result, out_path)

    console.print(
        f"[bold]Series {series}[/bold]: {result.annotator_a} vs {result.annotator_b} "
        f"({result.n_items} paired items)."
    )
    console.print(
        f"  existence kappa: {result.existence_kappa:.3f} "
        f"({len(result.existence_disagreements)} disagreements)"
    )
    if result.type_kappa is not None:
        console.print(
            f"  type kappa:      {result.type_kappa:.3f} "
            f"({len(result.type_disagreements)} disagreements, over "
            f"{result.n_type_items} pairs both annotators marked as existing links)"
        )
    else:
        console.print(
            "  type kappa:      n/a (no pair was marked as an existing link by both "
            "annotators)"
        )
    console.print(
        f"  direction kappa: {result.direction_kappa:.3f} "
        f"({len(result.direction_disagreements)} disagreements)"
    )
    for axis, disagreements in (
        ("existence", result.existence_disagreements),
        ("type", result.type_disagreements),
        ("direction", result.direction_disagreements),
    ):
        if disagreements:
            console.print(f"  {axis} disagreements (adjudicate): {', '.join(disagreements)}")

    console.print(f"Wrote {out_path}")


@gold_app.command("evidence")
def gold_evidence(
    meeting: str = typer.Option(..., "--meeting", help="AMI meeting id, e.g. IS1004d."),
    term: str = typer.Option(..., "--term", help="Word to search for (case-insensitive)."),
) -> None:
    """Find a term in a meeting's transcript, with context (manual section 3.3).

    The tool an annotator reaches for once a decision row's ``evidence_da_count`` is 0:
    searches every speaker's ``words/<meeting>.<speaker>.words.xml`` for ``term`` as a
    whole word token and prints each hit with surrounding context.
    """
    from afg.annotation.goldset import MeetingNotFoundError, find_term_occurrences

    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]AMI corpus not found at {ami_root}. "
            "Run `uv run afg corpus download` first.[/bold red]"
        )
        raise typer.Exit(code=1)

    try:
        hits = find_term_occurrences(ami_root, meeting, term)
    except MeetingNotFoundError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    if not hits:
        console.print(f"[yellow]No occurrences of {term!r} found for meeting {meeting!r}.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"[bold]{len(hits)} occurrence(s) of {term!r} in {meeting}:[/bold]")
    for hit in hits:
        try:
            source = hit.source_path.relative_to(ami_root)
        except ValueError:
            source = hit.source_path
        console.print(f"\n[bold]{source}[/bold], near {hit.word_id} (speaker {hit.speaker})")
        console.print(f"  {hit.context}")


def _decisions_for_series_or_exit(ami_root: Path, series: str) -> list[Decision]:
    if not ami_root.exists():
        console.print(
            f"[bold red]AMI corpus not found at {ami_root}. "
            "Run `uv run afg corpus download` first.[/bold red]"
        )
        raise typer.Exit(code=1)

    decisions = decisions_from_abstractive(ami_root, series)
    if not decisions:
        console.print(
            f"[bold red]No abstractive DECISIONS sentences found for series {series!r} "
            f"under {ami_root}. Check the series id (e.g. 'IS1004') and that the corpus "
            "was extracted correctly.[/bold red]"
        )
        raise typer.Exit(code=1)
    return decisions


@gold_app.command("candidates")
def gold_candidates(
    series: str = typer.Option(..., "--series", help="AMI series id, e.g. IS1004."),
    threshold: float = typer.Option(
        0.30,
        "--threshold",
        help="Overlap-coefficient blocking threshold (thesis manual section 4).",
    ),
    min_overlap: int = typer.Option(
        2,
        "--min-overlap",
        help="Minimum absolute shared-token count (|A & B|), alongside --threshold.",
    ),
) -> None:
    """Generate cross-meeting candidate decision pairs for human adjudication (Tarea B).

    Provisional: candidates are built from raw abstractive DECISIONS sentences
    (``afg.annotation.blocking.decisions_from_abstractive``), not yet P3's normalised gold
    decisions. Writes ``data/processed/relations/<series>.candidates.csv``.
    """
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    decisions = _decisions_for_series_or_exit(ami_root, series)

    total_pairs = len(chronological_candidate_pairs(decisions))
    candidates = generate_candidates(decisions, threshold=threshold, min_overlap_tokens=min_overlap)
    out_path = GOLD_RELATIONS_DIR / f"{series}.candidates.csv"
    write_candidate_pairs_csv(candidates, out_path)

    pct = (len(candidates) / total_pairs * 100) if total_pairs else 0.0
    console.print(
        f"Series {series}: {total_pairs} pairs considered, {len(candidates)} candidates "
        f"selected ({pct:.1f}%) at threshold={threshold:.2f}, min_overlap={min_overlap}, "
        f"blocker_version={BLOCKER_VERSION}."
    )
    console.print(f"Wrote {out_path}")


@gold_app.command("recall-sample")
def gold_recall_sample(
    series: str = typer.Option(..., "--series", help="AMI series id, e.g. IS1004."),
    n: int = typer.Option(50, "--n", help="Number of rejected pairs to sample."),
    seed: int = typer.Option(42, "--seed", help="Random seed for a reproducible sample."),
    threshold: float = typer.Option(
        0.30,
        "--threshold",
        help="Overlap-coefficient blocking threshold (thesis manual section 4).",
    ),
    min_overlap: int = typer.Option(
        2,
        "--min-overlap",
        help="Minimum absolute shared-token count (|A & B|), alongside --threshold.",
    ),
) -> None:
    """Sample rejected pairs for the blocker recall check (Tarea C).

    Provisional: sampled from raw abstractive DECISIONS sentences, same caveat as
    ``afg gold candidates``. Writes ``data/processed/relations/<series>.recall-sample.csv``.
    """
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    decisions = _decisions_for_series_or_exit(ami_root, series)

    sample = sample_rejected(
        decisions, n=n, seed=seed, threshold=threshold, min_overlap_tokens=min_overlap
    )
    out_path = GOLD_RELATIONS_DIR / f"{series}.recall-sample.csv"
    write_candidate_pairs_csv(sample, out_path)

    console.print(
        f"Series {series}: sampled {len(sample)} rejected pairs (seed={seed}), "
        f"threshold={threshold:.2f}, min_overlap={min_overlap}, "
        f"blocker_version={BLOCKER_VERSION}."
    )
    console.print(f"Wrote {out_path}")


# --- experiment (OE2/OE3) ------------------------------------------------------------------


@experiment_app.command("a")
def experiment_a() -> None:
    """Experiment A: extraction quality vs. gold (OE2). Requires the corpus and gold set."""
    console.print(
        "[yellow]Not yet implemented: requires a working Extractor "
        "(src/afg/extraction/openkos_adapter.py) and the OE1 gold set. "
        "See thesis section 3, OE2.[/yellow]"
    )
    raise typer.Exit(code=2)


@experiment_app.command("b")
def experiment_b() -> None:
    """Experiment B: C1 vs C2 vs C3 over the question bank (OE3). Requires all three
    conditions and the question bank."""
    console.print(
        "[yellow]Not yet implemented: requires all three conditions "
        "(src/afg/conditions/) and the question bank (thesis section 5.5). "
        "See thesis section 3, OE3.[/yellow]"
    )
    raise typer.Exit(code=2)


# --- report ---------------------------------------------------------------------------------


@app.command("report")
def report() -> None:
    """Regenerate reports/tables/*.csv from whatever data is currently available."""
    console.print("Regenerating bibliography audit...")
    biblio_audit()
    console.print(
        "Corpus inventory and experiment reports require the AMI corpus; "
        "run `afg corpus inventory` separately once it is downloaded."
    )


if __name__ == "__main__":
    app()
