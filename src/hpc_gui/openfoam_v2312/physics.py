"""Typed physics context schemas (W65 UNIT C, HPC-W65-PHYS-006)."""
from __future__ import annotations
from dataclasses import dataclass
SOLVER_ICOFOAM = "icoFoam"
SOLVER_SIMPLEFOAM = "simpleFoam"
SOLVER_PIMPLEFOAM = "pimpleFoam"
SOLVER_CHT = "chtMultiRegionSimpleFoam"
KNOWN_SOLVERS = (SOLVER_ICOFOAM, SOLVER_SIMPLEFOAM, SOLVER_PIMPLEFOAM, SOLVER_CHT)
STEADY_SOLVERS = frozenset({SOLVER_SIMPLEFOAM, SOLVER_CHT})
INCOMPRESSIBLE_SOLVERS = frozenset({SOLVER_ICOFOAM, SOLVER_SIMPLEFOAM})
FLOW_LAMINAR = "laminar"
FLOW_RAS_K_EPSILON = "RAS-kEpsilon"
FLOW_RAS_K_OMEGA_SST = "RAS-kOmegaSST"
FLOW_LES_SMAGORINSKY = "LES-Smagorinsky"
KNOWN_FLOW_MODELS = (FLOW_LAMINAR, FLOW_RAS_K_EPSILON, FLOW_RAS_K_OMEGA_SST, FLOW_LES_SMAGORINSKY)
@dataclass(frozen=True)
class PhysicsSpec:
    solver: str
    flow_model: str
    transient: bool = False
    compressible: bool = False
    heat_transfer: bool = False
    cht: bool = False
    regions: tuple = ()
    def to_dict(self):
        return {"solver": self.solver, "flow_model": self.flow_model, "transient": self.transient, "compressible": self.compressible, "heat_transfer": self.heat_transfer, "cht": self.cht, "regions": list(self.regions)}
    @staticmethod
    def from_dict(raw):
        return PhysicsSpec(solver=str(raw["solver"]), flow_model=str(raw["flow_model"]), transient=bool(raw.get("transient", False)), compressible=bool(raw.get("compressible", False)), heat_transfer=bool(raw.get("heat_transfer", False)), cht=bool(raw.get("cht", False)), regions=tuple(str(n) for n in raw.get("regions", ())))
def validate_physics(spec):
    errors = []
    if spec.solver not in KNOWN_SOLVERS:
        errors.append("unknown solver: " + spec.solver)
    if spec.flow_model not in KNOWN_FLOW_MODELS:
        errors.append("unknown flow model: " + spec.flow_model)
    if spec.transient and spec.solver in STEADY_SOLVERS:
        errors.append("transient run needs a transient solver, not " + spec.solver)
    if spec.compressible and spec.solver in INCOMPRESSIBLE_SOLVERS:
        errors.append("compressible physics needs a compressible solver, not " + spec.solver)
    if spec.cht:
        if spec.solver != SOLVER_CHT:
            errors.append("CHT regions need chtMultiRegionSimpleFoam, not " + spec.solver)
        if len(spec.regions) < 2:
            errors.append("CHT needs at least two regions")
    if spec.heat_transfer and not spec.cht and not spec.compressible:
        errors.append("heat transfer needs the CHT solver or a compressible model in this unit")
    seen = set()
    for name in spec.regions:
        if not name.strip():
            errors.append("empty region name")
        elif name in seen:
            errors.append("duplicate region: " + name)
        else:
            seen.add(name)
    return tuple(errors)
def list_solvers():
    return KNOWN_SOLVERS
def list_flow_models():
    return KNOWN_FLOW_MODELS