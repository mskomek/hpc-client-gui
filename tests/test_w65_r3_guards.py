"""W65r3: solver-effect mapping + explicit RAW-ADVANCED refusal (G23/G30).

W65r4: truthful non-dictionary/verify-only effects — exact PatchOp-target
mapping, no fictitious system/<tool>.dict fallback.
"""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.solver import SOLVER_BINARIES, check_solver_compat
from hpc_gui.plugins.openfoam_studio.solver_effects import bound_state, solver_effect_paths
from hpc_gui.plugins.openfoam_studio.workflow import (
    FUNCTION_OBJECTS,
    SOLVER_TOOLS,
    VERIFY_ONLY_TOOLS,
    Node,
    WorkflowDAG,
    compile_to_effects,
)
from hpc_gui.plugins.openfoam_studio.workflow_compiler import compile_patch_plan

SOLVER_TRIPLE = ["system/controlDict", "system/fvSchemes", "system/fvSolution"]


def _solver_dag(tool: str, params: dict) -> WorkflowDAG:
    dag = WorkflowDAG(nodes=[
        Node("m", "blockMesh", {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}),
        Node("s", tool, dict(params)),
    ], edges=[("m", "s")])
    return dag


def _mutating_solver_targets(tool: str, params: dict) -> list[str]:
    plan = compile_patch_plan(_solver_dag(tool, params))
    return [op.relpath for op in plan.ops
            if op.node_id == "s" and op.action in ("create", "replace", "append-token")]


# Representative valid solver nodes per family (round 5): simple, transient,
# compressible, buoyant, multiphase, CHT. Params are schema-valid; bound
# defaults fill the rest exactly as the compiler binds them.
VALID_SOLVER_CASES = [
    ("simpleFoam", {"endTime": 100.0, "writeInterval": 10.0,
                    "model": "kOmegaSST", "fields": ["U", "p", "k", "omega"]}),
    ("pimpleFoam", {"endTime": 1.0, "deltaT": 0.001, "maxCo": 1.0,
                    "model": "kOmegaSST", "fields": ["U", "p", "k", "omega"]}),
    ("rhoSimpleFoam", {"model": "kOmegaSST",
                       "fields": ["U", "p", "T", "k", "omega"]}),
    ("buoyantSimpleFoam", {"model": "kOmegaSST",
                           "fields": ["U", "p", "T", "k", "omega"]}),
    ("interFoam", {"model": "laminar", "fields": ["U", "p", "alpha.water"]}),
    ("chtMultiRegionSimpleFoam",
     {"endTime": 200.0, "writeInterval": 20.0, "model": "kOmegaSST",
      "fields": ["U", "p", "T", "k", "omega"],
      "regions": {"fluid": ["fluid"], "solid": ["solid"]}}),
]


@pytest.mark.parametrize(("tool", "params"), VALID_SOLVER_CASES)
def test_solver_effects_equal_compiler_patchop_targets(tool, params):
    """Equality (not subset): effect paths == all mutating PatchOp targets."""
    dag = _solver_dag(tool, params)
    assert compile_to_effects(dag)["s"] == _mutating_solver_targets(tool, params)


@pytest.mark.parametrize(("tool", "params"), VALID_SOLVER_CASES)
def test_solver_effects_are_complete_beyond_numerics_triple(tool, params):
    paths = solver_effect_paths(tool, params)
    assert paths[:3] == SOLVER_TRIPLE
    assert len(paths) > 3  # 0/<field> + transport/turbulence + family extras
    assert compile_to_effects(_solver_dag(tool, params))["s"] == paths


@pytest.mark.parametrize(("tool", "params"), [
    ("simpleFoam", {"endTime": 100.0, "writeInterval": 10.0}),
    ("interFoam", {}),
    ("rhoSimpleFoam", {"model": "kOmegaSST"}),
])
def test_solver_effects_default_binding_matches_compiler(tool, params):
    """Bound params/defaults bind identically in preview and compiler."""
    dag = _solver_dag(tool, dict(params))
    assert (compile_to_effects(dag)["s"]
            == _mutating_solver_targets(tool, dict(params))
            == solver_effect_paths(tool, dict(params)))


def test_cht_custom_regions_effects_equal_compiler_targets():
    params = {"endTime": 200.0, "writeInterval": 20.0, "model": "kOmegaSST",
              "fields": ["U", "p", "T", "k", "omega"],
              "regions": {"fluid": ["fluidA", "fluidB"], "solid": ["solidA"]}}
    dag = _solver_dag("chtMultiRegionSimpleFoam", params)
    expected = (["system/controlDict", "system/fvSchemes", "system/fvSolution",
                 "0/U", "0/p", "0/T", "0/k", "0/omega",
                 "constant/transportProperties", "constant/turbulenceProperties",
                 "constant/regionProperties",
                 "constant/fluidA/thermophysicalProperties",
                 "constant/fluidB/thermophysicalProperties",
                 "constant/solidA/thermophysicalProperties"])
    assert compile_to_effects(dag)["s"] == expected
    assert _mutating_solver_targets("chtMultiRegionSimpleFoam", params) == expected


@pytest.mark.parametrize("regions", [
    {"fluid": ["fluid"], "solid": []},
    ["fluid"],
])
def test_cht_effects_reject_missing_solid_region(regions):
    with pytest.raises(ValueError, match="at least one solid region"):
        bound_state("chtMultiRegionSimpleFoam", {"regions": regions})


@pytest.mark.parametrize("tool", ["reactingFoam", "potentialFoam"])
def test_unsupported_solvers_refuse_in_effects_and_compiler(tool):
    """reacting/potential have no typed model: explicit refusal, no paths."""
    with pytest.raises(ValueError, match="RAW-ADVANCED/UNSUPPORTED"):
        compile_to_effects(WorkflowDAG(nodes=[Node("s", tool)]))
    with pytest.raises(ValueError, match="RAW-ADVANCED/UNSUPPORTED"):
        compile_patch_plan(_solver_dag(tool, {}))


@pytest.mark.parametrize("tool", ["meshConverter", "fluentMeshToFoam", "foamToVTK"])
def test_converters_not_mapped_to_solver_triple(tool):
    """Converters/import targets never mutate solver numerics files.

    Exact assertion (not inequality): converter/verify-only nodes report
    ``[]`` — no file mutation — instead of a fictitious solver triple or
    ``system/<tool>.dict`` path. ``meshConverter`` compiles to a verify
    ``constant/polyMesh/IMPORTED`` PatchOp; ``fluentMeshToFoam`` is an
    unknown/RAW-ADVANCED tool name; ``foamToVTK`` compiles to a verify
    ``postProcessing/foamToVTK.report`` PatchOp.
    """
    from hpc_gui.plugins.openfoam_studio.workflow_compiler import compile_patch_plan as _c

    dag = WorkflowDAG(nodes=[Node("n", tool)])
    assert compile_to_effects(dag)["n"] == []
    assert compile_to_effects(dag)["n"] != SOLVER_TRIPLE
    if tool in ("meshConverter", "foamToVTK"):
        params = ({"converter": "fluentMeshToFoam", "meshFile": "fluent.msh"}
                  if tool == "meshConverter" else {"latestTime": True})
        chain = _chain_for_verify(tool, params)
        plan = _c(chain)
        mutating = [op.relpath for op in plan.ops
                    if op.node_id == "v" and op.action in ("create", "replace", "append-token")]
        assert mutating == []
        assert compile_to_effects(chain)["v"] == []


def _chain_for_verify(tool: str, params: dict) -> WorkflowDAG:
    """Single target node ``v`` with satisfied upstream guards.

    ``meshConverter``/``foamToVTK`` need a mesh producer / solver upstream
    for the compiler's stale-input guard; verify gates need none.
    """
    dag = WorkflowDAG()
    if tool == "meshConverter":
        dag.add_node(Node("m", "blockMesh",
                          {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}))
        dag.add_node(Node("v", tool, dict(params)))
        dag.add_edge("m", "v")
    elif tool == "foamToVTK":
        dag.add_node(Node("m", "blockMesh",
                          {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}))
        dag.add_node(Node("s", "simpleFoam",
                          {"endTime": 1.0, "writeInterval": 1.0,
                           "model": "kOmegaSST",
                           "fields": ["U", "p", "k", "omega"]}))
        dag.add_node(Node("v", tool, dict(params)))
        dag.add_edge("m", "s")
        dag.add_edge("s", "v")
    else:
        dag.add_node(Node("v", tool, dict(params)))
    return dag


def _full_tool_chain() -> WorkflowDAG:
    """One DAG covering every typed non-solver tool with guard-satisfying order."""
    bm = {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}
    dag = WorkflowDAG()
    dag.add_node(Node("bm", "blockMesh", dict(bm)))
    dag.add_node(Node("sfe", "surfaceFeatureExtract",
                      {"dict": "system/surfaceFeatureExtractDict",
                       "surfaces": ["wing.stl"]}))
    dag.add_node(Node("snappy", "snappyHexMesh", {"maxGlobalCells": 1000}))
    dag.add_node(Node("split", "splitMeshRegions", {}))
    dag.add_node(Node("check", "checkMesh", {}))
    dag.add_node(Node("decomp", "decomposePar", {"numberOfSubdomains": 2}))
    dag.add_node(Node("recon", "reconstructPar", {}))
    dag.add_node(Node("solver", "simpleFoam",
                      {"endTime": 1.0, "writeInterval": 1.0,
                       "model": "kOmegaSST", "fields": ["U", "p", "k", "omega"]}))
    dag.add_node(Node("func", "yPlus", {}))
    dag.add_node(Node("post", "postProcess", {"func": "probes"}))
    dag.add_node(Node("vtk", "foamToVTK", {"latestTime": True}))
    for a, b in [("bm", "sfe"), ("sfe", "snappy"), ("bm", "split"),
                 ("snappy", "check"), ("check", "decomp"),
                 ("decomp", "recon"), ("bm", "solver"),
                 ("solver", "func"), ("solver", "post"), ("solver", "vtk")]:
        dag.add_edge(a, b)
    return dag


def test_effects_equal_mutating_patchop_targets_all_typed_tools():
    """Equality (not subset) for EVERY typed non-solver tool.

    For each node: ``compile_to_effects`` == relpaths of that node's
    ``create``/``replace``/``append-token`` PatchOps. Verify-only nodes
    (checkMesh/reconstructPar/postProcess/foamToVTK) must have zero
    mutating ops and ``[]`` effects.
    """
    dag = _full_tool_chain()
    plan = compile_patch_plan(dag)
    effects = compile_to_effects(dag)
    for node in dag.nodes:
        mutating = [op.relpath for op in plan.ops
                    if op.node_id == node.node_id
                    and op.action in ("create", "replace", "append-token")]
        assert effects[node.node_id] == mutating, node.tool


def test_effects_equal_mutating_targets_mesh_converter_chain():
    """meshConverter import target is verify-only: effects ``[]`` == no mutating ops."""
    dag = WorkflowDAG()
    dag.add_node(Node("cv", "meshConverter",
                      {"converter": "fluentMeshToFoam", "meshFile": "fluent.msh"}))
    dag.add_node(Node("check", "checkMesh", {}))
    dag.add_edge("cv", "check")
    plan = compile_patch_plan(dag)
    mutating = [op for op in plan.ops
                if op.node_id == "cv" and op.action in ("create", "replace", "append-token")]
    assert mutating == []
    assert compile_to_effects(dag)["cv"] == []


@pytest.mark.parametrize(("tool", "params"), [
    ("probes", {"fields": ["U"], "probeLocations": ["(0 0 0)"]}),
    ("fieldAverage", {"fields": ["U"], "timeStart": 0.0}),
    ("forces", {"patches": ["walls"], "rhoInf": 1.225}),
    ("forceCoeffs", {"patches": ["walls"], "magUInf": 10.0,
                     "lRef": 1.0, "Aref": 1.0}),
    ("yPlus", {}),
    ("wallShearStress", {}),
])
def test_effects_equal_mutating_targets_function_objects(tool, params):
    """Each function object appends exactly system/controlDict#functions."""
    dag = WorkflowDAG(nodes=[Node("f", tool, dict(params))])
    plan = compile_patch_plan(dag)
    mutating = [op.relpath for op in plan.ops
                if op.node_id == "f" and op.action in ("create", "replace", "append-token")]
    assert mutating == ["system/controlDict#functions"]
    assert compile_to_effects(dag)["f"] == ["system/controlDict#functions"]


def test_reacting_refusal_names_raw_advanced():
    with pytest.raises(ValueError, match="RAW-ADVANCED/UNSUPPORTED"):
        check_solver_compat("reactingFoam", "laminar", ["U", "p", "T"])


def test_reacting_still_refuses_unknown_model_first():
    with pytest.raises(ValueError, match="RAW-ADVANCED/UNSUPPORTED"):
        check_solver_compat("reactingFoam", "kOmegaSST", ["U", "p", "T", "k", "omega"])


def test_effect_solver_tool_set_matches_classified_binaries():
    assert SOLVER_TOOLS == set(SOLVER_BINARIES)


@pytest.mark.parametrize(("tool", "expected"), [
    ("surfaceFeatureExtract", ["system/surfaceFeatureExtractDict"]),
    ("splitMeshRegions", ["constant/regionProperties"]),
    ("blockMesh", ["system/blockMeshDict"]),
    ("snappyHexMesh", ["system/snappyHexMeshDict"]),
    ("decomposePar", ["system/decomposeParDict"]),
])
def test_dictionary_nodes_map_to_exact_patchop_targets(tool, expected):
    dag = WorkflowDAG(nodes=[Node("n", tool)])
    assert compile_to_effects(dag)["n"] == expected


@pytest.mark.parametrize("tool", sorted(FUNCTION_OBJECTS))
def test_function_objects_append_control_dict_functions(tool):
    dag = WorkflowDAG(nodes=[Node("n", tool)])
    assert compile_to_effects(dag)["n"] == ["system/controlDict#functions"]


@pytest.mark.parametrize("tool", sorted(VERIFY_ONLY_TOOLS))
def test_verify_only_nodes_report_no_file_mutation(tool):
    """checkMesh/cadGate/intakes/meshConverter/postProcess/foamToVTK/
    reconstructPar compile to verify PatchOps: no case-file mutation."""
    dag = WorkflowDAG(nodes=[Node("n", tool)])
    assert compile_to_effects(dag)["n"] == []


@pytest.mark.parametrize("tool", ["fluentMeshToFoam", "gmshToFoam", "ghostTool", "snappyFoo"])
def test_no_fictitious_system_tool_dict_fallback(tool):
    """Unknown/RAW-ADVANCED tools must not get a fake system/<tool>.dict."""
    dag = WorkflowDAG(nodes=[Node("n", tool)])
    assert compile_to_effects(dag)["n"] == []


def test_unclassified_foam_suffix_is_not_a_solver():
    dag = WorkflowDAG(nodes=[Node("n", "customFoam")])
    assert compile_to_effects(dag)["n"] == []
