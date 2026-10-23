"""Journal Studio -> Slurm draft: input allowlists reject traversal and injection."""

from __future__ import annotations

import dataclasses

import pytest

from hpc_gui.journal_studio.document import JournalDocument
from hpc_gui.journal_studio.slurm_draft import build_slurm_draft
from hpc_gui.journal_studio.slurm_draft_inputs import SlurmDraftError, SlurmDraftRequest


def _request(**overrides) -> SlurmDraftRequest:
    base = SlurmDraftRequest(
        workdir="/arf/scratch/mkomek/case",
        journal_path="run.jou",
        partition="debug",
        account="proj1",
    )
    return dataclasses.replace(base, **overrides)


def _document() -> JournalDocument:
    return JournalDocument.from_bytes(b"/exit\n", path="/arf/scratch/mkomek/case/run.jou", remote=True)


def _assert_rejected(request: SlurmDraftRequest) -> None:
    with pytest.raises(SlurmDraftError):
        build_slurm_draft(_document(), request)


@pytest.mark.parametrize(
    "workdir",
    [
        "relative/dir",
        "/arf/../etc",
        "/arf/./case",
        "/arf//case/",
        "/arf/case dir",
        "/arf/$(id)",
        "/arf/`whoami`",
        "/arf/case;rm -rf ~",
        "/arf/case'x'",
        "/arf/case\nset -x",
        "C:\\arf\\case",
        "",
    ],
)
def test_workdir_traversal_and_injection_are_rejected(workdir):
    _assert_rejected(_request(workdir=workdir))


@pytest.mark.parametrize(
    "journal",
    [
        "/abs/run.jou",
        "../run.jou",
        "a/../../run.jou",
        "./run.jou",
        "-rf.jou",
        "run;id.jou",
        "run name.jou",
        "$(id).jou",
        "run\n/exit.jou",
        "",
    ],
)
def test_journal_path_traversal_and_injection_are_rejected(journal):
    _assert_rejected(_request(journal_path=journal))


@pytest.mark.parametrize(
    "field,value",
    [
        ("partition", "debug;id"),
        ("partition", "debug\n#SBATCH --x"),
        ("partition", "$(id)"),
        ("partition", "debug name"),
        ("partition", ""),
        ("partition", "TODO"),
        ("account", "proj1 && id"),
        ("account", "`id`"),
        ("account", ""),
        ("job_name", "1leading-digit"),
        ("job_name", "has space"),
        ("job_name", "x/y"),
    ],
)
def test_partition_account_and_job_name_allowlist(field, value):
    _assert_rejected(_request(**{field: value}))


@pytest.mark.parametrize(
    "field,value",
    [
        ("cpus_per_task", "0"),
        ("cpus_per_task", "129"),
        ("cpus_per_task", "many"),
        ("walltime", "00:00:00"),
        ("walltime", "1:2"),
        ("walltime", "2h"),
        ("walltime", "00:30:00;id"),
        ("nodes", "2"),
        ("nodes", "0"),
        ("fluent_version", "25"),
        ("fluent_version", "25.2;rm"),
        ("dimension", "4d"),
        ("precision", "xp"),
    ],
)
def test_numeric_and_fluent_fields_have_strict_formats(field, value):
    _assert_rejected(_request(**{field: value}))


def test_all_blocking_problems_are_reported_together():
    with pytest.raises(SlurmDraftError) as exc:
        build_slurm_draft(_document(), _request(workdir="rel", nodes="3", dimension="4d"))

    assert len(exc.value.errors) == 3
    assert any("working directory" in message for message in exc.value.errors)
    assert any("exactly one node" in message for message in exc.value.errors)
    assert any("dimension" in message for message in exc.value.errors)


def test_placeholder_partition_is_blocked_by_existing_submit_validation():
    # "TODO" passes the name allowlist, so the existing Jobs placeholder gate must catch it.
    with pytest.raises(SlurmDraftError) as exc:
        build_slurm_draft(_document(), _request(partition="TODO"))

    assert any("template placeholder detected" in message for message in exc.value.errors)
