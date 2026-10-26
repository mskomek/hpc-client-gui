"""Fail-closed loader for the pinned API 3 application-tool contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.plugins._api3_engine_loader import (
    ToolLoadError,
    _load_api3_engine_verified,
    unload_api3_engine,
)
from hpc_gui.plugins.trusted_api3 import API3_STUDIO_ID, api3_application_entrypoint


@dataclass(frozen=True)
class ApplicationTool:
    plugin_id: str
    version: str
    title: str
    description: str
    qt_page_factory: Callable[..., Any] | None
    wx_page_factory: Callable[..., Any] | None
    module_name: str


def load_application_tool_for_plugin(installed) -> ApplicationTool:
    """Load the exact host-pinned Studio bytes into a private namespace.

    This is a trusted in-process plugin, not an OS sandbox. The exact module
    closure is verified against the application's release pin immediately
    before import; package paths, imports and manifest fields cannot extend
    that closure.
    """
    manifest = getattr(installed, "manifest", None)
    if getattr(manifest, "id", None) != API3_STUDIO_ID:
        raise ToolLoadError("plugin is not the approved OpenFOAM Case Studio identity")
    rel = api3_application_entrypoint(manifest)
    descriptor_ref = getattr(installed, "application_tool", None) or {}
    if rel is None or descriptor_ref.get("module") != rel:
        raise ToolLoadError("application-tool entrypoint is not host-approved")
    module = None
    try:
        module = _load_api3_engine_verified(installed, rel)
        descriptor = module.create_plugin()
    except ToolLoadError:
        raise
    except Exception as exc:
        raise ToolLoadError(f"trusted application tool failed to load: {exc}") from exc
    try:
        if not isinstance(descriptor, dict) or descriptor.get("id") != API3_STUDIO_ID:
            raise ToolLoadError("trusted application tool descriptor identity mismatch")
        title = descriptor.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 128:
            raise ToolLoadError("trusted application tool descriptor has an invalid title")
        factories: dict[str, Callable[..., Any] | None] = {}
        for key in ("qt_page_factory", "wx_page_factory"):
            value = descriptor.get(key)
            if value is not None and not callable(value):
                raise ToolLoadError(f"trusted application tool descriptor has invalid {key}")
            factories[key] = value
        if not any(factories.values()):
            raise ToolLoadError("trusted application tool has no supported GUI factory")
    except Exception:
        if module is not None:
            unload_api3_engine(module.__name__)
        raise
    return ApplicationTool(
        plugin_id=manifest.id,
        version=manifest.version,
        title=title,
        description=str(descriptor.get("description", ""))[:2048],
        qt_page_factory=factories["qt_page_factory"],
        wx_page_factory=factories["wx_page_factory"],
        module_name=module.__name__,
    )
