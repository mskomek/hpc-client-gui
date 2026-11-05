"""W65r2 F2: GUI parity data layer + lazy wx builders (G33/G35)."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.workflow_compiler import journey_dag
from hpc_gui.plugins.openfoam_studio.wx_flow import build_flow_panel, cards_for_dag, move_node
from hpc_gui.plugins.openfoam_studio.wx_panels import (
    LABELS,
    diff_rows,
    inspector_rows,
    results_rows,
    selector_state,
    validation_rows,
)


def test_flow_cards_and_reorder():
    dag = journey_dag("T1")
    cards = cards_for_dag(dag)
    assert [c.node_id for c in cards] == dag.ids()
    assert all(c.title_en for c in cards)
    moved = move_node(dag, dag.ids()[0], 2)
    assert moved.ids()[2] == dag.ids()[0]
    assert moved.ids() != dag.ids()
    with pytest.raises(ValueError):
        move_node(dag, "ghost", 0)
    with pytest.raises(ValueError):
        move_node(dag, dag.ids()[0], 99)


def test_inspector_selector_tr_en():
    rows = inspector_rows("blockMesh", {"nx": 20})
    assert any(r["name"] == "nx" and r["required"] for r in rows)
    raw = inspector_rows("teleportFoam", {})
    assert raw[0]["type"] == "raw"
    sel = selector_state()
    assert sel["version"] == "v2312" and sel["unsupported_disabled"] is True
    with pytest.raises(ValueError):
        selector_state(version="v9999")
    assert LABELS["inspector"]["tr"] == "Denetçi"
    assert LABELS["results"]["en"] == "Results"


def test_diff_validation_results_panels():
    from hpc_gui.plugins.openfoam_studio.workflow_compiler import (
        compile_patch_plan,
        preview_plan,
    )
    text = preview_plan(compile_patch_plan(journey_dag("T1")))
    rows = diff_rows(text)
    assert any(r["kind"] == "add" for r in rows)
    assert diff_rows("--- verify-only gate [x]") == [{"kind": "info",
                                                     "text": "--- verify-only gate [x]"}]
    from hpc_gui.plugins.openfoam_lint.api import lint_text
    diags = lint_text("0/U", "#codeStream\n{\ncode 1;\n}\n")
    vrows = validation_rows(diags)
    assert vrows and all("rule" in r for r in vrows)
    missing = results_rows([], [])
    assert missing["status"] == "MISSING"
    present = results_rows(["0", "1"], ["postProcessing/sets"], {"Ux": [0.5]})
    assert present["status"] == "PRESENT" and present["series"] == ["Ux"]


def test_wx_importable_and_builders_exist():
    pytest.importorskip("wx")
    assert callable(build_flow_panel)
