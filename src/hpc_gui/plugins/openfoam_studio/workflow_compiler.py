"""Typed DAG-to-patch-set compiler for T1-T12 journeys (W65 FLOW-011, G31).

:func:`compile_patch_plan` turns a :class:`WorkflowDAG` into a reviewable
:class:`PatchPlan` with exact per-file bytes built by the typed writers
(blockMesh, snappy, boundary, numerics, physics, CHT, solver, post).
``preview_plan``/``apply_plan`` route through :mod:`patch_plan`, hence
through ``safe_patch``. Guards: stale-input edges, solver-before-mesh
ordering, duplicate destructive mesh steps, and destructive-overwrite
confirmation. Nothing here executes a solver or touches the network.
"""

from __future__ import annotations

from hpc_gui.plugins.openfoam_studio import (
    advanced_physics,
    blockmesh,
    boundary,
    cht,
    command_schemas,
    mesh_regions,
    numerics_text,
    numerics,
    physics,
    post,
    snappy,
    solver,
    solver_effects,
    surface_actions,
)
from hpc_gui.plugins.openfoam_studio.patch_plan import PatchOp, PatchPlan, apply, preview
from hpc_gui.plugins.openfoam_studio.workflow import (
    WorkflowDAG,
    find_cycle,
    solver_before_mesh,
    Node,
)


SOLVER_TOOLS = frozenset(solver.SOLVER_BINARIES)
MESH_TOOLS = frozenset({"blockMesh", "snappyHexMesh", "meshConverter"})
VERIFY_ONLY = frozenset({"checkMesh", "cadGate", "sftpStage", "lifecycleGate",
                         "meshIntake", "surfaceIntake"})

#: Predecessor tool-classes each tool requires upstream (stale-input guard).
REQUIRES: dict[str, frozenset[str]] = {
    "snappyHexMesh": frozenset({"blockMesh"}),
    "surfaceFeatureExtract": frozenset({"blockMesh", "surfaceIntake"}),
    "decomposePar": MESH_TOOLS | {"meshIntake"},
    "splitMeshRegions": MESH_TOOLS | {"meshIntake"},
    "postProcess": SOLVER_TOOLS,
    "foamToVTK": SOLVER_TOOLS,
    "reconstructPar": frozenset({"decomposePar"}),
}

DEFAULT_PATCHES = {"inlet": ("inlet", "fixedValue"),
                   "outlet": ("outlet", "zeroGradient"),
                   "walls": ("wall", "noSlip")}


SOLVER_EXTRAS = frozenset({"model", "fields", "patches", "regions", "rho", "mu",
                           "deltaT", "endTime", "writeInterval", "parallel",
                           "numberOfSubdomains", "maxCo"})
EXTRA_PARAMS: dict[str, frozenset[str]] = {
    "surfaceFeatureExtract": frozenset({"surfaces"}),
    "snappyHexMesh": frozenset({"overwrite", "surfaces"}),
    "meshConverter": frozenset({"converter", "meshFile"}),
    "splitMeshRegions": frozenset({"regions"}),
}
for _solver_tool in SOLVER_TOOLS:
    EXTRA_PARAMS.setdefault(_solver_tool, SOLVER_EXTRAS)


def _validated(tool: str, params: dict) -> dict:
    extras = EXTRA_PARAMS.get(tool, frozenset())
    if tool in command_schemas.SCHEMAS:
        known = {p["name"] for p in command_schemas.SCHEMAS[tool]["params"]}
        unknown = sorted(set(params) - known - extras)
        if unknown:
            raise ValueError(f"node params unknown for '{tool}': {', '.join(unknown)}")
        try:
            merged = command_schemas.validate(
                tool, {k: v for k, v in params.items() if k in known})
        except command_schemas.SchemaError as exc:
            raise ValueError(f"node params invalid for '{tool}': {exc}") from exc
        merged.update({k: v for k, v in params.items() if k in extras})
        return merged
    return dict(params)


def _solver_files(tool: str, params: dict) -> list[tuple[str, str, bool]]:
    """(relpath, content, destructive) for a solver node.

    Binds (family, model, fields, regions) through the shared leaf
    ``solver_effects.bound_state`` — the same binding
    ``workflow.compile_to_effects`` uses — so effect paths and mutating
    PatchOp targets stay identical for bound params/defaults.
    """
    family, model, fields, regions = solver_effects.bound_state(tool, params)
    patches = params.get("patches", dict(DEFAULT_PATCHES))
    solver.check_solver_compat(tool, model, fields,
                               list(regions["fluid"]) + list(regions["solid"])
                               if family == "cht" and regions else None)
    end_time = float(params.get("endTime", 100.0))
    delta_t = float(params.get("deltaT", 0.005 if family == "transient" else 1.0))
    write_interval = params.get("writeInterval", 10.0)
    files = [("system/controlDict",
              numerics.render_control_dict(tool, 0.0, end_time, delta_t, write_interval), False)]
    nu_entries = {"ddt": numerics_text.ddt_scheme(tool),
                  "grad": "Gauss linear", "div": "Gauss linear",
                  "laplacian": "Gauss linear corrected", "family": family}
    numerics.validate_fv_schemes(nu_entries["ddt"], nu_entries["grad"],
                                 nu_entries["div"], nu_entries["laplacian"],
                                 nu_entries["family"], tool=tool)
    files.append(("system/fvSchemes", numerics_text.fv_schemes_text(tool, family), False))
    numerics.validate_fv_solution("GAMG",
                                  {"nCorrectors": 2} if family == "transient" else None,
                                  {"p": 0.3, "U": 0.7})
    files.append(("system/fvSolution", numerics_text.fv_solution_text(tool, family), False))
    internal = {"U": "(0 0 0)", "p": "0", "T": "300",
                "k": "0.1", "epsilon": "0.01", "omega": "1.0",
                "alpha.water": "0", "p_rgh": "0"}
    for fld in fields:
        files.append((f"0/{fld}",
                      boundary.render_field_file(fld, internal.get(fld, "0"), patches), False))
    files.append(("constant/transportProperties",
                  physics.transport_properties_dict(float(params.get("rho", 1.225)),
                                                    float(params.get("mu", 1.789e-05))), False))
    files.append(("constant/turbulenceProperties",
                  physics.turbulence_properties_dict(model), False))
    if family == "cht":
        assert regions is not None
        files.append(("constant/regionProperties",
                      mesh_regions.region_properties_dict(regions.get("fluid", ["fluid"]),
                                                          regions.get("solid", ["solid"])),
                      False))
        for region in regions.get("fluid", ["fluid"]):
            files.append((f"constant/{region}/thermophysicalProperties",
                          cht.region_thermophysical_dict(region, fluid=True), False))
        for region in regions.get("solid", ["solid"]):
            files.append((f"constant/{region}/thermophysicalProperties",
                          cht.region_thermophysical_dict(region, fluid=False), False))
    elif family in ("compressible", "buoyant", "multiphase"):
        files.append(("constant/thermophysicalProperties",
                      advanced_physics.thermophysical_properties_dict(family), False))
    return files


def _ops_for_tool(node: Node) -> list[PatchOp]:
    tool, params = node.tool, _validated(node.tool, node.params)
    nid = node.node_id
    if tool == "blockMesh":
        blockmesh.validate_topology(params["nx"], params["ny"], params["nz"])
        text = blockmesh.render_block_mesh_dict(params["nx"], params["ny"],
                                                params["nz"], params["patches"],
                                                params.get("grading", "simpleGrading (1 1 1)"))
        return [PatchOp(nid, tool, "system/blockMeshDict", "create", text.encode(),
                        argv=("blockMesh", "-case", "."))]
    if tool == "surfaceFeatureExtract":
        text = surface_actions.feature_extract_dict(
            params.get("surfaces", ["surface.stl"]),
            included_angle=float(params.get("includedAngle", 150.0)))
        return [PatchOp(nid, tool, "system/surfaceFeatureExtractDict", "create",
                        text.encode(),
                        argv=tuple(surface_actions.feature_extract_argv("surface.stl")))]
    if tool == "snappyHexMesh":
        text = snappy.render_snappy_dict(
            max_global_cells=params["maxGlobalCells"],
            castellated=bool(params.get("castellatedMesh", True)),
            snap=bool(params.get("snap", True)),
            add_layers=bool(params.get("addLayers", False)),
            n_layers=int(params.get("nLayers", 0)),
            expansion_ratio=float(params.get("expansionRatio", 1.2)))
        destructive = bool(params.get("overwrite", False))
        argv = ["snappyHexMesh", "-case", "."] + (["-overwrite"] if destructive else [])
        return [PatchOp(nid, tool, "system/snappyHexMeshDict", "create", text.encode(),
                        argv=tuple(argv), destructive=destructive)]
    if tool == "decomposePar":
        text = numerics.render_decompose_dict(params["numberOfSubdomains"],
                                              params.get("method", "scotch"))
        return [PatchOp(nid, tool, "system/decomposeParDict", "create", text.encode(),
                        argv=("decomposePar", "-case", ".", "-force"), destructive=True)]
    if tool == "splitMeshRegions":
        regions = params.get("regions", {"fluid": ["fluid"], "solid": ["solid"]})
        text = mesh_regions.region_properties_dict(regions.get("fluid", ["fluid"]),
                                                   regions.get("solid", ["solid"]))
        return [PatchOp(nid, tool, "constant/regionProperties", "create", text.encode(),
                        argv=tuple(mesh_regions.zone_argv("splitMeshRegions")),
                        destructive=True)]
    if tool == "meshConverter":
        from hpc_gui.plugins.openfoam_studio.mesh_regions import converter_argv
        argv = converter_argv(params["converter"], params["meshFile"])
        return [PatchOp(nid, tool, "constant/polyMesh/IMPORTED", "verify", b"",
                        argv=tuple(argv), destructive=True,
                        detail=f"imports {params['meshFile']} via {params['converter']}")]
    if tool in ("probes", "fieldAverage", "forces", "forceCoeffs", "yPlus", "wallShearStress"):
        text = post.render_function_object(tool, {k: v for k, v in params.items()
                                                  if k not in ("dict",)})
        return [PatchOp(nid, tool, "system/controlDict#functions", "append-token",
                        text.encode(), old_token=b"}",
                        new_token=("}\n" + text).encode(),
                        detail=f"functionObject {tool}")]
    if tool in ("postProcess", "foamToVTK", "reconstructPar"):
        argv = [tool, "-case", "."]
        if params.get("func"):
            argv += ["-func", str(params["func"])]
        if params.get("latestTime"):
            argv.append("-latestTime")
        return [PatchOp(nid, tool, f"postProcessing/{tool}.report", "verify", b"",
                        argv=tuple(argv), detail=f"{tool} draft preview")]
    if tool in SOLVER_TOOLS:
        return [PatchOp(nid, tool, path, "create", text.encode(),
                        argv=tuple(solver.render_run_plan(
                            tool, parallel=bool(params.get("parallel", False)),
                            n_subdomains=int(params.get("numberOfSubdomains", 1)))["steps"][0]))
                for path, text, _ in _solver_files(tool, params)]
    if tool in VERIFY_ONLY:
        detail = {"cadGate": "STEP intake gated: converter absent -> BLOCKED_EXTERNAL",
                  "checkMesh": "mesh quality readback; no fabrication"}.get(tool, tool)
        return [PatchOp(nid, tool, f"flow/{nid}.gate", "verify", b"", detail=detail)]
    raise ValueError(f"compiler has no typed schema for tool '{tool}' (RAW-ADVANCED only)")


def _topo_order(dag: WorkflowDAG) -> list[str]:
    ids = dag.ids()
    for a, b in dag.edges:
        if a not in ids or b not in ids:
            raise ValueError(f"stale-input edge '{a}'->'{b}': missing producer/consumer node")
    incoming: dict[str, int] = {i: 0 for i in ids}
    succ: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in dag.edges:
        succ[a].append(b)
        incoming[b] += 1
    queue = [n.node_id for n in dag.nodes if incoming[n.node_id] == 0]
    order: list[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in succ[current]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(ids):
        raise ValueError("illegal cycle rejected: DAG is not topologically sortable")
    return order


def compile_patch_plan(dag: WorkflowDAG) -> PatchPlan:
    """Compile a DAG to a typed per-file patch plan (raises on guards)."""
    if find_cycle(dag):
        raise ValueError("illegal cycle rejected")
    if solver_before_mesh(dag):
        raise ValueError("solver-before-mesh rejected: mesh producer must precede solver")
    force_decomposes = [n.node_id for n in dag.nodes
                        if n.tool == "decomposePar" and n.params.get("force", True)]
    if len(force_decomposes) > 1:
        raise ValueError(f"duplicate destructive decomposePar rejected: {force_decomposes}")
    order = _topo_order(dag)
    by_id = {n.node_id: n for n in dag.nodes}
    plan = PatchPlan(node_order=order)
    for nid in order:
        node = by_id[nid]
        need = REQUIRES.get(node.tool)
        if need:
            prior = {by_id[earlier].tool for earlier in order[:order.index(nid)]}
            if not (prior & need):
                raise ValueError(
                    f"stale input: node '{nid}' ({node.tool}) requires one of "
                    f"{sorted(need)} upstream")
        plan.ops.extend(_ops_for_tool(node))
    return plan


def preview_plan(plan: PatchPlan, originals: dict[str, bytes] | None = None) -> str:
    return preview(plan, originals)


def apply_plan(plan: PatchPlan, case_files: dict[str, bytes],
               *, allow_destructive: bool = False) -> dict[str, bytes]:
    return apply(plan, case_files, allow_destructive=allow_destructive)


def _chain(steps: list[tuple[str, dict]]) -> WorkflowDAG:
    dag = WorkflowDAG()
    prev = ""
    for i, (tool, params) in enumerate(steps):
        nid = f"n{i}-{tool}"
        dag.add_node(Node(nid, tool, params))
        if prev:
            dag.add_edge(prev, nid)
        prev = nid
    return dag


def journey_dag(journey: str) -> WorkflowDAG:
    """Canonical T1-T12 journey DAGs with schema-validated default params."""
    bm = {"nx": 20, "ny": 20, "nz": 20, "patches": ["inlet", "outlet", "walls"]}
    snappy = {"maxGlobalCells": 200000}
    simple = {"endTime": 100.0, "writeInterval": 10.0, "model": "kOmegaSST",
              "fields": ["U", "p", "k", "omega"]}
    if journey == "T1":
        return _chain([("blockMesh", bm), ("checkMesh", {}),
                       ("simpleFoam", simple), ("postProcess", {"func": "probes"})])
    if journey == "T2":
        return _chain([("surfaceIntake", {}), ("blockMesh", bm),
                       ("surfaceFeatureExtract", {"dict": "system/surfaceFeatureExtractDict",
                                                 "surfaces": ["wing.stl"]}),
                       ("snappyHexMesh", snappy), ("checkMesh", {}),
                       ("simpleFoam", simple), ("postProcess", {"func": "yPlus"})])
    if journey == "T3":
        return _chain([("cadGate", {}), ("surfaceIntake", {}), ("blockMesh", bm),
                       ("snappyHexMesh", snappy),
                       ("simpleFoam", simple)])
    if journey == "T4":
        return _chain([("blockMesh", bm), ("simpleFoam", simple),
                       ("postProcess", {"func": "forceCoeffs"})])
    if journey == "T5":
        pimple = {"endTime": 1.0, "deltaT": 0.001, "maxCo": 1.0,
                  "model": "kOmegaSST", "fields": ["U", "p", "k", "omega"],
                  "parallel": True, "numberOfSubdomains": 2}
        return _chain([("blockMesh", bm),
                       ("decomposePar", {"numberOfSubdomains": 2}),
                       ("pimpleFoam", pimple), ("reconstructPar", {}),
                       ("postProcess", {"func": "probes"})])
    if journey == "T6":
        cht_params = {"endTime": 200.0, "writeInterval": 20.0, "model": "kOmegaSST",
                      "fields": ["U", "p", "T", "k", "omega"],
                      "regions": {"fluid": ["fluid"], "solid": ["solid"]}}
        return _chain([("blockMesh", bm), ("splitMeshRegions", {}),
                       ("chtMultiRegionSimpleFoam", cht_params),
                       ("postProcess", {"func": "fieldAverage"})])
    if journey == "T7":
        return _chain([("meshConverter", {"converter": "fluentMeshToFoam",
                                          "meshFile": "fluent.msh"}),
                       ("checkMesh", {}), ("simpleFoam", simple),
                       ("foamToVTK", {"latestTime": True})])
    if journey == "T8":
        inter = {"endTime": 1.0, "writeInterval": 0.1, "model": "laminar",
                 "fields": ["U", "p", "alpha.water"]}
        return _chain([("blockMesh", bm), ("interFoam", inter),
                       ("postProcess", {"func": "probes"})])
    if journey == "T9":
        buoyant = {"endTime": 200.0, "writeInterval": 20.0, "model": "kOmegaSST",
                   "fields": ["U", "p", "T", "k", "omega"]}
        return _chain([("blockMesh", bm), ("buoyantSimpleFoam", buoyant),
                       ("postProcess", {"func": "fieldAverage"})])
    if journey == "T10":
        reacting = {"endTime": 1.0, "writeInterval": 0.1, "model": "laminar",
                    "fields": ["U", "p", "T"]}
        return _chain([("blockMesh", bm), ("reactingFoam", reacting)])
    if journey == "T11":
        return _chain([("meshIntake", {}), ("sftpStage", {}), ("checkMesh", {})])
    if journey == "T12":
        return _chain([("lifecycleGate", {}), ("checkMesh", {})])
    raise ValueError(f"unknown journey '{journey}' (expected T1-T12)")
