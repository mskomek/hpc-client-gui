"""Typed workflow DAG + migration + compiler + history (W65 FLOW-011, G30-G32)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from hpc_gui.plugins.openfoam_studio.solver_effects import SOLVER_BINARIES

LEGACY_8 = ("blockMesh", "checkMesh", "decomposePar", "splitMeshRegions",
            "icoFoam", "chtMultiRegionSimpleFoam", "reconstructPar", "postProcess")


@dataclass
class Node:
    node_id: str
    tool: str
    params: dict = field(default_factory=dict)
    inputs: tuple = ()
    outputs: tuple = ()
    lint_ids: tuple = ()


@dataclass
class WorkflowDAG:
    nodes: list[Node] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)

    def ids(self) -> list[str]:
        return [n.node_id for n in self.nodes]

    def add_node(self, node: Node) -> None:
        if node.node_id in self.ids():
            raise ValueError(f"duplicate node id '{node.node_id}'")
        self.nodes.append(node)

    def add_edge(self, producer: str, consumer: str) -> None:
        if producer not in self.ids() or consumer not in self.ids():
            raise ValueError("edge references missing producer/consumer (stale consumer)")
        self.edges.append((producer, consumer))
        if find_cycle(self):
            self.edges.pop()
            raise ValueError("illegal cycle rejected")


def find_cycle(dag: WorkflowDAG) -> list[str] | None:
    adj: dict[str, list[str]] = {n.node_id: [] for n in dag.nodes}
    for a, b in dag.edges:
        adj.setdefault(a, []).append(b)
    color: dict[str, int] = {}
    stack: list[str] = []

    def visit(u: str) -> list[str] | None:
        color[u] = 1
        stack.append(u)
        for v in adj.get(u, []):
            if color.get(v) == 1:
                return stack[stack.index(v):] + [v]
            if color.get(v) is None:
                hit = visit(v)
                if hit:
                    return hit
        stack.pop()
        color[u] = 2
        return None

    for node in dag.nodes:
        if color.get(node.node_id) is None:
            hit = visit(node.node_id)
            if hit:
                return hit
    return None


#: Tools that actually produce a mesh (checkMesh only reads it).
MESH_PRODUCERS = frozenset({"blockMesh", "snappyHexMesh", "meshConverter", "meshIntake"})

#: Classified solver binaries mutate the case files listed by
#: ``solver_effects.solver_effect_paths`` (shared with the typed compiler).
#: workflow.py imports only the leaf ``solver_effects`` module — never
#: ``solver`` itself — to keep the dependency DAG acyclic toward
#: lower-level contracts.
SOLVER_TOOLS = frozenset(SOLVER_BINARIES)

#: Function-object nodes append into system/controlDict (same target as the
#: compiler's append-token PatchOps in workflow_compiler._ops_for_tool).
FUNCTION_OBJECTS = frozenset({
    "probes", "fieldAverage", "forces", "forceCoeffs", "yPlus", "wallShearStress",
})

#: Read-only/verify-only nodes: the compiler emits verify PatchOps with no
#: case-file mutation, so the effect set is empty.
VERIFY_ONLY_TOOLS = frozenset({
    "checkMesh", "cadGate", "sftpStage", "lifecycleGate",
    "meshIntake", "surfaceIntake", "meshConverter",
    "postProcess", "foamToVTK", "reconstructPar",
})

SOLVER_TRIPLE = ["system/controlDict", "system/fvSchemes", "system/fvSolution"]


def solver_before_mesh(dag: WorkflowDAG) -> bool:
    tools = [n.tool for n in dag.nodes]
    first_solver = next((i for i, t in enumerate(tools) if "Foam" in t), None)
    first_mesh = next((i for i, t in enumerate(tools) if t in MESH_PRODUCERS), None)
    return first_solver is not None and (first_mesh is None or first_solver < first_mesh)


def migrate_legacy(plan: list[str]) -> WorkflowDAG:
    dag = WorkflowDAG()
    for i, tool in enumerate(plan):
        if tool not in LEGACY_8:
            raise ValueError(f"legacy plan contains unknown 0.2.1 command '{tool}'")
        dag.add_node(Node(f"legacy-{i}-{tool}", tool))
        if i:
            dag.add_edge(f"legacy-{i-1}-{plan[i-1]}", f"legacy-{i}-{tool}")
    return dag


def compile_to_effects(dag: WorkflowDAG) -> dict[str, list[str]]:
    """Map each node to the case-file paths it mutates (static, no execution).

    The mapping mirrors the PatchOp targets/modes emitted by
    ``workflow_compiler._ops_for_tool``: ``create``/``replace``/``append-token``
    ops report their exact relpath; ``verify``-only nodes (read-only checks,
    intake gates, mesh-converter import targets, postprocess report previews)
    and unknown/RAW-ADVANCED tools report ``[]`` (no file mutation) instead of
    a fictitious ``system/<tool>.dict`` path.

    Solver nodes report the COMPLETE mutating set for bound params/defaults
    via the shared leaf ``solver_effects.solver_effect_paths`` — the numerics
    triple plus ``0/<field>`` files, transport/turbulence properties, and
    family extras (CHT regionProperties + per-region thermophysical files,
    or single thermophysicalProperties for compressible/buoyant/multiphase).
    Unsupported solvers (reacting/potential: no typed model) raise the same
    explicit RAW-ADVANCED/UNSUPPORTED refusal the compiler emits.
    """
    from hpc_gui.plugins.openfoam_studio.solver_effects import solver_effect_paths

    effects: dict[str, list[str]] = {}
    for node in dag.nodes:
        tool = node.tool
        if tool == "blockMesh":
            effects[node.node_id] = ["system/blockMeshDict"]
        elif tool == "surfaceFeatureExtract":
            effects[node.node_id] = ["system/surfaceFeatureExtractDict"]
        elif tool == "snappyHexMesh":
            effects[node.node_id] = ["system/snappyHexMeshDict"]
        elif tool in SOLVER_TOOLS:
            # Complete solver file set for bound params/defaults; raises for
            # unsupported families. Converter names (fluentMeshToFoam,
            # meshConverter, foamToVTK) are NOT solvers and fall through to
            # the verify-only branch.
            effects[node.node_id] = list(solver_effect_paths(tool, node.params))
        elif tool == "decomposePar":
            effects[node.node_id] = ["system/decomposeParDict"]
        elif tool == "splitMeshRegions":
            effects[node.node_id] = ["constant/regionProperties"]
        elif tool in FUNCTION_OBJECTS:
            effects[node.node_id] = ["system/controlDict#functions"]
        elif tool in VERIFY_ONLY_TOOLS:
            effects[node.node_id] = []
        else:
            # Unknown/RAW-ADVANCED tool: the typed compiler has no schema for
            # it, so there is no known file mutation to report.
            effects[node.node_id] = []
    return effects


class EditHistory:
    """Undo/redo over DAG snapshots (in-memory; crash recovery serializes)."""

    def __init__(self, initial: WorkflowDAG) -> None:
        self._past: list[WorkflowDAG] = []
        self._future: list[WorkflowDAG] = []
        self.current = copy.deepcopy(initial)

    def commit(self, dag: WorkflowDAG) -> None:
        self._past.append(copy.deepcopy(self.current))
        self.current = copy.deepcopy(dag)
        self._future.clear()

    def undo(self) -> WorkflowDAG:
        if not self._past:
            raise ValueError("nothing to undo")
        self._future.append(copy.deepcopy(self.current))
        self.current = self._past.pop()
        return copy.deepcopy(self.current)

    def redo(self) -> WorkflowDAG:
        if not self._future:
            raise ValueError("nothing to redo")
        self._past.append(copy.deepcopy(self.current))
        self.current = self._future.pop()
        return copy.deepcopy(self.current)

    def serialize(self) -> dict:
        return {"nodes": [{"node_id": n.node_id, "tool": n.tool, "params": n.params}
                          for n in self.current.nodes],
                "edges": [list(e) for e in self.current.edges]}

    @staticmethod
    def deserialize(data: dict) -> WorkflowDAG:
        dag = WorkflowDAG()
        for raw in data.get("nodes", []):
            dag.add_node(Node(raw["node_id"], raw["tool"], raw.get("params", {})))
        for a, b in data.get("edges", []):
            dag.add_edge(a, b)
        return dag
