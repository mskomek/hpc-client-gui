"""Typed workflow DAG descriptors (W65 UNIT D, HPC-W65-FLOW-011).

Ordered dependency graphs over run stages with legacy command import.
Graphs describe work; they never execute solvers, touch case files, or
rewrite Allrun scripts. Case files plus explicit orchestration metadata
stay the source of truth.
"""
from __future__ import annotations
from dataclasses import dataclass
from hpc_gui.openfoam_v2312.solver import (
    KNOWN_STAGES, STAGE_CHECK, STAGE_DECOMPOSE, STAGE_MESH, STAGE_POST,
    STAGE_PREFLIGHT, STAGE_RECONSTRUCT, STAGE_SOLVE,
)
JOURNEY_T1 = "T1"
JOURNEY_T2 = "T2"
JOURNEY_T3 = "T3"
JOURNEY_T4 = "T4"
JOURNEY_T5 = "T5"
JOURNEY_T6 = "T6"
JOURNEY_T7 = "T7"
JOURNEY_T8 = "T8"
JOURNEY_SPECS = {
    JOURNEY_T1: ("existing mesh to incompressible results", "P0",
                 (STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T2: ("surface to snappy mesh to fluid results", "P0",
                 (STAGE_MESH, STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T3: ("STEP converter gate to mesh to results", "P0",
                 (STAGE_PREFLIGHT, STAGE_MESH, STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T4: ("structured mesh to simpleFoam report", "P0",
                 (STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T5: ("transient parallel run with sampling", "P0",
                 (STAGE_CHECK, STAGE_DECOMPOSE, STAGE_SOLVE, STAGE_RECONSTRUCT, STAGE_POST)),
    JOURNEY_T6: ("conjugate heat transfer regions to report", "P0",
                 (STAGE_MESH, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T7: ("converted mesh to VTK and CSV results", "P1",
                 (STAGE_MESH, STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
    JOURNEY_T8: ("multi-region advanced workflow", "P1",
                 (STAGE_MESH, STAGE_CHECK, STAGE_SOLVE, STAGE_POST)),
}
LEGACY_COMMAND_TO_STAGE = {
    "blockMesh": STAGE_MESH, "surfaceFeatureExtract": STAGE_MESH,
    "snappyHexMesh": STAGE_MESH, "splitMeshRegions": STAGE_MESH,
    "checkMesh": STAGE_CHECK, "decomposePar": STAGE_DECOMPOSE,
    "simpleFoam": STAGE_SOLVE, "icoFoam": STAGE_SOLVE,
    "chtMultiRegionSimpleFoam": STAGE_SOLVE,
    "reconstructPar": STAGE_RECONSTRUCT, "postProcess": STAGE_POST,
}
@dataclass(frozen=True)
class FlowNode:
    """One DAG node with its artifact ports and hazard flags."""
    node_id: str
    stage: str
    produces: tuple = ()
    consumes: tuple = ()
    destructive: bool = False
    needs_review: bool = False
    def to_dict(self):
        return {
            "node_id": self.node_id, "stage": self.stage,
            "produces": list(self.produces),
            "consumes": list(self.consumes),
            "destructive": self.destructive,
            "needs_review": self.needs_review,
        }
    @staticmethod
    def from_dict(raw):
        return FlowNode(
            node_id=str(raw["node_id"]), stage=str(raw["stage"]),
            produces=tuple(str(p) for p in raw.get("produces", ())),
            consumes=tuple(str(c) for c in raw.get("consumes", ())),
            destructive=bool(raw.get("destructive", False)),
            needs_review=bool(raw.get("needs_review", False)),
        )
def validate_flow(nodes):
    """Return deterministic error strings; empty means runnable in order."""
    errors = []
    if not nodes:
        errors.append("empty workflow graph")
        return tuple(errors)
    seen = set()
    for node in nodes:
        if node.node_id in seen:
            errors.append("duplicate node id: " + node.node_id)
        seen.add(node.node_id)
        if node.stage not in KNOWN_STAGES:
            errors.append("unknown pipeline stage: " + node.stage)
    produced = set()
    solve_seen = False
    mesh_seen = False
    destructive_pending = False
    for node in nodes:
        if node.stage == STAGE_MESH:
            mesh_seen = True
        if node.destructive and node.stage in (STAGE_MESH, STAGE_CHECK):
            if destructive_pending and not node.needs_review:
                errors.append("duplicate destructive mesh step needs review: " + node.node_id)
            destructive_pending = True
        if node.stage == STAGE_SOLVE:
            if not mesh_seen:
                errors.append("solve node precedes any mesh node: " + node.node_id)
            solve_seen = True
        if node.stage == STAGE_POST and not solve_seen:
            errors.append("post node precedes any solve node: " + node.node_id)
        for artifact in node.consumes:
            if artifact not in produced:
                errors.append("node " + node.node_id + " consumes " + artifact + " with no earlier producer")
        produced.update(node.produces)
    return tuple(errors)
def validate_journey(journey_id, stages):
    """Check a stage list against its approved journey template."""
    if journey_id not in JOURNEY_SPECS:
        return ("unknown journey: " + journey_id,)
    expected = JOURNEY_SPECS[journey_id][2]
    if tuple(stages) != expected:
        return ("journey " + journey_id + " expects " + "/".join(expected)
                + " but got " + "/".join(tuple(stages)),)
    return ()
def from_legacy(commands):
    """Map legacy workflow commands to stages; unknown names are reported."""
    stages = []
    unknown = []
    for command in commands:
        if command in LEGACY_COMMAND_TO_STAGE:
            stages.append(LEGACY_COMMAND_TO_STAGE[command])
        else:
            unknown.append(command)
    return (tuple(stages), tuple(unknown))
def list_journeys():
    return tuple(JOURNEY_SPECS)