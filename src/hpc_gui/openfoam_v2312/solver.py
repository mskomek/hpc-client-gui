"""Typed run pipeline schemas (W65 UNIT C, HPC-W65-SOLV-009)."""
from __future__ import annotations
from dataclasses import dataclass
from hpc_gui.openfoam_v2312.physics import KNOWN_SOLVERS
STAGE_PREFLIGHT = "preflight"
STAGE_MESH = "mesh"
STAGE_CHECK = "check"
STAGE_DECOMPOSE = "decompose"
STAGE_SOLVE = "solve"
STAGE_RECONSTRUCT = "reconstruct"
STAGE_POST = "post"
KNOWN_STAGES = (STAGE_PREFLIGHT, STAGE_MESH, STAGE_CHECK, STAGE_DECOMPOSE, STAGE_SOLVE, STAGE_RECONSTRUCT, STAGE_POST)
@dataclass(frozen=True)
class RunSpec:
    stages: tuple = ()
    solver: str = "simpleFoam"
    parallel: bool = False
    subdomains: int = 1
    def to_dict(self):
        return {"stages": list(self.stages), "solver": self.solver, "parallel": self.parallel, "subdomains": self.subdomains}
    @staticmethod
    def from_dict(raw):
        return RunSpec(stages=tuple(str(s) for s in raw.get("stages", ())), solver=str(raw.get("solver", "simpleFoam")), parallel=bool(raw.get("parallel", False)), subdomains=int(raw.get("subdomains", 1)))
def validate_run(spec):
    errors = []
    if not spec.stages:
        errors.append("empty run pipeline")
        return tuple(errors)
    for stage in spec.stages:
        if stage not in KNOWN_STAGES:
            errors.append("unknown pipeline stage: " + stage)
    if spec.solver not in KNOWN_SOLVERS:
        errors.append("unknown solver: " + spec.solver)
    if STAGE_SOLVE in spec.stages:
        solve_at = spec.stages.index(STAGE_SOLVE)
        for early in (STAGE_MESH, STAGE_CHECK):
            if early in spec.stages and spec.stages.index(early) > solve_at:
                errors.append("solver stage precedes mesh validation")
                break
    if spec.stages.count(STAGE_SOLVE) > 1:
        errors.append("duplicate solve stage")
    if spec.stages.count(STAGE_DECOMPOSE) > 1:
        errors.append("duplicate decompose stage")
    if STAGE_DECOMPOSE in spec.stages and not spec.parallel:
        errors.append("decompose stage needs parallel execution")
    if spec.parallel and spec.subdomains < 2:
        errors.append("parallel runs need at least 2 subdomains")
    if STAGE_RECONSTRUCT in spec.stages and STAGE_DECOMPOSE not in spec.stages[:spec.stages.index(STAGE_RECONSTRUCT)]:
        errors.append("reconstruct stage needs a prior decompose stage")
    if STAGE_POST in spec.stages and STAGE_SOLVE not in spec.stages[:spec.stages.index(STAGE_POST)]:
        errors.append("post stage needs a prior solve stage")
    return tuple(errors)
def list_stages():
    return KNOWN_STAGES