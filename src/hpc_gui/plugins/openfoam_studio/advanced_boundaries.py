"""Coupled / mapped / cyclic boundary profiles (W65 BC-007, G19).

Typed subset: cyclic pairs and CHT fluid-solid coupled interfaces. Both
sides of a coupled interface must exist; a one-sided profile is UNKNOWN,
never auto-completed.
"""

from __future__ import annotations


def validate_cyclic_pair(patch_a: str, patch_b: str, neighbour_field: str = "") -> None:
    if not patch_a or not patch_b:
        raise ValueError("cyclic pair requires two named patches")
    if patch_a == patch_b:
        raise ValueError("cyclic pair patches must differ (no self-pair)")
    for name in (patch_a, patch_b):
        if any(c in name for c in " \t\n;|&$`\"'"):
            raise ValueError(f"unsafe patch name '{name}'")


def cyclic_entries(patch_a: str, patch_b: str) -> dict[str, str]:
    validate_cyclic_pair(patch_a, patch_b)
    block = ("type cyclic;\n        neighbourPatch {other};")
    return {patch_a: block.format(other=patch_b),
            patch_b: block.format(other=patch_a)}


def validate_coupled_interface(fluid_patch: str, solid_patch: str) -> None:
    for name in (fluid_patch, solid_patch):
        if not name:
            raise ValueError("coupled interface requires both fluid and solid patch names")
        if any(c in name for c in " \t\n;|&$`\"'"):
            raise ValueError(f"unsafe interface patch name '{name}'")
    if fluid_patch == solid_patch:
        raise ValueError("fluid and solid interface patches must differ")


def coupled_temperature_entries(fluid_patch: str, solid_patch: str,
                                *, kappa: float = 0.026) -> dict[str, str]:
    """Both sides of a CHT temperature coupling, or raise."""
    validate_coupled_interface(fluid_patch, solid_patch)
    if kappa <= 0:
        raise ValueError("kappa must be positive SI")
    fluid = ("type compressible::turbulentTemperatureCoupledBaffleMixed;\n"
             f"        Tnbr T; // solid side: {solid_patch}")
    solid = ("type compressible::turbulentTemperatureCoupledBaffleMixed;\n"
             f"        Tnbr T; // fluid side: {fluid_patch}")
    return {fluid_patch: fluid, solid_patch: solid}


def mapped_wall_entry(patch: str, neighbour: str, offset: tuple[float, float, float]) -> str:
    if not patch or not neighbour:
        raise ValueError("mappedWall requires patch and neighbourPatch")
    if len(offset) != 3:
        raise ValueError("mappedWall offset must be a 3-vector")
    return (f"type mappedWall;\n        neighbourPatch {neighbour};\n"
            f"        offset ({offset[0]:g} {offset[1]:g} {offset[2]:g});")
