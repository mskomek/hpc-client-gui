"""API3-pinned Case Studio command catalog contract tests."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from hpc_gui.plugin_engines.openfoam_studio.command_catalog import load_command_catalog
from hpc_gui.plugin_engines.openfoam_studio.job_draft import build_draft_bundle, validate_job_spec


def _catalog(commands=None):
    return {
        "schema_version": 1,
        "product": "OpenFOAM.com / ESI",
        "version": "v2312",
        "commands": commands if commands is not None else [
            {"name": name, "category": category, "verification_status": "unverified",
             "parameters": [], "execution": "draft-only"}
            for name, category in (
                ("simpleFoam", "Solver"), ("blockMesh", "Mesh"),
                ("icoFoam", "Solver"),
                ("checkMesh", "Mesh"), ("decomposePar", "Mesh"),
                ("reconstructPar", "Post-processing"),
                ("postProcess", "Post-processing"),
            )
        ],
    }


def _plugin(tmp_path, catalog):
    relative = "engine/openfoam_studio/data/command_catalog.json"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    data = (json.dumps(catalog, sort_keys=True) + "\n").encode("utf-8")
    target.write_bytes(data)
    file = SimpleNamespace(path=relative, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    return SimpleNamespace(directory=tmp_path, manifest=SimpleNamespace(files=(file,)))


def test_catalog_requires_declared_manifest_file_and_hash(tmp_path):
    plugin = _plugin(tmp_path, _catalog())
    assert load_command_catalog(plugin)["commands"][0]["name"] == "simpleFoam"
    (tmp_path / "engine/openfoam_studio/data/command_catalog.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest hash"):
        load_command_catalog(plugin)


@pytest.mark.parametrize("commands", [
    [],
    [{"name": "simpleFoam; id", "category": "Solver", "verification_status": "unverified", "parameters": [], "execution": "draft-only"}],
    [{"name": "simpleFoam", "category": "Solver", "verification_status": "invented-pass", "parameters": [], "execution": "draft-only"}],
    [{"name": "simpleFoam", "category": "Solver", "verification_status": "unverified", "parameters": ["-case"], "execution": "draft-only"}],
    [{"name": "simpleFoam", "category": "Solver", "verification_status": "unverified", "parameters": [], "execution": "execute"}],
    [
        {"name": "simpleFoam", "category": "Solver", "verification_status": "unverified", "parameters": [], "execution": "draft-only"},
        {"name": "simpleFoam", "category": "Solver", "verification_status": "unverified", "parameters": [], "execution": "draft-only"},
    ],
])
def test_catalog_rejects_empty_or_unsafe_command_records(tmp_path, commands):
    with pytest.raises(ValueError):
        load_command_catalog(_plugin(tmp_path, _catalog(commands)))


def test_catalog_rejects_symlink(tmp_path):
    plugin = _plugin(tmp_path, _catalog())
    path = tmp_path / "engine/openfoam_studio/data/command_catalog.json"
    target = tmp_path / "outside.json"
    target.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="missing or outside"):
        load_command_catalog(plugin)


def test_runtime_verified_icofoam_builds_a_bounded_parallel_draft(tmp_path):
    catalog = load_command_catalog(_plugin(tmp_path, _catalog()))

    class Parsed:
        def __init__(self, values):
            self._values = values

        def value(self, key, default=None):
            return self._values.get(key, default)

    documents = {
        "system/controlDict": SimpleNamespace(parsed=Parsed({"application": "icoFoam"})),
        "system/decomposeParDict": SimpleNamespace(parsed=Parsed({"numberOfSubdomains": 4})),
    }
    bundle = build_draft_bundle(
        documents,
        catalog,
        ["blockMesh", "checkMesh", "icoFoam"],
        validate_job_spec(
            job_name="w65-icofoam-smoke", nodes=1, ntasks=4,
            time="00:02:00", partition="debug",
        ),
    )

    assert bundle.solver == "icoFoam"
    assert "mpirun -np \"$nprocs\" \"$solver\" -parallel" in bundle.allrun_text
    assert bundle.allrun_sha256 in bundle.slurm_text
    assert "exec bash -- ./Allrun" in bundle.slurm_text
    assert "sbatch " not in bundle.slurm_text
