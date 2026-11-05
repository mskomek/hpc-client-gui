"""W65r2 F1: typed DAG compiler (G31) — patch plans for T1-T12 + guards."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.workflow import Node, WorkflowDAG
from hpc_gui.plugins.openfoam_studio.patch_plan import PatchOp, PatchPlan, apply, sha256_bytes
from hpc_gui.plugins.openfoam_studio.workflow_compiler import (
    apply_plan,
    compile_patch_plan,
    journey_dag,
    preview_plan,
)

COMPILES = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T11", "T12"]


@pytest.mark.parametrize("journey", COMPILES)
def test_journey_compiles_to_typed_patch_set(journey):
    plan = compile_patch_plan(journey_dag(journey))
    assert plan.node_order and plan.ops and plan.files()
    text = preview_plan(plan)
    assert "system/" in text or "verify-only" in text or "postProcessing" in text
    for op in plan.ops:
        assert op.relpath and op.provenance.startswith("workflow-compiler")


def test_t10_reacting_refused_as_raw_advanced():
    with pytest.raises(ValueError):
        compile_patch_plan(journey_dag("T10"))


def test_apply_creates_files_and_destructive_needs_confirm():
    plan = compile_patch_plan(journey_dag("T5"))  # has decomposePar -force
    assert plan.destructive_ops()
    with pytest.raises(ValueError, match="destructive-overwrite guard"):
        apply_plan(plan, {})
    result = apply_plan(plan, {}, allow_destructive=True)
    assert "system/decomposeParDict" in result
    assert "system/blockMeshDict" in result


def test_apply_rejects_create_over_existing_and_stale_append():
    plan = compile_patch_plan(journey_dag("T1"))
    with pytest.raises(ValueError, match="already exists"):
        apply_plan(plan, {"system/blockMeshDict": b"old"}, allow_destructive=True)


def test_stale_input_edge_missing_producer():
    dag = WorkflowDAG(nodes=[Node("s", "snappyHexMesh",
                                   {"maxGlobalCells": 1000})])
    dag.edges.append(("ghost", "s"))
    with pytest.raises(ValueError, match="stale-input"):
        compile_patch_plan(dag)


def test_stale_upstream_requirement():
    dag = WorkflowDAG(nodes=[Node("s", "snappyHexMesh", {"maxGlobalCells": 1000}),
                             Node("c", "checkMesh", {})],
                      edges=[("s", "c")])
    with pytest.raises(ValueError, match="requires one of"):
        compile_patch_plan(dag)


def test_solver_before_mesh_rejected():
    dag = WorkflowDAG(nodes=[Node("s", "simpleFoam",
                                   {"endTime": 1.0, "writeInterval": 1.0}),
                             Node("m", "blockMesh",
                                   {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]})])
    with pytest.raises(ValueError, match="solver-before-mesh"):
        compile_patch_plan(dag)


def test_duplicate_destructive_decompose_rejected():
    dag = WorkflowDAG()
    dag.add_node(Node("d1", "decomposePar", {"numberOfSubdomains": 2}))
    dag.add_node(Node("m", "blockMesh",
                      {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}))
    dag.add_node(Node("d2", "decomposePar", {"numberOfSubdomains": 2}))
    dag.add_edge("m", "d1")
    dag.add_edge("d1", "d2")
    with pytest.raises(ValueError, match="duplicate destructive"):
        compile_patch_plan(dag)


def test_reordered_mesh_after_solver_rejected():
    from hpc_gui.plugins.openfoam_studio.wx_flow import move_node
    dag = WorkflowDAG(nodes=[Node("m", "blockMesh",
                                   {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}),
                             Node("s", "simpleFoam",
                                   {"endTime": 1.0, "writeInterval": 1.0})],
                      edges=[("m", "s")])
    moved = move_node(dag, "m", 1)
    with pytest.raises(ValueError, match="solver-before-mesh"):
        compile_patch_plan(moved)


def test_unknown_tool_and_param_rejected():
    dag = WorkflowDAG(nodes=[Node("m", "blockMesh",
                                   {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]})])
    dag.add_node(Node("x", "teleportFoam", {}))
    dag.add_edge("m", "x")
    with pytest.raises(ValueError, match="no typed schema"):
        compile_patch_plan(dag)
    bad = WorkflowDAG(nodes=[Node("m", "blockMesh",
                                   {"nx": 2, "ny": 2, "nz": 2,
                                    "patches": ["walls"], "warp": 9})])
    with pytest.raises(ValueError, match="unknown"):
        compile_patch_plan(bad)


def test_replace_requires_matching_source_hash():
    plan = PatchPlan(ops=[PatchOp("n", "controlDict", "system/controlDict",
                                  "replace", b"new", expected_sha256=sha256_bytes(b"old"))])
    assert apply(plan, {"system/controlDict": b"old"})["system/controlDict"] == b"new"
    with pytest.raises(ValueError, match="changed since preview"):
        apply(plan, {"system/controlDict": b"user edit"})
    unbound = PatchPlan(ops=[PatchOp("n", "controlDict", "system/controlDict",
                                     "replace", b"new")])
    with pytest.raises(ValueError, match="requires existing bytes and expected_sha256"):
        apply(unbound, {"system/controlDict": b"old"})
