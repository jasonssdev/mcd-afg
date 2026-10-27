"""``afg`` -- command-line entry point for the evaluation harness.

Every command is written to either work or fail with a clear, actionable message when the
AMI corpus has not been downloaded yet -- most commands cannot do anything useful before
paso cero (thesis section 5.0), and they say so instead of crashing with a stack trace.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import typer.rich_utils as typer_rich_utils
from rich.console import Console
from rich.markup import escape

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from afg.annotation.workspace import AnnotationPlan, WorkspacePaths
    from afg.conditions.c1_chunking import FrozenTurn

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
from afg.conditions.c0_closed_book import (
    ClosedBookCondition,
    EvaluationSeriesError,
    require_development_series,
)
from afg.conditions.c1_ablation import ABLATION_PATH as C1_ABLATION_PATH
from afg.conditions.c1_ablation import evaluate_modes, save_ablation_results
from afg.conditions.c1_document_rag import (
    ChatError,
    DocumentRagCondition,
    GenerationSettings,
    OllamaChatBackend,
)
from afg.conditions.c1_retrieval import OllamaEmbedder, configured_embedding_model
from afg.conditions.c1_tuning import (
    RESULTS_PATH as C1_TUNING_RESULTS_PATH,
)
from afg.conditions.c1_tuning import (
    NoEligibleConfigError,
    TuningConfig,
    TuningQuestion,
    evaluate_grid,
    load_pinned_c1_params,
    load_tuning_config,
    load_tuning_questions,
    questions_with_any_delivered_hit,
    questions_with_any_hit,
    save_tuning_results,
    select_winner,
    series_meetings,
)
from afg.conditions.c2_compiled_auto import CompiledAutoCondition
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
    development_series,
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
from afg.experiments.provenance import LiveProbe, ProvenanceProbe, collect_provenance
from afg.experiments.question_bank import (
    QuestionBankIssue,
    QuestionBankReport,
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
from afg.extraction.openkos.commands import OpenKosError, SubprocessRunner
from afg.extraction.openkos.settings import openkos_run_settings
from afg.extraction.openkos_adapter import OpenKosAdapter
from afg.shared.config import Settings, get_settings, load_corpus_config, load_experiments_config
from afg.shared.logging import configure_logging, get_logger, quiet_http_logs
from afg.shared.paths import (
    AMI_DIR,
    EXPERIMENT_A_DIR,
    EXPERIMENT_B_DIR,
    GOLD_DECISIONS_DIR,
    GOLD_RELATIONS_DIR,
    OPENKOS_WORKSPACES_DIR,
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

# Section titles of ``--help`` in Spanish (typer reads these module constants at render time).
typer_rich_utils.COMMANDS_PANEL_TITLE = "Comandos"
typer_rich_utils.OPTIONS_PANEL_TITLE = "Opciones"
typer_rich_utils.ARGUMENTS_PANEL_TITLE = "Argumentos"

_PANEL_ANNOTATORS = "Para anotadores"
_PANEL_MAINTENANCE = "Para mantenimiento (mantenedor)"

app = typer.Typer(
    name="afg",
    help="Banco de pruebas de la tesis: RAG sobre documentos frente a representaciones "
    "compiladas de decisiones, sobre el corpus de reuniones AMI. Quien anota usa solo "
    "`afg gold` (ver `afg gold --help`).",
    no_args_is_help=True,
)
corpus_app = typer.Typer(
    help="Descarga, inventario y transcripciones del corpus AMI (paso cero, sección 5.0)."
)
biblio_app = typer.Typer(
    help="Cobertura y estadísticas de la bibliografía (bibliography/refs.bib)."
)
gold_app = typer.Typer(
    help="Conjunto de referencia de OE1: anotación de decisiones y relaciones. Quien anota "
    "usa los comandos de «Para anotadores»; el resto es del mantenedor."
)
judge_app = typer.Typer(
    help="Selección del modelo juez: preguntas, respuestas y calibración (issue #82)."
)
c1_app = typer.Typer(help="C1 (RAG sobre documentos): ajuste de la segmentación y de K (ADR 0005).")
experiment_app = typer.Typer(
    help="OE2/OE3: corre el Experimento A y el Experimento B (tesis, sección 3)."
)
skills_app = typer.Typer(help="Instala, verifica y enlaza las skills de .agents/skills/.")

app.add_typer(gold_app, name="gold")
app.add_typer(corpus_app, name="corpus", rich_help_panel=_PANEL_MAINTENANCE)
app.add_typer(biblio_app, name="biblio", rich_help_panel=_PANEL_MAINTENANCE)
app.add_typer(judge_app, name="judge", rich_help_panel=_PANEL_MAINTENANCE)
app.add_typer(c1_app, name="c1", rich_help_panel=_PANEL_MAINTENANCE)
app.add_typer(experiment_app, name="experiment", rich_help_panel=_PANEL_MAINTENANCE)
app.add_typer(skills_app, name="skills", rich_help_panel=_PANEL_MAINTENANCE)


@app.callback()
def main(
    log_level: str | None = typer.Option(
        None, help="Nivel de registro (log). Si se omite, usa AFG_LOG_LEVEL o INFO."
    ),
) -> None:
    configure_logging(log_level or Settings().log_level)
    ensure_dirs()


# --- skills -----------------------------------------------------------------------------


@skills_app.command("sync-assets")
def skills_sync_assets(
    skill: Annotated[str, typer.Argument(help="Nombre de la skill, p. ej. deck-uc.")],
    source: Annotated[
        Path | None,
        typer.Option(
            "--source",
            help="Carpeta compartida sincronizada; por defecto, AFG_SKILL_ASSETS_DIR. Los "
            "archivos se leen de <source>/<skill>/ si esa carpeta existe; si no, de <source>/.",
        ),
    ] = None,
) -> None:
    """Copia los archivos no versionados de una skill, tras verificar su SHA-256."""
    origin = source or get_settings().skill_assets_dir
    if origin is None:
        console.print(
            "[red]Falta la carpeta de origen.[/red] Define AFG_SKILL_ASSETS_DIR en .env con la "
            "carpeta compartida sincronizada en tu equipo, o pasa --source."
        )
        raise typer.Exit(code=1)
    try:
        copied = sync_assets(skill, origin, SKILLS_DIR)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    if copied:
        console.print(f"Instalados {len(copied)} archivo(s) de '{skill}': {', '.join(copied)}")
    else:
        console.print(f"Los archivos de '{skill}' ya estaban al día.")


@skills_app.command("verify")
def skills_verify(
    skill: Annotated[str, typer.Argument(help="Nombre de la skill, p. ej. deck-uc.")],
) -> None:
    """Verifica los archivos instalados de una skill contra su lista de sumas de control."""
    try:
        verify_installed(skill, SKILLS_DIR)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    console.print(
        f"Los archivos de '{skill}' están completos y coinciden con sus sumas de control."
    )


@skills_app.command("link")
def skills_link(
    skill: Annotated[str, typer.Argument(help="Nombre de la skill, p. ej. deck-uc.")],
    dest_dir: Annotated[
        Path, typer.Argument(help="Carpeta desde la que una herramienta lee skills.")
    ],
) -> None:
    """Enlaza una skill en otra carpeta y mantiene esa carpeta fuera de git."""
    try:
        link = link_skill(skill, dest_dir, SKILLS_DIR, PROJECT_ROOT)
    except SkillAssetsError as error:
        console.print(f"[red]{error}[/red]", markup=True, highlight=False)
        raise typer.Exit(code=1) from error
    console.print(f"Enlazado: {link} -> {link.readlink()}")


# --- corpus -----------------------------------------------------------------------------


def _print_corpus_licence() -> None:
    """Tell the person, in Spanish, what is about to be downloaded and under which terms."""
    cfg = load_corpus_config()
    licence = cfg["corpus"]["licence"]
    annotations = cfg["corpus"]["annotations"]
    console.print(
        f"[bold]Licencia:[/bold] el corpus AMI se publica con la licencia {licence['name']}: "
        "se puede usar citando la fuente. Texto de la licencia: "
        f"{licence['licence_page']}"
    )
    console.print(f"[bold]Fuente:[/bold] {annotations['url']}")
    console.print(
        f"[bold]Tamaño:[/bold] la descarga pesa unos {annotations['approximate_size_mb']} MB; "
        f"ya extraído, el corpus ocupa unos {annotations['extracted_size_mb']} MB en disco."
    )


def _confirm_and_download_corpus(yes: bool) -> None:
    """Print the licence, ask for confirmation unless ``yes``, then download.

    Shared by ``corpus download`` and ``gold setup`` so the licence text and the
    confirmation are asked in exactly one place. Exits the process (code 1) on decline or
    on download failure.
    """
    _print_corpus_licence()

    if not yes and not typer.confirm("¿Descargar el corpus ahora?"):
        console.print("Cancelado: no se descargó nada.")
        raise typer.Exit(code=1)

    try:
        result = download_annotations(AMI_DIR)
    except DownloadError as exc:
        console.print(f"[bold red]La descarga falló:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"Descargados {result.bytes_downloaded} bytes y extraídos en {result.extracted_to}"
    )


@corpus_app.command("download")
def corpus_download(
    yes: bool = typer.Option(False, "--yes", help="Omite la confirmación de descarga."),
) -> None:
    """Descarga y extrae las anotaciones manuales de AMI (CC BY 4.0), tras mostrar la licencia."""
    _confirm_and_download_corpus(yes)


@corpus_app.command("inventory")
def corpus_inventory() -> None:
    """Paso cero: verifica las series y cuenta decisiones y enlaces candidatos."""
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    try:
        inventory = build_inventory(ami_root)
    except CorpusNotDownloadedError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    render_inventory_table(inventory, console)
    out_path = write_inventory_csv(inventory)
    console.print(f"Escrito: {out_path}")


@corpus_app.command("participants")
def corpus_participants() -> None:
    """Desglose de participantes por inglés nativo o no nativo y por rol, en todo el corpus y por
    serie objetivo (tesis, secciones 5.1 y 6.3)."""
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]No se encontró el corpus AMI en {ami_root}. "
            "Ejecuta primero `uv run afg corpus download`.[/bold red]"
        )
        raise typer.Exit(code=1)

    corpus_wide = load_native_language_records(ami_root)
    series_participants = load_participants(ami_root)
    if not corpus_wide or not series_participants:
        console.print(
            "[yellow]No se pudo cargar ningún participante del archivo de recursos del corpus. "
            "Es lo esperado mientras no se confirme el formato real del archivo con un corpus "
            "descargado (ver src/afg/corpus/participants.py).[/yellow]"
        )
        raise typer.Exit(code=1)

    render_participants_table(corpus_wide, series_participants, console)
    out_path = write_participants_csv(series_participants)
    console.print(f"Escrito: {out_path}")


_TRANSCRIPTS_SERIES_OPTION = typer.Option(
    None, "--series", help="Serie de AMI a renderizar, p. ej. IS1004. Repetible; sin ella, todas."
)
_TRANSCRIPTS_OUT_OPTION = typer.Option(
    None,
    "--out",
    help="Carpeta de salida de las transcripciones (por defecto, data/interim/transcripts).",
)


@corpus_app.command("transcripts")
def corpus_transcripts(
    series: list[str] | None = _TRANSCRIPTS_SERIES_OPTION,
    out: Path | None = _TRANSCRIPTS_OUT_OPTION,
    force: bool = typer.Option(
        False, "--force/--no-force", help="Sobrescribe una carpeta de salida que ya tiene archivos."
    ),
) -> None:
    """Congela las transcripciones (.md y .jsonl) y su manifiesto (tesis, secciones 5.3 y 5.4).

    No sobrescribe una carpeta con archivos salvo con --force: las transcripciones se congelan
    antes de anotar, y volver a renderizarlas bajo quienes anotan invalidaría sus posiciones.
    """
    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    out_dir = out or TRANSCRIPTS_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]No se encontró el corpus AMI en {ami_root}. "
            "Ejecuta primero `uv run afg corpus download`.[/bold red]"
        )
        raise typer.Exit(code=1)

    meeting_ids = discover_meeting_ids(ami_root, series)
    if not meeting_ids:
        console.print(
            f"[bold red]No se encontraron reuniones en {ami_root}/words/"
            f"{' para la serie ' + ', '.join(series) if series else ''}.[/bold red]"
        )
        raise typer.Exit(code=1)

    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        console.print(
            f"[bold red]{out_dir} ya existe y no está vacía. Las transcripciones se congelan "
            "antes de anotar; volver a renderizarlas bajo quienes anotan invalidaría sus "
            "posiciones de carácter sin avisar. Usa --force para sobrescribir.[/bold red]"
        )
        raise typer.Exit(code=1)

    # A render into the canonical transcripts directory writes the tracked manifest at
    # TABLES_DIR (and merges into it, see write_manifest_csv). Any other --out is a
    # scratch render and must not touch that tracked file at all -- its manifest goes
    # next to its own output instead.
    is_canonical_out_dir = out_dir.resolve() == TRANSCRIPTS_DIR.resolve()
    manifest_dir = TABLES_DIR if is_canonical_out_dir else out_dir

    console.print(f"Renderizando {len(meeting_ids)} reunión(es)...")
    result = render_meetings(ami_root, meeting_ids, out_dir, manifest_dir=manifest_dir)

    for meeting_id in result.meeting_ids:
        console.print(f"Escrito: {out_dir / f'{meeting_id}.md'}")
        console.print(f"Escrito: {out_dir / f'{meeting_id}.jsonl'}")
    console.print(f"Escrito: {result.manifest_path}")

    console.print(
        f"[bold]{len(result.meeting_ids)} reunión(es) renderizada(s)[/bold], "
        f"{result.total_turns} turnos, {result.total_characters} caracteres, "
        f"renderizador {result.renderer_revision}."
    )
    console.print(f"Transcripciones: {result.out_dir}")
    console.print(f"Manifiesto:      {result.manifest_path}")


# --- bibliography -------------------------------------------------------------------------


@biblio_app.command("audit")
def biblio_audit() -> None:
    """Cobertura por sección de la tesis, preprints sin revisar y DOI faltantes o repetidos."""
    audit = run_audit()
    render_biblio_table(audit, console)
    out_path = write_biblio_csv(audit)
    console.print(f"Escrito: {out_path}")


@biblio_app.command("stats")
def biblio_stats() -> None:
    """Conteo por sección de la tesis y división entre preprints y artículos revisados por pares."""
    entries = load_library()
    console.print(f"Total de entradas: {len(entries)}")
    by_section: dict[str, int] = {}
    for entry in entries:
        for section in entry.sections:
            by_section[section] = by_section.get(section, 0) + 1
    for section in sorted(by_section):
        console.print(f"  {section}: {by_section[section]}")
    preprints = sum(1 for e in entries if e.is_preprint)
    console.print(f"Preprints (sin revisión por pares): {preprints}")
    console.print(f"Revisadas por pares o estándar: {len(entries) - preprints}")


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


@gold_app.command("build", rich_help_panel=_PANEL_MAINTENANCE)
def gold_build(
    series: str = typer.Option(..., "--series", help="Serie de AMI, p. ej. IS1004."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Regenera aunque haya anotación cargada en los archivos derivados de la serie. "
        "Desalinea `afg gold validate` para todo el mundo.",
    ),
) -> None:
    """(Mantenedor) Genera el archivo base de la Tarea A de una serie (manual, secciones 2 y 3).

    Escribe ``data/processed/decisions/<serie>.decisions.csv``. Es un
    archivo de trabajo para quien anota, no un conjunto de referencia
    terminado: ``machine_flags`` son solo pistas de triaje, nunca un
    veredicto, y ``status``, ``decision_object``, ``decision_content``,
    ``annotator`` y ``notes`` salen siempre vacías para que las llene una
    persona. Se niega a correr si algún
    ``<serie>.decisions.<iniciales>.csv`` o
    ``<serie>.candidates.<iniciales>.csv`` derivado ya tiene anotación,
    salvo con ``--force``.
    """
    from afg.annotation.goldset import build_gold_decisions, write_gold_decisions_csv

    _refuse_or_warn_if_series_annotated(series, force=force)

    settings = get_settings()
    ami_root = settings.ami_root or AMI_DIR
    if not ami_root.exists():
        console.print(
            f"[bold red]No se encontró el corpus AMI en {ami_root}. "
            "Ejecuta primero `uv run afg corpus download`.[/bold red]"
        )
        raise typer.Exit(code=1)

    rows = build_gold_decisions(ami_root, series)
    if not rows:
        console.print(
            f"[bold red]No se encontraron oraciones DECISIONS del resumen abstractivo para "
            f"la serie {series!r} en {ami_root}. Revisa el identificador de la serie "
            "(p. ej. 'IS1004') y que el corpus se haya extraído bien.[/bold red]"
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
        f"[bold]Serie {series}[/bold]: {len(rows)} oraciones de decisión en "
        f"{len(per_meeting)} reuniones."
    )
    for meeting_id in sorted(per_meeting):
        console.print(f"  {meeting_id}: {per_meeting[meeting_id]}")

    console.print(
        "[bold]machine_flags[/bold] son pistas de triaje, NO un veredicto: status, "
        "decision_object, decision_content, annotator y notes se escribieron VACÍOS en "
        "todas las filas y las debe llenar una persona que anota:"
    )
    if flag_counts:
        for flag in sorted(flag_counts):
            console.print(f"  {flag}: {flag_counts[flag]}")
    else:
        console.print("  (ninguna)")

    console.print(f"Escrito: {out_path}")


@gold_app.command("link", rich_help_panel=_PANEL_MAINTENANCE)
def gold_link() -> None:
    """(Mantenedor) Sin implementar: espera OpenKOS ~0.6.0 (sale con código 2).

    Candidatos de relación entre reuniones (tesis, secciones 3 y 5.1). Hasta entonces,
    `afg gold candidates` genera los candidatos de una serie.
    """
    console.print(
        "[yellow]Sin implementar: espera OpenKOS ~0.6.0. Necesita el conjunto de decisiones "
        "de referencia (`afg gold build`). Mientras tanto, `afg gold candidates` genera los "
        "pares candidatos de una serie.[/yellow]"
    )
    raise typer.Exit(code=2)


def _print_pooled_agreement() -> None:
    from afg.annotation import pooled

    report = pooled.pooled_agreement_report(_plan_or_exit())
    if not report:
        console.print("[bold red]Ninguna serie tiene la adjudicación completa.[/bold red]")
        raise typer.Exit(code=1)
    for group in report:
        console.print(f"[bold]Kappa agrupado ({group.scope})[/bold]: {', '.join(group.series)}")
        for item in group.axes:
            console.print(
                f"  {item.axis:<10} n={item.n_items:<3} desacuerdos={item.n_disagreements:<3} "
                f"kappa={item.kappa:.3f}  acuerdo crudo={item.percent_agreement:.1%}"
            )
    out_path = pooled.write_pooled_csv(report, TABLES_DIR / "agreement-pooled.csv")
    console.print(f"Escrito: {out_path}")


@gold_app.command("agreement", rich_help_panel=_PANEL_MAINTENANCE)
def gold_agreement(
    series: str | None = typer.Option(None, "--series", help="Serie de AMI, p. ej. IS1004."),
    pooled: bool = typer.Option(
        False,
        "--pooled",
        help="Kappa agrupado de todas las series adjudicadas (en total y por fase).",
    ),
) -> None:
    """(Mantenedor) Calcula el kappa de Cohen de existencia, tipo y dirección (manual, sección 6).

    Lee cada ``data/processed/relations/<serie>.candidates.<iniciales>.csv``
    (uno por anotador independiente) y escribe
    ``reports/tables/<serie>.agreement.csv``. Con ``--pooled`` calcula un solo kappa por eje
    sobre los ítems de todas las series adjudicadas (no el promedio de kappas) y escribe
    ``reports/tables/agreement-pooled.csv``.
    """
    from afg.annotation.agreement import (
        AgreementInputError,
        annotator_csvs,
        compute_series_agreement,
        write_agreement_csv,
    )

    if pooled:
        _print_pooled_agreement()
        return
    if series is None:
        console.print("[bold red]Indica --series <serie> o --pooled.[/bold red]")
        raise typer.Exit(code=2)

    pattern = f"{series}.candidates.<initials>.csv"
    paths = annotator_csvs(GOLD_RELATIONS_DIR, series, "candidates")
    if len(paths) < 2:
        console.print(
            f"[bold red]Hacen falta al menos 2 archivos de anotadores que coincidan con "
            f"data/processed/relations/{pattern} (hay {len(paths)}). La copia independiente "
            "de cada anotador debe llamarse <serie>.candidates.<iniciales>.csv, según la "
            "sección 6 del manual de anotación.[/bold red]"
        )
        raise typer.Exit(code=1)
    if len(paths) > 2:
        console.print(
            f"[yellow]Se encontraron {len(paths)} archivos de anotadores; se usan los dos "
            f"primeros ({paths[0].name}, {paths[1].name}): el kappa de Cohen es de a pares."
            "[/yellow]"
        )

    try:
        result = compute_series_agreement(paths)
    except AgreementInputError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    out_path = TABLES_DIR / f"{series}.agreement.csv"
    write_agreement_csv(result, out_path)

    console.print(
        f"[bold]Serie {series}[/bold]: {result.annotator_a} vs {result.annotator_b} "
        f"({result.n_items} ítems pareados)."
    )
    console.print(
        f"  kappa de existencia: {result.existence_kappa:.3f} "
        f"({len(result.existence_disagreements)} desacuerdos)"
    )
    if result.type_kappa is not None:
        console.print(
            f"  kappa de tipo:      {result.type_kappa:.3f} "
            f"({len(result.type_disagreements)} desacuerdos, sobre "
            f"{result.n_type_items} pares que ambos anotadores marcaron como vínculo existente)"
        )
    else:
        console.print(
            "  kappa de tipo:      n/d (ningún par fue marcado como vínculo existente por "
            "ambos anotadores)"
        )
    console.print(
        f"  kappa de dirección: {result.direction_kappa:.3f} "
        f"({len(result.direction_disagreements)} desacuerdos)"
    )
    for axis, disagreements in (
        ("existencia", result.existence_disagreements),
        ("tipo", result.type_disagreements),
        ("dirección", result.direction_disagreements),
    ):
        if disagreements:
            console.print(f"  desacuerdos de {axis} (por adjudicar): {', '.join(disagreements)}")

    console.print(f"Escrito: {out_path}")


@gold_app.command("evidence", hidden=True)
def gold_evidence(
    meeting: Annotated[
        str | None, typer.Option("--meeting", help="Reunión, p. ej. ES2015a.")
    ] = None,
    term: Annotated[str | None, typer.Option("--term", help="Palabra o frase a buscar.")] = None,
) -> None:
    """Nombre anterior de `afg gold evidencia`, que ahora cubre también este uso."""
    console.print(
        "[dim]Este comando se llama ahora `uv run afg gold evidencia`; se ejecuta ese.[/dim]"
    )
    gold_evidencia(meeting=meeting, term=term, turns=None, decision=None)


@gold_app.command("evidencia", rich_help_panel=_PANEL_ANNOTATORS)
def gold_evidencia(
    meeting: Annotated[
        str | None, typer.Option("--meeting", help="Reunión de AMI, p. ej. ES2015a.")
    ] = None,
    term: Annotated[
        str | None,
        typer.Option(
            "--term", help="Palabra o frase a buscar en la reunión (sin distinguir mayúsculas)."
        ),
    ] = None,
    turns: Annotated[
        str | None,
        typer.Option("--turnos", help="Turno o rango de turnos de esa reunión, p. ej. 40 o 40-46."),
    ] = None,
    decision: Annotated[
        str | None,
        typer.Option(
            "--decision",
            help="Decisión ya adjudicada (p. ej. ES2015a.d01): su evidencia lista para pegar.",
        ),
    ] = None,
) -> None:
    """Busca en la transcripción de una reunión (Tarea A y banco de preguntas).

    \b
    Cuándo usarlo:
    1. Tarea A, si `evidence_text` no alcanza: busca una palabra con su
       contexto. Ejemplo: --meeting ES2015a --term "remote" (con
       --turnos 40-46 para ver un tramo).
    2. Banco de preguntas, para llenar `reference_evidence`: cada turno
       trae quién habló, el texto y el valor para pegar en la celda.
       Si la decisión ya está adjudicada, --decision ES2015a.d01 lo da
       directo.

    Necesita las transcripciones: `uv run afg gold setup`.
    """
    from afg.annotation.evidence_lookup import (
        EvidenceLookupError,
        find_turns,
        format_evidence,
        parse_turn_range,
    )

    try:
        if decision:
            _evidencia_por_decision(decision)
            return
        if not meeting or not (term or turns):
            console.print(
                "[bold red]Indica una forma de búsqueda:[/bold red] `--decision ES2015a.d01`, o "
                '`--meeting ES2015a` con `--term "palabra"` y/o `--turnos 40-46`.'
            )
            raise typer.Exit(code=1)
        found = find_turns(
            meeting,
            term=term,
            turn_range=parse_turn_range(turns) if turns else None,
            transcripts_dir=TRANSCRIPTS_DIR,
        )
    except EvidenceLookupError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    if not found:
        what = f"{term!r}" if term else f"los turnos {turns}"
        console.print(f"[yellow]No hay turnos de {meeting} con {what}.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"[bold]{len(found)} turno(s) de {meeting}:[/bold]")
    for turn in found:
        _print_turn(turn)
        console.print(
            f"  para pegar: {format_evidence(meeting, [turn])}", markup=False, soft_wrap=True
        )
    if len(found) > 1:
        console.print("\n[bold]Todos los turnos juntos:[/bold]")
        console.print(f"  {format_evidence(meeting, found)}", markup=False, soft_wrap=True)
    console.print(
        "\nEn la celda `reference_evidence` de una pregunta se pega solo lo que respalda la "
        "respuesta; varias reuniones se separan con `|`.",
        markup=False,
    )


def _print_turn(turn: FrozenTurn, only: Collection[str] | None = None) -> None:
    console.print(f"\n[bold]turno {turn.turn_index}[/bold] ({turn.role})")
    console.print(f"  {turn.text}", markup=False, soft_wrap=True)
    shown = [a for a in turn.dialogue_act_ids if only is None or a in only]
    console.print(f"  actos: {'; '.join(shown)}", markup=False, soft_wrap=True)


def _evidencia_por_decision(decision: str) -> None:
    from afg.annotation.evidence_lookup import (
        EvidenceLookupError,
        format_evidence,
        turns_with_acts,
    )
    from afg.annotation.goldset import summlink_dialogue_act_ids
    from afg.evaluation.reference import (
        DecisionNotFoundError,
        NotAdjudicatedError,
        adjudicated_decision_evidence,
    )

    meeting_id, _, _ = decision.partition(".")
    series = meeting_id[:-1]
    path = GOLD_DECISIONS_DIR / f"{series}.decisions.adjudicated.csv"
    if not path.is_file():
        console.print(
            f"[bold red]La serie {series} aún no tiene decisiones adjudicadas "
            f"({_short(path)}).[/bold red] Mientras tanto busca en la transcripción: "
            f'`uv run afg gold evidencia --meeting {meeting_id} --term "palabra"`.'
        )
        raise typer.Exit(code=1)
    if not (AMI_DIR.exists() and TRANSCRIPTS_DIR.exists()):
        console.print(
            "[bold red]Falta el corpus o las transcripciones.[/bold red] "
            "Corre `uv run afg gold setup`."
        )
        raise typer.Exit(code=1)
    try:
        acts = summlink_dialogue_act_ids(AMI_DIR, meeting_id)
        info = adjudicated_decision_evidence(
            path, decision, sentence_acts=acts, transcripts_dir=TRANSCRIPTS_DIR
        )
        if info.final_status != "decision":
            console.print(
                f"[bold red]{decision} quedó adjudicada como `{info.final_status}`, no como "
                "decisión:[/bold red] no sirve de base para una pregunta."
            )
            raise typer.Exit(code=1)
        if not info.act_ids:
            console.print(
                f"[bold red]No se encontró evidencia automática para {decision}.[/bold red] "
                f"Búscala a mano: `uv run afg gold evidencia --meeting {meeting_id} --term "
                '"palabra"`.'
            )
            raise typer.Exit(code=1)
        found = turns_with_acts(meeting_id, info.act_ids, transcripts_dir=TRANSCRIPTS_DIR)
    except (EvidenceLookupError, DecisionNotFoundError, NotAdjudicatedError, ValueError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]{decision}[/bold]: {info.final_object} — {info.final_content}")
    console.print(f"Evidencia en {len(found)} turno(s) de {meeting_id}:")
    for turn in found:
        _print_turn(turn, set(info.act_ids))
    console.print("\n[bold]Para pegar en `reference_evidence`:[/bold]")
    console.print(
        f"  {format_evidence(meeting_id, found, only=info.act_ids)}", markup=False, soft_wrap=True
    )
    console.print(
        "\nRevisa que los turnos de arriba respalden de verdad tu respuesta de referencia; "
        "si sobra alguno, quita sus ids de la celda.",
        markup=False,
    )


def _decisions_for_series_or_exit(ami_root: Path, series: str) -> list[Decision]:
    if not ami_root.exists():
        console.print(
            f"[bold red]No se encontró el corpus AMI en {ami_root}. "
            "Ejecuta primero `uv run afg corpus download`.[/bold red]"
        )
        raise typer.Exit(code=1)

    decisions = decisions_from_abstractive(ami_root, series)
    if not decisions:
        console.print(
            f"[bold red]No se encontraron oraciones DECISIONS del resumen abstractivo para "
            f"la serie {series!r} en {ami_root}. Revisa el identificador de la serie "
            "(p. ej. 'IS1004') y que el corpus se haya extraído bien.[/bold red]"
        )
        raise typer.Exit(code=1)
    return decisions


@gold_app.command("candidates", rich_help_panel=_PANEL_MAINTENANCE)
def gold_candidates(
    series: str = typer.Option(..., "--series", help="Serie de AMI, p. ej. IS1004."),
    threshold: float = typer.Option(
        0.30,
        "--threshold",
        help="Umbral de bloqueo por coeficiente de solapamiento (manual de la tesis, sección 4).",
    ),
    min_overlap: int = typer.Option(
        2,
        "--min-overlap",
        help="Mínimo absoluto de palabras compartidas (|A & B|), junto con --threshold.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Regenera aunque haya anotación cargada en los archivos derivados de la serie. "
        "Desalinea `afg gold validate` para todo el mundo.",
    ),
) -> None:
    """(Mantenedor) Genera el archivo base de la Tarea B: pares candidatos entre reuniones.

    Provisional: los candidatos salen de las oraciones DECISIONS del resumen
    abstractivo (``afg.annotation.blocking.decisions_from_abstractive``),
    todavía no de las decisiones normalizadas del conjunto de referencia.
    Escribe ``data/processed/relations/<serie>.candidates.csv``. Se niega a
    correr si algún ``<serie>.decisions.<iniciales>.csv`` o
    ``<serie>.candidates.<iniciales>.csv`` derivado ya tiene anotación,
    salvo con ``--force``.
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
        f"Serie {series}: {total_pairs} pares considerados, {len(candidates)} candidatos "
        f"seleccionados ({pct:.1f} %) con threshold={threshold:.2f}, min_overlap={min_overlap}, "
        f"blocker_version={BLOCKER_VERSION}."
    )
    console.print(f"Escrito: {out_path}")


@gold_app.command("recall-sample", rich_help_panel=_PANEL_MAINTENANCE)
def gold_recall_sample(
    series: str = typer.Option(..., "--series", help="Serie de AMI, p. ej. IS1004."),
    n: int = typer.Option(50, "--n", help="Cantidad de pares rechazados a muestrear."),
    seed: int = typer.Option(42, "--seed", help="Semilla para que la muestra sea reproducible."),
    threshold: float = typer.Option(
        0.30,
        "--threshold",
        help="Umbral de bloqueo por coeficiente de solapamiento (manual de la tesis, sección 4).",
    ),
    min_overlap: int = typer.Option(
        2,
        "--min-overlap",
        help="Mínimo absoluto de palabras compartidas (|A & B|), junto con --threshold.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Sobrescribe una muestra existente. Invalida la anotación hecha sobre ella.",
    ),
) -> None:
    """(Mantenedor) Muestrea pares rechazados para la Tarea C (recall del bloqueador).

    Provisional: la muestra sale de las oraciones DECISIONS del resumen
    abstractivo, con la misma salvedad que ``afg gold candidates``. Escribe
    ``data/processed/relations/<serie>.recall-sample.csv``.

    Se niega a sobrescribir una muestra existente salvo con ``--force``: la
    muestra se saca una sola vez con semilla fija, y una regenerada tras ver
    resultados deja de ser una estimación válida
    (docs/anotacion/asignacion/tareas-jss.md, sección 5).
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
        f"Serie {series}: muestra de {len(sample)} pares rechazados (semilla={seed}), "
        f"threshold={threshold:.2f}, min_overlap={min_overlap}, "
        f"blocker_version={BLOCKER_VERSION}."
    )
    console.print(f"Escrito: {out_path}")


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


@gold_app.command("setup", rich_help_panel=_PANEL_ANNOTATORS)
def gold_setup(
    annotator: str = typer.Option(..., "--annotator", help="Iniciales del anotador, p. ej. gv."),
    yes: bool = typer.Option(
        False, "--yes", help="Salta la confirmación de la licencia del corpus (paso 1)."
    ),
) -> None:
    """De un clon nuevo a "abre este archivo y empieza", en un solo comando.

    Corre, en orden, saltando lo que ya esté hecho: descarga el corpus AMI (pide
    confirmación explícita de la licencia CC BY 4.0 y del tamaño de la descarga, salvo
    que pases --yes), genera las 171 transcripciones y prepara tu espacio de trabajo.
    Nunca usa --force, así que jamás borra anotación ya hecha. Termina diciendo
    exactamente qué archivo abrir primero.
    """
    from afg.annotation.progress import NextKind
    from afg.annotation.setup import CorpusDownloadDeclinedError, run_setup
    from afg.annotation.workspace import UnknownAnnotatorError

    plan = _plan_or_exit()

    def confirm_corpus_download() -> bool:
        _print_corpus_licence()
        if yes:
            return True
        return typer.confirm("¿Descargar el corpus ahora?")

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
        console.print(f"[bold red]La descarga falló:[/bold red] {exc}")
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

    if not prep.created and not prep.skipped_annotated and not prep.not_open:
        console.print("[bold red]No se creó ningún archivo.[/bold red]")
        raise typer.Exit(code=1)

    if prep.not_open:
        waiting = dict.fromkeys(f.series_id for f in prep.not_open)
        console.print(
            f"[dim]Series aún no abiertas: {', '.join(waiting)}. No se crearon archivos de "
            f"ellas; {plan.adjudicator} avisa cuándo toca cada una.[/dim]"
        )

    status = outcome.status
    assert status is not None  # only the maintainer has none, and returned above
    if status.bank_gate is not None:
        console.print(f"[dim]{status.bank_gate}[/dim]")
    action = status.next_action
    console.print("\n[bold]Qué hacer ahora.[/bold]")
    if action.kind is NextKind.ANNOTATE and action.target and action.partner:
        console.print(
            f"  1. Lee la transcripción de la serie {action.series_id} (fase {action.phase}) en "
            f"{_short(TRANSCRIPTS_DIR)}/{action.series_id}*.md antes de llenar una sola "
            "fila -- anotar solo desde el resumen es el error que más cuesta corregir.\n"
            f"  2. Abre {_short(action.target)} y llena las columnas humanas (luego "
            f"{_short(action.partner)} para la otra tarea de la misma serie).\n"
            f"  3. Cuando cierres esa serie: uv run afg gold validate --annotator {annotator} "
            f"--series {action.series_id}\n"
            "  4. Sin errores -> abre el PR de esa serie (una serie por PR).",
            markup=False,
            soft_wrap=True,
        )
    else:
        console.print(f"  {action.message}", markup=False, soft_wrap=True)
    console.print(
        f"\nPara ver tu avance en cualquier momento: uv run afg gold status --annotator {annotator}"
    )


@gold_app.command("prepare", rich_help_panel=_PANEL_ANNOTATORS)
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

    if outcome.not_open:
        waiting = dict.fromkeys(f.series_id for f in outcome.not_open)
        console.print(
            f"[dim]Series aún no abiertas: {', '.join(waiting)}. No se crean archivos de "
            f"series que {plan.adjudicator} no ha abierto.[/dim]"
        )

    if (
        not outcome.created
        and not outcome.overwritten
        and not outcome.skipped_annotated
        and not outcome.not_open
    ):
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


@gold_app.command("validate", rich_help_panel=_PANEL_ANNOTATORS)
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
    PR para archivos que no existen. La Tarea C (muestra de recall) se entrega en un PR
    aparte: si su archivo aún no existe se informa como `pendiente`, sin fallar.
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
        if progress.recall_pending:
            console.print(
                f"  [dim]{progress.series_id} Tarea C: pendiente (se entrega en un PR aparte)[/dim]"
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


@gold_app.command("status", rich_help_panel=_PANEL_ANNOTATORS)
def gold_status(
    annotator: str | None = typer.Option(
        None, "--annotator", help="Muestra solo las series de esta persona, p. ej. gv."
    ),
) -> None:
    """Avance por persona y serie, y qué hacer a continuación.

    Cada serie está en uno de estos estados: `pendiente (aún no)` (el mantenedor todavía no
    la abre), `sin preparar` (abierta pero sin archivos), `por empezar`, `en curso`,
    `con errores`, `lista para entregar` (todo lleno y válido), `entregada` (además, sus
    archivos ya están en `main` sin cambios) o `adjudicada` (cerrada). Con
    `--annotator`, muestra solo la fila de esa persona, la Tarea C y el banco de preguntas
    si le tocan, y termina con una línea `Siguiente:` con lo único que toca hacer ahora.
    """
    from rich import box
    from rich.table import Table

    from afg.annotation.progress import SeriesState, annotator_status
    from afg.annotation.workspace import UnknownAnnotatorError

    plan = _plan_or_exit()
    paths = _workspace_paths()

    if annotator is not None:
        try:
            plan.annotator(annotator)
        except UnknownAnnotatorError as exc:
            console.print(f"[bold red]{exc}[/bold red]")
            raise typer.Exit(code=1) from exc

    table = Table(title="Anotación OE1 — avance por persona y serie", box=box.SIMPLE_HEAD)
    table.add_column("Anotador", no_wrap=True)
    table.add_column("Serie", no_wrap=True)
    table.add_column("Fase", justify="right")
    table.add_column("Estado", no_wrap=True)
    table.add_column("Tarea A", justify="right")
    table.add_column("Tarea B", justify="right")

    colors = {
        SeriesState.NOT_YET: "dim",
        SeriesState.NOT_PREPARED: "dim",
        SeriesState.TO_START: "yellow",
        SeriesState.IN_PROGRESS: "yellow",
        SeriesState.ERRORS: "bold red",
        SeriesState.READY: "green",
        SeriesState.DELIVERED: "green",
        SeriesState.ADJUDICATED: "green",
    }
    notes: list[str] = []
    statuses = []
    for person in plan.annotators:
        if not person.annotates:
            continue
        if annotator is not None and person.initials != annotator:
            continue
        try:
            status = annotator_status(plan, person.initials, paths=paths)
        except ValueError as exc:
            console.print(f"[bold red]{exc}[/bold red]")
            raise typer.Exit(code=1) from exc
        statuses.append(status)
        for item in status.series:
            label = item.state.value
            if item.state is SeriesState.ERRORS:
                label = f"{item.issue_count} error(es)"
            started = item.state not in (SeriesState.NOT_YET, SeriesState.NOT_PREPARED)
            table.add_row(
                f"{person.initials} ({person.github})",
                item.series_id,
                str(item.phase),
                f"[{colors[item.state]}]{label}[/{colors[item.state]}]",
                f"{item.decisions_filled}/{item.decisions_total}" if started else "—",
                f"{item.candidates_filled}/{item.candidates_total}" if started else "—",
            )
            if item.parts:
                notes.append(
                    f"{item.series_id}: {item.decisions_total} filas ({item.originals} "
                    f"originales + {item.parts} partes de compuestas)"
                )

    if not statuses:
        console.print("[yellow]No hay ninguna serie asignada en config/annotation.toml.[/yellow]")
        raise typer.Exit(code=1)

    console.print(table)
    for note in notes:
        console.print(f"  {note}", markup=False, soft_wrap=True)

    if annotator is None:
        console.print(
            f"Adjudica `{plan.adjudicator}`. Banco de preguntas: lo escribe "
            f"`{plan.question_bank.author}`, lo valida `{plan.question_bank.validator}`. "
            f"Muestra de recall (Tarea C): `{plan.recall_sample.owner}` sobre "
            f"{', '.join(plan.recall_sample.series_ids)}."
        )
        return

    status = statuses[0]
    for rec in status.recall:
        progress = f" {rec.filled}/{rec.total}" if rec.total else ""
        console.print(
            f"Tarea C (muestra de recall) {rec.series_id}: {rec.state.value}{progress}",
            markup=False,
        )
    if status.bank_gate is not None:
        console.print(status.bank_gate, markup=False, soft_wrap=True)
    if status.bank is not None:
        bank = status.bank
        per_stratum = ", ".join(
            f"{s.stratum.value} {s.written}/{s.minimum}"
            + (f" (hasta {s.rows})" if s.rows > s.minimum else "")
            for s in bank.strata
        )
        console.print(
            f"Banco de preguntas (escritas/mínimo por estrato): {per_stratum}; "
            f"validadas {bank.validated} de {bank.written} escritas.",
            markup=False,
            soft_wrap=True,
        )
        console.print(
            "E3 depende de relaciones ya adjudicadas: la mayoría llegará con la Fase 3.",
            markup=False,
        )
    console.print(f"Siguiente: {status.next_action.message}", markup=False, soft_wrap=True)


@gold_app.command("adjudicate", rich_help_panel=_PANEL_MAINTENANCE)
def gold_adjudicate(
    series: str = typer.Option(..., "--series", help="Serie de doble anotación, p. ej. ES2015."),
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque los CSV ya tengan veredictos escritos."
    ),
) -> None:
    """(Mantenedor) Escribe los dos CSV de adjudicación de una serie, lado a lado.

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


@gold_app.command("validate-adjudication", rich_help_panel=_PANEL_MAINTENANCE)
def gold_validate_adjudication(
    series: str = typer.Option(..., "--series", help="Serie de doble anotación, p. ej. ES2015."),
) -> None:
    """(Mantenedor) Verifica que el adjudicador terminó los dos CSV de adjudicación de una serie.

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


@gold_app.command("translation-template", rich_help_panel=_PANEL_MAINTENANCE)
def gold_translation_template(
    series: str = typer.Option(..., "--series", help="Serie adjudicada, p. ej. ES2015."),
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque el archivo ya exista (borra la traducción)."
    ),
) -> None:
    """(Mantenedor) Crea la plantilla de traducción al inglés de la referencia de una serie.

    Escribe `<serie>.reference-en.csv` con una fila por decisión de la referencia adjudicada,
    el español copiado y `object_en`/`content_en` vacíos. La traducción es automática y no es
    una etiqueta: el español adjudicado sigue siendo la verdad. Ver
    docs/anotacion/traduccion-referencia.md.
    """
    from afg.evaluation.translation import write_translation_template

    try:
        path = write_translation_template(series, decisions_dir=GOLD_DECISIONS_DIR, force=force)
    except (FileExistsError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(f"Escrito {_short(path)}")
    console.print(
        "Llena `object_en` y `content_en` de cada fila (sin tocar el español) y luego corre: "
        f"uv run afg gold validate-translation --series {series}"
    )


@gold_app.command("validate-translation", rich_help_panel=_PANEL_MAINTENANCE)
def gold_validate_translation(
    series: str = typer.Option(..., "--series", help="Serie adjudicada, p. ej. ES2015."),
) -> None:
    """(Mantenedor) Verifica que la traducción de la referencia está completa y vigente.

    Cada decisión de la referencia necesita exactamente una fila con `object_en` y
    `content_en` llenos, el español igual al adjudicado actual (si no, está desactualizada)
    y un `translation_method` permitido. Sale con código distinto de cero si algo falla.
    """
    from afg.evaluation.translation import validate_translation

    issues = validate_translation(series, decisions_dir=GOLD_DECISIONS_DIR)
    if not issues:
        console.print(f"[green]Sin errores.[/green] La traducción de {series} está completa.")
        return
    console.print(f"[bold red]{len(issues)} problema(s) en la traducción de {series}:[/bold red]")
    for issue in issues:
        console.print(f"  - {issue}", markup=False, soft_wrap=True)
    raise typer.Exit(code=1)


@gold_app.command("questions-init", rich_help_panel=_PANEL_MAINTENANCE)
def gold_questions_init(
    force: bool = typer.Option(
        False, "--force", help="Regenera aunque el banco ya tenga preguntas escritas."
    ),
) -> None:
    """(Mantenedor) Crea el banco de preguntas: filas numeradas y vacías (25 por estrato, 40 en E3).

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
    for line in _collapsed_issue_lines(report.errors):
        console.print(f"[bold red]  error {escape(line)}[/bold red]")
    for line in _collapsed_issue_lines(report.warnings):
        console.print(f"[yellow]  aviso {escape(line)}[/yellow]")


def _collapsed_issue_lines(issues: Sequence[QuestionBankIssue]) -> list[str]:
    """One line per kind of problem: repeated messages become a count with a few row ids."""
    by_message: dict[str, list[str]] = {}
    for issue in issues:
        by_message.setdefault(issue.message, []).append(issue.row_id)
    lines: list[str] = []
    for message, row_ids in by_message.items():
        if len(row_ids) == 1:
            lines.append(f"{row_ids[0]}: {message}")
            continue
        shown = ", ".join(row_ids[:3])
        rest = len(row_ids) - 3
        examples = f"{shown} y {rest} más" if rest > 0 else shown
        lines.append(f"{len(row_ids)} filas ({examples}): {message}")
    return lines


@gold_app.command("questions-check", rich_help_panel=_PANEL_ANNOTATORS)
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
        report = load_configured_question_bank(bank_path, require_complete=complete, strict=True)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    _print_question_bank_report(report)
    if report.has_errors:
        raise typer.Exit(code=1)


# Annotator commands first in ``afg gold --help``; the sort is stable, so each group keeps the
# order in which its commands are defined above.
gold_app.registered_commands.sort(key=lambda c: c.rich_help_panel != _PANEL_ANNOTATORS)


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
    """The embedder C1 retrieval uses (model from the config, host from the Ollama settings)."""
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


def _c1_development_inputs() -> tuple[TuningConfig, list[TuningQuestion], list[str]]:
    """Development config, questions and meetings for the C1 retrieval analyses.

    Refuses non-development series (ADR 0005) and checks that the embedding model is
    installed in Ollama; prints the reason and exits with code 1 otherwise.
    """
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
    return config, questions, meetings


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

    config, questions, meetings = _c1_development_inputs()

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


@c1_app.command("ablate")
def c1_ablate() -> None:
    """Compara BM25, denso e híbrido (RRF) como recuperador de C1 sobre desarrollo.

    Solo recuperación (sin modelo generativo): con la segmentación y el K fijados en
    `[retrieval.c1]`, mide para cada modo de recuperación las mismas cifras que `afg c1 tune`
    (recall de evidencia, recall entregado tras el recorte del presupuesto de contexto y
    preguntas con algún acierto). Usa las series de desarrollo de `[retrieval.tuning]`
    (ADR 0005) y deja los resultados en `reports/c1-tuning/ablacion-recuperacion.json`.
    """
    from rich.table import Table

    config, questions, meetings = _c1_development_inputs()
    try:
        params = load_pinned_c1_params()
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"{len(questions)} preguntas, {len(meetings)} reuniones ({', '.join(config.series)}), "
        f"max_chars={params.max_chars}, overlap_turns={params.overlap_turns}, K={params.k}."
    )
    try:
        results = evaluate_modes(
            questions, meetings, params, config, make_c1_embedder(), TRANSCRIPTS_DIR
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    table = Table(title="Recuperación de C1 por modo")
    for column in ("modo", "recall entregado", "recall fragmentos", "con acierto", "entregado"):
        table.add_column(column, justify="right")
    for r in results:
        table.add_row(
            r.mode,
            f"{r.result.mean_delivered_recall:.3f}",
            f"{r.result.mean_recall:.3f}",
            f"{questions_with_any_hit(r.result)}/{len(questions)}",
            f"{questions_with_any_delivered_hit(r.result)}/{len(questions)}",
        )
    console.print(table)
    save_ablation_results(
        C1_ABLATION_PATH,
        results,
        params=params,
        config=config,
        n_questions=len(questions),
        git_commit=current_git_commit(),
    )
    console.print(f"Resultados guardados en {_short(C1_ABLATION_PATH)}.")


def make_openkos_adapter(base_dir: Path) -> OpenKosAdapter:
    """The adapter wired to the local ``openkos`` executable, the frozen transcripts and the AMI
    ``meetings.xml`` (event dates, ADR 0008); workspaces are created under ``base_dir``."""
    meetings_xml = AMI_DIR / "corpusResources" / "meetings.xml"
    return OpenKosAdapter(
        runner=SubprocessRunner(),
        settings=openkos_run_settings(),
        base_dir=base_dir,
        transcripts_dir=TRANSCRIPTS_DIR,
        meetings_xml=meetings_xml if meetings_xml.exists() else None,
    )


EXPERIMENT_A_PROVENANCE_KEYS = (
    "generative_model_digest",
    "embedding_model_digest",
    "model_digest_source",
    "ollama_version",
)
"""The :func:`collect_provenance` fields that apply to Experiment A (it has no judge or C1)."""


def _require_development_series(series_ids: Sequence[str]) -> str:
    """The partition of ``series_ids`` when all are development; otherwise refuse and exit.

    The one place the Experiment A gate lives (``a`` and ``a-batch``): while the OpenKOS
    version is not pinned, only development series run (ADR 0005 and ADR 0006).
    """
    partition_of = configured_partition_of()
    refused = [(s, partition_of(s)) for s in series_ids if partition_of(s) != "development"]
    if refused:
        partitions = ", ".join(sorted({partition for _, partition in refused}))
        names = ", ".join(series for series, _ in refused)
        subject = (
            f"{names} no es una serie de desarrollo"
            if len(refused) == 1
            else f"{names} no son series de desarrollo"
        )
        console.print(
            f"[bold red]{subject} (partición: {partitions}). "
            "El Experimento A solo corre series de desarrollo mientras la versión de OpenKOS "
            "no esté fijada (ADR 0005 y ADR 0006).[/bold red]"
        )
    if refused:
        raise typer.Exit(code=1)
    return "development"


def _experiment_a_manifest(name: str, series: str, partition: str, n_runs: int) -> dict[str, Any]:
    """The opening manifest of an Experiment A run directory (settings and provenance)."""
    from datetime import UTC, datetime

    run_settings = openkos_run_settings()
    provenance = collect_provenance(
        make_provenance_probe(),
        generative_model=run_settings.generative_model,
        embedding_model=run_settings.embedding_model,
    )
    return {
        "schema_version": 1,
        "run_name": name,
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": current_git_commit(),
        "series": series,
        "partition": partition,
        "runs": n_runs,
        "openkos": {
            "executable": run_settings.executable,
            "generative_model": run_settings.generative_model,
            "embedding_model": run_settings.embedding_model,
            "seed": run_settings.base_seed,
            "temperature": run_settings.temperature,
            "versions": [],
            **{key: provenance[key] for key in EXPERIMENT_A_PROVENANCE_KEYS},
        },
        "git_dirty": provenance["git_dirty"],
        "status": "running",
        "completed_runs": [],
        "error": None,
    }


@experiment_app.command("a")
def experiment_a(
    series: Annotated[
        str,
        typer.Option(
            "--series", help="Serie a extraer (solo de desarrollo, ADR 0005), por ejemplo ES2015."
        ),
    ],
    runs: Annotated[
        int | None,
        typer.Option("--runs", min=1, help="Corridas (por defecto runs_per_config)."),
    ] = None,
    run_name: Annotated[
        str | None,
        typer.Option(
            "--run-name",
            help="Nombre de la carpeta en reports/experiment-a/. Un nombre ya usado se rechaza.",
        ),
    ] = None,
) -> None:
    """Experimento A: extracción de decisiones con OpenKOS sobre una serie (OE2).

    Por cada corrida crea un espacio de trabajo nuevo de OpenKOS en `data/interim/openkos/`,
    ingesta las cuatro reuniones de la serie en orden, lee las decisiones compiladas y agrega
    una línea a `extracciones.jsonl` en `reports/experiment-a/<run-name>/`, junto con
    `manifest.json`. Solo corre series de desarrollo: las de evaluación se niegan (ADR 0005)
    hasta fijar la versión de OpenKOS (ADR 0006). La semilla de la corrida r es `seed + r`.
    """
    import json
    from datetime import UTC, datetime

    partition = _require_development_series([series])

    budget = load_experiments_config()["shared_budget"]
    n_runs = runs if runs is not None else int(budget["runs_per_config"])
    name = run_name or datetime.now(UTC).strftime("a-%Y%m%d-%H%M%S")
    run_dir = EXPERIMENT_A_DIR / name
    if run_dir.exists():
        console.print(
            f"[bold red]Ya existe {_short(run_dir)}. Usa otro --run-name: una corrida no se "
            "sobrescribe ni se reanuda.[/bold red]"
        )
        raise typer.Exit(code=1)

    manifest = _experiment_a_manifest(name, series, partition, n_runs)
    manifest_path = run_dir / "manifest.json"
    records_path = run_dir / "extracciones.jsonl"

    def save_manifest() -> None:
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    run_dir.mkdir(parents=True)
    save_manifest()
    adapter = make_openkos_adapter(OPENKOS_WORKSPACES_DIR / name)
    console.print(f"{series}: {n_runs} corrida(s) -> {_short(run_dir)}")
    for run in range(n_runs):
        try:
            extraction = adapter.extract_series(series, run)
        except (OpenKosError, FileNotFoundError) as exc:
            manifest["status"] = "failed"
            manifest["error"] = f"corrida {run}: {type(exc).__name__}: {exc}"
            save_manifest()
            console.print(f"[bold red]Corrida {run} fallida: {exc}[/bold red]")
            raise typer.Exit(code=1) from exc
        with records_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(extraction.to_record(), ensure_ascii=False) + "\n")
        manifest["completed_runs"].append(run)
        if extraction.openkos_version not in manifest["openkos"]["versions"]:
            manifest["openkos"]["versions"].append(extraction.openkos_version)
        save_manifest()
        quotes = extraction.quotes
        console.print(
            f"  corrida {run}: {len(extraction.result.decisions)} decisiones, "
            f"{len(extraction.unmapped)} sin evidencia, "
            f"{quotes.not_found} de {quotes.total} citas no encontradas "
            f"(OpenKOS {extraction.openkos_version})."
        )
    manifest["status"] = "ok"
    save_manifest()
    console.print(f"Listo. Manifiesto en {_short(manifest_path)}.")


def _batch_series(series: str | None, partition: str | None) -> list[str]:
    """The series of an ``a-batch`` request: ``--series`` xor ``--partition``."""
    if (series is None) == (partition is None):
        console.print("[bold red]Indica --series o --partition, pero no ambos.[/bold red]")
        raise typer.Exit(code=2)
    if series is not None:
        ids = list(dict.fromkeys(s.strip() for s in series.split(",") if s.strip()))
        if not ids:
            console.print("[bold red]--series no tiene ninguna serie.[/bold red]")
            raise typer.Exit(code=2)
        return ids
    if partition not in ("development", "evaluation"):
        console.print("[bold red]--partition es development o evaluation.[/bold red]")
        raise typer.Exit(code=2)
    return list(load_corpus_config()["oe1"][f"{partition}_series"])


@experiment_app.command("a-batch")
def experiment_a_batch(
    series: Annotated[
        str | None,
        typer.Option("--series", help="Series separadas por comas (solo de desarrollo, ADR 0005)."),
    ] = None,
    partition: Annotated[
        str | None,
        typer.Option(
            "--partition",
            help="Todas las series de una partición (development; evaluation se rechaza).",
        ),
    ] = None,
    runs: Annotated[
        int | None,
        typer.Option("--runs", min=1, help="Corridas por serie (por defecto runs_per_config)."),
    ] = None,
    run_name: Annotated[
        str | None,
        typer.Option(
            "--run-name",
            help="Carpeta en reports/experiment-a/. Si ya es un lote, se reanuda: se omiten "
            "las corridas completas y se rehacen las demás.",
        ),
    ] = None,
) -> None:
    """Experimento A en lote: varias series y corridas sin supervisión, bajo un solo nombre.

    Corre cada par (serie, corrida) como `afg experiment a` y los guarda juntos en
    `reports/experiment-a/<run-name>/` (cada registro conserva su serie) y en
    `data/interim/openkos/<run-name>/`, donde C2 los busca. Un par fallido se registra y el
    lote sigue; el código de salida es distinto de cero si alguno falló. Al final imprime un
    resumen de integridad, sin puntajes (ADR 0005). Repetir `--run-name` reanuda el lote.
    Solo series de desarrollo mientras la versión de OpenKOS no esté fijada (ADR 0006).
    """
    import time
    from datetime import UTC, datetime

    from afg.experiments.extraction_batch import (
        BatchConflictError,
        batch_summary_lines,
        run_batch,
    )

    series_ids = _batch_series(series, partition)
    batch_partition = _require_development_series(series_ids)
    budget = load_experiments_config()["shared_budget"]
    n_runs = runs if runs is not None else int(budget["runs_per_config"])
    name = run_name or datetime.now(UTC).strftime("a-%Y%m%d-%H%M%S")
    base_manifest = _experiment_a_manifest(name, ",".join(series_ids), batch_partition, n_runs)
    base_manifest.pop("completed_runs")
    base_manifest.pop("error")
    run_dir = EXPERIMENT_A_DIR / name
    console.print(f"{', '.join(series_ids)}: {n_runs} corrida(s) por serie -> {_short(run_dir)}")
    started = time.monotonic()
    try:
        manifest = run_batch(
            make_openkos_adapter(OPENKOS_WORKSPACES_DIR / name),
            run_dir=run_dir,
            workspace_root=OPENKOS_WORKSPACES_DIR / name,
            series_ids=series_ids,
            runs=n_runs,
            base_manifest=base_manifest,
            report=lambda line: console.print(escape(line)),
        )
    except BatchConflictError as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    for line in batch_summary_lines(manifest, elapsed_seconds=time.monotonic() - started):
        console.print(escape(line))
    console.print(f"Manifiesto en {_short(run_dir / 'manifest.json')}.")
    if manifest["status"] != "ok":
        raise typer.Exit(code=1)


def make_provenance_probe() -> ProvenanceProbe:
    """The probe that reads model digests and versions from the local machine."""
    return LiveProbe(openkos_executable=get_settings().openkos_executable)


JUDGE_ORDER: PresentationOrder = "reference_first"
JUDGE_TEMPERATURE = 0.0
"""The judge configuration of the calibration's primary run (reference first, temperature 0)."""

C2_EXTRACTION_REQUIRED = (
    "La condición C2 necesita `--c2-extraction <nombre>`: el `--run-name` de la corrida de "
    "`afg experiment a` cuyos espacios de trabajo de OpenKOS consulta."
)

EXPERIMENT_B_CONDITIONS: tuple[str, ...] = ("c1", "c2", "c3")
"""Condition ids ``--conditions`` knows; only those in :func:`make_experiment_b_condition` run."""


def experiment_b_settings(runs: int | None) -> RunSettings:
    """Run settings of Experiment B from ``[shared_budget]``; ``runs`` defaults to the config."""
    budget = load_experiments_config()["shared_budget"]
    return RunSettings(
        generative_model=str(budget["generative_model"]),
        temperature=float(budget["temperature"]),
        base_seed=int(budget["seed"]),
        runs=runs if runs is not None else int(budget["runs_per_config"]),
        judge_model=get_settings().judge_model,
        judge_order=JUDGE_ORDER,
        judge_seed=int(budget["seed"]),
        judge_temperature=JUDGE_TEMPERATURE,
    )


def make_judge_backend() -> OllamaJudgeBackend:
    """The production judge backend, with the reasoning setting of ``[judge.calibration.think]``."""
    return OllamaJudgeBackend(think=load_think_settings())


def make_c2_condition(extraction_run: str) -> CompiledAutoCondition:
    """C2 wired to the workspaces of the ``afg experiment a`` run ``extraction_run``.

    Raises:
        ValueError: that run has no workspaces under ``data/interim/openkos/``.
    """
    base_dir = OPENKOS_WORKSPACES_DIR
    if not (base_dir / extraction_run).is_dir():
        raise ValueError(
            f"No hay espacios de trabajo de OpenKOS de la corrida {extraction_run!r} en "
            f"{_short(base_dir)}. Genéralos antes con `afg experiment a --run-name "
            f"{extraction_run}`."
        )
    return CompiledAutoCondition(
        runner=SubprocessRunner(),
        settings=openkos_run_settings(),
        extraction_run=extraction_run,
        base_dir=base_dir,
        transcripts_dir=TRANSCRIPTS_DIR,
    )


def make_experiment_b_condition(
    condition_id: str, *, c2_extraction: str | None = None
) -> Condition:
    """The condition ``condition_id`` wired from the config (C1 and C2; C3 does not exist yet).

    ``c2_extraction`` is the ``--run-name`` of the ``afg experiment a`` run C2 queries.
    """
    if condition_id == "c1":
        return make_c1_condition()
    if condition_id == "c2":
        if c2_extraction is None:
            raise ValueError(C2_EXTRACTION_REQUIRED)
        return make_c2_condition(c2_extraction)
    raise ValueError(
        f"La condición {condition_id.upper()} no está disponible todavía: C3 depende de la "
        "anotación de oro (tesis, sección 5.3)."
    )


@experiment_app.command("b")
def experiment_b(
    questions: Annotated[
        Path,
        typer.Option(
            "--questions",
            help="CSV de preguntas: el banco `banco-preguntas.csv` (corre solo las filas "
            "validadas y se niega si hay errores bloqueantes, con las mismas verificaciones de "
            "`afg gold questions-check`), la hoja `ES2015.preguntas.csv` "
            "o el CSV de preguntas de calibración.",
        ),
    ],
    conditions: Annotated[
        str,
        typer.Option("--conditions", help="Condiciones separadas por coma: `c1` y `c2` (C3 no)."),
    ] = "c1",
    c2_extraction: Annotated[
        str | None,
        typer.Option(
            "--c2-extraction",
            help="Obligatorio con `c2`: `--run-name` de la corrida de `afg experiment a` cuyos "
            "espacios de trabajo consulta C2. La corrida r usa `run-r` de cada serie.",
        ),
    ] = None,
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
    se reintentan. La semilla de generación de la corrida r es `seed + r`. C2 responde con
    `openkos query` sobre el espacio de trabajo `run-r` que `afg experiment a` compiló para la
    serie de la pregunta y rechaza el espacio cuya semilla no sea `seed + r`.
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
    if c2_extraction is not None and "c2" not in wanted:
        console.print(
            "[bold red]`--c2-extraction` solo tiene sentido con la condición c2: agrégala a "
            "`--conditions` o quita la opción.[/bold red]"
        )
        raise typer.Exit(code=1)
    try:
        built = {
            c.upper(): make_experiment_b_condition(c, c2_extraction=c2_extraction)
            for c in dict.fromkeys(wanted)
        }
        if questions.exists() and is_question_bank(questions):
            bank_report = load_configured_question_bank(questions, strict=True)
            if not bank_report.has_errors:
                _print_question_bank_report(bank_report)
        bank = load_experiment_questions(questions, limit=limit_questions)
    except (QuestionBankError, ValueError, FileNotFoundError, CalibrationSetError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    config = load_experiments_config()
    settings = experiment_b_settings(runs)
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
    provenance = collect_provenance(
        make_provenance_probe(),
        generative_model=settings.generative_model,
        judge_model=settings.judge_model,
        embedding_model=configured_embedding_model(),
        c1_params=config["retrieval"]["c1"],
        questions_path=questions,
        c2_extraction=c2_extraction,
    )

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
            provenance=provenance,
            progress=report,
        )
    except (JudgeConfigurationError, ManifestMismatchError, RunAbortedError, ValueError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"{summary.written} registros nuevos, {summary.skipped} ya hechos, "
        f"{summary.errors} con error. Manifiesto en {_short(run_dir / 'manifest.json')}."
    )


CLOSED_BOOK_RUN_NAME = "diagnostico-sin-contexto-es2015"


def make_closed_book_condition() -> ClosedBookCondition:
    """C0 wired to the shared generation settings and the local Ollama (no retrieval)."""
    return ClosedBookCondition(chat=OllamaChatBackend(), settings=GenerationSettings.from_config())


@experiment_app.command("b-closed-book")
def experiment_b_closed_book(
    questions: Annotated[
        Path,
        typer.Option(
            "--questions",
            help="CSV de preguntas de calibración (hoja `ES2015.preguntas.csv`).",
        ),
    ] = WORKSHEET_PATH,
    runs: Annotated[
        int | None,
        typer.Option("--runs", min=1, help="Corridas por pregunta (por defecto runs_per_config)."),
    ] = None,
    run_name: Annotated[
        str,
        typer.Option(
            "--run-name",
            help="Nombre de la carpeta en reports/experiment-b/. Repetir un nombre reanuda.",
        ),
    ] = CLOSED_BOOK_RUN_NAME,
) -> None:
    """Diagnóstico de desarrollo: el modelo de C1 responde sin ningún contexto recuperado.

    Mide el punto de partida más simple y cuánto del escenario AMI ya conoce el modelo. No es una
    condición de la tesis (C1, C2, C3): solo corre sobre series de desarrollo (ADR 0005), con el
    mismo modelo, ajustes, semillas (`seed + r`) y juez que el Experimento B, y escribe en
    `reports/experiment-b/<run-name>/` con el mismo formato. Repetir el nombre reanuda.
    """
    quiet_http_logs()
    try:
        bank = load_experiment_questions(questions)
        require_development_series(bank, development_series())
    except (QuestionBankError, EvaluationSeriesError, ValueError, FileNotFoundError) as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc

    settings = experiment_b_settings(runs)
    try:
        absent = missing_models(
            [settings.generative_model, settings.judge_model], list_installed_models()
        )
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

    run_dir = EXPERIMENT_B_DIR / run_name
    provenance = collect_provenance(
        make_provenance_probe(),
        generative_model=settings.generative_model,
        judge_model=settings.judge_model,
        embedding_model=configured_embedding_model(),
        questions_path=questions,
    )

    def report(done: int, total: int) -> None:
        step = max(total // 10, 1)
        if done == total or done % step == 0:
            console.print(f"  {done}/{total} registros")

    console.print(
        f"{len(bank)} preguntas sin contexto x {settings.runs} corridas -> {_short(run_dir)}"
    )
    try:
        summary = run_experiment_b(
            bank,
            {"C0": make_closed_book_condition()},
            settings=settings,
            judge_backend=make_judge_backend(),
            run_dir=run_dir,
            partition_of=configured_partition_of(),
            excerpt_for=default_excerpt_for,
            git_commit=current_git_commit(),
            provenance=provenance,
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


def _width_cells(width: Any) -> tuple[str, str, str]:
    """The three width columns of ``b-report``; ``-`` where a figure is unknown, never zero."""
    if width is None:
        return "-", "-", "-"
    sources = "-" if width.source_citations is None else str(width.source_citations)
    if width.answered == 0:
        return "-", "-", sources
    return (
        f"{width.cited_acts_median:g} ({width.cited_acts_min}-{width.cited_acts_max})",
        f"{width.mean_act_coverage:.2f}",
        sources,
    )


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
    questions: Annotated[
        Path | None,
        typer.Option(
            "--questions",
            help="CSV de preguntas de la corrida, con la evidencia de referencia. Es obligatorio: "
            "la tabla informa junto a la cita la anchura de las citas, la cobertura por acto y "
            "las citas a fuentes completas (ADR 0009, enmienda).",
        ),
    ] = None,
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

    if questions is None:
        console.print(
            "[bold red]Falta --questions: la tabla de citación necesita el CSV de preguntas para "
            "informar la anchura de las citas y la cobertura por acto (ADR 0009, "
            "enmienda).[/bold red]"
        )
        raise typer.Exit(code=1)
    run_dir, records = _load_run_records(run_name)
    config = load_experiments_config()
    try:
        bank = {q.id: q for q in load_experiment_questions(questions)}
    except (QuestionBankError, ValueError, FileNotFoundError, CalibrationSetError) as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    try:
        report = analyze_runs(
            records,
            settings=interval_settings_from_config(),
            min_questions=int(config["question_bank"]["min_questions"]),
            min_runs=int(config["shared_budget"]["runs_per_config"]),
            allow_development=descriptive,
            questions=bank,
        )
    except KeyError as exc:
        console.print(
            f"[bold red]La pregunta {escape(str(exc))} de los registros no está en "
            f"{_short(questions)}.[/bold red]"
        )
        raise typer.Exit(code=1) from exc
    except DevelopmentResultError as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        console.print("Para explorar sin reportar, usar la opción --descriptive.")
        raise typer.Exit(code=1) from exc

    label = "reportable" if report.reportable else f"DESCRIPTIVO, partición {report.partition}"
    table = Table(title=f"Experimento B, {run_name} ({label})")
    columns = (
        "Condición",
        "Estrato",
        "Preguntas",
        "Correcta",
        "Soportada",
        "Cita",
        "Actos citados, mediana (mín-máx)",
        "Cobertura por acto",
        "Citas a fuentes completas",
        "Fallas",
    )
    for column in columns:
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
            *_width_cells(cell.citation_width),
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


OE4_SHEET_FILE = "oe4-etapa-e1.csv"


@experiment_app.command("b-oe4-sheet")
def experiment_b_oe4_sheet(
    run_name: Annotated[
        str, typer.Option("--run-name", help="Carpeta de la corrida C2 en reports/experiment-b/.")
    ],
    questions: Annotated[
        Path,
        typer.Option("--questions", help="CSV de preguntas de la corrida (referencia)."),
    ] = WORKSHEET_PATH,
    force: Annotated[
        bool, typer.Option("--force", help="Sobrescribir una hoja que ya tiene etiquetas.")
    ] = False,
) -> None:
    """Hoja de evidencia OE4: fallas E1 de C2 que la traza no puede atribuir, con la base compilada.

    La base se ubica con `c2_extraction` del manifiesto de la corrida. Para cada falla se listan
    los objetos de la base con más términos de la referencia (y si se recuperaron) y la mejor
    transcripción en bruto. La columna `etapa_humana` queda vacía: la etiqueta la pone una
    persona (CONTRIBUTING §7.6).
    """
    import json

    from afg.experiments.c2_base_evidence import (
        bundle_dir_for_run,
        oe4_worksheet_rows,
        write_oe4_worksheet,
    )

    run_dir, records = _load_run_records(run_name)
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        bundle = bundle_dir_for_run(manifest)
        bank = {q.id: q for q in load_experiment_questions(questions)}
        rows = oe4_worksheet_rows(records, bank, bundle)
        write_oe4_worksheet(run_dir / OE4_SHEET_FILE, rows, force=force)
    except (ValueError, KeyError, FileNotFoundError, QuestionBankError, CalibrationSetError) as exc:
        console.print(f"[bold red]{escape(str(exc))}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"{len(rows)} filas desde la base {_short(bundle)}. "
        f"Hoja para la persona: {_short(run_dir / OE4_SHEET_FILE)}."
    )


# --- report ---------------------------------------------------------------------------------


@app.command("report", rich_help_panel=_PANEL_MAINTENANCE)
def report() -> None:
    """Regenera solo reports/tables/bibliography_audit.csv (mantenedor).

    Las tablas que dependen del corpus se regeneran aparte: `afg corpus inventory` y
    `afg corpus participants`.
    """
    console.print("Regenerando la auditoría bibliográfica...")
    biblio_audit()
    console.print(
        "El inventario del corpus y los informes de experimentos necesitan el corpus AMI; "
        "ejecuta `afg corpus inventory` aparte cuando esté descargado."
    )


if __name__ == "__main__":
    app()
