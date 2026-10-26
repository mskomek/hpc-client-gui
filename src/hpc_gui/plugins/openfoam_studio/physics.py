"""Materials + turbulence/physics registries (W65 PHYS-006, G14/G15/G17)."""

from __future__ import annotations

from hpc_gui.openfoam_core.physics import (
    SOLVER_FAMILIES,  # noqa: F401 — compatibility re-export used by solver.py
    TURBULENCE_MODELS,
    required_fields_for,  # noqa: F401 — compatibility re-export used by solver.py
)

AIR_15C = {"rho": 1.225, "mu": 1.789e-05, "units": "SI", "provenance": "user-library:air-15C"}
WATER_20C = {"rho": 998.0, "mu": 1.002e-03, "units": "SI", "provenance": "user-library:water-20C"}

MATERIAL_LIBRARY = {"air-15C": AIR_15C, "water-20C": WATER_20C}


def material_entry(name: str, rho: float, mu: float) -> dict:
    if rho <= 0 or mu <= 0:
        raise ValueError("density and viscosity must be positive with SI units")
    return {"name": name, "rho": rho, "mu": mu, "nu": mu / rho,
            "units": "SI", "provenance": "user-supplied"}


def transport_properties_dict(rho: float, mu: float, model: str = "Newtonian") -> str:
    if rho <= 0 or mu <= 0:
        raise ValueError("unphysical material: rho/mu must be positive")
    nu = mu / rho
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n    object transportProperties;\n}\n"
        f"transportModel {model};\nnu [0 2 -1 0 0 0 0] {nu:.6e};\n"
    )


def turbulence_properties_dict(model: str) -> str:
    if model == "laminar":
        return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
                "    object turbulenceProperties;\n}\nsimulationType laminar;\n")
    if model not in TURBULENCE_MODELS:
        raise ValueError(f"unsupported turbulence model '{model}' (RAW-ADVANCED only)")
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
            "    object turbulenceProperties;\n}\n"
            f"simulationType RAS;\nRAS {{ RASModel {model}; turbulence on; printCoeffs on; }}\n")


