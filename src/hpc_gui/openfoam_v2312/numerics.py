"""Typed numerics schemas (W65 UNIT C, HPC-W65-NUM-008)."""
from __future__ import annotations
from dataclasses import dataclass
from hpc_gui.openfoam_v2312.physics import KNOWN_SOLVERS
START_FIRST = "firstTime"
START_TIME = "startTime"
START_LATEST = "latestTime"
KNOWN_START_FROM = (START_FIRST, START_TIME, START_LATEST)
WRITE_TIMESTEP = "timeStep"
WRITE_RUNTIME = "runTime"
WRITE_ADJUSTABLE = "adjustableRunTime"
WRITE_CLOCK = "clockTime"
WRITE_CPU = "cpuTime"
KNOWN_WRITE_CONTROL = (WRITE_TIMESTEP, WRITE_RUNTIME, WRITE_ADJUSTABLE, WRITE_CLOCK, WRITE_CPU)
LINEAR_PCG = "PCG"
LINEAR_PBICGSTAB = "PBiCGStab"
LINEAR_GAMG = "GAMG"
LINEAR_SMOOTH = "smoothSolver"
KNOWN_LINEAR_SOLVERS = (LINEAR_PCG, LINEAR_PBICGSTAB, LINEAR_GAMG, LINEAR_SMOOTH)
DECOMP_SCOTCH = "scotch"
DECOMP_HIER = "hierarchical"
DECOMP_SIMPLE = "simple"
DECOMP_MULTI = "multiLevel"
KNOWN_DECOMP_METHODS = (DECOMP_SCOTCH, DECOMP_HIER, DECOMP_SIMPLE, DECOMP_MULTI)
@dataclass(frozen=True)
class ControlSpec:
    application: str
    start_from: str
    start_time: float
    end_time: float
    delta_t: float
    write_control: str
    write_interval: float
    def to_dict(self):
        return {"application": self.application, "start_from": self.start_from, "start_time": self.start_time, "end_time": self.end_time, "delta_t": self.delta_t, "write_control": self.write_control, "write_interval": self.write_interval}
    @staticmethod
    def from_dict(raw):
        return ControlSpec(application=str(raw["application"]), start_from=str(raw["start_from"]), start_time=float(raw["start_time"]), end_time=float(raw["end_time"]), delta_t=float(raw["delta_t"]), write_control=str(raw["write_control"]), write_interval=float(raw["write_interval"]))
@dataclass(frozen=True)
class SolverEntry:
    field: str
    linear_solver: str
    tolerance: float
    rel_tol: float
    def to_dict(self):
        return {"field": self.field, "linear_solver": self.linear_solver, "tolerance": self.tolerance, "rel_tol": self.rel_tol}
    @staticmethod
    def from_dict(raw):
        return SolverEntry(field=str(raw["field"]), linear_solver=str(raw["linear_solver"]), tolerance=float(raw["tolerance"]), rel_tol=float(raw["rel_tol"]))
def validate_control(spec):
    errors = []
    if spec.application not in KNOWN_SOLVERS:
        errors.append("unknown application: " + spec.application)
    if spec.start_from not in KNOWN_START_FROM:
        errors.append("unknown startFrom: " + spec.start_from)
    if spec.write_control not in KNOWN_WRITE_CONTROL:
        errors.append("unknown writeControl: " + spec.write_control)
    if spec.end_time <= spec.start_time:
        errors.append("endTime must be after startTime")
    if spec.delta_t <= 0:
        errors.append("deltaT must be positive")
    if spec.write_interval <= 0:
        errors.append("writeInterval must be positive")
    return tuple(errors)
def validate_solver_entry(entry):
    errors = []
    if not entry.field.strip():
        errors.append("empty solution field")
    if entry.linear_solver not in KNOWN_LINEAR_SOLVERS:
        errors.append("unknown linear solver: " + entry.linear_solver)
    if entry.tolerance <= 0 or entry.tolerance >= 1:
        errors.append("tolerance must be inside (0, 1)")
    if entry.rel_tol < 0 or entry.rel_tol >= 1:
        errors.append("relTol must be inside [0, 1)")
    return tuple(errors)
def validate_decompose(subdomains, method):
    errors = []
    if subdomains < 1:
        errors.append("subdomains must be at least 1")
    if method not in KNOWN_DECOMP_METHODS:
        errors.append("unknown decompose method: " + method)
    return tuple(errors)