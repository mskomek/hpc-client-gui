"""W65 G39-G43: SFTP fault model, Slurm draft-only, security gates."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.host_adapter import contributions
from hpc_gui.plugins.openfoam_studio.hpc import (
    FileStage, MultiFileCommit, SlurmResources, plan_ranks_match, render_slurm_job,
)
from hpc_gui.plugins.openfoam_studio.solver import render_run_plan
from hpc_gui.plugins.openfoam_studio.security import assert_argv_safe, include_is_safe


def test_slurm_draft_only_and_ranks():
    plan = render_run_plan("simpleFoam")
    job = render_slurm_job(
        "of-case", SlurmResources(nodes=1, ntasks=4), allrun_sha256=plan["allrun_sha256"])
    assert "DRAFT ONLY" in job and "--ntasks=4" in job and "never auto-submitted" in job
    assert not any(line.strip().startswith("sbatch") for line in job.splitlines())
    assert "exec bash -- ./Allrun" in job
    assert plan["allrun_sha256"] in job
    assert "simpleFoam -case ." not in job
    assert "sha256sum --check --status" in job
    plan_ranks_match(4, 4)
    with pytest.raises(ValueError):
        plan_ranks_match(4, 2)
    with pytest.raises(ValueError):
        render_slurm_job("bad;name", SlurmResources(), allrun_sha256=plan["allrun_sha256"])


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
            render_slurm_job("of-case", resources, allrun_sha256=render_run_plan("simpleFoam")["allrun_sha256"])

    job = render_slurm_job(
        "case_01", SlurmResources(time="2-03:04:05", partition="compute-long"),
        allrun_sha256=render_run_plan("simpleFoam")["allrun_sha256"],
    )
    assert "#SBATCH --time=2-03:04:05" in job
    assert "#SBATCH --partition=compute-long" in job
    assert "module load apps/openfoam/v2312-2025" in job


def test_slurm_draft_requires_a_validated_run_plan_digest():
    digest = render_run_plan("simpleFoam")["allrun_sha256"]
    for invalid in ("", "a" * 63, "g" * 64, "a" * 64 + "\n#SBATCH --output=bad"):
        with pytest.raises(ValueError):
            render_slurm_job("of-case", SlurmResources(), allrun_sha256=invalid)
    with pytest.raises(TypeError):
        render_slurm_job("of-case", "simpleFoam; touch /tmp/pwned", SlurmResources())
    with pytest.raises(TypeError):
        render_slurm_job("of-case", SlurmResources(), allrun_body="echo injected")
    script = render_slurm_job("of-case", SlurmResources(), allrun_sha256=digest)
    assert "Allrun body" not in script
    assert "echo injected" not in script


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
