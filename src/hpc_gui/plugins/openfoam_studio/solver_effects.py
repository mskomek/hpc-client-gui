"""Shared solver file-effect paths (W65 FLOW-011 G30, round 5).

Single lower-level source for the complete set of case files a solver node
mutates, for bound params/defaults. Both the static preview
(:func:`workflow.compile_to_effects`) and the typed compiler
(:func:`workflow_compiler._solver_files`) bind through :func:`bound_state`
so the effect list and the mutating ``PatchOp`` targets cannot drift apart.

Only imports the foundation contract ``hpc_gui.openfoam_core.physics``;
never imports sibling plugin modules, keeping the dependency DAG acyclic.
No execution, no I/O, no physics defaults invented beyond the compiler's own.
"""

from __future__ import annotations

from hpc_gui.openfoam_core.physics import SOLVER_FAMILIES, required_fields_for

#: Canonical classified v2312 solver binaries -> family. Single source of
#: truth; ``solver.SOLVER_BINARIES`` and ``workflow.SOLVER_TOOLS`` mirror it.
SOLVER_BINARIES = {"icoFoam": "laminar", "simpleFoam": "rans-steady",
                   "pimpleFoam": "transient", "pisoFoam": "transient",
                   "chtMultiRegionSimpleFoam": "cht", "chtMultiRegionFoam": "cht",
                   "buoyantSimpleFoam": "buoyant", "rhoSimpleFoam": "compressible",
                   "rhoPimpleFoam": "compressible", "interFoam": "multiphase",
                   "reactingFoam": "reacting", "potentialFoam": "potential"}

#: Families that add a single constant/thermophysicalProperties file.
SINGLE_THERMO_FAMILIES = frozenset({"compressible", "buoyant", "multiphase"})

_DEFAULT_REGIONS = {"fluid": ["fluid"], "solid": ["solid"]}
_DEFAULT_MODEL = {"rans-steady": "kOmegaSST"}


def solver_family(tool: str) -> str:
    """Return the solver family, or raise for an unclassified tool."""
    if tool not in SOLVER_BINARIES:
        raise ValueError(f"solver '{tool}' is not a classified v2312 binary")
    return SOLVER_BINARIES[tool]


def bound_state(tool: str, params: dict | None = None
                ) -> tuple[str, str, list[str], dict | None]:
    """Bind (family, model, fields, regions) with compiler-identical defaults.

    Raises ``ValueError`` naming RAW-ADVANCED/UNSUPPORTED for families with
    no typed model (reacting, potential/unknown), for incompatible models,
    for missing required fields, and for empty CHT regions — the same
    refusal the typed compiler emits, so previews never claim mutations
    the compiler would refuse to produce.
    """
    params = dict(params or {})
    family = solver_family(tool)
    allowed = SOLVER_FAMILIES.get(family, {}).get("models", [])
    if not allowed:
        raise ValueError(
            f"solver '{tool}' is RAW-ADVANCED/UNSUPPORTED in this release "
            f"(family '{family}' has no typed model)")
    model = params.get("model", _DEFAULT_MODEL.get(family, "laminar"))
    if model not in allowed:
        raise ValueError(f"model '{model}' incompatible with {tool} ({family})")
    if "fields" in params:
        fields = list(params["fields"])
    else:
        fields = list(required_fields_for(family, model))
    missing = [f for f in required_fields_for(family, model) if f not in fields]
    if missing:
        raise ValueError(f"solver '{tool}' missing required field(s): {', '.join(missing)}")
    regions: dict | None = None
    if family == "cht":
        raw = params.get("regions", dict(_DEFAULT_REGIONS))
        if not raw:
            raise ValueError("CHT solver requires at least one region")
        if isinstance(raw, dict):
            regions = {"fluid": list(raw.get("fluid", ["fluid"])),
                       "solid": list(raw.get("solid", ["solid"]))}
        else:
            regions = {"fluid": list(raw), "solid": []}
        if not regions["fluid"]:
            raise ValueError("CHT missing fluid region (regionProperties invalid)")
    return family, model, fields, regions


def solver_effect_paths(tool: str, params: dict | None = None) -> list[str]:
    """Complete ordered case-file list a solver node mutates.

    Mirrors ``workflow_compiler._solver_files`` relpaths exactly: the
    numerics triple, one ``0/<field>`` per bound field, transport +
    turbulence properties, then family extras (CHT regionProperties plus
    per-region thermophysical files, or single thermophysicalProperties
    for compressible/buoyant/multiphase). Every op is a ``create`` PatchOp
    (mutating), so all paths are reported — no verify-only filtering.
    """
    family, _model, fields, regions = bound_state(tool, params)
    paths = ["system/controlDict", "system/fvSchemes", "system/fvSolution"]
    paths.extend(f"0/{fld}" for fld in fields)
    paths.append("constant/transportProperties")
    paths.append("constant/turbulenceProperties")
    if family == "cht":
        assert regions is not None
        paths.append("constant/regionProperties")
        for region in regions.get("fluid", ["fluid"]):
            paths.append(f"constant/{region}/thermophysicalProperties")
        for region in regions.get("solid", ["solid"]):
            paths.append(f"constant/{region}/thermophysicalProperties")
    elif family in SINGLE_THERMO_FAMILIES:
        paths.append("constant/thermophysicalProperties")
    return paths
