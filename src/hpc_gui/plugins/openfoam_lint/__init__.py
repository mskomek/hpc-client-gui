"""OpenFOAM Linter plugin identity + trusted-tool engine facade (W65 LINT-013).

Version 0.2.0-w65r1. Preserved 0.1.0 rule-ID prefixes; new W65 rules extend
the same families.

Rule families: OF-DICT / OF-CASE / OF-CTRL / OF-SOLVER / OF-BC / OF-MESH /
OF-CROSS / OF-PAR / OF-HPC / OF-SEC.

Host engine surface (W65 r12): the application approves this identity in
``hpc_gui.plugins.trusted_tools`` with entrypoint
``engine/openfoam_lint/__init__.py``; the host loader records that declared
path and ``hpc_gui.plugins.linter_tools`` imports it lazily only when a
user explicitly opens the tool. Static only: linting never executes case
content, solver commands or dynamic directives. There is no wx page yet:
``create_plugin`` loads (title/description) but its page factory fails
closed with an actionable message; use the standalone CLI or the
``lint_text``/``lint_paths`` engine API until a wx host path is VM-proven.
"""

from __future__ import annotations

import os

PLUGIN_ID = "openfoam-linter"
PLUGIN_VERSION = "0.2.0-w65r1"
PLUGIN_BASE = "0.1.0"
# Preserved 0.1.0 rule-ID prefixes; new W65 rules extend the same families.
RULE_FAMILIES = ("OF-DICT", "OF-CASE", "OF-CTRL", "OF-SOLVER", "OF-BC",
                 "OF-MESH", "OF-CROSS", "OF-PAR", "OF-HPC", "OF-SEC")

# Approved engine entrypoint (mirrors plugins/trusted_tools.py policy).
ENGINE_ENTRYPOINT = "engine/openfoam_lint/__init__.py"

# OpenFOAM dictionaries are typically extensionless, so suffix routing is
# explicitly unsupported (empty); tool selection is by case content.
SUPPORTED_SUFFIXES = frozenset()


def _unavailable_page(parent=None):
    """Fail closed: no wx tool page is implemented for this engine yet."""
    raise RuntimeError(
        "OpenFOAM Linter has no wx tool page yet (explicitly unsupported); "
        "use the standalone openfoam-lint CLI or the lint_text engine API"
    )


def create_plugin() -> dict:
    """Host trusted-tool descriptor (title/description/page factory)."""
    return {
        "title": "OpenFOAM Linter",
        "description": "Static OpenFOAM case linter (v2312, offline)",
        "page_factory": _unavailable_page,
    }


def lint_text(text: str, file_name: str = "", options=None):
    """Lint in-memory text; returns a list of api.Diagnostic. No execution."""
    from hpc_gui.plugins.openfoam_lint.api import lint_text as _core

    return _core(file_name or "<buffer>", text)


def lint_paths(paths, options=None):
    """Lint files/directories; returns a flat list of api.Diagnostic.

    Directories are walked for OpenFOAM dictionary basenames (same filter
    as the standalone CLI). Files are read as text; unreadable paths
    raise ValueError. Never executes case content.
    """
    from hpc_gui.plugins.openfoam_lint.api import lint_text as _core

    diags = []
    targets: list[str] = []
    for path in paths or []:
        entry = os.fspath(path)
        if os.path.isdir(entry):
            for root, _, files in os.walk(entry):
                targets += [os.path.join(root, name) for name in files
                            if name.endswith(("Dict", "Properties", "FoamFile"))]
        else:
            targets.append(entry)
    for target in targets:
        try:
            with open(target, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise ValueError(f"cannot read '{target}': {exc}") from exc
        diags.extend(_core(target, text))
    return diags


__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "PLUGIN_BASE", "RULE_FAMILIES",
           "ENGINE_ENTRYPOINT", "SUPPORTED_SUFFIXES", "create_plugin",
           "lint_text", "lint_paths"]
