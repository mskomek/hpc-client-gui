"""Application-owned policy for the small set of executable tools."""

from __future__ import annotations

from typing import Any, Mapping

TRUSTED_TOOL_API_VERSION = 1

# This is deliberately code-owned. A manifest cannot grant itself trust.
APPROVED_TRUSTED_TOOLS = {
    "org.hpcclient.ansyslint": {
        "publisher": "HPC Client GUI",
        "api": TRUSTED_TOOL_API_VERSION,
        "entrypoint": "engine/ansys_lint/__init__.py",
    },
    # W65 r12: verified OpenFOAM Linter plugin identity (LINT-013/G38).
    # Identity source: N plugins/openfoam_lint/__init__.py PLUGIN_ID
    # ("openfoam-linter") and engine layout engine/openfoam_lint/.
    # Publisher follows the host's own approved-tool publisher. Approval
    # stays code-owned here: a manifest naming this id with a different
    # publisher or entrypoint is still rejected below.
    "openfoam-linter": {
        "publisher": "HPC Client GUI",
        "api": TRUSTED_TOOL_API_VERSION,
        "entrypoint": "engine/openfoam_lint/__init__.py",
    },
}


def trusted_tool_error(manifest: Mapping[str, Any]) -> str | None:
    """Return a rejection reason unless the manifest is explicitly approved."""
    if manifest.get("plugin_api") != 2 or "linter-tool" not in manifest.get("capabilities", []):
        return "executable payloads require the approved trusted-tool contract"
    policy = APPROVED_TRUSTED_TOOLS.get(manifest.get("id"))
    if policy is None:
        return "trusted tool ID is not approved by the application"
    if manifest.get("publisher") != policy["publisher"]:
        return "trusted tool publisher is not approved by the application"
    entrypoint = (manifest.get("entrypoints") or {}).get("linter_engine")
    if entrypoint != policy["entrypoint"]:
        return "trusted tool entrypoint is not application-approved"
    return None


def is_approved_trusted_tool(manifest: Any) -> bool:
    raw = manifest if isinstance(manifest, Mapping) else vars(manifest)
    return trusted_tool_error(raw) is None
