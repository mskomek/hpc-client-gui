"""W65 SAFE-016: shell argv allowlist and script trust proof."""

from __future__ import annotations

import hashlib

import pytest

from hpc_gui.plugins.openfoam_studio.security import (
    ALLOWED_EXECUTABLES,
    ScriptTrust,
    UntrustedArgvError,
    UntrustedScriptError,
    assert_argv_allowed,
    executable_name,
    render_exec_line,
)
import hpc_gui.plugin_engines.openfoam_studio.job_draft as job_draft_module
import hpc_gui.plugins.openfoam_studio.hpc as hpc_module
from hpc_gui.plugins.openfoam_studio.hpc import SlurmResources, render_slurm_job


def test_allowlisted_executable_passes():
    assert assert_argv_allowed(["simpleFoam", "-case", "."]) == "simpleFoam"


def test_absolute_path_is_reduced_to_its_basename():
    argv = ["/opt/openfoam2312/platforms/linux64GccDPInt32Opt/bin/snappyHexMesh", "-overwrite"]
    assert assert_argv_allowed(argv) == "snappyHexMesh"
    assert "snappyHexMesh" in ALLOWED_EXECUTABLES


def test_windows_style_path_is_reduced_and_the_exe_suffix_tolerated():
    argv = ["C:\\OpenFOAM\\bin\\blockMesh.exe"]
    assert executable_name(argv) == "blockMesh.exe"
    assert assert_argv_allowed(argv) == "blockMesh"
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed(["C:\\tools\\curl.exe", "http://example.invalid"])


def test_bash_only_runs_a_script():
    assert assert_argv_allowed(["bash", "--", "./Allrun"]) == "bash"
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed(["bash", "-c", "ls"])
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed(["bash", "--", "./Allrun", "extra"])
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed(["/bin/bash"])


def test_unknown_executable_is_refused():
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed(["rm", "-rf", "/"])


def test_empty_argv_is_refused():
    with pytest.raises(UntrustedArgvError):
        assert_argv_allowed([])


def test_metacharacter_inside_an_argument_is_refused():
    with pytest.raises(ValueError):
        assert_argv_allowed(["simpleFoam", "-case", "cavity;rm -rf /"])
    with pytest.raises(ValueError):
        assert_argv_allowed(["simpleFoam", "$(id)"])


def test_render_exec_line_quotes_spaces():
    line = render_exec_line(["foamDictionary", "-entry", "value 1", "system/controlDict"])
    assert line == "foamDictionary -entry 'value 1' system/controlDict"


def test_render_exec_line_applies_the_allowlist():
    with pytest.raises(UntrustedArgvError):
        render_exec_line(["curl", "http://example.invalid"])


def test_trust_without_approval_is_refused():
    trust = ScriptTrust(hashlib.sha256(b"solvers;").hexdigest())
    with pytest.raises(UntrustedScriptError):
        trust.verify(b"solvers;")


def test_approved_script_with_matching_bytes_passes():
    payload = b"blockMesh\nsimpleFoam\n"
    trust = ScriptTrust(hashlib.sha256(payload).hexdigest(), approved=True)
    trust.verify(payload)


def test_approved_script_with_changed_bytes_is_refused():
    trust = ScriptTrust(hashlib.sha256(b"blockMesh\n").hexdigest(), approved=True)
    with pytest.raises(UntrustedScriptError):
        trust.verify(b"blockMesh\nrm -rf /\n")


def test_hash_format_is_validated():
    with pytest.raises(ValueError):
        ScriptTrust("not-a-hash", approved=True)
    with pytest.raises(ValueError):
        ScriptTrust("A" * 64, approved=True)


def test_verify_path_reads_the_file(tmp_path):
    script = tmp_path / "Allrun"
    script.write_bytes(b"simpleFoam\n")
    trust = ScriptTrust(hashlib.sha256(b"simpleFoam\n").hexdigest(), approved=True)
    trust.verify_path(script)
    script.write_bytes(b"simpleFoam; rm -rf /\n")
    with pytest.raises(UntrustedScriptError):
        trust.verify_path(script)


def test_slurm_draft_exec_line_goes_through_the_allowlist(monkeypatch):
    seen = {}

    def fake_render(argv):
        seen["argv"] = list(argv)
        return "bash -- ./Allrun-via-allowlist"

    monkeypatch.setattr(hpc_module, "render_exec_line", fake_render)
    digest = hashlib.sha256(b"blockMesh\nsimpleFoam\n").hexdigest()
    resources = SlurmResources(nodes=1, ntasks=4, time="00:10:00", partition="", module="apps/openfoam/2312")
    rendered = render_slurm_job("cavity", resources, allrun_sha256=digest)
    assert seen["argv"] == ["bash", "--", "./Allrun"]
    assert "exec bash -- ./Allrun-via-allowlist" in rendered




def test_engine_slurm_wrapper_exec_line_goes_through_the_allowlist(monkeypatch):
    seen = {}

    def fake_render(argv):
        seen["argv"] = list(argv)
        return "bash -- ./Allrun-engine-path"

    monkeypatch.setattr(job_draft_module, "render_exec_line", fake_render)
    spec = job_draft_module.JobSpec(
        job_name="cavity",
        nodes=1,
        ntasks=2,
        time="00:10:00",
        partition="",
        module="apps/openfoam/v2312-2025",
    )
    rendered = job_draft_module.render_slurm_wrapper(
        spec,
        allrun_sha256=hashlib.sha256(b"blockMesh\nsimpleFoam\n").hexdigest(),
        release="v2312",
        required_commands=("simpleFoam",),
    )
    assert seen["argv"] == ["bash", "--", "./Allrun"]
    assert "exec bash -- ./Allrun-engine-path" in rendered

