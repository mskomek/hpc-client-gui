"""API3-pinned Case Studio command catalog contract tests."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from hpc_gui.plugin_engines.openfoam_studio.command_catalog import load_command_catalog


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
