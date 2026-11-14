"""Solver family/model initial-field checks (W65 LINT-013, OF-SOLVER-010).
Base fields are a rule-local map because the generator contract in
openfoam_core.physics is used by the Studio writers; the two must not be
changed together without a deliberate decision.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from hpc_gui.openfoam_core import Diagnostic, ParsedDictionary, SOURCE_DOCS
from hpc_gui.openfoam_core.physics import SOLVER_FAMILIES, TURBULENCE_MODELS

_BASE_FIELDS = {
    "laminar": ("U", "p"),
    "rans-steady": ("U", "p"),
    "transient": ("U", "p"),
    "cht": ("U", "p", "T"),
    "buoyant": ("U", "p_rgh", "T"),
    "compressible": ("U", "p", "T"),
    "multiphase": ("U", "p_rgh", "alpha.water"),
    "reacting": ("U", "p", "T"),
}

#: Fields every reacting case carries regardless of its chemistry. Stock
#: reactingFoam tutorials name species by formula (CH4, O2, N2, ...), not by a
#: Y prefix, so a species set is inferred from any 0/ field outside this set.
_NON_SPECIES_FIELDS = frozenset({
    "U", "p", "p_rgh", "T", "k", "epsilon", "omega", "nut", "nuTilda",
    "alphat", "mut", "rho", "h", "e", "phi", "pFinal", "UFinal",
})

#: Solvers the shared family table does not list yet; mapped here so the
#: read-only linter can judge them without changing the generator contract.
_FAMILY_FALLBACK = {
    "buoyantPimpleFoam": "buoyant",
    "sonicFoam": "compressible",
    "rhoCentralFoam": "compressible",
    "potentialFoam": "laminar",
}


def _simulation_type(parsed: ParsedDictionary) -> str | None:
    entries = parsed.find("simulationType")
    if len(entries) != 1 or entries[0].dynamic:
        return None
    return entries[0].value.strip().strip('"').strip("'")


def _turbulence_model(files: dict[str, ParsedDictionary]) -> str | None:
    parsed = files.get("constant/turbulenceProperties")
    if parsed is None:
        return "laminar"
    simulation = _simulation_type(parsed)
    if simulation == "laminar":
        return "laminar"
    if simulation not in {"RAS", "LES"}:
        return None
    for entry in parsed.entries:
        if entry.key in {"RASModel", "LESModel"}:
            value = entry.value.strip()
            if value in TURBULENCE_MODELS and value != "laminar":
                return value
    return None


_SPECIES_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _declared_species(files: dict[str, ParsedDictionary]) -> list[str]:
    """Species names declared by the case's chemistry dictionaries.

    Stock ESI cases keep the list in constant/reactions or in a thermo.*
    include, so thermophysicalProperties, reactions and every scanned
    constant/thermo.* file are merged (deduplicated, first-seen order). The
    declarations
    describe the same chemistry, so the result is their union: a case that
    declares a species in only one of them still has to initialise it, and a
    genuine mismatch is the case author's inconsistency to fix. Union is
    also the conservative direction for a linter, which may warn about an
    extra name but must never stay silent about a transported species.
    """
    names: list[str] = []
    sources = ["constant/thermophysicalProperties", "constant/reactions"]
    sources += sorted(name for name in files if name.startswith("constant/thermo."))
    for source in dict.fromkeys(sources):
        parsed = files.get(source)
        if parsed is None:
            continue
        for entry in parsed.find("species"):
            raw = str(entry.value or "")
            for token in re.split(r"[\s,()]+", raw):
                token = token.strip().strip('"').strip("'")
                if token and _SPECIES_NAME.fullmatch(token) and token not in names:
                    names.append(token)
    return names


def required_fields(family: str, model: str | None) -> list[str]:
    """Base fields per family plus turbulence fields for a recognised model."""
    fields = list(_BASE_FIELDS.get(family, ("U", "p")))
    if model and model != "laminar":
        for field in TURBULENCE_MODELS.get(model, {}).get("required_fields", []):
            if field not in fields:
                fields.append(field)
    return fields


def lint_solver_fields(
    files: dict[str, ParsedDictionary], application: str | None,
) -> list[Diagnostic]:
    """Report initial fields missing from a scanned 0/ or 0.orig/ directory."""
    if not application:
        return []
    family = next(
        (name for name, meta in SOLVER_FAMILIES.items() if application in meta["solvers"]),
        None,
    ) or _FAMILY_FALLBACK.get(application)
    if family is None:
        return []
    model = _turbulence_model(files)
    present = {
        PurePosixPath(name).name
        for name in files
        if len(PurePosixPath(name).parts) == 2
        and PurePosixPath(name).parts[0] in {"0", "0.orig"}
    }
    if not present:
        return []
    diagnostics = [
        Diagnostic(
            "OF-SOLVER-010", "warning", "contextual", "0/", 1, 1,
            f"Solver {application} (family {family}, model {model or 'unresolved'}) has no scanned "
            f"initial field {field!r}.",
            "Add the missing field under 0/ (or confirm it is supplied by an include) "
            "before running the solver.",
            SOURCE_DOCS, verification_level="contextual",
        )
        for field in required_fields(family, model)
        if field not in present
    ]
    declared = _declared_species(files) if family == "reacting" else []
    for name in declared:
        if name in present:
            continue
        diagnostics.append(
            Diagnostic(
                "OF-SOLVER-010", "warning", "contextual", "0/", 1, 1,
                f"Solver {application} declares species {name!r} but has no 0/ initial field for it.",
                "Add the declared species field under 0/ or confirm it is supplied by an include "
                "before running the solver.",
                SOURCE_DOCS, verification_level="contextual",
            )
        )
    if family == "reacting" and not declared and present <= _NON_SPECIES_FIELDS:
        diagnostics.append(
            Diagnostic(
                "OF-SOLVER-010", "warning", "contextual", "0/", 1, 1,
                f"Solver {application} is a reacting case but no species field exists under 0/ "
                "(only the base transport fields were found).",
                "Add the species fields declared by the case's thermophysical/reaction setup "
                "(stock tutorials use chemical formulas such as CH4 and O2) or confirm they are "
                "supplied by an include before running the solver.",
                SOURCE_DOCS, verification_level="contextual",
            )
        )
    return diagnostics
