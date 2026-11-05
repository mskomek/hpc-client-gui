"""Typed boundary/initial condition schemas (W65 UNIT C, HPC-W65-BC-007)."""
from __future__ import annotations
from dataclasses import dataclass
PATCH_PATCH = "patch"
PATCH_WALL = "wall"
PATCH_SYMMETRY = "symmetry"
PATCH_SYMMETRY_PLANE = "symmetryPlane"
PATCH_CYCLIC = "cyclic"
PATCH_WEDGE = "wedge"
PATCH_EMPTY = "empty"
PATCH_MAPPED = "mapped"
KNOWN_PATCH_KINDS = (PATCH_PATCH, PATCH_WALL, PATCH_SYMMETRY, PATCH_SYMMETRY_PLANE, PATCH_CYCLIC, PATCH_WEDGE, PATCH_EMPTY, PATCH_MAPPED)
FIELD_U = "U"
FIELD_P = "p"
FIELD_T = "T"
FIELD_K = "k"
FIELD_EPSILON = "epsilon"
FIELD_OMEGA = "omega"
FIELD_NUT = "nut"
KNOWN_FIELDS = (FIELD_U, FIELD_P, FIELD_T, FIELD_K, FIELD_EPSILON, FIELD_OMEGA, FIELD_NUT)
DIMENSIONS = {FIELD_U: "[0 1 -1 0 0 0 0]", FIELD_P: "[0 2 -2 0 0 0 0]", FIELD_T: "[0 0 0 1 0 0 0]", FIELD_K: "[0 2 -2 0 0 0 0]", FIELD_EPSILON: "[0 2 -3 0 0 0 0]", FIELD_OMEGA: "[0 0 -1 0 0 0 0]", FIELD_NUT: "[0 2 -1 0 0 0 0]"}
BC_FIXED = "fixedValue"
BC_NO_SLIP = "noSlip"
BC_ZERO_GRADIENT = "zeroGradient"
BC_INLET_OUTLET = "inletOutlet"
BC_SCALAR_TYPES = frozenset({BC_FIXED, BC_ZERO_GRADIENT, PATCH_SYMMETRY, PATCH_CYCLIC, PATCH_WEDGE, PATCH_EMPTY, PATCH_MAPPED})
BC_FOR_FIELD = {FIELD_U: BC_SCALAR_TYPES | {BC_NO_SLIP, BC_INLET_OUTLET}, FIELD_P: BC_SCALAR_TYPES, FIELD_T: BC_SCALAR_TYPES, FIELD_K: BC_SCALAR_TYPES, FIELD_EPSILON: BC_SCALAR_TYPES, FIELD_OMEGA: BC_SCALAR_TYPES, FIELD_NUT: BC_SCALAR_TYPES}
@dataclass(frozen=True)
class BCSpec:
    patch: str
    patch_kind: str
    field: str
    bc_type: str
    dimensions: str
    def to_dict(self):
        return {"patch": self.patch, "patch_kind": self.patch_kind, "field": self.field, "bc_type": self.bc_type, "dimensions": self.dimensions}
    @staticmethod
    def from_dict(raw):
        return BCSpec(patch=str(raw["patch"]), patch_kind=str(raw["patch_kind"]), field=str(raw["field"]), bc_type=str(raw["bc_type"]), dimensions=str(raw["dimensions"]))
def validate_bc(spec):
    errors = []
    if not spec.patch.strip():
        errors.append("empty patch name")
    if spec.patch_kind not in KNOWN_PATCH_KINDS:
        errors.append("unknown patch kind: " + spec.patch_kind)
    if spec.field not in KNOWN_FIELDS:
        errors.append("unknown field: " + spec.field)
        return tuple(errors)
    allowed = BC_FOR_FIELD[spec.field]
    if spec.bc_type not in allowed:
        errors.append("BC type " + spec.bc_type + " is not valid for field " + spec.field)
    expected = DIMENSIONS[spec.field]
    if spec.dimensions != expected:
        errors.append("dimensions " + spec.dimensions + " do not match " + expected + " for field " + spec.field)
    return tuple(errors)
def list_patch_kinds():
    return KNOWN_PATCH_KINDS
def list_fields():
    return KNOWN_FIELDS