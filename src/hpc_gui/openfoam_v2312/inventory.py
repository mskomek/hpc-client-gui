"""Version-pinned OpenFOAM v2312 P0 command inventory (W65 UNIT A).

Static, source-bound registry of the P0 journey commands named by the W65
wave specification. Each entry carries a classification tier: "typed" means
parameter schemas verified against v2312 sources, "raw" means advanced use
only with draft-only execution and no verified schemas claimed yet, and
"unsupported" means explicitly out of scope with a recorded reason.

No entry claims live execution. The TRUBA module name is a site hint from
the wave spec, not a claim about any particular machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

V2312_VERSION = "v2312"
V2312_TAG = "OpenFOAM-v2312"
V2312_COMMIT = "1d8f0d55f79e6488dae75e4b839e358a88af77b5"
TRUBA_MODULE_HINT = "apps/openfoam/v2312-2025"

TIER_TYPED = "typed"
TIER_RAW = "raw"
TIER_UNSUPPORTED = "unsupported"
VALID_TIERS = frozenset({TIER_TYPED, TIER_RAW, TIER_UNSUPPORTED})

EXECUTION_DRAFT_ONLY = "draft-only"

FAMILY_MESH = "mesh"
FAMILY_PARALLEL = "parallel"
FAMILY_SOLVER = "solver"
FAMILY_POST = "post"

PROVENANCE_V2312_TOOLS = "OpenFOAM.com v2312 tools"

_DEFERRED_SCHEMA_REASON = (
    "typed parameter schemas deferred to UNIT C; "
    "execution stays draft-only until the UNIT F runtime gate"
)


@dataclass(frozen=True)
class CommandEntry:
    """One inventoried v2312 command with its support claim."""

    name: str
    family: str
    tier: str
    execution: str
    provenance: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable view of this entry."""
        return {
            "name": self.name,
            "family": self.family,
            "tier": self.tier,
            "execution": self.execution,
            "provenance": self.provenance,
            "reason": self.reason,
        }

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "CommandEntry":
        """Rebuild an entry, rejecting unknown tiers."""
        entry = CommandEntry(
            name=str(raw["name"]),
            family=str(raw["family"]),
            tier=str(raw["tier"]),
            execution=str(raw["execution"]),
            provenance=str(raw["provenance"]),
            reason=str(raw["reason"]),
        )
        if entry.tier not in VALID_TIERS:
            raise ValueError("unknown tier for command " + entry.name)
        return entry


def _p0_entries() -> tuple[CommandEntry, ...]:
    return (
        CommandEntry("blockMesh", FAMILY_MESH, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("checkMesh", FAMILY_MESH, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("chtMultiRegionSimpleFoam", FAMILY_SOLVER, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("decomposePar", FAMILY_PARALLEL, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("icoFoam", FAMILY_SOLVER, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("postProcess", FAMILY_POST, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("reconstructPar", FAMILY_PARALLEL, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("simpleFoam", FAMILY_SOLVER, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
        CommandEntry("splitMeshRegions", FAMILY_MESH, TIER_RAW,
                     EXECUTION_DRAFT_ONLY, PROVENANCE_V2312_TOOLS,
                     _DEFERRED_SCHEMA_REASON),
    )


COMMANDS: tuple[CommandEntry, ...] = _p0_entries()


def list_commands() -> tuple[str, ...]:
    """Return P0 command names in canonical alphabetical order."""
    return tuple(entry.name for entry in COMMANDS)


def get_command(name: str) -> CommandEntry:
    """Return the entry for a command, raising KeyError when unknown."""
    for entry in COMMANDS:
        if entry.name == name:
            return entry
    raise KeyError("unknown OpenFOAM v2312 command: " + name)


def to_dicts() -> list[dict[str, Any]]:
    """Return the canonical JSON-serializable inventory export."""
    return [entry.to_dict() for entry in COMMANDS]


def from_dicts(raw: list[Mapping[str, Any]]) -> tuple[CommandEntry, ...]:
    """Rebuild entries from an export, rejecting unknown tiers."""
    return tuple(CommandEntry.from_dict(item) for item in raw)
