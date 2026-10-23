"""Journal Studio -> Slurm draft: happy path, quoting and document gating."""

from __future__ import annotations

import dataclasses
import hashlib
import shlex

import pytest

from hpc_gui.journal_studio.document import JournalDocument
from hpc_gui.journal_studio.slurm_draft import build_slurm_draft
from hpc_gui.journal_studio.slurm_draft_inputs import (
    SlurmDraftError,
    SlurmDraftRequest,
    resolve_request,
)
from hpc_gui.journal_studio.slurm_draft_script import draft_template, render_draft_script


JOURNAL = b'; case setup\n/file/read-case "case.cas"\n/solve/iterate 100\n'


def _request(**overrides) -> SlurmDraftRequest:
    base = SlurmDraftRequest(
        workdir="/arf/scratch/mkomek/case",
        journal_path="run.jou",
        partition="debug",
        account="proj1",
    )
    return dataclasses.replace(base, **overrides)


def _saved_document(path: str = "/arf/scratch/mkomek/case/run.jou", data: bytes = JOURNAL) -> JournalDocument:
    return JournalDocument.from_bytes(data, path=path, remote=True)


def _fluent_line(script: str) -> str:
    return next(line for line in script.splitlines() if line.startswith('"$FLUENT_BIN"'))


def test_draft_produces_script_and_target_paths_without_submitting():
    draft = build_slurm_draft(_saved_document(), _request())

    assert draft.script_name == "journal_studio_draft.slurm"
    assert draft.script_path == "/arf/scratch/mkomek/case/journal_studio_draft.slurm"
    assert draft.journal_remote_path == "/arf/scratch/mkomek/case/run.jou"
    assert draft.source_remote is True
    assert "#SBATCH --partition=debug" in draft.script_text
    assert "#SBATCH --account=proj1" in draft.script_text
    assert "#SBATCH --cpus-per-task=56" in draft.script_text
    assert "#SBATCH --time=00:30:00" in draft.script_text
    assert "#SBATCH --output=/arf/scratch/mkomek/case/%x_%j.out" in draft.script_text
    assert "{{" not in draft.script_text and "}}" not in draft.script_text
    assert any("does not copy it" in note for note in draft.notes)
    assert any("Jobs view" in note for note in draft.notes)


def test_fluent_invocation_follows_existing_truba_convention_and_quotes_journal():
    draft = build_slurm_draft(_saved_document(), _request(dimension="2d", precision="sp", fluent_version="26.1"))

    tokens = shlex.split(_fluent_line(draft.script_text))
    assert tokens[0] == "$FLUENT_BIN"
    assert tokens[1:] == ["2dsp", "-g", "-t56", "-mpi=intel", "-i", "run.jou"]
    assert "$HOME/ansys/ansys_inc/v261/fluent/bin/fluent" in draft.script_text
    assert "cd -- /arf/scratch/mkomek/case" in draft.script_text


def test_journal_hash_in_script_matches_document_bytes():
    draft = build_slurm_draft(_saved_document(), _request())

    expected = hashlib.sha256(JOURNAL).hexdigest()
    assert draft.journal_sha256 == expected
    assert f"# Journal SHA-256: {expected}" in draft.script_text


def test_nested_journal_with_allowed_punctuation_survives_shell_split():
    draft = build_slurm_draft(_saved_document(), _request(journal_path="runs/a+b@c.v2/run-1.jou"))

    tokens = shlex.split(_fluent_line(draft.script_text))
    assert tokens[-1] == "runs/a+b@c.v2/run-1.jou"
    assert draft.journal_remote_path == "/arf/scratch/mkomek/case/runs/a+b@c.v2/run-1.jou"


def test_unsaved_edits_block_the_draft():
    document = _saved_document()
    document.text = document.text + "/exit\n"

    with pytest.raises(SlurmDraftError) as exc:
        build_slurm_draft(document, _request())
    assert any("save the journal first" in message for message in exc.value.errors)


def test_document_without_path_blocks_the_draft():
    document = JournalDocument.new(path=None, remote=False, text="/exit\n")

    with pytest.raises(SlurmDraftError) as exc:
        build_slurm_draft(document, _request())
    assert any("save the journal to a path" in message for message in exc.value.errors)


def test_local_document_is_flagged_as_local_source():
    document = JournalDocument.from_bytes(JOURNAL, path="C:/work/run.jou", remote=False)
    draft = build_slurm_draft(document, _request())

    assert draft.source_remote is False
    assert draft.source_path == "C:/work/run.jou"


def test_render_rejects_malformed_digest_and_template_declares_all_variables():
    resolved = resolve_request(_request())

    with pytest.raises(ValueError):
        render_draft_script(resolved, journal_sha256="not-a-digest")
    names = {variable.name for variable in draft_template().variables}
    assert {"workdir_q", "journal_q", "journal_sha256", "cpus_per_task"} <= names
