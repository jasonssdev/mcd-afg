"""``afg gold setup``: fresh clone to "open this file and start", in one command.

Before this module, an annotator's first half hour was five separate steps -- sync
dependencies, download the corpus, render the transcripts, prepare the workspace, and
then guess which file to open -- each with its own way of failing quietly. This wraps the
last four behind one idempotent command that skips whatever is already done and closes
with the one thing that actually matters: the exact path to open first.

Nothing here talks to the terminal. The interactive corpus-licence confirmation is kept in
:mod:`afg.cli`, which is the only place a user's yes/no answer to a 228 MB CC BY 4.0
download should live; :func:`run_setup` receives that answer (or the decision to skip
asking at all) as a plain callback, so the whole flow can be tested without a TTY, the AMI
corpus, or network access.

## Why the corpus step is not simply "call ``corpus_download``"

``afg corpus download`` (:func:`afg.cli.corpus_download`) always asks -- it has no
"already downloaded, skip" branch, because a person who explicitly runs the download
command has already decided to download. ``setup`` is different: it must first ask a
factual question ("is the corpus already here?") and only fall back to the confirmation
prompt when the answer is no. That branch belongs here, not duplicated in ``cli.py``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from afg.annotation.workspace import (
    AnnotationPlan,
    PrepareOutcome,
    WorkspaceFile,
    WorkspacePaths,
    expected_files,
    prepare_annotator_workspace,
)
from afg.corpus.download import DownloadResult, download_annotations
from afg.corpus.inventory import corpus_is_present
from afg.corpus.render import RenderResult, discover_meeting_ids, render_meetings

__all__ = [
    "CorpusDownloadDeclinedError",
    "SetupOutcome",
    "run_setup",
]


class CorpusDownloadDeclinedError(RuntimeError):
    """Raised when the corpus licence confirmation is declined.

    Distinct from any other failure: this is not a bug, it is the annotator explicitly
    saying "not now" to a 228 MB download under CC BY 4.0. ``setup`` must stop
    immediately -- no transcripts, no workspace files -- and say nothing else ran.
    """


@dataclass(frozen=True, slots=True)
class SetupOutcome:
    """Everything ``afg gold setup`` did, and everything it needs to tell the annotator to
    do next.

    ``first_file`` is ``None`` for the maintainer (see :attr:`is_maintainer`), who never
    fills a workspace file -- ``prepare_annotator_workspace`` already draws that
    distinction and this mirrors it rather than re-deriving it.
    """

    initials: str
    is_maintainer: bool
    corpus_already_present: bool
    corpus_download: DownloadResult | None
    transcripts_already_rendered: bool
    transcripts_render: RenderResult | None
    prepare: PrepareOutcome
    first_file: WorkspaceFile | None


def run_setup(
    plan: AnnotationPlan,
    initials: str,
    *,
    paths: WorkspacePaths,
    ami_root: Path,
    transcripts_dir: Path,
    manifest_dir: Path,
    confirm_corpus_download: Callable[[], bool],
    download: Callable[[Path], DownloadResult] = download_annotations,
    render: Callable[..., RenderResult] = render_meetings,
    discover: Callable[[Path, Sequence[str] | None], list[str]] = discover_meeting_ids,
) -> SetupOutcome:
    """Run every step of ``afg gold setup``, in order, skipping whatever is already done.

    1. **Corpus.** Skipped when :func:`~afg.corpus.inventory.corpus_is_present` is already
       true. Otherwise ``confirm_corpus_download`` is called -- it must print the licence
       and ask, exactly like ``afg corpus download`` does -- and the corpus is downloaded
       only if it returns ``True``.
    2. **Transcripts.** Skipped when ``transcripts_dir`` already exists and holds at least
       one entry. Otherwise every meeting in the corpus is discovered and rendered there
       (the full 171, not just this person's assigned series -- the same set ``afg corpus
       transcripts`` renders with no ``--series``).
    3. **Workspace.** Delegates to :func:`~afg.annotation.workspace.
       prepare_annotator_workspace` with ``force=False``, always -- ``setup`` must never
       be a way to lose annotated work.

    ``download``/``render``/``discover`` default to the real corpus functions and exist as
    parameters purely so tests can stub them without touching the network or the AMI
    corpus.

    Raises:
        UnknownAnnotatorError: if ``initials`` is not in the plan (from
            :meth:`~afg.annotation.workspace.AnnotationPlan.annotator`). Raised before any
            step runs, so a mistyped annotator never triggers a download.
        CorpusDownloadDeclinedError: the corpus was missing and ``confirm_corpus_download``
            returned ``False``. Nothing past step 1 runs.
    """
    annotator = plan.annotator(initials)  # raises UnknownAnnotatorError

    corpus_already_present = corpus_is_present(ami_root)
    corpus_result: DownloadResult | None = None
    if not corpus_already_present:
        if not confirm_corpus_download():
            raise CorpusDownloadDeclinedError(
                "Descarga del corpus rechazada. `afg gold setup` no puede continuar sin "
                "el corpus AMI: no se hizo nada más."
            )
        corpus_result = download(ami_root)

    transcripts_already_rendered = transcripts_dir.exists() and any(transcripts_dir.iterdir())
    render_result: RenderResult | None = None
    if not transcripts_already_rendered:
        meeting_ids = discover(ami_root, None)
        render_result = render(ami_root, meeting_ids, transcripts_dir, manifest_dir=manifest_dir)

    prepare_outcome = prepare_annotator_workspace(plan, initials, paths=paths, force=False)

    first_file: WorkspaceFile | None = None
    if annotator.annotates:
        files = expected_files(plan, annotator, paths)
        first_file = files[0] if files else None

    return SetupOutcome(
        initials=initials,
        is_maintainer=prepare_outcome.is_maintainer,
        corpus_already_present=corpus_already_present,
        corpus_download=corpus_result,
        transcripts_already_rendered=transcripts_already_rendered,
        transcripts_render=render_result,
        prepare=prepare_outcome,
        first_file=first_file,
    )
