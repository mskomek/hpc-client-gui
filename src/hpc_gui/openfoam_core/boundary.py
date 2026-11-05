"""Shared, toolkit-free OpenFOAM boundary and field contracts."""

from __future__ import annotations

PATCH_TYPES = ("inlet", "outlet", "wall", "symmetry", "cyclic", "wedge",
               "mappedWall", "empty", "symmetryPlane")

BC_TYPES = {"fixedValue", "zeroGradient", "inletOutlet", "noSlip", "slip",
            "empty", "symmetry", "cyclic", "mappedWall", "wallFunction",
            "kqRWallFunction", "epsilonWallFunction", "omegaWallFunction", "nutkWallFunction"}

FIELD_DIMS = {"U": "[0 1 -1 0 0 0 0]", "p": "[0 2 -2 0 0 0 0]",
              "T": "[0 0 0 1 0 0 0]", "k": "[0 2 -2 0 0 0 0]",
              "epsilon": "[0 2 -3 0 0 0 0]", "omega": "[0 0 -1 0 0 0 0]",
              "p_rgh": "[1 -1 -2 0 0 0 0]", "alpha.water": "[0 0 0 0 0 0 0]"}


def allowed_bc(patch_kind: str) -> tuple[str, ...]:
    if patch_kind == "wall":
        return ("noSlip", "fixedValue", "zeroGradient", "wallFunction",
                "kqRWallFunction", "epsilonWallFunction", "omegaWallFunction", "nutkWallFunction")
    if patch_kind == "inlet":
        return ("fixedValue", "inletOutlet")
    if patch_kind == "outlet":
        return ("zeroGradient", "inletOutlet", "fixedValue")
    if patch_kind in ("symmetry", "symmetryPlane", "empty", "wedge"):
        return ("symmetry", "empty")
    if patch_kind in ("cyclic", "mappedWall"):
        return ("cyclic", "mappedWall")
    raise ValueError(f"unknown patch kind '{patch_kind}'")
