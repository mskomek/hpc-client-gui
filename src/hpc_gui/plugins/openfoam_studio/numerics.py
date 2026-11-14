"""Numerics: controlDict / fvSchemes / fvSolution (W65 NUM-008, G20-G22)."""

from __future__ import annotations

import math
import re

from hpc_gui.openfoam_core import time_treatment_for

DDT = {"Euler", "backward", "CrankNicolson", "steadyState"}
GRAD = {"Gauss linear", "Gauss pointLinear", "leastSquares", "fourth"}
DIV = {"Gauss linear", "Gauss upwind", "Gauss linearUpwind", "Gauss vanLeer", "Gauss MUSCL"}
LAPLACIAN = {"Gauss linear corrected", "Gauss linear uncorrected", "Gauss linear limited"}
SOLVERS = {"PCG", "PBiCGStab", "smoothSolver", "GAMG"}
PRECOND = {"DIC", "DILU", "diagonal", "GAMG"}


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def render_control_dict(application: str, start_time: float, end_time: float,
                        delta_t: float, write_interval: float,
                        max_co: float | None = None) -> str:
    if not isinstance(application, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", application):
        raise ValueError("application must be a solver identifier")
    values = (("startTime", start_time), ("endTime", end_time),
              ("deltaT", delta_t), ("writeInterval", write_interval))
    for name, value in values:
        if not _finite_number(value):
            raise ValueError(f"invalid time control: {name} must be a finite number")
    if end_time <= start_time:
        raise ValueError("endTime must be greater than startTime")
    for name, value in (("deltaT", delta_t), ("writeInterval", write_interval)):
        if value <= 0:
            raise ValueError(f"invalid time control: {name}={value} must be positive")
    if max_co is not None and (not _finite_number(max_co) or max_co <= 0):
        raise ValueError("maxCo must be a positive finite number")
    max_co_line = f"maxCo {max_co};\n" if max_co is not None else ""
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n    object controlDict;\n}\n"
        f"application {application};\nstartFrom startTime;\nstartTime {start_time};\n"
        f"stopAt endTime;\nendTime {end_time};\ndeltaT {delta_t};\n"
        f"writeControl timeStep;\nwriteInterval {write_interval};\n{max_co_line}")


def validate_fv_schemes(ddt: str, grad: str, div: str, laplacian: str, solver_family: str,
                        *, tool: str | None = None) -> None:
    """Validate schemes; a classified tool wins over the family heuristic."""
    treatment = time_treatment_for(tool) if tool else None
    if treatment is None and solver_family in ("rans-steady", "transient"):
        treatment = "steady" if solver_family == "rans-steady" else "transient"
    if treatment == "steady" and ddt != "steadyState":
        raise ValueError(f"{tool or solver_family} requires ddtSchemes steadyState")
    if treatment == "transient" and ddt == "steadyState":
        raise ValueError(f"{tool or solver_family} is transient and is incompatible with steadyState ddt")
    if ddt not in DDT:
        raise ValueError(f"unsupported ddt scheme '{ddt}'")
    if grad not in GRAD:
        raise ValueError(f"unsupported grad scheme '{grad}'")
    if div not in DIV:
        raise ValueError(f"unsupported div scheme '{div}'")
    if laplacian not in LAPLACIAN:
        raise ValueError(f"unsupported laplacian scheme '{laplacian}'")


def validate_fv_solution(solver: str, pimple: dict | None, relaxation: dict | None) -> None:
    if solver not in SOLVERS:
        raise ValueError(f"unsupported linear solver '{solver}'")
    if pimple is not None:
        if "nCorrectors" in pimple and int(pimple["nCorrectors"]) < 1:
            raise ValueError("PIMPLE nCorrectors must be >= 1")
        if "nOuterCorrectors" in pimple and int(pimple["nOuterCorrectors"]) < 1:
            raise ValueError("PIMPLE nOuterCorrectors must be >= 1")
    if relaxation:
        for key, value in relaxation.items():
            if not 0.0 < float(value) <= 1.0:
                raise ValueError(f"relaxation '{key}'={value} outside (0, 1]")


def render_decompose_dict(n_subdomains: int, method: str = "scotch") -> str:
    if n_subdomains < 1:
        raise ValueError("numberOfSubdomains must be >= 1")
    if method not in ("scotch", "simple", "hierarchical", "manual"):
        raise ValueError(f"unsupported decompose method '{method}'")
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n    object decomposeParDict;\n}\n"
        f"numberOfSubdomains {n_subdomains};\nmethod {method};\n")
