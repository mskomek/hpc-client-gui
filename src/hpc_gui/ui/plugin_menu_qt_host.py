"""Qt host for plugin menu actions – owns the Qt UI."""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)

_LINTER_ID = "org.hpcclient.openfoamlint"
_STUDIO_ID = "org.hpcclient.openfoamcasestudio"


def _studio_gate(plugin: InstalledPlugin) -> str | None:
    """Return a failure reason, or None when the studio package is usable.

    Declarative API 3 only: never imports package Python. Verifies exact
    studio identity and API 3 static+on-disk integrity via
    ``api3_error_for_dir``. Empty production pins fail closed here.
    """
    from hpc_gui.plugins.trusted_api3 import api3_error_for_dir

    manifest = getattr(plugin, "manifest", None)
    if manifest is None or getattr(manifest, "id", None) != _STUDIO_ID:
        return f"plugin {getattr(manifest, 'id', '?')!r} is not the OpenFOAM studio owner"
    if getattr(manifest, "plugin_api", None) != 3:
        return "openfoam host binding pending readiness (menu stays disabled; no execution)"
    try:
        problem = api3_error_for_dir(manifest, plugin.directory)
    except Exception as exc:
        return f"openfoam integrity evidence unavailable: {exc}"
    return problem


_STUDIO_ACTION_IDS = {
    None: "openfoam.open_studio",
    "new": "openfoam.new_case",
    "draft": "openfoam.create_job_draft",
}

_STUDIO_DIALOG_TITLES = {
    None: "OpenFOAM Case Studio",
    "new": "OpenFOAM Case Studio — New Case",
    "draft": "OpenFOAM Case Studio — Job Draft (review only)",
}


def _open_qt_studio_page(plugin: InstalledPlugin, host_window, *, action=None) -> bool:
    """Route only to the page factory from the exact host-pinned Studio engine.

    No fallback to another plugin or framework is allowed on any failure.
    """
    action_id = _STUDIO_ACTION_IDS.get(action, "openfoam.open_studio")
    try:
        from hpc_gui.services.plugin_menu_actions import can_execute_action
    except Exception as exc:
        logger.warning("Qt openfoam studio dispatcher unavailable: %s", exc, exc_info=exc)
        return False
    allowed, reason = can_execute_action(action_id, plugin)
    if not allowed:
        logger.warning(
            "Qt openfoam studio blocked for %s: %s",
            getattr(getattr(plugin, "manifest", None), "id", "?"), reason,
        )
        return False
    reason = _studio_gate(plugin)
    if reason:
        logger.warning(
            "Qt openfoam studio blocked for %s: %s",
            getattr(getattr(plugin, "manifest", None), "id", "?"), reason,
        )
        return False
    try:
        from hpc_gui.plugins.application_tools import load_application_tool_for_plugin

        tool = load_application_tool_for_plugin(plugin)
        create_qt_page = tool.qt_page_factory
        if not callable(create_qt_page):
            logger.warning("Qt OpenFOAM Case Studio factory is unavailable")
            return False
    except Exception as exc:
        logger.warning("Qt openfoam studio unavailable: %s", exc, exc_info=exc)
        return False
    try:
        session_state: dict = {}
        session = getattr(host_window, "_session", None) if host_window is not None else None
        if isinstance(session, dict):
            session_state = {"session": session}
        if host_window is None:
            logger.warning("Qt OpenFOAM Case Studio needs the active main window")
            return False
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        dialog = QDialog(host_window)
        dialog.setWindowTitle(_STUDIO_DIALOG_TITLES.get(action, _STUDIO_DIALOG_TITLES[None]))
        dialog.resize(1200, 800)
        layout = QVBoxLayout(dialog)
        page = create_qt_page(
            dialog, plugin=plugin, session_state=session_state,
            initial_path=None, remote=False, action=action,
        )
        layout.addWidget(page)
        dialog.exec()
        return True
    except Exception as exc:
        logger.warning(
            "Qt openfoam studio failed for %s: %s",
            getattr(getattr(plugin, "manifest", None), "id", "?"), exc, exc_info=exc,
        )
        return False


def _linter_gate(plugin: InstalledPlugin) -> str | None:
    from hpc_gui.plugins.trusted_api3 import api3_error_for_dir

    manifest = getattr(plugin, "manifest", None)
    if manifest is None or getattr(manifest, "id", None) != _LINTER_ID:
        return f"plugin {getattr(manifest, 'id', '?')!r} is not the OpenFOAM linter owner"
    if getattr(manifest, "plugin_api", None) != 3:
        return "openfoam host binding pending readiness (menu stays disabled; no execution)"
    try:
        problem = api3_error_for_dir(manifest, plugin.directory)
    except Exception as exc:
        return f"openfoam integrity evidence unavailable: {exc}"
    return problem


class QtPluginMenuHost:
    """Qt implementation of PluginMenuHost."""

    def __init__(self, editor_widget=None, host_window=None, *, initial_paths=(), session_state=None):
        self._editor = editor_widget
        self._window = host_window
        self._initial_paths = tuple(str(path) for path in (initial_paths or ()))
        self._session_state = dict(session_state or {})

    def run_editor_lint(self, plugin_id: str) -> bool:
        editor = self._editor
        if editor is None:
            logger.warning("run_editor_lint requires editor_widget")
            return False
        # Prefer plugin-scoped lint
        scoped = getattr(editor, "run_lint_for_plugin", None)
        if callable(scoped):
            try:
                scoped(plugin_id)
                return True
            except Exception:
                pass
        try:
            editor.run_lint()  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            logger.warning("run_editor_lint failed: %s", exc, exc_info=exc)
            return False

    def open_plugin_templates(self, plugin_id: str) -> bool:
        editor = self._editor
        if editor is None:
            logger.warning("open_plugin_templates requires editor_widget")
            return False
        scoped = getattr(editor, "new_from_template_for_plugin", None)
        if callable(scoped):
            try:
                scoped(plugin_id)
                return True
            except Exception as exc:
                logger.warning("open_plugin_templates failed: %s", exc, exc_info=exc)
                return False
        logger.warning("open_plugin_templates: editor missing new_from_template_for_plugin")
        return False

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
        from hpc_gui.plugins.trusted_tools import is_approved_trusted_tool

        if not is_approved_trusted_tool(plugin.manifest):
            logger.warning("plugin %s is not an approved trusted tool", plugin.manifest.id)
            return False
        try:
            tool = load_tool_for_plugin(plugin)
        except ToolLoadError as exc:
            logger.warning("Cannot load trusted tool %s: %s", plugin.manifest.id, exc)
            return False
        except Exception as exc:
            logger.warning("Unexpected error loading trusted tool %s: %s", plugin.manifest.id, exc, exc_info=exc)
            return False

        # Qt UI construction lives here, not in the shared service
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout

            parent = self._window
            dialog = QDialog(parent)
            dialog.setWindowTitle(f"{tool.title} — {plugin.manifest.id}@{tool.version}")
            dialog.resize(980, 680)
            layout = QVBoxLayout(dialog)
            page = tool.page_factory(parent=dialog)
            layout.addWidget(page)
            dialog.exec()
            return True
        except Exception as exc:
            logger.warning("Opening trusted tool %s failed: %s", plugin.manifest.id, exc, exc_info=exc)
            return False

    def run_openfoam_studio(self, plugin: InstalledPlugin) -> bool:
        """Open the page factory from the exact host-pinned Studio engine."""
        return _open_qt_studio_page(plugin, self._window, action=None)

    def new_openfoam_case(self, plugin: InstalledPlugin) -> bool:
        """Open Case Studio for a new case (review-only, no execution)."""
        return _open_qt_studio_page(plugin, self._window, action="new")

    def create_openfoam_job_draft(self, plugin: InstalledPlugin) -> bool:
        """Open Case Studio job-draft flow (review-only, no execution).

        Draft generation stays inside the page via validated
        workflow-generated scripts and the create-only Allrun store: an
        existing Allrun is never overwritten, and no sbatch/subprocess/
        shell/network call runs here.
        """
        return _open_qt_studio_page(plugin, self._window, action="draft")

    def validate_with_openfoam_linter(self, plugin: InstalledPlugin) -> bool:
        """Validate via the verified-byte API 3 linter engine (read-only)."""
        reason = _linter_gate(plugin)
        if reason:
            logger.warning(
                "Qt openfoam validate blocked for %s: %s",
                getattr(getattr(plugin, "manifest", None), "id", "?"), reason,
            )
            return False
        try:
            from hpc_gui.plugins.linter_tools import load_tool_for_plugin
        except Exception as exc:
            logger.warning("Qt openfoam linter loader unavailable: %s", exc, exc_info=exc)
            return False
        try:
            tool = load_tool_for_plugin(plugin)
        except Exception as exc:
            logger.warning(
                "Qt openfoam validate failed to load %s: %s",
                plugin.manifest.id, exc, exc_info=exc,
            )
            return False
        if getattr(tool, "plugin_id", None) != _LINTER_ID:
            logger.warning("Qt openfoam validate identity mismatch for %s", plugin.manifest.id)
            return False
        try:
            import sys as _sys

            module = _sys.modules.get(getattr(tool, "module_name", ""))
            descriptor = module.create_plugin() if module is not None else None
        except Exception as exc:
            logger.warning("Qt openfoam validate descriptor failed: %s", exc, exc_info=exc)
            return False
        if not isinstance(descriptor, dict):
            logger.warning("Qt openfoam validate descriptor invalid for %s", plugin.manifest.id)
            return False
        factory = descriptor.get("page_factory")
        if not callable(factory):
            logger.warning("Qt openfoam validate has no Qt page factory for %s", plugin.manifest.id)
            return False
        try:
            if self._window is None:
                logger.warning("Qt OpenFOAM Linter needs the active main window")
                return False
            from PySide6.QtWidgets import QDialog, QVBoxLayout

            parent = self._window
            dialog = QDialog(parent)
            dialog.setWindowTitle(f"{tool.title} — {plugin.manifest.id}@{tool.version}")
            dialog.resize(980, 680)
            layout = QVBoxLayout(dialog)
            page = factory(parent=dialog, initial_paths=self._initial_paths,
                           session_state=self._session_state, action="validate",
                           host_window=self._window)
            layout.addWidget(page)
            dialog.exec()
            return True
        except Exception as exc:
            logger.warning("Qt openfoam validate failed for %s: %s", plugin.manifest.id, exc, exc_info=exc)
            return False
