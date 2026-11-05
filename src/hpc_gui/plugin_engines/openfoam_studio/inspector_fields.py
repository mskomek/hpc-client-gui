"""Conservative value typing for source-preserving dictionary edits."""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from hpc_gui.openfoam_core import Entry

_INTEGER = re.compile(r"[+-]?\d+\Z")
_SCALAR = re.compile(r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?\Z")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_SPIN_MIN = -(2**31)
_SPIN_MAX = 2**31 - 1


@dataclass(frozen=True, slots=True)
class FieldSpec:
    kind: str
    component_count: int = 0
    choices: tuple[str, ...] = ()


def _is_scalar(value: str) -> bool:
    return bool(_SCALAR.fullmatch(value)) and math.isfinite(float(value))


def _infer_lexical_field(entry: Entry) -> FieldSpec:
    """Infer lexical types that can be safely edited without replacing syntax."""
    if entry.is_dictionary or entry.dynamic or not entry.value_tokens:
        return FieldSpec("raw")

    tokens = list(entry.value_tokens)
    if len(tokens) == 1:
        token = tokens[0]
        if token.kind != "atom":
            return FieldSpec("raw")
        value = token.value
        if value in {"true", "false"}:
            return FieldSpec("boolean")
        if _INTEGER.fullmatch(value):
            number = int(value)
            return FieldSpec("integer") if _SPIN_MIN <= number <= _SPIN_MAX else FieldSpec("raw")
        if _is_scalar(value):
            return FieldSpec("scalar")
        if _WORD.fullmatch(value):
            return FieldSpec("word")
        return FieldSpec("raw")

    if tokens[0].kind == "atom" and tokens[0].value == "uniform":
        tokens = tokens[1:]
    if len(tokens) < 5 or tokens[0].value != "(" or tokens[-1].value != ")":
        return FieldSpec("raw")
    components = tokens[1:-1]
    if any(token.kind != "atom" or not _is_scalar(token.value) for token in components):
        return FieldSpec("raw")
    kinds = {3: "vector", 6: "symmTensor", 9: "tensor"}
    kind = kinds.get(len(components), "raw")
    return FieldSpec(kind, len(components) if kind != "raw" else 0)


_CONTROL_DICT_CHOICES = {
    "startFrom": ("firstTime", "startTime", "latestTime"),
    "stopAt": ("endTime", "writeNow", "noWriteNow", "nextWrite"),
    "writeControl": ("timeStep", "runTime", "adjustableRunTime", "cpuTime", "clockTime"),
    "writeFormat": ("ascii", "binary"),
    "writeCompression": ("off", "on", "false", "true"),
    "timeFormat": ("fixed", "scientific", "general"),
    "adjustTimeStep": ("off", "on", "false", "true"),
    "runTimeModifiable": ("off", "on", "false", "true"),
}
_FUNCTION_CONTROL_CHOICES = (
    "none", "timeStep", "writeTime", "runTime", "adjustableRunTime",
    "clockTime", "cpuTime", "onEnd",
)
_SCHEME_CHOICES = {
    ("ddtSchemes", "default"): ("Euler", "backward", "CrankNicolson 0.9"),
    ("gradSchemes", "default"): ("Gauss linear", "leastSquares"),
    ("divSchemes", "default"): ("none", "Gauss linear", "Gauss upwind"),
    ("divSchemes", "div(phi,U)"): (
        "Gauss linearUpwind grad(U)", "Gauss upwind", "Gauss limitedLinearV 1",
        "Gauss linear",
    ),
    ("divSchemes", "div(phi,T)"): (
        "Gauss upwind", "Gauss linearUpwind grad(T)", "Gauss limitedLinear 1",
        "Gauss linear",
    ),
    ("laplacianSchemes", "default"): (
        "Gauss linear corrected", "Gauss linear uncorrected", "Gauss linear limited 0.5",
    ),
    ("interpolationSchemes", "default"): ("linear", "cubic", "midPoint"),
    ("snGradSchemes", "default"): (
        "corrected", "uncorrected", "limited 0.3333",
    ),
}
_LINEAR_SOLVER_CHOICES = ("PCG", "PBiCG", "PBiCGStab", "smoothSolver", "GAMG", "diagonal")
_PRECONDITIONER_CHOICES = (
    "DIC", "DILU", "FDIC", "diagonal", "none", "GAMG", "GaussSeidel",
    "symGaussSeidel",
)
_SMOOTHER_CHOICES = (
    "GaussSeidel", "symGaussSeidel", "DICGaussSeidel", "DILUGaussSeidel",
    "FDICGaussSeidel", "none",
)
_BOUNDARY_TYPE_CHOICES = (
    "fixedValue", "zeroGradient", "calculated", "uniformFixedValue", "inletOutlet",
    "outletInlet", "pressureInletOutletVelocity", "totalPressure", "fixedFluxPressure",
    "noSlip", "slip", "symmetry", "symmetryPlane", "empty", "cyclic", "wedge",
    "mappedWall", "freestream", "fixedMean", "movingWallVelocity",
)


def infer_field(entry: Entry, *, dictionary_path: str = "") -> FieldSpec:
    """Infer safe lexical editors plus curated v2312 dictionary choices."""
    spec = _infer_lexical_field(entry)
    path = str(dictionary_path).replace("\\", "/").rstrip("/").split("/")
    if entry.dynamic or len(path) < 2:
        return spec
    relative_path = path[-2:]
    choices = None
    expected_kinds = {"word", "boolean"}
    if relative_path == ["system", "controlDict"]:
        if entry.scope and entry.scope[0] == "functions" and entry.key in {"executeControl", "writeControl"}:
            choices = _FUNCTION_CONTROL_CHOICES
        elif not entry.scope:
            choices = _CONTROL_DICT_CHOICES.get(entry.key)
    elif relative_path == ["system", "fvSchemes"]:
        choices = _SCHEME_CHOICES.get((entry.scope[0], entry.key)) if len(entry.scope) == 1 else None
        expected_kinds = {"word", "raw"}
    elif relative_path == ["system", "fvSolution"] and len(entry.scope) == 2 and entry.scope[0] == "solvers":
        choices = {
            "solver": _LINEAR_SOLVER_CHOICES,
            "preconditioner": _PRECONDITIONER_CHOICES,
            "smoother": _SMOOTHER_CHOICES,
        }.get(entry.key)
    elif relative_path == ["system", "decomposeParDict"] and not entry.scope and entry.key == "method":
        choices = ("scotch", "simple", "hierarchical", "manual", "multiLevel", "structured")
    elif len(path) >= 2 and path[-2] in {"0", "0.orig"} and entry.key == "type" and entry.scope[:1] == ("boundaryField",):
        choices = _BOUNDARY_TYPE_CHOICES
    if not choices or spec.kind not in expected_kinds:
        return spec
    current = entry.value.strip()
    if current and current not in choices:
        choices = (*choices, current)
    return FieldSpec("choice", choices=choices)


def initial_values(entry: Entry, spec: FieldSpec) -> tuple[str, ...]:
    if spec.kind in {"vector", "symmTensor", "tensor"}:
        tokens = list(entry.value_tokens)
        if tokens and tokens[0].kind == "atom" and tokens[0].value == "uniform":
            tokens = tokens[1:]
        return tuple(token.value for token in tokens[1:-1])
    if spec.kind == "raw":
        return ()
    return (entry.value.strip(),)


def validate_values(spec: FieldSpec, values: tuple[str, ...] | list[str]) -> str | tuple[str, ...]:
    if spec.kind == "choice":
        value = values[0].strip() if len(values) == 1 else ""
        if value not in spec.choices:
            raise ValueError("choose a supported value")
        return value
    if spec.kind == "boolean":
        value = values[0].strip().lower() if len(values) == 1 else ""
        if value not in {"true", "false"}:
            raise ValueError("choose true or false")
        return value
    if spec.kind == "integer":
        value = values[0].strip() if len(values) == 1 else ""
        if not _INTEGER.fullmatch(value) or not _SPIN_MIN <= int(value) <= _SPIN_MAX:
            raise ValueError("enter a 32-bit integer")
        return value
    if spec.kind == "scalar":
        value = values[0].strip() if len(values) == 1 else ""
        if not _is_scalar(value):
            raise ValueError("enter a finite OpenFOAM scalar")
        return value
    if spec.kind == "word":
        value = values[0].strip() if len(values) == 1 else ""
        if not _WORD.fullmatch(value):
            raise ValueError("enter one OpenFOAM word without spaces or shell syntax")
        return value
    if spec.kind in {"vector", "symmTensor", "tensor"}:
        result = tuple(value.strip() for value in values)
        if len(result) != spec.component_count or any(not _is_scalar(value) for value in result):
            raise ValueError(f"enter {spec.component_count} finite numeric components")
        return result
    raise ValueError("this value is preserved as raw source and cannot be edited visually")
