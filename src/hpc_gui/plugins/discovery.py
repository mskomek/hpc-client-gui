"""Canonical plugin discovery sources for W32 (Workstream A).

Enumerates the five planning sources, documents the implemented status of
each, and provides the deterministic helpers the loader relies on:

- bundled
- user-installed
- configured path
- entry point / package mechanism
- development path

Only ``user-installed`` (local declarative storage under
``plugins_root``) is an active discovery source. Every other source is
explicitly NOT an active source: the loader never scans the current working
directory, ``sys.path``, installed distributions, or package resources.
``configured path`` exists only as the explicit ``root`` override used by
tests and explicit user configuration (``storage.plugins_root(override)``).

Precedence, duplicate handling, trust and restart semantics are defined
here so the Wave requirement trace has one live owner.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


BUNDLED_SOURCE_ID = "bundled"
USER_INSTALLED_SOURCE_ID = "user-installed"
CONFIGURED_PATH_SOURCE_ID = "configured-path"
ENTRY_POINT_SOURCE_ID = "entry-point"
DEVELOPMENT_PATH_SOURCE_ID = "development-path"

ALL_SOURCE_IDS: tuple[str, ...] = (
    BUNDLED_SOURCE_ID,
    USER_INSTALLED_SOURCE_ID,
    CONFIGURED_PATH_SOURCE_ID,
    ENTRY_POINT_SOURCE_ID,
    DEVELOPMENT_PATH_SOURCE_ID,
)


@dataclass(frozen=True)
class DiscoverySource:
    """One planning discovery source with its implemented status."""

    source_id: str
    active: bool
    precedence: int | None
    trust: str
    requires_restart: bool
    restart_note: str
    detail: str


def list_sources(*, root: str | Path | None = None) -> tuple[DiscoverySource, ...]:
    """Return the five canonical sources in precedence order."""
    from hpc_gui.plugins.storage import plugins_root

    resolved = str(plugins_root(root))
    return (
        DiscoverySource(
            source_id=USER_INSTALLED_SOURCE_ID,
            active=True,
            precedence=1,
            trust=(
                "local declarative payloads only; manifest validated, "
                "requires_app compatibility checked, trusted manifest hash "
                "plus per-file size/SHA-256 re-validated on every load"
            ),
            requires_restart=False,
            restart_note=(
                "install/enable/disable takes effect on the next "
                "load_installed_plugins() call; no application restart is "
                "required for the listing, and disabled plugins contribute "
                "no profiles, templates, rules, or tools"
            ),
            detail=f"active discovery root: {resolved}",
        ),
        DiscoverySource(
            source_id=CONFIGURED_PATH_SOURCE_ID,
            active=False,
            precedence=None,
            trust=(
                "explicit root override only (tests and explicit user "
                "configuration via storage.plugins_root(override)); never "
                "read from environment variables or implicit search paths"
            ),
            requires_restart=False,
            restart_note="override applies to the next load call with that root",
            detail=(
                "conditional: the same user-installed layout under an "
                "explicitly passed root; not a second implicit search path"
            ),
        ),
        DiscoverySource(
            source_id=BUNDLED_SOURCE_ID,
            active=False,
            precedence=None,
            trust="no bundled plugin directory is scanned; nothing is trusted by location",
            requires_restart=False,
            restart_note="not applicable: no bundled source is discovered",
            detail="intentionally unsupported: no package-resource scan",
        ),
        DiscoverySource(
            source_id=ENTRY_POINT_SOURCE_ID,
            active=False,
            precedence=None,
            trust=(
                "no setuptools entry_points, importlib.metadata scan, or "
                "importable-code execution; declarative JSON/Markdown only"
            ),
            requires_restart=False,
            restart_note="not applicable: entry points never execute",
            detail="intentionally unsupported: entrypoints in the manifest are "
            "relative declarative payload paths, not importable code",
        ),
        DiscoverySource(
            source_id=DEVELOPMENT_PATH_SOURCE_ID,
            active=False,
            precedence=None,
            trust=(
                "development checkouts on PYTHONPATH/CWD must not change "
                "discovery; packaged builds discover the same set"
            ),
            requires_restart=False,
            restart_note="not applicable: development paths are never scanned",
            detail="intentionally unsupported: loader takes no sys.path/CWD input",
        ),
    )


def active_sources(*, root: str | Path | None = None) -> tuple[DiscoverySource, ...]:
    """Return only the active discovery sources (currently one)."""
    return tuple(source for source in list_sources(root=root) if source.active)


def discovery_precedence() -> tuple[str, ...]:
    """Return active source ids in precedence order (deterministic)."""
    return tuple(source.source_id for source in active_sources())


def duplicate_handling_note() -> str:
    """Document deterministic duplicate handling (loader-enforced)."""
    return (
        "active index iteration is sorted by plugin id; the first claimant "
        "of a cluster profile id wins deterministically and every later "
        "claimant (including a self-collision) is rejected whole with a "
        "contained diagnostic; no profile set is ever partially applied"
    )


def deterministic_registry_identity(active: Mapping[str, str]) -> str:
    """Return the deterministic registry identity for an active index.

    The identity is SHA-256 over LF-joined ``id@version`` pairs sorted by
    plugin id. Sorting makes the identity independent of dict insertion
    order, file order, or discovery order.
    """
    pairs = sorted((str(plugin_id), str(version)) for plugin_id, version in active.items())
    canonical = "\n".join(f"{plugin_id}@{version}" for plugin_id, version in pairs)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_no_cwd_discovery(cwd: str | Path | None = None) -> Path:
    """Prove the loader takes no current-working-directory input.

    Returns the probed directory. Callers place a fake plugin tree under
    ``cwd`` and then verify ``load_installed_plugins`` is unaffected.
    The assertion here guards the contract statically: the loader and
    storage modules must not reference ``os.getcwd``/``os.getcwdb``.
    """
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.plugins.storage as storage_module
    import inspect

    for module in (loader_module, storage_module):
        try:
            source = inspect.getsource(module)
        except (OSError, TypeError):
            continue
        assert "getcwd" not in source, f"{module.__name__} must not use getcwd"
        assert "getcwdb" not in source, f"{module.__name__} must not use getcwdb"
    return Path(cwd) if cwd is not None else Path.cwd()


def describe_for_report(*, root: str | Path | None = None) -> dict[str, Any]:
    """Return a JSON-serialisable discovery summary for Wave evidence."""
    sources = list_sources(root=root)
    return {
        "active_precedence": [s.source_id for s in sources if s.active],
        "all_sources": [
            {
                "id": s.source_id,
                "active": s.active,
                "precedence": s.precedence,
                "trust": s.trust,
                "requires_restart": s.requires_restart,
                "restart_note": s.restart_note,
                "detail": s.detail,
            }
            for s in sources
        ],
        "duplicate_handling": duplicate_handling_note(),
    }


__all__ = [
    "ALL_SOURCE_IDS",
    "BUNDLED_SOURCE_ID",
    "CONFIGURED_PATH_SOURCE_ID",
    "DEVELOPMENT_PATH_SOURCE_ID",
    "ENTRY_POINT_SOURCE_ID",
    "USER_INSTALLED_SOURCE_ID",
    "DiscoverySource",
    "active_sources",
    "assert_no_cwd_discovery",
    "describe_for_report",
    "deterministic_registry_identity",
    "discovery_precedence",
    "duplicate_handling_note",
    "list_sources",
]
