"""Shared solver-family and turbulence field contracts."""

from __future__ import annotations

TURBULENCE_MODELS = {
    "laminar": {"required_fields": [], "wall_functions": []},
    "kEpsilon": {"required_fields": ["k", "epsilon"], "wall_functions": ["epsilonWallFunction"]},
    "kOmegaSST": {"required_fields": ["k", "omega"], "wall_functions": ["omegaWallFunction"]},
}

SOLVER_FAMILIES = {
    "laminar": {"solvers": ["icoFoam"], "models": ["laminar"]},
    "rans-steady": {"solvers": ["simpleFoam"], "models": ["kEpsilon", "kOmegaSST", "laminar"]},
    "transient": {"solvers": ["pimpleFoam", "pisoFoam"], "models": ["kEpsilon", "kOmegaSST", "laminar"]},
    "cht": {"solvers": ["chtMultiRegionSimpleFoam", "chtMultiRegionFoam"],
            "models": ["kEpsilon", "kOmegaSST", "laminar"]},
    "buoyant": {"solvers": ["buoyantSimpleFoam"], "models": ["kEpsilon", "kOmegaSST"]},
    "compressible": {"solvers": ["rhoSimpleFoam", "rhoPimpleFoam"], "models": ["kEpsilon", "kOmegaSST"]},
    "multiphase": {"solvers": ["interFoam"], "models": ["kEpsilon", "laminar"]},
    "reacting": {"solvers": ["reactingFoam"], "models": []},  # RAW-ADVANCED only
}

#: Canonical steady/transient treatment per classified v2312 solver. The
#: case generator and the linter both read this map so generated cases and
#: lint findings cannot disagree.
SOLVER_TIME_TREATMENT = {
    "icoFoam": "transient",
    "pisoFoam": "transient",
    "pimpleFoam": "transient",
    "rhoPimpleFoam": "transient",
    "buoyantPimpleFoam": "transient",
    "interFoam": "transient",
    "reactingFoam": "transient",
    "sonicFoam": "transient",
    "rhoCentralFoam": "transient",
    "multiphaseEulerFoam": "transient",
    "chtMultiRegionFoam": "transient",
    "simpleFoam": "steady",
    "rhoSimpleFoam": "steady",
    "buoyantSimpleFoam": "steady",
    "buoyantBoussinesqSimpleFoam": "steady",
    "potentialFoam": "steady",
    "chtMultiRegionSimpleFoam": "steady",
}


def time_treatment_for(solver: str) -> str | None:
    """Return 'steady' or 'transient' for a classified solver, else None."""
    return SOLVER_TIME_TREATMENT.get(solver)


def required_fields_for(family: str, model: str) -> list[str]:
    base = {"laminar": ["U", "p"], "rans-steady": ["U", "p"],
            "transient": ["U", "p"], "cht": ["U", "p", "T"],
            "buoyant": ["U", "p", "T"], "compressible": ["U", "p", "T"],
            "multiphase": ["U", "p", "alpha.water"]}.get(family, ["U", "p"])
    extra = TURBULENCE_MODELS.get(model, {}).get("required_fields", [])
    return base + [field for field in extra if field not in base]
