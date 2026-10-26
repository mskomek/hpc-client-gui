"""W65 G39-G43: SFTP fault model, Slurm draft-only, security gates."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.host_adapter import contributions
from hpc_gui.plugins.openfoam_studio.hpc import (
    FileStage, MultiFileCommit, SlurmResources, plan_ranks_match, render_slurm_job,
)
from hpc_gui.plugins.openfoam_studio.security import assert_argv_safe, include_is_safe


def test_slurm_draft_only_and_ranks():
    job = render_slurm_job("of-case", "simpleFoam -case .", SlurmResources(nodes=1, ntasks=4))
    assert "DRAFT ONLY" in job and "--ntasks=4" in job and "never auto-submitted" in job
    assert not any(line.strip().startswith("sbatch") for line in job.splitlines())
    plan_ranks_match(4, 4)
    with pytest.raises(ValueError):
        plan_ranks_match(4, 2)
    with pytest.raises(ValueError):
        render_slurm_job("bad;name", "x", SlurmResources())


def test_slurm_header_fields_reject_injection_and_invalid_values():
    invalid = (
        SlurmResources(time="01:00:00\n#SBATCH --output=/tmp/injected"),
        SlurmResources(partition="compute\n#SBATCH --output=/tmp/injected"),
        SlurmResources(module="openfoam;touch /tmp/injected"),
        SlurmResources(module="apps/../outside"),
        SlurmResources(time="1-24:00:00"),
        SlurmResources(nodes=True),
    )
    for resources in invalid:
        with pytest.raises((TypeError, ValueError)):
            render_slurm_job("of-case", "simpleFoam -case .", resources)

    job = render_slurm_job(
        "case_01", "simpleFoam -case .",
        SlurmResources(time="2-03:04:05", partition="compute-long"),
    )
    assert "#SBATCH --time=2-03:04:05" in job
    assert "#SBATCH --partition=compute-long" in job
    assert "module load apps/openfoam/v2312-2025" in job


def test_partial_commit_never_all_green():
    commit = MultiFileCommit([FileStage("0/U", "a", "b", True), FileStage("0/p", "a", "b", False, "rename failed")])
    assert commit.overall().startswith("PARTIAL")
    assert MultiFileCommit([FileStage("0/U", "a", "b", True)]).overall() == "COMMITTED"
    assert MultiFileCommit([FileStage("0/U", "a", "b", False, "lost")]).overall() == "FAILED"


def test_include_traversal_blocked():
    assert include_is_safe("sub/dict", "/case")
    assert not include_is_safe("../escape", "/case")
    assert not include_is_safe("/etc/passwd", "/case")
    assert not include_is_safe(r"C:\\outside\\dict", "/case")


def test_argv_injection_refused():
    assert_argv_safe(["simpleFoam", "-case", "."])
    with pytest.raises(ValueError):
        assert_argv_safe(["simpleFoam; rm -rf /"])


def test_host_adapter_contract():
    data = contributions()
    ids = [a["id"] for a in data["file_context"]]
    assert "of.newCase" in ids and "of.validate" in ids
    assert data["requires_app"] == ">=1.5.9"


def test_include_symlink_escape_blocked(tmp_path):
    case = tmp_path / "case"
    outside = tmp_path / "outside"
    case.mkdir()
    outside.mkdir()
    (outside / "secretDict").write_text("secret", encoding="utf-8")
    try:
        (case / "linked").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"filesystem symlinks unavailable for this test: {exc}")
    assert not include_is_safe("linked/secretDict", str(case))
