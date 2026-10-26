"""Verified advanced-family physics subsets (W65 PHYS-006, G17).

Only families with a schema-backed fixture may claim ACTIVE-TYPED; every
other advanced solver stays RAW-ADVANCED, and reacting stays UNSUPPORTED
until a verified transport/chemistry fixture exists.
"""

from __future__ import annotations

TYPED_ADVANCED = frozenset({"multiphase", "compressible", "buoyant"})
UNSUPPORTED_ADVANCED = frozenset({"reacting", "lagrangian", "dynamicMesh"})


def advanced_availability(family: str) -> str:
    if family in TYPED_ADVANCED:
        return "ACTIVE-TYPED"
    if family in UNSUPPORTED_ADVANCED:
        return "UNSUPPORTED"
    return "RAW-ADVANCED"


def require_typed_advanced(family: str) -> None:
    status = advanced_availability(family)
    if status != "ACTIVE-TYPED":
        raise ValueError(f"advanced family '{family}' is {status}; typed generation refused")


def alpha_water_field(internal: float, patches: dict[str, tuple[str, str]]) -> str:
    """Typed 0/alpha.water for interFoam (multiphase verified subset)."""
    from hpc_gui.plugins.openfoam_studio.boundary import render_field_file
    require_typed_advanced("multiphase")
    if not 0.0 <= internal <= 1.0:
        raise ValueError("alpha.water internalField must be within [0, 1]")
    return render_field_file("alpha.water", f"{internal:g}", patches)


def thermophysical_properties_dict(family: str, *, rho: float = 1.225,
                                   mu: float = 1.789e-05, cp: float = 1005.0,
                                   pr: float = 0.7) -> str:
    """Typed constant/thermophysicalProperties for verified families."""
    require_typed_advanced(family)
    for label, value in (("rho", rho), ("mu", mu), ("Cp", cp), ("Pr", pr)):
        if value <= 0:
            raise ValueError(f"{family}: {label} must be positive SI")
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
        "    object thermophysicalProperties;\n}\n"
        f"thermoType {{ type heRhoThermo; mixture pureMixture; }}\n"
        f"mixture {{ specie {{ molWeight 28.9; }} transport {{ mu {mu:.6e}; Pr {pr:g}; }} "
        f"thermodynamics {{ Cp {cp:g}; Hf 0; }} equationOfState {{ rhoConst {rho:g}; }} }}\n"
    )


def gravity_dict(g: tuple[float, float, float] = (0.0, -9.81, 0.0)) -> str:
    if len(g) != 3:
        raise ValueError("gravity vector must have 3 components")
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class uniformDimensionedVectorField;\n"
            "    object g;\n}\n"
            f"dimensions [0 1 -2 0 0 0 0];\nvalue ({g[0]:g} {g[1]:g} {g[2]:g});\n")
