"""Release gates for the multi-version OpenFOAM candidate profiles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.openfoam_core.release_support import (
    linter_supports_release,
    release_profile,
    supported_releases,
)
from hpc_gui.plugin_engines.openfoam_lint.api import lint_text
from hpc_gui.plugin_engines.openfoam_lint.lint_worker import LintTask
from hpc_gui.plugin_engines.openfoam_studio.command_catalog import load_command_catalog
from hpc_gui.plugin_engines.openfoam_studio.job_draft import (
    build_draft_bundle,
    validate_job_spec,
)
from hpc_gui.plugin_engines.openfoam_studio.release_selection import ReleaseSelectionController
from hpc_gui.plugin_engines.openfoam_studio.workflow import WorkflowPlan
from hpc_gui.plugins.openfoam_studio.catalog_release import (
    coverage_for_release,
    inventory_for_release,
)
from hpc_gui.plugins.openfoam_studio.command_schemas import SchemaError, validate
from hpc_gui.plugins.openfoam_studio.selection import select
from hpc_gui.plugins.openfoam_studio.solver_effects import solver_effect_paths


ROOT = Path(__file__).resolve().parents[1]
STUDIO_DATA = ROOT / "src/hpc_gui/plugin_engines/openfoam_studio/data"


def _pinned_plugin(tmp_path: Path, release: str):
    releases = ("v2312", "v1912") if release == "both" else (release,)
    records = []
    for supported in releases:
        profile = release_profile(supported)
        source = STUDIO_DATA / Path(profile["catalog_file"]).name
        target = tmp_path.joinpath(*profile["catalog_file"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        target.write_bytes(data)
        records.append(SimpleNamespace(
            path=profile["catalog_file"],
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        ))
    plugin = SimpleNamespace(
        directory=tmp_path,
        manifest=SimpleNamespace(files=tuple(records)),
    )
    return plugin


def test_release_profiles_are_explicit_and_ordered():
    assert supported_releases() == ("v2312", "v1912")
    assert release_profile("v2312")["truba_module"] == "apps/openfoam/v2312-2025"
    assert release_profile("v1912")["truba_module"] is None
    assert release_profile("v1912")["feature_level"] == "runtime-verified-subset"
    with pytest.raises(ValueError, match="unsupported"):
        release_profile("v9999")


def test_v1912_selector_and_typed_schema_are_narrow():
    chosen = select("OpenFOAM.com / ESI (OpenCFD)", "v1912", "simpleFoam", "serial", "local")
    assert chosen.version == "v1912"
    assert validate("simpleFoam", {"endTime": 3, "writeInterval": 1}, release="v1912")["endTime"] == 3
    assert validate("blockMesh", {"nx": 1, "ny": 1, "nz": 1, "patches": ["inlet"]}, release="v1912")["nz"] == 1
    with pytest.raises(ValueError, match="not enabled for v1912"):
        select("OpenFOAM.com / ESI (OpenCFD)", "v1912", "pimpleFoam", "serial", "local")
    with pytest.raises(SchemaError, match="no typed schema for v1912"):
        validate("pimpleFoam", {"endTime": 3, "deltaT": 1}, release="v1912")
    with pytest.raises(ValueError, match="not classified for v1912"):
        solver_effect_paths("pimpleFoam", release="v1912")
    assert "0/U" in solver_effect_paths("simpleFoam", release="v1912")


def test_v1912_inventory_does_not_inherit_v2312_catalog():
    rows = inventory_for_release("v1912")
    assert {row["command_name"] for row in rows} == {"blockMesh", "checkMesh", "simpleFoam"}
    assert all(row["source_commit"] == "51dd8f1c633dda9a38e974bded29f0c772f42fe9" for row in rows)
    assert coverage_for_release("v1912")["inventory_rows"] == 3
    assert len(inventory_for_release("v2312")) == 305


def test_v1912_manifest_catalog_is_pinned_and_source_bound(tmp_path):
    plugin = _pinned_plugin(tmp_path, "v1912")
    catalog = load_command_catalog(plugin, "v1912")
    assert catalog["source_tag"] == "OpenFOAM-v1912.200626"
    assert {row["name"] for row in catalog["commands"]} == {"blockMesh", "checkMesh", "simpleFoam"}


def test_v1912_catalog_rejects_extra_command_even_with_updated_file_hash(tmp_path):
    plugin = _pinned_plugin(tmp_path, "v1912")
    path = tmp_path / release_profile("v1912")["catalog_file"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["commands"][0]["name"] = "pimpleFoam"
    data = (json.dumps(value) + "\n").encode("utf-8")
    path.write_bytes(data)
    record = SimpleNamespace(path=plugin.manifest.files[0].path, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    plugin.manifest.files = (record,)
    with pytest.raises(ValueError, match="approved v1912 command set"):
        load_command_catalog(plugin, "v1912")


def test_release_switch_preserves_workflow_and_rejects_lossy_switch(tmp_path):
    plugin = _pinned_plugin(tmp_path, "both")

    class Selector:
        def __init__(self):
            self.value = "v2312"

        def setCurrentText(self, value):
            self.value = value

        def blockSignals(self, _value):
            return None

    class Status:
        value = ""

        def setText(self, value):
            self.value = value

    class Page:
        pass

    page = Page()
    page.plugin = plugin
    page.target_release = "v2312"
    page.version = Selector()
    page.status = Status()
    page.command_catalog = {"commands": []}
    page.workflow_plan = WorkflowPlan([
        {"name": "blockMesh", "execution": "draft-only", "verification_status": "unverified"}
    ])
    page.workflow_plan.add("blockMesh")
    page._show_commands = lambda: None
    page._refresh_flow = lambda: None
    controller = ReleaseSelectionController(page)
    controller._switch("v1912")
    assert page.target_release == "v1912"
    assert page.workflow_plan.steps == ("blockMesh",)

    page.version.value = "v1912"
    page.workflow_plan = WorkflowPlan([
        {"name": "decomposePar", "execution": "draft-only", "verification_status": "unverified"}
    ])
    page.workflow_plan.add("decomposePar")
    controller._switch("v2312")
    assert page.target_release == "v2312"
    page.version.value = "v2312"
    controller._switch("v1912")
    assert page.target_release == "v2312"
    assert page.version.value == "v2312"
    assert "not in the approved command catalog" in page.status.value


def test_v1912_slurm_draft_is_blocked_without_verified_truba_module(tmp_path):
    catalog = load_command_catalog(_pinned_plugin(tmp_path, "v1912"), "v1912")
    with pytest.raises(ValueError, match="no TRUBA module is verified"):
        build_draft_bundle({"system/controlDict": object()}, catalog, (), validate_job_spec())


@pytest.mark.parametrize("release", ["v1912", "v2312"])
def test_linter_explicit_release_gate_accepts_supported_common_subset(release):
    assert linter_supports_release(release)
    result = lint_text("application simpleFoam;\n", file_name="system/controlDict", release=release)
    assert result.files_checked == ("system/controlDict",)
    assert result.version == release


def test_linter_worker_preserves_selected_release(tmp_path):
    case = tmp_path / "controlDict"
    case.write_text("application simpleFoam;\n", encoding="utf-8")
    results = []
    task = LintTask(1, (str(case),), release="v1912")
    task.signals.finished.connect(lambda _token, result: results.append(result))
    task.run()
    assert len(results) == 1
    assert results[0].version == "v1912"


def test_linter_rejects_unverified_release():
    with pytest.raises(ValueError, match="not supported by the static linter"):
        lint_text("application simpleFoam;\n", file_name="system/controlDict", release="v9999")
