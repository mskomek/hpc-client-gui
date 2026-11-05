"""Solver registry + run-plan renderer (W65 SOLV-009, G23/G24)."""

from __future__ import annotations

from hashlib import sha256
import shlex

from hpc_gui.plugins.openfoam_studio.physics import SOLVER_FAMILIES, required_fields_for
from hpc_gui.plugins.openfoam_studio.solver_effects import SOLVER_BINARIES


def solver_family(solver: str) -> str:
    if solver not in SOLVER_BINARIES:
        raise ValueError(f"solver '{solver}' is not a classified v2312 binary")
    return SOLVER_BINARIES[solver]


def check_solver_compat(solver: str, model: str, fields_present: list[str],
                        regions: list[str] | None = None) -> None:
    family = solver_family(solver)
    allowed = SOLVER_FAMILIES.get(family, {}).get("models", [])
    if not allowed:
        raise ValueError(
            f"solver '{solver}' is RAW-ADVANCED/UNSUPPORTED in this release "
            f"(family '{family}' has no typed model)")
    if model not in allowed:
        raise ValueError(f"model '{model}' incompatible with {solver} ({family})")
    missing = [f for f in required_fields_for(family, model) if f not in fields_present]
    if missing:
        raise ValueError(f"solver '{solver}' missing required field(s): {', '.join(missing)}")
    if family == "cht" and not regions:
        raise ValueError("CHT solver requires at least one region")


def render_run_plan(solver: str, *, case_dir: str = ".", parallel: bool = False,
                   n_subdomains: int = 1, latest_time: bool = False,
                   post_func: str | None = None, decompose: bool = False,
                   reconstruct: bool = False) -> dict:
    """Return argv lists + Allrun draft. Never executes anything."""
    family = solver_family(solver)
    steps: list[list[str]] = []
    if decompose and parallel:
        if n_subdomains < 2:
            raise ValueError("parallel decompose requires >= 2 subdomains")
        steps.append(["decomposePar", "-case", case_dir, "-force"])
    cmd = [solver, "-case", case_dir]
    if parallel:
        cmd = ["mpirun", "-np", str(n_subdomains)] + cmd
    if latest_time:
        cmd += ["-latestTime"]
    steps.append(cmd)
    if reconstruct and parallel:
        steps.append(["reconstructPar", "-case", case_dir])
    if post_func:
        steps.append(["postProcess", "-case", case_dir, "-func", post_func])
    _guard_no_injection(steps)
    lines = ["#!/bin/sh", f"cd {shlex.quote(case_dir)} || exit 1"]
    for argv in steps:
        lines.append(" ".join(shlex.quote(a) for a in argv))
    if family in ("transient",):
        lines.append("# transient: resume with -latestTime only after checkpoint review")
    allrun = "\n".join(lines) + "\n"
    return {"steps": steps, "allrun": allrun,
            "allrun_sha256": sha256(allrun.encode("utf-8", errors="strict")).hexdigest(),
            "solver": solver, "family": family}


def _guard_no_injection(steps: list[list[str]]) -> None:
    dangerous = (";", "&", "|", "$", "`", ">", "<", "\n")
    for argv in steps:
        for token in argv:
            if any(d in token for d in dangerous):
                raise ValueError(f"refusing to render shell metacharacter in argv token: {token!r}")
