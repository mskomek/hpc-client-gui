"""W65 LINT-013: snappyHexMeshDict completeness for enabled stages."""
from __future__ import annotations

from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, rule_catalog


def _lint(text: str):
    files = {
        "system/controlDict": "application simpleFoam;\n",
        "system/snappyHexMeshDict": text,
    }
    return [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-MESH-010"]


COMPLETE = (
    "castellatedMesh true;\nsnap true;\naddLayers false;\n"
    "castellatedMeshControls { maxLocalCells 100; }\n"
    "snapControls { nSmoothPatch 3; }\n"
    "meshQualityControls { maxNonOrtho 65; }\n"
)


def test_complete_dictionary_has_no_finding():
    assert _lint(COMPLETE) == []


def test_missing_castellation_controls_are_reported():
    text = COMPLETE.replace("castellatedMeshControls { maxLocalCells 100; }\n", "")

    reported = _lint(text)

    assert len(reported) == 1
    assert "castellatedMeshControls" in reported[0].message
    assert reported[0].path == "system/snappyHexMeshDict"


def test_missing_snap_controls_are_reported():
    text = COMPLETE.replace("snapControls { nSmoothPatch 3; }\n", "")

    assert "snapControls" in _lint(text)[0].message


def test_enabled_layers_require_their_controls():
    text = COMPLETE.replace("addLayers false;", "addLayers true;")

    assert "addLayersControls" in _lint(text)[0].message


def test_mesh_quality_controls_are_always_required():
    text = COMPLETE.replace("meshQualityControls { maxNonOrtho 65; }\n", "")

    assert "meshQualityControls" in _lint(text)[0].message


def test_rule_catalog_documents_the_snappy_rule():
    metadata = rule_catalog()["OF-MESH-010"]
    assert metadata["title"] == "Incomplete snappy dictionary"
    assert metadata["severity"] == "warning"
    assert metadata["confidence"] == "structural"


def test_omitted_switches_default_to_enabled():
    text = "meshQualityControls { maxNonOrtho 65; }\n"

    reported = _lint(text)

    assert len(reported) == 1
    message = reported[0].message
    assert "castellatedMeshControls" in message
    assert "snapControls" in message
    assert "addLayersControls" in message


def test_on_off_spelling_is_understood():
    text = COMPLETE.replace("addLayers false;", "addLayers off;")

    assert _lint(text) == []


def test_dynamic_switch_is_not_judged():
    text = (
        "castellatedMesh $castellate;\nsnap true;\naddLayers false;\n"
        "snapControls { nSmoothPatch 3; }\n"
        "meshQualityControls { maxNonOrtho 65; }\n"
    )

    assert _lint(text) == []


def test_include_is_called_out_in_the_message():
    text = COMPLETE.replace(
        "meshQualityControls { maxNonOrtho 65; }\n",
        '#include "meshQualityDict"\n',
    )

    reported = _lint(text)

    assert "meshQualityControls" in reported[0].message
    assert "not expanded" in reported[0].message
