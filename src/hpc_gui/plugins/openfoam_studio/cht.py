"""CHT region coupling helpers (W65 PHYS-006, G16)."""

from __future__ import annotations


def validate_cht_regions(fluid_regions: list[str], solid_regions: list[str],
                         available: list[str]) -> None:
    if not fluid_regions:
        raise ValueError("CHT missing fluid region (regionProperties invalid)")
    missing = [r for r in fluid_regions + solid_regions if r not in available]
    if missing:
        raise ValueError(f"CHT region(s) absent from mesh: {', '.join(missing)}")


def cht_interface_hint(fluid: str, solid: str) -> dict:
    return {"fluid": fluid, "solid": solid,
            "interface_type": "mappedWall",
            "note": "both sides must exist; temperature coupling validated by Linter OF-BC rule"}


def region_thermophysical_dict(region: str, *, fluid: bool, rho: float = 1.225,
                               cp: float = 1005.0, kappa: float = 0.026,
                               mu: float = 1.789e-05) -> str:
    """Full per-region thermophysicalProperties dict (G16 typed subset)."""
    if not region or any(c in region for c in " \t\n;|&$`\"'"):
        raise ValueError(f"unsafe region name '{region}'")
    for label, value in (("rho", rho), ("Cp", cp), ("kappa", kappa), ("mu", mu)):
        if value <= 0:
            raise ValueError(f"region '{region}': {label} must be positive SI")
    kind = ("heRhoThermo <pureMixture<constTransport<specieThermo"
            "<hConstThermo<perfectGas<specie>>>>>>>" if fluid
            else "heSolidThermo <pureMixture<constIsoSolidTransport<specieThermo<hConstThermo<separated>>>")
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
        f"    object thermophysicalProperties;\n}}\n"
        f"thermoType {{ type {kind}; mixture pureMixture; }}\n"
        f"mixture {{ specie {{ molWeight 28.9; }} thermodynamics {{ Cp {cp:g}; Hf 0; }} "
        f"transport {{ mu {mu:.6e}; Pr 0.7; }} }}\n"
        f"// region={region} rho={rho:g} kappa={kappa:g} provenance=user-supplied\n"
    )


def cht_region_temperature_field(region: str, internal: float,
                                 interfaces: list[tuple[str, str]]) -> str:
    """Render region-scoped 0/<region>/T with coupled mappedWall interfaces."""
    from hpc_gui.plugins.openfoam_studio.advanced_boundaries import (
        validate_coupled_interface,
    )
    for fluid_patch, solid_patch in interfaces:
        validate_coupled_interface(fluid_patch, solid_patch)
    lines = ["FoamFile", "{", "    version 2.0;", "    format ascii;",
             "    class volScalarField;", f"    object T; // region {region}",
             "}", "dimensions [0 0 0 1 0 0 0];",
             f"internalField uniform {internal};", "boundaryField", "{"]
    for fluid_patch, solid_patch in interfaces:
        lines += ["    " + fluid_patch, "    {",
                  "        type compressible::turbulentTemperatureCoupledBaffleMixed;",
                  f"        Tnbr T; // solid side: {solid_patch}", "    }"]
    lines.append("}")
    return "\n".join(lines) + "\n"
