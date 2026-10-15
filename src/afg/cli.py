"""``afg`` -- command-line entry point for the evaluation harness.

Every command is written to either work or fail with a clear, actionable message when the
AMI corpus has not been downloaded yet -- most commands cannot do anything useful before
paso cero (thesis section 5.0), and they say so instead of crashing with a stack trace.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.markup import escape

if TYPE_CHECKING:
    from afg.annotation.workspace import AnnotationPlan, WorkspacePaths

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
from afg.conditions.base import Condition
from afg.conditions.c1_document_rag import (
    ChatError,
    DocumentRagCondition,
    GenerationSettings,
)
from afg.conditions.c1_retrieval import OllamaEmbedder, configured_embedding_model
from afg.conditions.c1_tuning import (
    RESULTS_PATH as C1_TUNING_RESULTS_PATH,
)
from afg.conditions.c1_tuning import (
    NoEligibleConfigError,
    evaluate_grid,
    load_tuning_config,
    load_tuning_questions,
    save_tuning_results,
    select_winner,
    series_meetings,
)
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
from afg.corpus.render import discover_meeting_ids, render_meetings
from afg.domain.decision import Decision
from afg.domain.question import Question, QuestionStratum
from afg.evaluation.judge import (
    JudgeConfigurationError,
    OllamaJudgeBackend,
    PresentationOrder,
    list_installed_models,
    missing_models,
)
from afg.evaluation.judge_calibration import load_thresholds
from afg.evaluation.judge_calibration_agreement import (
    AGREEMENT_PATH,
    DEFAULT_SAMPLE_SEED,
    DEFAULT_SAMPLE_SIZE,
    SECOND_SHEET_PATH,
    AgreementError,
    SecondSheetLabeledError,
    compute_human_agreement,
    read_label_rows,
    save_agreement,
    select_second_sheet_rows,
    write_second_sheet,
)
from afg.evaluation.judge_calibration_checkpoint import CandidateCheckpoints, calibration_key
from afg.evaluation.judge_calibration_generation import (
    CALIBRATION_PATH,
    OllamaGenerationBackend,
    generate_calibration_set,
)
from afg.evaluation.judge_calibration_results import RESULTS_PATH, save_calibration_results
from afg.evaluation.judge_calibration_runner import (
    CandidateRun,
    load_candidates,
    load_think_settings,
    run_calibration,
    stored_excerpt_for,
)
from afg.evaluation.judge_calibration_set import (
    CalibrationSetError,
    load_calibration_items,
    summarize_calibration_set,
)
from afg.evaluation.judge_calibration_worksheet import (
    E4_BLANK_ROWS,
    WORKSHEET_PATH,
    WorksheetError,
    WorksheetNotEmptyError,
    build_worksheet_rows,
    load_worksheet,
    make_act_resolver,
    validate_worksheet,
    worksheet_questions,
    write_worksheet,
)
from afg.experiments.question_bank import (
    QuestionBankReport,
    format_issue,
    is_question_bank,
    load_configured_question_bank,
)
from afg.experiments.questions import QuestionBankError, load_experiment_questions
from afg.experiments.runner import (
    ManifestMismatchError,
    RunAbortedError,
    RunSettings,
    configured_partition_of,
    current_git_commit,
    default_excerpt_for,
    run_experiment_b,
)
from afg.shared.config import get_settings, load_corpus_config, load_experiments_config
from afg.shared.logging import configure_logging, get_logger, quiet_http_logs
from afg.shared.paths import (
    AMI_DIR,
    EXPERIMENT_B_DIR,
    GOLD_DECISIONS_DIR,
    GOLD_RELATIONS_DIR,
    PROJECT_ROOT,
    QUESTIONS_DIR,
    SKILLS_DIR,
    TABLES_DIR,
    TRANSCRIPTS_DIR,
    ensure_dirs,
)
from afg.shared.skills import SkillAssetsError, link_skill, sync_assets, verify_installed

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
judge_app = typer.Typer(
    help="Selección del modelo juez: preguntas, respuestas y calibración (issue #82)."
)
c1_app = typer.Typer(help="C1 (RAG sobre documentos): ajuste de la segmentación y de K (ADR 0005).")
experiment_app = typer.Typer(help="OE2/OE3: run Experiment A / Experiment B (thesis section 3).")
skills_app = typer.Typer(help="Install, verify and link skills under .agents/skills/.")

app.add_typer(corpus_app, name="corpus")
app.add_typer(biblio_app, name="biblio")
app.add_typer(gold_app, name="gold")
app.add_typer(judge_app, name="judge")
app.add_typer(c1_app, name="c1")
app.add_typer(experiment_app, name="experiment")
app.add_typer(skills_app, name="skills")


@app.callback()
def main(log_level: str = typer.Option("INFO", help="Logging level.")) -> None:
    configure_logging(log_level)
    ensure_dirs()


# --- skills -----------------------------------------------------------------------------


@skills_app.command("sync-assets")
def skills_sync_assets(
    skill: Annotated[str, typer.Argument(help="Skill name, e.g. deck-uc.")],
    source: Annotated[
        Path | None,
        typer.Option(
            "--source",
            help="Synced shared folder. Defaults to AFG_SKILL_ASSETS_DIR. Files are read "
            "from <source>/<skill>/ if that folder exists, else directly from <source>/.",
        ),
    ] = None,
) -> None:
    """Copy a skill's non-versioned assets after verifying their SHA-256."""
    origin = source or get_settings().skill_assets_dir
    if origin is None:
        console.print(
            "[red]No source folder.[/red] Set AFG_SKILL_ASSETS_DIR in .env to the locally "
            "synced shared folder, or pass --source."
        )
        raise typer.Exit(code=1)
    try:
        copied = sync_assets(skill, origin, SKILLS_DIR)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    if copied:
        console.print(f"Installed {len(copied)} asset(s) for '{skill}': {', '.join(copied)}")
    else:
        console.print(f"Assets for '{skill}' were already up to date.")


@skills_app.command("verify")
def skills_verify(skill: Annotated[str, typer.Argument(help="Skill name, e.g. deck-uc.")]) -> None:
    """Check the installed assets of a skill against its checksum list."""
    try:
        verify_installed(skill, SKILLS_DIR)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    console.print(f"Assets for '{skill}' are complete and match their checksums.")


@skills_app.command("link")
def skills_link(
    skill: Annotated[str, typer.Argument(help="Skill name, e.g. deck-uc.")],
    dest_dir: Annotated[Path, typer.Argument(help="Directory a tool reads skills from.")],
) -> None:
    """Symlink a skill into another directory, keeping that directory out of git."""
    try:
        link = link_skill(skill, dest_dir, SKILLS_DIR, PROJECT_ROOT)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    console.print(f"Linked {link} -> {link.readlink()}")


# --- corpus -----------------------------------------------------------------------------


def _print_corpus_licence() -> None:
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


def _confirm_and_download_corpus(yes: bool) -> None:
    """Print the licence, ask for confirmation unless ``yes``, then download.

    Shared by ``corpus download`` and ``gold setup`` so the licence text and the
    confirmation are asked in exactly one place. Exits the process (code 1) on decline or
    on download failure.
    """
    _print_corpus_licence()

    if not yes and not typer.confirm("Proceed with download?"):
        console.print("Aborted.")
        raise typer.Exit(code=1)

    try:
        result = download_annotations(AMI_DIR)
    except DownloadError as exc:
        console.print(f"[bold red]Download failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"Downloaded {result.bytes_downloaded} bytes, extracted to {result.extracted_to}")


@corpus_app.command("download")
def corpus_download(
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Fetch and extract the AMI manual annotations (CC BY 4.0). Prints the licence first."""
    _confirm_and_download_corpus(yes)


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


_TRANSCRIPTS_SERIES_OPTION = typer.Option(
    None, "--series", help="AMI series id to render (e.g. IS1004). Repeatable; omit for all."
)
_TRANSCRIPTS_OUT_OPTION = typer.Option(
    None,
    "--out",
    help="Output directory for rendered transcripts (default: data/interim/transcripts).",
)


@corpus_app.command("transcripts")
def corpus_transcripts(
    series: list[str] | None = _TRANSCRIPTS_SERIES_OPTION,
    out: Path | None = _TRANSCRIPTS_OUT_OPTION,
    force: bool = typer.Option(
        False, "--force/--no-force", help="Overwrite an existing non-empty output directory."
    ),
) -> None:
    """Freeze rendered transcripts (.md + .jsonl) to disk, plus a tracked manifest
    (thesis sections 5.3/5.4). Refuses to overwrite a non-empty output directory unless
    --force is given: transcripts are meant to be frozen before human annotation starts,
    and silently re-rendering under the annotators would invalidate their offsets."""
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    out_dir = out or TRANSCRIPTS_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]AMI corpus not found at {ami_root}. "
            "Run `uv run afg corpus download` first.[/bold red]"
        )
        raise typer.Exit(code=1)

    meeting_ids = discover_meeting_ids(ami_root, series)
    if not meeting_ids:
        console.print(
            f"[bold red]No meetings discovered under {ami_root}/words/"
            f"{' for series ' + ', '.join(series) if series else ''}.[/bold red]"
        )
        raise typer.Exit(code=1)

    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        console.print(
            f"[bold red]{out_dir} already exists and is not empty. Transcripts are frozen "
            "before human annotation starts; re-rendering under the annotators would "
            "silently invalidate their char offsets. Pass --force to overwrite.[/bold red]"
        )
        raise typer.Exit(code=1)

    # A render into the canonical transcripts directory writes the tracked manifest at
    # TABLES_DIR (and merges into it, see write_manifest_csv). Any other --out is a
    # scratch render and must not touch that tracked file at all -- its manifest goes
    # next to its own output instead.
    is_canonical_out_dir = out_dir.resolve() == TRANSCRIPTS_DIR.resolve()
    manifest_dir = TABLES_DIR if is_canonical_out_dir else out_dir

    console.print(f"Rendering {len(meeting_ids)} meeting(s)...")
    result = render_meetings(ami_root, meeting_ids, out_dir, manifest_dir=manifest_dir)

    for meeting_id in result.meeting_ids:
        console.print(f"Wrote {out_dir / f'{meeting_id}.md'}")
        console.print(f"Wrote {out_dir / f'{meeting_id}.jsonl'}")
    console.print(f"Wrote {result.manifest_path}")

    console.print(
        f"[bold]{len(result.meeting_ids)} meeting(s) rendered[/bold], "
        f"{result.total_turns} turns, {result.total_characters} characters, "
        f"renderer {result.renderer_revision}."
    )
    console.print(f"Transcripts: {result.out_dir}")
    console.print(f"Manifest:    {result.manifest_path}")


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


def _refuse_or_warn_if_series_annotated(series: str, *, force: bool) -> None:
    """Shared guard for ``afg gold build`` and ``afg gold candidates``.

    Both commands regenerate a base file (``<series>.decisions.csv`` /
    ``<series>.candidates.csv``) from scratch from the AMI abstractive summary. Refuses
    when any derived per-annotator file for ``series`` already holds annotation, unless
    ``force`` -- naming the files found and what regenerating would lose. With ``force``,
    still warns: the named files will fail ``afg gold validate`` until they are prepared
    again.
    """
    from afg.annotation.workspace import series_has_annotated_work

    annotated = series_has_annotated_work(series, paths=_workspace_paths())
    if not annotated:
        return

    names = ", ".join(_short(path) for path in annotated)
    if not force:
        console.print(
            f"[bold red]La serie {series} ya tiene anotación cargada en los siguientes "
            f"archivos derivados: {names}.[/bold red]\n"
            "[bold red]No se regenera la base.[/bold red] Hacerlo ahora mismo:\n"
            "  - borraría en silencio cualquier fila `compuesta` que ya se haya dividido "
            "en filas hijas (manual de anotación sección 2), y\n"
            "  - desalinearía las columnas de máquina de esos archivos frente a la base "
            "nueva, lo que hace que `afg gold validate` reporte error para todo el mundo, "
            "no solo para quien anotó.\n"
            "Usa --force solo si de verdad quieres perder eso."
        )
        raise typer.Exit(code=1)

    console.print(
        f"[yellow]--force: regenerando con anotación cargada en: {names}. Esos archivos "
        "quedarán desalineados frente a la base nueva hasta que se vuelvan a preparar "
        "(`uv run afg gold prepare --force`).[/yellow]"
    )


@gold_app.command("build")
def gold_build(
    series: str = typer.Option(..., "--series", help="AMI series id, e.g. IS1004."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Regenera aunque haya anotación cargada en los archivos derivados de la serie. "
        "Desalinea `afg gold validate` para todo el mundo.",
    ),
) -> None:
    """Build the Task-A working file for a series (manual de anotacion secciones 2, 3).

    Writes ``data/processed/decisions/<series>.decisions.csv``. IMPORTANT: this is a
    working file for a human annotator, not a finished gold set. ``machine_flags`` are
    triage hints only, never a verdict -- ``status``, ``decision_object``,
    ``decision_content``, ``annotator``, and ``notes`` are always written empty and must be
    filled in by a human (see ``afg.annotation.goldset`` module docstring). Refuses to run
    at all if a derived ``<series>.decisions.<iniciales>.csv`` or
    ``<series>.candidates.<iniciales>.csv`` already holds annotation, unless ``--force``.
    """
    from afg.annotation.goldset import build_gold_decisions, write_gold_decisions_csv

    _refuse_or_warn_if_series_annotated(series, force=force)

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
        annotator_csvs,
        compute_series_agreement,
        write_agreement_csv,
    )

    pattern = f"{series}.candidates.<initials>.csv"
    paths = annotator_csvs(GOLD_RELATIONS_DIR, series, "candidates")
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
            "  type kappa:      n/a (no pair was marked as an existing link by both annotators)"
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
    force: bool = typer.Option(
        False,
        "--force",
        help="Regenera aunque haya anotación cargada en los archivos derivados de la serie. "
        "Desalinea `afg gold validate` para todo el mundo.",
    ),
) -> None:
    """Generate cross-meeting candidate decision pairs for human adjudication (Tarea B).

    Provisional: candidates are built from raw abstractive DECISIONS sentences
    (``afg.annotation.blocking.decisions_from_abstractive``), not yet P3's normalised gold
    decisions. Writes ``data/processed/relations/<series>.candidates.csv``. Refuses to run
    at all if a derived ``<series>.decisions.<iniciales>.csv`` or
    ``<series>.candidates.<iniciales>.csv`` already holds annotation, unless ``--force``.
    """
    _refuse_or_warn_if_series_annotated(series, force=force)

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
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing sample. Invalidates any annotation made on it.",
    ),
) -> None:
    """Sample rejected pairs for the blocker recall check (Tarea C).

    Provisional: sampled from raw abstractive DECISIONS sentences, same caveat as
    ``afg gold candidates``. Writes ``data/processed/relations/<series>.recall-sample.csv``.

    Refuses to overwrite an existing sample unless ``--force`` is given: the sample is
    drawn once with a fixed seed, and one regenerated after seeing results is no longer
    a valid estimate (docs/anotacion/asignacion/tareas-jss.md section 5).
    """
    out_path = GOLD_RELATIONS_DIR / f"{series}.recall-sample.csv"
    if out_path.exists() and not force:
        console.print(
            f"[bold red]{out_path} ya existe y no se sobrescribe.[/bold red] La muestra de "
            "recall se genera una sola vez; regenerarla invalida la Tarea C. Si de verdad "
            "hay que reemplazarla, lo decide quien adjudica y se corre con --force."
        )
        raise typer.Exit(code=1)

    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    decisions = _decisions_for_series_or_exit(ami_root, series)

    sample = sample_rejected(
        decisions, n=n, seed=seed, threshold=threshold, min_overlap_tokens=min_overlap
    )
    write_candidate_pairs_csv(sample, out_path)

    console.print(
        f"Series {series}: sampled {len(sample)} rejected pairs (seed={seed}), "
        f"threshold={threshold:.2f}, min_overlap={min_overlap}, "
        f"blocker_version={BLOCKER_VERSION}."
    )
    console.print(f"Wrote {out_path}")


# --- gold: per-annotator workspace (docs/anotacion/asignacion/) -----------------------------
#
# These six commands exist so an annotator never copies, renames, or remembers anything.
# All the logic lives in afg.annotation.workspace (and, for `setup`, its sibling module
# afg.annotation.setup); this layer only parses options, prints Spanish, and picks an exit
# code.


def _plan_or_exit() -> AnnotationPlan:
    from afg.annotation.workspace import load_annotation_plan

    try:
        return load_annotation_plan()
    except FileNotFoundError as exc:
        console.print(f"[bold red]No se encontró config/annotation.toml. {exc}[/bold red]")
        raise typer.Exit(code=1) from exc


def _workspace_paths() -> WorkspacePaths:
    from afg.annotation.workspace import WorkspacePaths

    return WorkspacePaths(
        decisions_dir=GOLD_DECISIONS_DIR,
        relations_dir=GOLD_RELATIONS_DIR,
        questions_dir=QUESTIONS_DIR,
    )


def _short(path: Path) -> str:
    """Path relative to the repository root, so a list of 21 files stays readable."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


@gold_app.command("setup")
def gold_setup(
    annotator: str = typer.Option(..., "--annotator", help="Iniciales del anotador, p. ej. gv."),
    yes: bool = typer.Option(
        False, "--yes", help="Salta la confirmación de la licencia del corpus (paso 1)."
    ),
) -> None:
    """De un clon nuevo a "abre este archivo y empieza", en un solo comando.

    Corre, en orden, saltando lo que ya esté hecho: descarga el corpus AMI (pide
    confirmación explícita de la licencia CC BY 4.0 y del tamaño de la descarga, salvo
    que pases --yes), genera las 171 transcripciones, y prepara tu espacio de trabajo --
    nunca con --force, así que jamás borra anotación ya hecha. Termina diciendo
    exactamente qué archivo abrir primero.
    """
    from afg.annotation.setup import CorpusDownloadDeclinedError, run_setup
    from afg.annotation.workspace import TaskKind, UnknownAnnotatorError

    plan = _plan_or_exit()

    def confirm_corpus_download() -> bool:
        _print_corpus_licence()
        if yes:
            return True
        return typer.confirm("Proceed with download?")

    try:
        outcome = run_setup(
            plan,
            annotator,
            paths=_workspace_paths(),
            ami_root=AMI_DIR,
            transcripts_dir=TRANSCRIPTS_DIR,
            manifest_dir=TABLES_DIR,
            confirm_corpus_download=confirm_corpus_download,
            download=download_annotations,
            render=render_meetings,
            discover=discover_meeting_ids,
        )
    except UnknownAnnotatorError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    except CorpusDownloadDeclinedError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    except DownloadError as exc:
        console.print(f"[bold red]Download failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    # --- 1/3 corpus ---
    if outcome.corpus_already_present:
        console.print(f"[green]1/3 El corpus ya está en {_short(AMI_DIR)}: se salta.[/green]")
    else:
        result = outcome.corpus_download
        assert result is not None  # not present -> confirmed -> downloaded, or we'd have raised
        console.print(
            f"[bold]1/3 Corpus descargado[/bold]: {result.bytes_downloaded} bytes en "
            f"{_short(result.extracted_to)}."
        )

    # --- 2/3 transcripts ---
    if outcome.transcripts_already_rendered:
        console.print(
            f"[green]2/3 Las transcripciones ya están en {_short(TRANSCRIPTS_DIR)}: "
            "se salta.[/green]"
        )
    else:
        render_result = outcome.transcripts_render
        assert render_result is not None
        console.print(
            f"[bold]2/3 {len(render_result.meeting_ids)} transcripción(es) generadas[/bold] "
            f"en {_short(TRANSCRIPTS_DIR)}."
        )

    # --- 3/3 workspace ---
    prep = outcome.prepare
    if outcome.is_maintainer:
        person = plan.annotator(annotator)
        console.print(
            f"[yellow]3/3 {person.name} (`{annotator}`) no anota ninguna serie: "
            "adjudica.[/yellow]\n"
            "Por diseño, quien adjudica no anota (CONTRIBUTING.md §1). Lo que sí te toca:\n"
            "  uv run afg gold status\n"
            "  uv run afg gold adjudicate --series <ID>   (tras cada serie doble)"
        )
        return

    if prep.created:
        console.print(f"[bold]3/3 Creados {len(prep.created)} archivo(s):[/bold]")
        for workspace_file in prep.created:
            console.print(f"  fase {workspace_file.phase}  {_short(workspace_file.target)}")
    if prep.skipped_annotated:
        console.print(
            f"[yellow]3/3 Respetados {len(prep.skipped_annotated)} archivo(s) que ya "
            "tienen trabajo hecho (no se tocaron):[/yellow]"
        )
        for workspace_file in prep.skipped_annotated:
            console.print(f"  {_short(workspace_file.target)}")
    if prep.missing_sources:
        console.print(
            "[bold red]3/3 Faltan archivos base; esas series no se prepararon:[/bold red]"
        )
        for workspace_file in prep.missing_sources:
            command = (
                "build" if workspace_file.kind.value == "decisions" else workspace_file.kind.value
            )
            console.print(
                f"  {_short(workspace_file.source)}  ->  uv run afg gold {command} "
                f"--series {workspace_file.series_id}"
            )

    if not prep.created and not prep.skipped_annotated:
        console.print("[bold red]No se creó ningún archivo.[/bold red]")
        raise typer.Exit(code=1)

    first = outcome.first_file
    if first is None:
        console.print(
            f"[bold red]{annotator} no tiene ninguna serie asignada en "
            "config/annotation.toml.[/bold red]"
        )
        raise typer.Exit(code=1)

    partner = (
        _short(_workspace_paths().target(TaskKind.CANDIDATES, first.series_id, annotator))
        if first.kind is TaskKind.DECISIONS
        else _short(_workspace_paths().target(TaskKind.DECISIONS, first.series_id, annotator))
    )
    console.print(
        "\n[bold]Qué hacer ahora.[/bold]\n"
        f"  1. Lee la transcripción de la serie {first.series_id} (fase {first.phase}, tu "
        f"primera) en {_short(TRANSCRIPTS_DIR)}/{first.series_id}*.md antes de llenar una "
        "sola fila -- anotar solo desde el resumen es el error que más cuesta corregir.\n"
        f"  2. Abre {_short(first.target)} y llena las columnas humanas (luego {partner} "
        "para la Tarea B de la misma serie).\n"
        f"  3. Cuando cierres esa serie: uv run afg gold validate --annotator {annotator} "
        f"--series {first.series_id}\n"
        "  4. Sin errores -> abre el PR de esa serie (una serie por PR)."
    )


@gold_app.command("prepare")
def gold_prepare(
    annotator: str = typer.Option(..., "--annotator", help="Iniciales del anotador, p. ej. gv."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Regenera incluso los archivos que ya tienen anotación. DESTRUYE trabajo.",
    ),
) -> None:
    """Crea los archivos que esta persona debe llenar, ya con el nombre correcto.

    Columnas de máquina puestas, columnas humanas vacías, un archivo por serie asignada
    según config/annotation.toml. Nunca sobrescribe un archivo que ya tenga anotación:
    volver a correr este comando después de un día de trabajo es inofensivo.
    """
    from afg.annotation.workspace import UnknownAnnotatorError, prepare_annotator_workspace

    plan = _plan_or_exit()
    try:
        outcome = prepare_annotator_workspace(
            plan, annotator, paths=_workspace_paths(), force=force
        )
    except UnknownAnnotatorError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    if outcome.is_maintainer:
        person = plan.annotator(annotator)
        console.print(
            f"[yellow]{person.name} (`{annotator}`) no anota ninguna serie: adjudica.[/yellow]\n"
            "Por diseño, quien adjudica no anota (CONTRIBUTING.md §1). Lo que sí te toca:\n"
            "  uv run afg gold adjudicate --series <ID>   (tras cada serie doble)"
        )
        return

    if outcome.created:
        console.print(f"[bold]Creados {len(outcome.created)} archivos:[/bold]")
        for workspace_file in outcome.created:
            console.print(f"  fase {workspace_file.phase}  {_short(workspace_file.target)}")
    if outcome.overwritten:
        console.print(
            f"[bold red]Sobrescritos {len(outcome.overwritten)} archivos que TENÍAN "
            "anotación (--force):[/bold red]"
        )
        for workspace_file in outcome.overwritten:
            console.print(f"  {_short(workspace_file.target)}")
    if outcome.skipped_annotated:
        console.print(
            f"[yellow]Respetados {len(outcome.skipped_annotated)} archivos que ya tienen "
            "trabajo hecho (no se tocaron):[/yellow]"
        )
        for workspace_file in outcome.skipped_annotated:
            console.print(f"  {_short(workspace_file.target)}")
    if outcome.missing_sources:
        console.print("[bold red]Faltan archivos base; esas series no se prepararon:[/bold red]")
        for workspace_file in outcome.missing_sources:
            command = (
                "build" if workspace_file.kind.value == "decisions" else workspace_file.kind.value
            )
            console.print(
                f"  {_short(workspace_file.source)}  ->  uv run afg gold {command} "
                f"--series {workspace_file.series_id}"
            )

    if not outcome.created and not outcome.overwritten and not outcome.skipped_annotated:
        console.print("[yellow]No se creó ningún archivo.[/yellow]")
        raise typer.Exit(code=1)

    console.print(
        "\n[bold]Qué sigue.[/bold] Llena solo las columnas humanas; las de máquina no se "
        "tocan (`afg gold validate` lo verifica).\n"
        "  1. Trabaja las series en el orden en que aparecen arriba: fase 1, luego 2, luego 3.\n"
        f"  2. Al cerrar una serie: uv run afg gold validate --annotator {annotator} "
        "--series <ID>\n"
        "  3. Si sale sin errores, abre el PR de esa serie (una serie por PR)."
    )


@gold_app.command("validate")
def gold_validate(
    annotator: str = typer.Option(..., "--annotator", help="Iniciales del anotador, p. ej. gv."),
    series: str | None = typer.Option(
        None, "--series", help="Valida solo esta serie en lugar de todas las asignadas."
    ),
) -> None:
    """Verifica el trabajo de una persona antes de abrir el pull request.

    Tres controles por archivo: los valores de conjunto cerrado son legales, ninguna fila
    quedó a medio llenar, y las columnas de máquina siguen idénticas al archivo base. Una
    serie sin preparar no cuenta como error de contenido -- se marca `sin preparar`, no
    `errores` -- pero de todos modos sale con código distinto de cero: no se puede abrir un
    PR para archivos que no existen.
    """
    from afg.annotation.workspace import IssueKind, UnknownAnnotatorError, validate_annotator

    plan = _plan_or_exit()
    try:
        report = validate_annotator(plan, annotator, paths=_workspace_paths(), series=series)
    except (UnknownAnnotatorError, ValueError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    person = plan.annotator(annotator)
    console.print(f"[bold]{person.name} (`{annotator}`)[/bold]")
    for progress in report.series:
        if progress.ok:
            mark = "[green]ok[/green]"
        elif progress.not_started:
            mark = "[dim]sin preparar[/dim]"
        else:
            mark = "[bold red]errores[/bold red]"
        console.print(
            f"  {progress.series_id}: {progress.decisions_filled}/"
            f"{progress.decisions_total} decisiones, {progress.candidates_filled}/"
            f"{progress.candidates_total} candidatos  (fase {progress.phase})  {mark}"
        )

    if report.ok:
        console.print(
            "\n[green]Sin errores.[/green] Recuerda que 0/N no es un error: es trabajo por hacer."
        )
        return

    real_issues = [issue for issue in report.issues if issue.kind is not IssueKind.MISSING_FILE]
    not_started = [progress for progress in report.series if progress.not_started]

    if real_issues:
        console.print(f"\n[bold red]{len(real_issues)} problema(s):[/bold red]")
        for issue in real_issues:
            console.print(f"  - {issue.message}")
    if not_started:
        console.print(
            f"\n[dim]{len(not_started)} serie(s) sin preparar.[/dim] Ejecuta "
            f"`uv run afg gold prepare --annotator {annotator}` para crear tus archivos."
        )
    raise typer.Exit(code=1)


@gold_app.command("status")
def gold_status(
    annotator: str | None = typer.Option(
        None, "--annotator", help="Muestra solo las series de esta persona, p. ej. gv."
    ),
) -> None:
    """Panel de control del mantenedor: una fila por anotador y serie.

    Muestra fase, avance en las dos tareas y si la serie pasa la validación, para seguir
    al equipo sin abrir un solo archivo. Con `--annotator`, muestra solo las filas de esa
    persona -- su propio avance, sin el resto del equipo.
    """
    from rich.table import Table

    from afg.annotation.workspace import UnknownAnnotatorError, validate_annotator

    plan = _plan_or_exit()
    paths = _workspace_paths()

    if annotator is not None:
        try:
            plan.annotator(annotator)
        except UnknownAnnotatorError as exc:
            console.print(f"[bold red]{exc}[/bold red]")
            raise typer.Exit(code=1) from exc

    table = Table(title="Anotación OE1 — avance por persona y serie")
    table.add_column("Anotador")
    table.add_column("Serie")
    table.add_column("Fase", justify="right")
    table.add_column("Decisiones", justify="right")
    table.add_column("Candidatos", justify="right")
    table.add_column("Validación")

    any_row = False
    for person in plan.annotators:
        if not person.annotates:
            continue
        if annotator is not None and person.initials != annotator:
            continue
        report = validate_annotator(plan, person.initials, paths=paths)
        for progress in report.series:
            any_row = True
            if progress.ok and progress.complete:
                verdict = "[green]completa[/green]"
            elif progress.ok:
                verdict = "[yellow]en curso[/yellow]"
            elif progress.not_started:
                verdict = "[dim]sin preparar[/dim]"
            else:
                verdict = f"[bold red]{len(progress.issues)} error(es)[/bold red]"
            table.add_row(
                f"{person.initials} ({person.github})",
                progress.series_id,
                str(progress.phase),
                f"{progress.decisions_filled}/{progress.decisions_total}",
                f"{progress.candidates_filled}/{progress.candidates_total}",
                verdict,
            )

    if not any_row:
        console.print("[yellow]No hay ninguna serie asignada en config/annotation.toml.[/yellow]")
        raise typer.Exit(code=1)

    console.print(table)
    console.print(
        f"Adjudica `{plan.adjudicator}`. Banco de preguntas: lo escribe "
        f"`{plan.question_bank.author}`, lo valida `{plan.question_bank.validator}`. "
        f"Muestra de recall (Tarea C): `{plan.recall_sample.owner}` sobre "
        f"{', '.join(plan.recall_sample.series_ids)}."
    )


@gold_app.command("adjudicate")
def gold_adjudicate(
    series: str = typer.Option(..., "--series", help="Serie de doble anotación, p. ej. ES2015."),
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque los CSV ya tengan veredictos escritos."
    ),
) -> None:
    """Escribe los dos CSV de adjudicación de una serie, con las respuestas lado a lado.

    Genera `<serie>.decisions.adjudicated.csv` (una fila por decisión base) y
    `<serie>.candidates.adjudicated.csv` (una fila por par). Cada archivo trae las columnas
    de los dos anotadores, `acuerdo` (`si`/`no`) y las columnas del veredicto final. Solo
    donde los dos coinciden se prellena el veredicto; donde discrepan, lo decide el
    adjudicador.
    """
    from afg.annotation.adjudication import write_adjudication_csvs
    from afg.annotation.agreement import AgreementInputError

    plan = _plan_or_exit()
    try:
        decisions_path, candidates_path = write_adjudication_csvs(
            plan, series, paths=_workspace_paths(), force=force
        )
    except (FileExistsError, FileNotFoundError, AgreementInputError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"Escrito {_short(decisions_path)}")
    console.print(f"Escrito {_short(candidates_path)}")
    console.print(
        "Donde `acuerdo` es `no`, el adjudicador llena `final_*` y `razon` (y su "
        "iniciales en `adjudicator`). Si una fila resulta `compuesta`, agrega debajo sus "
        "filas hijas `<id>-1`, `<id>-2`, ... con `final_*` cada una.\n"
        f"Luego corre: uv run afg gold validate-adjudication --series {series}\n"
        f"Y los kappas: uv run afg gold agreement --series {series}"
    )


@gold_app.command("validate-adjudication")
def gold_validate_adjudication(
    series: str = typer.Option(..., "--series", help="Serie de doble anotación, p. ej. ES2015."),
) -> None:
    """Verifica que el adjudicador terminó los dos CSV de adjudicación de una serie.

    Cada fila necesita un `final_*` legal, `razon` donde hubo desacuerdo o `sin_soporte`,
    y `adjudicator`; una fila `compuesta` necesita al menos dos filas hijas consecutivas.
    Sale con código distinto de cero si queda algo pendiente.
    """
    from afg.annotation.adjudication import validate_adjudication

    issues = validate_adjudication(series, paths=_workspace_paths())
    if not issues:
        console.print(f"[green]Sin errores.[/green] La adjudicación de {series} está completa.")
        return

    console.print(f"[bold red]{len(issues)} problema(s) en la adjudicación de {series}:[/bold red]")
    for issue in issues:
        console.print(f"  - {issue.message}")
    raise typer.Exit(code=1)


@gold_app.command("questions-init")
def gold_questions_init(
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque el banco ya tenga preguntas escritas."
    ),
) -> None:
    """Crea el banco de preguntas con filas numeradas y vacías: 25 por estrato, 40 en E3.

    Quien escribe el banco llena texto en filas que ya existen: nunca inventa un id ni
    escribe un estrato, que es lo que hacía que un estrato corto se descubriera contando
    al final.
    """
    from afg.annotation.workspace import QuestionBankNotEmptyError, write_question_bank_template

    plan = _plan_or_exit()
    bank = plan.question_bank
    out_path = _workspace_paths().question_bank
    try:
        write_question_bank_template(
            out_path,
            total=bank.total_questions,
            per_stratum=bank.questions_per_stratum,
            rows_per_stratum={s: bank.rows_for(s) for s in QuestionStratum},
            author=bank.author,
            force=force,
        )
    except QuestionBankNotEmptyError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(
        f"Escrito {_short(out_path)}: {bank.total_questions} filas, "
        f"{bank.questions_per_stratum} por estrato (E1, E2, E3, E4), salvo "
        + ", ".join(
            f"{s.value} con {bank.rows_for(s)}"
            for s in QuestionStratum
            if bank.rows_for(s) != bank.questions_per_stratum
        )
        + ". Las filas de más sobre el mínimo pueden quedar vacías."
    )
    console.print(
        f"Escribe `{bank.author}`, valida `{bank.validator}`. Llena `series_id`, `text`, "
        "`reference_answer` y `reference_evidence`; `id` y `stratum` ya están puestos y no "
        "se tocan. En E4 la respuesta de referencia va vacía a propósito: ese estrato mide "
        "abstención."
    )


def _print_question_bank_report(report: QuestionBankReport) -> None:
    """Counts per stratum, then every error and warning, one line each."""
    console.print(
        f"{report.total_rows} filas: {len(report.usable)} validada(s) y sin errores, "
        f"{len(report.pending_ids)} pendiente(s), {len(report.optional_ids)} opcional(es) "
        "sin usar (filas vacías sobre el mínimo del estrato)."
    )
    for stratum, count in report.usable_per_stratum.items():
        console.print(f"  {stratum.value}: {count} validada(s)")
    for issue in report.errors:
        console.print(f"[bold red]  error {escape(format_issue(issue))}[/bold red]")
    for issue in report.warnings:
        console.print(f"[yellow]  aviso {escape(format_issue(issue))}[/yellow]")


@gold_app.command("questions-check")
def gold_questions_check(
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Banco a revisar (por defecto el banco del proyecto)."),
    ] = None,
    complete: Annotated[
        bool,
        typer.Option(
            "--complete",
            help=(
                "Exige el mínimo validado por estrato y ninguna fila escrita sin validar; "
                "las filas vacías sobre el mínimo son opcionales (cierre del banco)."
            ),
        ),
    ] = False,
) -> None:
    """Revisa el banco de preguntas sin correr nada: informe por fila, sin parar en el primer error.

    Por defecto tolera un banco a medias (las filas sin validar quedan pendientes y el mínimo
    por estrato es un aviso). Sale con código 1 si hay errores bloqueantes.
    """
    bank_path = path or _workspace_paths().question_bank
    try:
        if not is_question_bank(bank_path):
            console.print(
                f"[bold red]{_short(bank_path)} no tiene el formato del banco.[/bold red]"
            )
            raise typer.Exit(code=1)
        report = load_configured_question_bank(bank_path, require_complete=complete)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    _print_question_bank_report(report)
    if report.has_errors:
        raise typer.Exit(code=1)


# --- judge calibration (issue #82) ---------------------------------------------------------


_CALIBRATION_SERIES = "ES2015"


def _load_valid_worksheet_or_exit() -> list[dict[str, str]]:
    """The worksheet rows, or a clear message and exit 1 when missing or invalid."""
    if not WORKSHEET_PATH.exists():
        console.print(
            f"[bold red]No existe {_short(WORKSHEET_PATH)}.[/bold red] "
            "Créala con `uv run afg judge calibration-init`."
        )
        raise typer.Exit(code=1)
    try:
        rows = load_worksheet(WORKSHEET_PATH)
    except WorksheetError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    report = validate_worksheet(rows)
    for warning in report.warnings:
        console.print(f"[yellow]Aviso: {warning}[/yellow]")
    if report.errors:
        console.print(
            f"[bold red]{len(report.errors)} problema(s) en {_short(WORKSHEET_PATH)}:[/bold red]"
        )
        for error in report.errors:
            console.print(f"  - {error}")
        for line in report.summary_lines():
            console.print(line)
        raise typer.Exit(code=1)
    return rows


@judge_app.command("calibration-init")
def judge_calibration_init(
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque la hoja ya tenga celdas llenadas."
    ),
) -> None:
    """Crea la hoja de preguntas de la calibración, prellenada desde ES2015.

    Una fila por decisión adjudicada y por par con relación, con la evidencia ya resuelta a
    actos de diálogo, más filas en blanco para E4. Quien escribe solo llena `usar`,
    `stratum`, `pregunta` y `respuesta_referencia`.
    """
    decisions_path = GOLD_DECISIONS_DIR / f"{_CALIBRATION_SERIES}.decisions.adjudicated.csv"
    relations_path = GOLD_RELATIONS_DIR / f"{_CALIBRATION_SERIES}.candidates.adjudicated.csv"
    for needed in (decisions_path, relations_path):
        if not needed.exists():
            console.print(
                f"[bold red]Falta {_short(needed)}: la serie no está adjudicada.[/bold red]"
            )
            raise typer.Exit(code=1)
    ami_root = get_settings().ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]No se encontró el corpus AMI en {ami_root}. "
            "Ejecuta primero `uv run afg corpus download`.[/bold red]"
        )
        raise typer.Exit(code=1)
    try:
        rows = build_worksheet_rows(
            decisions_path,
            relations_path,
            resolve_acts=make_act_resolver(ami_root, TRANSCRIPTS_DIR),
        )
        write_worksheet(WORKSHEET_PATH, rows, force=force)
    except FileNotFoundError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    except WorksheetNotEmptyError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    n_pairs = sum(1 for r in rows if r["origen"].startswith(f"{_CALIBRATION_SERIES}.p"))
    n_decisions = len(rows) - n_pairs - E4_BLANK_ROWS
    unresolved = sum(1 for r in rows if r["origen"] != "E4" and not r["reference_evidence"])
    console.print(
        f"Escrito {_short(WORKSHEET_PATH)}: {n_decisions} decisiones, {n_pairs} pares con "
        f"relación y {E4_BLANK_ROWS} filas E4 en blanco."
    )
    console.print(
        f"Evidencia sin resolver: {unresolved} fila(s) (ver la columna `aviso_evidencia`)."
    )
    console.print(
        "Abre el archivo en una hoja de cálculo y llena solo las cuatro primeras columnas "
        "(`usar`, `stratum`, `pregunta`, `respuesta_referencia`). Luego: "
        "`uv run afg judge calibration-validate`."
    )


@judge_app.command("calibration-validate")
def judge_calibration_validate() -> None:
    """Revisa la selección de la hoja de preguntas y muestra cuántas hay por estrato."""
    rows = _load_valid_worksheet_or_exit()
    report = validate_worksheet(rows)
    console.print("[bold green]La hoja está lista.[/bold green]")
    for line in report.summary_lines():
        console.print(line)
    console.print("Siguiente paso: `uv run afg judge calibration-answers`.")


@judge_app.command("calibration-answers")
def judge_calibration_answers() -> None:
    """Genera con el modelo generativo dos respuestas por cada pregunta seleccionada.

    Usa Ollama (`qwen3:8b`). Las preguntas que ya tienen respuestas no se regeneran, así que
    las etiquetas ya puestas se conservan.
    """
    rows = _load_valid_worksheet_or_exit()
    quiet_http_logs()
    try:
        questions = worksheet_questions(rows)
        report = generate_calibration_set(
            WORKSHEET_PATH,
            CALIBRATION_PATH,
            backend=OllamaGenerationBackend(),
            transcripts_dir=TRANSCRIPTS_DIR,
            questions=questions,
            on_progress=lambda done, total: console.print(f"Pregunta {done}/{total} lista."),
        )
    except (WorksheetError, CalibrationSetError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"Se generaron {report.rows_written} respuestas para {report.questions_processed} "
        f"preguntas ({report.questions_skipped} ya tenían respuestas y no se tocaron)."
    )
    console.print(
        f"Etiqueta ahora {_short(CALIBRATION_PATH)}: llena `correct` y `evidence_supported` "
        "con si/no en cada fila (las demás columnas no se tocan). Luego: "
        "`uv run afg judge calibration-run`."
    )


@judge_app.command("calibration-run")
def judge_calibration_run() -> None:
    """Corre los modelos candidatos sobre el conjunto etiquetado y guarda los resultados.

    Llama a cada candidato (Ollama) en ambos órdenes y con cada semilla; tarda. Los
    resultados quedan en `reports/judge-calibration/resultados.json` y el notebook 05 los
    lee, sin volver a calcular.
    """
    if not CALIBRATION_PATH.exists():
        console.print(
            f"[bold red]No existe {_short(CALIBRATION_PATH)}.[/bold red] "
            "Genéralo con `uv run afg judge calibration-answers`."
        )
        raise typer.Exit(code=1)
    quiet_http_logs()
    try:
        items = load_calibration_items(CALIBRATION_PATH)
    except CalibrationSetError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    summary = summarize_calibration_set(items)
    if not summary.ready:
        console.print(
            f"[bold red]Faltan etiquetas: {summary.n_items - summary.n_labeled} de "
            f"{summary.n_items} ítems sin etiquetas.[/bold red] Llena `correct` y "
            f"`evidence_supported` (si/no) en {_short(CALIBRATION_PATH)}."
        )
        raise typer.Exit(code=1)
    rebuilt = sum(1 for item in items if item.transcript_excerpt is None)
    if rebuilt:
        console.print(
            f"[yellow]Aviso: {rebuilt} ítem(s) sin pasaje guardado (el archivo no tiene la "
            "columna `pasaje_transcripcion`): el pasaje se reconstruye desde la transcripción "
            "con la ventana actual, que puede no ser el que vio quien etiquetó.[/yellow]"
        )
    candidates = load_candidates()
    try:
        absent = missing_models(candidates, list_installed_models())
    except (RuntimeError, ConnectionError, OSError) as exc:
        console.print(
            f"[bold red]No se pudo consultar los modelos instalados en Ollama: {exc}[/bold red] "
            "Comprueba que Ollama esté corriendo."
        )
        raise typer.Exit(code=1) from exc
    if absent:
        console.print(
            f"[bold red]Faltan {len(absent)} modelo(s) candidato(s) en Ollama; no se corrió "
            "nada:[/bold red]"
        )
        for model in absent:
            console.print(f"  - {model}: `ollama pull {model}`")
        raise typer.Exit(code=1)

    thresholds = load_thresholds()
    think = load_think_settings()
    generative_model = str(load_experiments_config()["shared_budget"]["generative_model"])
    try:
        excerpts = {
            item.id: stored_excerpt_for(item, transcripts_dir=TRANSCRIPTS_DIR) for item in items
        }
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    checkpoints = CandidateCheckpoints(
        RESULTS_PATH.parent / "candidatos",
        key_for=lambda model: calibration_key(
            items=items,
            excerpts=excerpts,
            thresholds=thresholds,
            model=model,
            generative_model=generative_model,
            think=think.get(model),
        ),
    )

    def report_progress(model: str, done: int, total: int) -> None:
        step = max(total // 10, 1)
        if done == total or done % step == 0:
            console.print(f"  {model}: {done}/{total} llamadas")

    def report_done(model: str, run: CandidateRun, reused: bool) -> None:
        metrics = run.metrics
        suffix = " (ya calculado, se reutiliza)" if reused else ""
        console.print(
            f"{model}: kappa {metrics.kappa_correct.point_estimate:.2f}, "
            f"posición {metrics.position_consistency:.2f}, "
            f"latencia {metrics.latency_seconds:.1f} s/llamada, "
            f"{run.calls} llamadas, {run.failures} fallos{suffix}"
        )

    console.print(f"Corriendo {len(candidates)} candidatos sobre {summary.n_items} ítems…")
    try:
        result = run_calibration(
            items,
            candidates=candidates,
            generative_model=generative_model,
            backend_for=lambda model: OllamaJudgeBackend(think=think),
            thresholds=thresholds,
            excerpt_for=lambda item: excerpts[item.id],
            progress=report_progress,
            load_run=checkpoints.load,
            save_run=checkpoints.save,
            on_done=report_done,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        console.print("Lo ya terminado quedó guardado; al repetir el comando se reanuda desde ahí.")
        raise typer.Exit(code=1) from exc
    save_calibration_results(RESULTS_PATH, result, n_items=summary.n_items)
    console.print(f"Resultados guardados en {_short(RESULTS_PATH)}.")
    console.print(
        "Vuelve a ejecutar el notebook 05 (`uv run jupyter nbconvert --to notebook --execute "
        "--inplace notebooks/05-jss-seleccion-juez.ipynb`) para ver la decisión."
    )


@judge_app.command("calibration-second-sheet")
def judge_calibration_second_sheet(
    n: int = typer.Option(DEFAULT_SAMPLE_SIZE, "--n", help="Ítems de la muestra."),
    seed: int = typer.Option(DEFAULT_SAMPLE_SEED, "--seed", help="Semilla del muestreo."),
    force: bool = typer.Option(
        False, "--force", help="Sobrescribe aunque la hoja ya tenga etiquetas."
    ),
) -> None:
    """Crea la hoja sin etiquetas para la segunda persona que etiqueta.

    La muestra es determinista (ids ordenados, barajados con la semilla). Si la hoja ya tiene
    etiquetas, no se toca salvo con `--force`.
    """
    if not CALIBRATION_PATH.exists():
        console.print(f"[bold red]No existe {_short(CALIBRATION_PATH)}.[/bold red]")
        raise typer.Exit(code=1)
    try:
        rows = select_second_sheet_rows(read_label_rows(CALIBRATION_PATH), n=n, seed=seed)
        write_second_sheet(SECOND_SHEET_PATH, rows, force=force)
    except SecondSheetLabeledError as exc:
        console.print(
            f"[bold red]{_short(SECOND_SHEET_PATH)} ya tiene etiquetas; no se sobrescribió "
            "nada.[/bold red] Usa `--force` solo si se quiere descartarlas."
        )
        raise typer.Exit(code=1) from exc
    except AgreementError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"Escrito {_short(SECOND_SHEET_PATH)} con {len(rows)} ítems sin etiquetas (semilla "
        f"{seed}). La segunda persona llena `correct` y `evidence_supported` con si/no, sin "
        "mirar las etiquetas de la primera ni el sufijo del `id`. Luego: "
        "`uv run afg judge calibration-agreement`."
    )


@judge_app.command("calibration-agreement")
def judge_calibration_agreement(
    primary: str = typer.Option("jss", "--primary", help="Quien etiquetó el conjunto."),
    second: str = typer.Option("gm", "--second", help="Quien etiquetó la muestra aparte."),
) -> None:
    """Calcula el acuerdo (kappa) entre las dos personas que etiquetan, por columna.

    Compara la hoja de la segunda persona con el conjunto de calibración, por `id`, y guarda
    el resultado en `reports/judge-calibration/acuerdo-humano.json` para el notebook 05.
    """
    for needed in (CALIBRATION_PATH, SECOND_SHEET_PATH):
        if not needed.exists():
            hint = (
                " Créala con `uv run afg judge calibration-second-sheet`."
                if needed == SECOND_SHEET_PATH
                else ""
            )
            console.print(f"[bold red]No existe {_short(needed)}.[/bold red]{hint}")
            raise typer.Exit(code=1)
    min_kappa = load_thresholds().min_kappa_correct
    try:
        agreements = compute_human_agreement(
            read_label_rows(CALIBRATION_PATH),
            read_label_rows(SECOND_SHEET_PATH),
            min_kappa=min_kappa,
        )
    except AgreementError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    save_agreement(AGREEMENT_PATH, agreements, min_kappa=min_kappa, labelers=(primary, second))
    console.print(f"Acuerdo {primary} vs {second} (kappa mínimo {min_kappa:.2f}):")
    for item in agreements:
        kappa = "indefinido" if item.kappa is None else f"{item.kappa:.3f}"
        verdict = "[green]cumple[/green]" if item.passes else "[red]no cumple[/red]"
        console.print(
            f"  {item.column}: {item.n_agree}/{item.n_items} coinciden, kappa {kappa}, {verdict}"
        )
        if item.disagreements:
            console.print(f"    discrepancias: {', '.join(item.disagreements)}")
    console.print(f"Guardado en {_short(AGREEMENT_PATH)}.")


# --- experiment (OE2/OE3) ------------------------------------------------------------------


def make_c1_embedder() -> OllamaEmbedder:
    """The embedder C1 retrieval uses (model from the config, host from ``OLLAMA_HOST``)."""
    return OllamaEmbedder.from_config()


def make_c1_condition() -> DocumentRagCondition:
    """C1 wired from ``config/experiments.toml`` and the local Ollama."""
    return DocumentRagCondition.from_config(TRANSCRIPTS_DIR)


@c1_app.command("ask")
def c1_ask(
    question: Annotated[str, typer.Argument(help="Pregunta a responder.")],
    series: Annotated[str, typer.Option("--series", help="Serie AMI a consultar, p. ej. ES2015.")],
) -> None:
    """Responde una pregunta con C1 como lo haría `openkos query`, con fragmentos de transcripción.

    Recupera K fragmentos de toda la serie (D15), pregunta al modelo si alcanzan para responder
    y, si es así, redacta la respuesta citando los fragmentos usados (ADR 0006). Sirve para
    probar C1 a mano; no guarda nada.
    """
    import time

    quiet_http_logs()
    try:
        model = GenerationSettings.from_config().model
        needed = [model, configured_embedding_model()]
        absent = missing_models(needed, list_installed_models())
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    except (RuntimeError, ConnectionError, OSError) as exc:
        console.print(
            f"[bold red]No se pudo consultar los modelos instalados en Ollama: {exc}[/bold red] "
            "Comprueba que Ollama esté corriendo."
        )
        raise typer.Exit(code=1) from exc
    if absent:
        for name in absent:
            console.print(
                f"[bold red]Falta el modelo {name} en Ollama:[/bold red] `ollama pull {name}`"
            )
        raise typer.Exit(code=1)

    item = Question(
        id="c1-ask", series_id=series, stratum=QuestionStratum.E1_POINT_FACT, text=question
    )
    started = time.monotonic()
    try:
        condition = make_c1_condition()
        answer, trace = condition.answer_with_trace(item)
    except (ValueError, FileNotFoundError, ChatError, RuntimeError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    elapsed = time.monotonic() - started

    console.print(f"[bold]Resultado:[/bold] {trace.outcome}")
    console.print(f"[bold]Respuesta:[/bold] {answer.text}")
    if answer.cited_evidence:
        console.print("[bold]Citas:[/bold]")
        for span in answer.cited_evidence:
            console.print(f"  {span.meeting_id}: {', '.join(span.dialogue_act_ids)}")
    else:
        console.print("[bold]Citas:[/bold] ninguna")
    console.print(
        f"{len(trace.context_blocks)} fragmentos enviados, {len(trace.omitted)} omitidos por "
        f"presupuesto, {sum(b.excerpted for b in trace.context_blocks)} recortados; "
        f"{elapsed:.1f} s."
    )


@c1_app.command("tune")
def c1_tune() -> None:
    """Mide el recall de evidencia de C1 sobre desarrollo y elige segmentación y K.

    Solo recuperación (sin modelo generativo): para cada combinación de `max_chars`,
    `overlap_turns` y K de `[retrieval.tuning]`, mide qué fracción de los actos de diálogo de
    referencia llegan completos al modelo, es decir, sobrevivientes al recorte del presupuesto
    de contexto de OpenKOS (recall entregado, el que decide), y los compara con los que caen
    en los K fragmentos recuperados sin recortar (recall de fragmentos completos). Indexa la
    serie completa (D15) y usa las preguntas respondibles (E1-E3) del conjunto de calibración
    del juez. Los resultados quedan en `reports/c1-tuning/resultados.json`.
    """
    from rich.table import Table

    quiet_http_logs()
    try:
        config = load_tuning_config()
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    if not CALIBRATION_PATH.exists():
        console.print(
            f"[bold red]No existe {_short(CALIBRATION_PATH)}.[/bold red] "
            "Las preguntas con evidencia salen de la calibración del juez "
            "(`uv run afg judge calibration-answers`)."
        )
        raise typer.Exit(code=1)
    try:
        questions = load_tuning_questions(CALIBRATION_PATH, config.series)
        meetings = [m for series in config.series for m in series_meetings(series, TRANSCRIPTS_DIR)]
    except (CalibrationSetError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    if not questions:
        console.print("[bold red]No hay preguntas respondibles (E1-E3) en la serie.[/bold red]")
        raise typer.Exit(code=1)

    model = configured_embedding_model()
    try:
        absent = missing_models([model], list_installed_models())
    except (RuntimeError, ConnectionError, OSError) as exc:
        console.print(
            f"[bold red]No se pudo consultar los modelos instalados en Ollama: {exc}[/bold red] "
            "Comprueba que Ollama esté corriendo."
        )
        raise typer.Exit(code=1) from exc
    if absent:
        console.print(
            f"[bold red]Falta el modelo de embeddings {model} en Ollama:[/bold red] "
            f"`ollama pull {model}`"
        )
        raise typer.Exit(code=1)

    n_configs = len(config.max_chars) * len(config.overlap_turns)
    console.print(
        f"{len(questions)} preguntas, {len(meetings)} reuniones ({', '.join(config.series)}), "
        f"{n_configs} segmentaciones x {len(config.k)} valores de K."
    )

    def report(max_chars: int, overlap: int, done: int, total: int) -> None:
        console.print(f"  [{done}/{total}] max_chars={max_chars}, overlap_turns={overlap}")

    try:
        results = evaluate_grid(
            questions, meetings, config, make_c1_embedder(), TRANSCRIPTS_DIR, progress=report
        )
        selection = select_winner(results, config.tie_margin)
    except NoEligibleConfigError as exc:
        console.print(
            "[bold red]Ninguna configuración cabe en el presupuesto de contexto "
            f"({config.char_budget} caracteres); no se eligió nada.[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    table = Table(title="Recall de evidencia por configuración")
    for column in (
        "max_chars",
        "overlap",
        "K",
        "recall entregado",
        "recall fragmentos",
        "entregado (car.)",
        "elegible",
    ):
        table.add_column(column, justify="right")
    for r in results:
        table.add_row(
            str(r.max_chars),
            str(r.overlap_turns),
            str(r.k),
            f"{r.mean_delivered_recall:.3f}",
            f"{r.mean_recall:.3f}",
            f"{r.mean_delivered_chars:.0f}",
            "sí" if r.eligible else "no",
        )
    console.print(table)
    win = selection.winner
    console.print(
        f"[bold green]Ganador:[/bold green] max_chars={win.max_chars}, "
        f"overlap_turns={win.overlap_turns}, K={win.k} "
        f"(recall entregado {win.mean_delivered_recall:.3f}). "
        f"{selection.reason}"
    )
    save_tuning_results(
        C1_TUNING_RESULTS_PATH, results, selection, config=config, n_questions=len(questions)
    )
    console.print(f"Resultados guardados en {_short(C1_TUNING_RESULTS_PATH)}.")


@experiment_app.command("a")
def experiment_a() -> None:
    """Experiment A: extraction quality vs. gold (OE2). Requires the corpus and gold set."""
    console.print(
        "[yellow]Not yet implemented: requires a working Extractor "
        "(src/afg/extraction/openkos_adapter.py) and the OE1 gold set. "
        "See thesis section 3, OE2.[/yellow]"
    )
    raise typer.Exit(code=2)


JUDGE_ORDER: PresentationOrder = "reference_first"
JUDGE_TEMPERATURE = 0.0
"""The judge configuration of the calibration's primary run (reference first, temperature 0)."""

EXPERIMENT_B_CONDITIONS: tuple[str, ...] = ("c1", "c2", "c3")
"""Condition ids ``--conditions`` knows; only those in :func:`make_experiment_b_condition` run."""


def make_judge_backend() -> OllamaJudgeBackend:
    """The production judge backend, with the reasoning setting of ``[judge.calibration.think]``."""
    return OllamaJudgeBackend(think=load_think_settings())


def make_experiment_b_condition(condition_id: str) -> Condition:
    """The condition ``condition_id`` wired from the config (only C1 exists so far)."""
    if condition_id == "c1":
        return make_c1_condition()
    raise ValueError(
        f"La condición {condition_id.upper()} no está disponible todavía: C2 y C3 dependen de "
        "OpenKOS y de la anotación de oro (tesis, sección 5.3)."
    )


@experiment_app.command("b")
def experiment_b(
    questions: Annotated[
        Path,
        typer.Option(
            "--questions",
            help="CSV de preguntas: el banco `banco-preguntas.csv` (corre solo las filas "
            "validadas y se niega si hay errores bloqueantes), la hoja `ES2015.preguntas.csv` "
            "o el CSV de preguntas de calibración.",
        ),
    ],
    conditions: Annotated[
        str, typer.Option("--conditions", help="Condiciones separadas por coma; hoy solo `c1`.")
    ] = "c1",
    runs: Annotated[
        int | None,
        typer.Option("--runs", min=1, help="Corridas por pregunta (por defecto runs_per_config)."),
    ] = None,
    run_name: Annotated[
        str | None,
        typer.Option(
            "--run-name",
            help="Nombre de la carpeta en reports/experiment-b/. Repetir un nombre reanuda.",
        ),
    ] = None,
    limit_questions: Annotated[
        int | None, typer.Option("--limit-questions", min=1, help="Solo las N primeras preguntas.")
    ] = None,
) -> None:
    """Experimento B: preguntas x condiciones x corridas, con juicio y citación (OE3).

    Por cada combinación obtiene la respuesta, la juzga con el modelo de `\\[judge]`, calcula la
    corrección de las citas y agrega un registro a `respuestas.jsonl`. Si se interrumpe, al
    repetir el comando con el mismo `--run-name` continúa donde quedó; los registros con error
    se reintentan. La semilla de generación de la corrida r es `seed + r`.
    """
    from datetime import UTC, datetime

    quiet_http_logs()
    wanted = [c.strip().lower() for c in conditions.split(",") if c.strip()]
    unknown = [c for c in wanted if c not in EXPERIMENT_B_CONDITIONS]
    if not wanted or unknown:
        console.print(
            f"[bold red]Condición desconocida: {', '.join(unknown) or '(vacía)'}. "
            f"Opciones: {', '.join(EXPERIMENT_B_CONDITIONS)}.[/bold red]"
        )
        raise typer.Exit(code=1)
    try:
        built = {c.upper(): make_experiment_b_condition(c) for c in dict.fromkeys(wanted)}
        if questions.exists() and is_question_bank(questions):
            bank_report = load_configured_question_bank(questions)
            if not bank_report.has_errors:
                _print_question_bank_report(bank_report)
        bank = load_experiment_questions(questions, limit=limit_questions)
    except (QuestionBankError, ValueError, FileNotFoundError, CalibrationSetError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    config = load_experiments_config()
    budget = config["shared_budget"]
    settings = RunSettings(
        generative_model=str(budget["generative_model"]),
        temperature=float(budget["temperature"]),
        base_seed=int(budget["seed"]),
        runs=runs if runs is not None else int(budget["runs_per_config"]),
        judge_model=get_settings().judge_model,
        judge_order=JUDGE_ORDER,
        judge_seed=int(budget["seed"]),
        judge_temperature=JUDGE_TEMPERATURE,
    )
    try:
        needed = [settings.generative_model, settings.judge_model, configured_embedding_model()]
        absent = missing_models(needed, list_installed_models())
    except (RuntimeError, ConnectionError, OSError) as exc:
        console.print(
            f"[bold red]No se pudo consultar los modelos instalados en Ollama: {exc}[/bold red] "
            "Comprueba que Ollama esté corriendo."
        )
        raise typer.Exit(code=1) from exc
    if absent:
        for name in absent:
            console.print(
                f"[bold red]Falta el modelo {name} en Ollama:[/bold red] `ollama pull {name}`"
            )
        raise typer.Exit(code=1)

    name = run_name or datetime.now(UTC).strftime("b-%Y%m%d-%H%M%S")
    run_dir = EXPERIMENT_B_DIR / name

    def report(done: int, total: int) -> None:
        step = max(total // 10, 1)
        if done == total or done % step == 0:
            console.print(f"  {done}/{total} registros")

    console.print(
        f"{len(bank)} preguntas x {len(built)} condición(es) x {settings.runs} corridas "
        f"-> {_short(run_dir)}"
    )
    try:
        summary = run_experiment_b(
            bank,
            built,
            settings=settings,
            judge_backend=make_judge_backend(),
            run_dir=run_dir,
            partition_of=configured_partition_of(),
            excerpt_for=default_excerpt_for,
            git_commit=current_git_commit(),
            progress=report,
        )
    except (JudgeConfigurationError, ManifestMismatchError, RunAbortedError, ValueError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"{summary.written} registros nuevos, {summary.skipped} ya hechos, "
        f"{summary.errors} con error. Manifiesto en {_short(run_dir / 'manifest.json')}."
    )


def _load_run_records(run_name: str) -> tuple[Path, list[dict[str, Any]]]:
    """The run folder and the latest record of each key; exits with a message when absent."""
    from afg.experiments.runner import RECORDS_FILE, load_records

    run_dir = EXPERIMENT_B_DIR / run_name
    records = load_records(run_dir / RECORDS_FILE, latest_only=True)
    if not records:
        console.print(f"[bold red]No hay registros en {_short(run_dir / RECORDS_FILE)}.[/bold red]")
        raise typer.Exit(code=1)
    return run_dir, records


@experiment_app.command("b-report")
def experiment_b_report(
    run_name: Annotated[
        str, typer.Option("--run-name", help="Carpeta de la corrida en reports/experiment-b/.")
    ],
    descriptive: Annotated[
        bool,
        typer.Option(
            "--descriptive",
            help="Vista descriptiva (--descriptive) de registros de desarrollo o mixtos: "
            "se guarda aparte y no es reportable.",
        ),
    ] = False,
) -> None:
    """Análisis del Experimento B: tasas, intervalos bootstrap y comparación D16 (OE3).

    Agrega por condición y estrato con intervalos que remuestrean preguntas, y compara C2 con
    C1 en E3 (criterio principal D16) y C2 con C3 (secundario). Se niega a producir tablas
    reportables con registros de desarrollo o mixtos.
    """
    import json

    from rich.table import Table

    from afg.evaluation.scoring import DevelopmentResultError, interval_settings_from_config
    from afg.experiments.analysis import CRITERION_NOTE, analyze_runs, report_to_dict

    run_dir, records = _load_run_records(run_name)
    config = load_experiments_config()
    try:
        report = analyze_runs(
            records,
            settings=interval_settings_from_config(),
            min_questions=int(config["question_bank"]["min_questions"]),
            min_runs=int(config["shared_budget"]["runs_per_config"]),
            allow_development=descriptive,
        )
    except DevelopmentResultError as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        console.print("Para explorar sin reportar, usar la opción --descriptive.")
        raise typer.Exit(code=1) from exc

    label = "reportable" if report.reportable else f"DESCRIPTIVO, partición {report.partition}"
    table = Table(title=f"Experimento B, {run_name} ({label})")
    for column in ("Condición", "Estrato", "Preguntas", "Correcta", "Soportada", "Cita", "Fallas"):
        table.add_column(column)

    def fmt(estimate: Any) -> str:
        if estimate is None:
            return "-"
        return f"{estimate.point:.2f} [{estimate.lower:.2f}, {estimate.upper:.2f}]"

    for cell in report.cells:
        table.add_row(
            cell.condition,
            cell.stratum,
            str(cell.questions),
            fmt(cell.metrics.get("correct")),
            fmt(cell.metrics.get("evidence_supported")),
            fmt(cell.metrics.get("citation_correct")),
            f"juez {cell.judge_failures}, error {cell.errors}",
        )
    console.print(table)
    for comparison in report.comparisons:
        if comparison.primary:
            console.print(
                f"[bold]Principal (D16)[/bold] C2 frente a C1 en E3: diferencia "
                f"{comparison.difference:+.2f} [{comparison.difference_lower:+.2f}, "
                f"{comparison.difference_upper:+.2f}] sobre {comparison.n_pairs} preguntas: "
                f"{comparison.criterion}. Robustez (intervalos independientes "
                f"{'solapados' if comparison.intervals_overlap else 'disjuntos'}): "
                f"{comparison.nonoverlap_criterion}."
            )
    console.print(f"[dim]{CRITERION_NOTE}[/dim]")
    for warning in report.warnings:
        console.print(f"[yellow]{escape(warning)}[/yellow]")

    target = run_dir / ("analisis.json" if report.reportable else "analisis-descriptivo.json")
    target.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    console.print(f"Guardado en {_short(target)}.")


HUMAN_SHEET_FILE = "muestra-juez.csv"
HUMAN_KEY_FILE = "muestra-juez.clave.csv"
HUMAN_CHECK_FILE = "juez-humano.json"


@experiment_app.command("b-sample")
def experiment_b_sample(
    run_name: Annotated[
        str, typer.Option("--run-name", help="Carpeta de la corrida en reports/experiment-b/.")
    ],
    questions: Annotated[
        Path,
        typer.Option(
            "--questions",
            help="CSV de preguntas de la corrida: aporta la respuesta de referencia y el pasaje "
            "de transcripción que vio el juez. Es obligatorio.",
        ),
    ],
    force: Annotated[
        bool, typer.Option("--force", help="Sobrescribir una hoja que ya tiene etiquetas.")
    ] = False,
) -> None:
    """Muestra para la verificación humana: una corrida sorteada por pregunta y condición.

    El tamaño por condición y estrato es el 20 % de las respuestas juzgadas (con tope en los
    pares pregunta-condición disponibles). Escribe la hoja ciega (sin condición ni veredicto del
    juez) y, aparte, la clave con la condición y el veredicto del juez. La semilla es
    `\\[shared_budget].seed`.
    """
    from afg.evaluation.judge_human_check import (
        question_context_for,
        select_human_sample,
        write_human_sample,
    )

    run_dir, records = _load_run_records(run_name)
    config = load_experiments_config()
    try:
        bank = load_experiment_questions(questions)
        context_for = question_context_for(bank)
    except (QuestionBankError, ValueError, FileNotFoundError, CalibrationSetError) as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    try:
        sample = select_human_sample(
            records,
            fraction=float(config["evaluation"]["human_validation_fraction"]),
            seed=int(config["shared_budget"]["seed"]),
            reference_answers={q.id: q.reference_answer or "" for q in bank},
            context_for=context_for,
        )
        write_human_sample(
            run_dir / HUMAN_SHEET_FILE, run_dir / HUMAN_KEY_FILE, sample, force=force
        )
    except (ValueError, FileNotFoundError, SecondSheetLabeledError) as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    for (condition, stratum), (judged, taken) in sample.per_cell.items():
        pairs = sample.pairs_per_cell[(condition, stratum)]
        console.print(
            f"  {condition} {stratum}: {taken} de {pairs} pares pregunta-condición "
            f"({judged} respuestas juzgadas)"
        )
    console.print(
        f"{len(sample.sheet_rows)} filas. Hoja para la persona: "
        f"{_short(run_dir / HUMAN_SHEET_FILE)}; clave (no compartir): "
        f"{_short(run_dir / HUMAN_KEY_FILE)}."
    )


@experiment_app.command("b-human-check")
def experiment_b_human_check(
    run_name: Annotated[
        str, typer.Option("--run-name", help="Carpeta de la corrida en reports/experiment-b/.")
    ],
) -> None:
    """Acuerdo juez-humano (kappa de Cohen) por etiqueta, con el umbral prerregistrado.

    `correct` decide el juicio automático de la métrica principal: si su kappa no alcanza
    `\\[judge.calibration].min_kappa_correct`, la corrección se reporta solo con evaluación
    humana. `evidence_supported` tiene su propio indicador de confiable o no confiable. Siempre
    se informan el acuerdo observado y la prevalencia junto al kappa.
    """
    from afg.evaluation.judge_human_check import (
        check_judge_against_humans,
        read_csv_rows,
        save_judge_human_check,
    )

    run_dir = EXPERIMENT_B_DIR / run_name
    sheet, key = run_dir / HUMAN_SHEET_FILE, run_dir / HUMAN_KEY_FILE
    for needed in (sheet, key):
        if not needed.exists():
            console.print(
                f"[bold red]No existe {_short(needed)}.[/bold red] "
                "Crearla con `uv run afg experiment b-sample`."
            )
            raise typer.Exit(code=1)
    min_kappa = load_thresholds().min_kappa_correct
    try:
        check = check_judge_against_humans(
            read_csv_rows(key), read_csv_rows(sheet), min_kappa=min_kappa
        )
    except (AgreementError, CalibrationSetError) as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    save_judge_human_check(run_dir / HUMAN_CHECK_FILE, check)
    console.print(
        f"Acuerdo juez-humano sobre {check.n_items} respuestas (kappa mínimo {min_kappa:.2f}):"
    )
    for column in check.columns:
        kappa = "indefinido" if column.kappa is None else f"{column.kappa:.3f}"
        verdict = "[green]cumple[/green]" if column.passes else "[red]no cumple[/red]"
        console.print(
            f"  {column.column}: acuerdo observado {column.n_agree}/{column.n_items} "
            f"({column.observed_agreement:.0%}), kappa {kappa}, {verdict}; "
            f"prevalencia de «sí»: juez {column.judge_positive_rate:.0%}, "
            f"personas {column.human_positive_rate:.0%}"
        )
    console.print(f"[bold]{check.decision}[/bold]")
    console.print(f"[bold]{check.evidence_decision}[/bold]")
    console.print(f"Guardado en {_short(run_dir / HUMAN_CHECK_FILE)}.")


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
