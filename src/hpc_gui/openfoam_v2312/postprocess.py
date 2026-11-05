"""Postprocessing result descriptors (W65 UNIT D, HPC-W65-POST-010).

Pure descriptors for v2312 postprocessing commands, function objects, and
the result artifacts they produce. Descriptors classify work; they never
execute solvers, read case files, or claim live runs. Absent result
artifacts are reported as missing, never zero.
"""
from __future__ import annotations
from dataclasses import dataclass
COMMAND_POSTPROCESS = "postProcess"
COMMAND_FOAMTOVTK = "foamToVTK"
POST_COMMANDS = (COMMAND_POSTPROCESS, COMMAND_FOAMTOVTK)
FUNCTION_PROBES = "probes"
FUNCTION_SETS = "sets"
FUNCTION_SURFACES = "surfaces"
FUNCTION_SAMPLE = "sample"
FUNCTION_FORCES = "forces"
FUNCTION_FORCE_COEFFS = "forceCoeffs"
FUNCTION_FIELD_AVERAGE = "fieldAverage"
FUNCTION_YPLUS = "yPlus"
FUNCTION_WALL_SHEAR = "wallShearStress"
FUNCTION_COURANT_NO = "CourantNo"
FUNCTION_VORTICITY = "vorticity"
FUNCTION_MAG = "mag"
FUNCTION_PATCH_AVERAGE = "patchAverage"
FUNCTION_PATCH_INTEGRATE = "patchIntegrate"
FUNCTION_OBJECTS = (
    FUNCTION_PROBES, FUNCTION_SETS, FUNCTION_SURFACES, FUNCTION_SAMPLE,
    FUNCTION_FORCES, FUNCTION_FORCE_COEFFS, FUNCTION_FIELD_AVERAGE,
    FUNCTION_YPLUS, FUNCTION_WALL_SHEAR, FUNCTION_COURANT_NO,
    FUNCTION_VORTICITY, FUNCTION_MAG, FUNCTION_PATCH_AVERAGE,
    FUNCTION_PATCH_INTEGRATE,
)
ARTIFACT_RESIDUALS = "residuals-log"
ARTIFACT_PROBES_CSV = "probes-csv"
ARTIFACT_SETS_CSV = "sets-csv"
ARTIFACT_SURFACES_VTK = "surfaces-vtk"
ARTIFACT_FORCES_DAT = "forces-dat"
ARTIFACT_YPLUS = "yplus-field"
ARTIFACT_CASE_VTK = "case-vtk"
ARTIFACT_REPORT = "report-md"
RESULT_ARTIFACTS = (
    ARTIFACT_RESIDUALS, ARTIFACT_PROBES_CSV, ARTIFACT_SETS_CSV,
    ARTIFACT_SURFACES_VTK, ARTIFACT_FORCES_DAT, ARTIFACT_YPLUS,
    ARTIFACT_CASE_VTK, ARTIFACT_REPORT,
)
COMMAND_ARTIFACTS = {
    COMMAND_POSTPROCESS: frozenset({
        ARTIFACT_RESIDUALS, ARTIFACT_PROBES_CSV, ARTIFACT_SETS_CSV,
        ARTIFACT_SURFACES_VTK, ARTIFACT_FORCES_DAT, ARTIFACT_YPLUS,
        ARTIFACT_REPORT,
    }),
    COMMAND_FOAMTOVTK: frozenset({ARTIFACT_CASE_VTK, ARTIFACT_SURFACES_VTK}),
}
REQUIRES_FUNCTION = {
    ARTIFACT_FORCES_DAT: frozenset({FUNCTION_FORCES, FUNCTION_FORCE_COEFFS}),
    ARTIFACT_YPLUS: frozenset({FUNCTION_YPLUS, FUNCTION_WALL_SHEAR}),
    ARTIFACT_PROBES_CSV: frozenset({FUNCTION_PROBES}),
    ARTIFACT_SETS_CSV: frozenset({FUNCTION_SETS, FUNCTION_SAMPLE}),
    ARTIFACT_SURFACES_VTK: frozenset({FUNCTION_SURFACES, FUNCTION_SAMPLE}),
}
@dataclass(frozen=True)
class PostView:
    """One named postprocessing view with its tool selection."""
    name: str
    command: str = COMMAND_POSTPROCESS
    functions: tuple = ()
    artifacts: tuple = ()
    methodology: str = ""
    def to_dict(self):
        return {
            "name": self.name, "command": self.command,
            "functions": list(self.functions),
            "artifacts": list(self.artifacts),
            "methodology": self.methodology,
        }
    @staticmethod
    def from_dict(raw):
        functions = raw.get("functions", [])
        if not isinstance(functions, (list, tuple)):
            raise ValueError("post functions must be a list of names")
        artifacts = raw.get("artifacts", [])
        if not isinstance(artifacts, (list, tuple)):
            raise ValueError("post artifacts must be a list of names")
        return PostView(
            name=str(raw["name"]),
            command=str(raw.get("command", COMMAND_POSTPROCESS)),
            functions=tuple(str(f) for f in functions),
            artifacts=tuple(str(a) for a in artifacts),
            methodology=str(raw.get("methodology", "")),
        )
def validate_post(view):
    """Return deterministic error strings; empty means viewable."""
    errors = []
    if not view.name.strip():
        errors.append("empty post view name")
    if view.command not in POST_COMMANDS:
        errors.append("unknown post command: " + view.command)
    for function in view.functions:
        if function not in FUNCTION_OBJECTS:
            errors.append("unknown function object: " + function)
    if not view.artifacts:
        errors.append("post view selects no result artifacts")
    for artifact in view.artifacts:
        if artifact not in RESULT_ARTIFACTS:
            errors.append("unknown result artifact: " + artifact)
        else:
            producers = sorted(c for c, arts in COMMAND_ARTIFACTS.items() if artifact in arts)
            if view.command in POST_COMMANDS and artifact not in COMMAND_ARTIFACTS[view.command]:
                errors.append("artifact " + artifact + " is produced by " + "/".join(producers) + ", not " + view.command)
        if artifact in REQUIRES_FUNCTION and not (set(view.functions) & REQUIRES_FUNCTION[artifact]):
            errors.append("artifact " + artifact + " needs one of " + "/".join(sorted(REQUIRES_FUNCTION[artifact])))
    if ARTIFACT_REPORT in view.artifacts and not view.methodology.strip():
        errors.append("report artifact needs a recorded methodology")
    return tuple(errors)
def missing_artifacts(view, available):
    """Return artifact names with no data; absent means missing, never zero."""
    return tuple(a for a in view.artifacts if not available.get(a, False))
def list_post_commands():
    return POST_COMMANDS
def list_function_objects():
    return FUNCTION_OBJECTS
def list_result_artifacts():
    return RESULT_ARTIFACTS