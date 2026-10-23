"""Journal Studio -> Slurm job *draft* facade.

Builds a reviewable sbatch script and target paths for an open, saved journal.
It never contacts a scheduler or host: submission stays on the user-confirmed
Jobs path, which receives ``script_path`` and ``script_text`` from the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from hpc_gui.journal_studio.document import JournalDocument
from hpc_gui.journal_studio.slurm_draft_inputs import (
    SlurmDraftError,
    SlurmDraftRequest,
    resolve_request,
)
from hpc_gui.journal_studio.slurm_draft_script import render_draft_script
from hpc_gui.services.job_submit_cancel import validate_submit_request


@dataclass(frozen=True, slots=True)
class SlurmDraft:
    """A reviewed, not-submitted job draft."""

    script_name: str
    script_path: str
    script_text: str
    journal_remote_path: str
    journal_sha256: str
    source_path: str
    source_remote: bool
    notes: tuple[str, ...]


def build_slurm_draft(document: JournalDocument, request: SlurmDraftRequest) -> SlurmDraft:
    """Return a draft for *document*, or raise SlurmDraftError listing every blocker."""
    blockers: list[str] = []
    if not document.path:
        blockers.append("save the journal to a path before creating a job draft")
    if document.modified:
        blockers.append("save the journal first; unsaved edits would not match the file the job runs")
    if blockers:
        raise SlurmDraftError(blockers)

    resolved = resolve_request(request)
    journal_sha256 = hashlib.sha256(document.to_bytes()).hexdigest()
    script_text = render_draft_script(resolved, journal_sha256=journal_sha256)
    problems = validate_submit_request(resolved.script_path, script_text, provider_config=None)
    if problems:
        raise SlurmDraftError(problems)

    return SlurmDraft(
        script_name=resolved.script_name,
        script_path=resolved.script_path,
        script_text=script_text,
        journal_remote_path=resolved.journal_remote_path,
        journal_sha256=journal_sha256,
        source_path=str(document.path),
        source_remote=bool(document.remote),
        notes=(
            f"Upload or save the journal to {resolved.journal_remote_path} before submitting; this draft does not copy it.",
            "Nothing was sent to a host or scheduler. Submit only through the Jobs view after review.",
        ),
    )
