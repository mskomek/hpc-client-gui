"""Typed parameter schemas for ACTIVE-TYPED tools (W65 CAT-003, G04).

Each schema lists parameters with type/required/default/units/choices and
the v2312 source anchor. Validation rejects unknown parameters and
out-of-range values; raw/advanced tools are not listed here.
"""

from __future__ import annotations


def _p(name, ptype, required=False, default=None, units=None, choices=None, minimum=None, maximum=None):
    return {"name": name, "type": ptype, "required": required, "default": default,
            "units": units, "choices": choices, "minimum": minimum, "maximum": maximum}


SCHEMAS: dict[str, dict] = {
    "blockMesh": {"params": [
        _p("nx", "int", True, minimum=1), _p("ny", "int", True, minimum=1),
        _p("nz", "int", True, minimum=1),
        _p("grading", "string", False, default="simpleGrading (1 1 1)"),
        _p("patches", "list", True)], "source": "v2312:applications/utilities/mesh/generation/blockMesh"},
    "checkMesh": {"params": [
        _p("allGeometry", "bool", False, False), _p("writeAllFields", "bool", False, False)],
        "source": "v2312:applications/utilities/mesh/manipulation/checkMesh"},
    "surfaceFeatureExtract": {"params": [
        _p("dict", "string", True), _p("includedAngle", "float", False, 150.0, "deg", minimum=0.0, maximum=180.0)],
        "source": "v2312:applications/utilities/surface/surfaceFeatureExtract"},
    "snappyHexMesh": {"params": [
        _p("castellatedMesh", "bool", False, True), _p("snap", "bool", False, True),
        _p("addLayers", "bool", False, False),
        _p("maxGlobalCells", "int", True, minimum=1),
        _p("minRefinementCells", "int", False, 10, minimum=0),
        _p("nCellsBetweenLevels", "int", False, 3, minimum=1, maximum=10),
        _p("nLayers", "int", False, 0, minimum=0, maximum=20),
        _p("expansionRatio", "float", False, 1.2, minimum=1.0, maximum=2.0)],
        "source": "https://doc.openfoam.com/2312/tools/pre-processing/mesh/generation/snappyhexmesh/"},
    "decomposePar": {"params": [
        _p("numberOfSubdomains", "int", True, minimum=1),
        _p("method", "string", False, "scotch", choices=["scotch", "simple", "hierarchical", "manual"]),
        _p("force", "bool", False, False)], "source": "v2312:applications/utilities/parallelProcessing/decomposePar"},
    "reconstructPar": {"params": [
        _p("latestTime", "bool", False, False), _p("noFields", "bool", False, False)],
        "source": "v2312:applications/utilities/parallelProcessing/reconstructPar"},
    "splitMeshRegions": {"params": [
        _p("cellZones", "bool", False, True), _p("overwrite", "bool", False, False)],
        "source": "v2312:applications/utilities/mesh/manipulation/splitMeshRegions"},
    "setFields": {"params": [_p("dict", "string", False, "system/setFieldsDict")],
                  "source": "v2312:applications/utilities/preProcessing/setFields"},
    "simpleFoam": {"params": [
        _p("endTime", "float", True, minimum=0.0), _p("writeInterval", "float", True, minimum=0.0)],
        "source": "v2312:applications/solvers/incompressible/simpleFoam"},
    "pimpleFoam": {"params": [
        _p("endTime", "float", True, minimum=0.0), _p("deltaT", "float", True, minimum=0.0),
        _p("maxCo", "float", False, 1.0, minimum=0.0)],
        "source": "v2312:applications/solvers/incompressible/pimpleFoam"},
    "icoFoam": {"params": [
        _p("endTime", "float", True, minimum=0.0), _p("deltaT", "float", True, minimum=0.0)],
        "source": "v2312:applications/solvers/incompressible/icoFoam"},
    "chtMultiRegionSimpleFoam": {"params": [
        _p("endTime", "float", True, minimum=0.0),
        _p("regions", "list", True)],
        "source": "v2312:applications/solvers/heatTransfer/chtMultiRegionSimpleFoam"},
    "postProcess": {"params": [
        _p("func", "string", True), _p("latestTime", "bool", False, False),
        _p("time", "string", False, "all")],
        "source": "https://doc.openfoam.com/2312/tools/post-processing/utilities/postProcess/"},
    "foamToVTK": {"params": [
        _p("latestTime", "bool", False, False), _p("ascii", "bool", False, False)],
        "source": "v2312:applications/utilities/postProcessing/dataConversion/foam/foamToVTK"},
    "probes": {"params": [
        _p("fields", "list", True), _p("probeLocations", "list", True)],
        "source": "v2312:src/functionObjects/field/probes"},
    "fieldAverage": {"params": [
        _p("fields", "list", True), _p("timeStart", "float", True, minimum=0.0)],
        "source": "https://doc.openfoam.com/2312/tools/post-processing/function-objects/field/fieldAverage/"},
    "forces": {"params": [
        _p("patches", "list", True), _p("rhoInf", "float", True, minimum=0.0),
        _p("CofR", "list", False)],
        "source": "v2312:src/functionObjects/forces/forces"},
    "forceCoeffs": {"params": [
        _p("patches", "list", True), _p("magUInf", "float", True, minimum=0.0),
        _p("lRef", "float", True, minimum=0.0), _p("Aref", "float", True, minimum=0.0)],
        "source": "v2312:src/functionObjects/forces/forceCoeffs"},
    "yPlus": {"params": [_p("patches", "list", False)],
              "source": "v2312:src/functionObjects/field/yPlus"},
    "wallShearStress": {"params": [_p("patches", "list", False)],
                        "source": "v2312:src/functionObjects/field/wallShearStress"},
}


class SchemaError(ValueError):
    pass


def validate(tool: str, params: dict) -> dict:
    if tool not in SCHEMAS:
        raise SchemaError(f"tool '{tool}' has no ACTIVE-TYPED schema (RAW-ADVANCED only)")
    spec = {p["name"]: p for p in SCHEMAS[tool]["params"]}
    unknown = sorted(set(params) - set(spec))
    if unknown:
        raise SchemaError(f"unknown parameter(s) for {tool}: {', '.join(unknown)}")
    out = {}
    for name, decl in spec.items():
        if name in params:
            value = params[name]
        elif decl.get("required"):
            raise SchemaError(f"missing required parameter '{name}' for {tool}")
        else:
            value = decl.get("default")
        minimum, maximum = decl.get("minimum"), decl.get("maximum")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if minimum is not None and value < minimum:
                raise SchemaError(f"parameter '{name}' below minimum {minimum}")
            if maximum is not None and value > maximum:
                raise SchemaError(f"parameter '{name}' above maximum {maximum}")
        if decl.get("choices") is not None and value is not None and name in params:
            if value not in decl["choices"]:
                raise SchemaError(f"parameter '{name}' must be one of {decl['choices']}")
        out[name] = value
    return out
