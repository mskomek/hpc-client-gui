"""wx host for plugin menu actions – never touches Qt."""

from __future__ import annotations

import logging

from hpc_gui.plugins.models import InstalledPlugin

logger = logging.getLogger(__name__)

_STUDIO_ID = "org.hpcclient.openfoamcasestudio"
_LINTER_ID = "org.hpcclient.openfoamlint"


def _studio_gate(plugin: InstalledPlugin) -> str | None:
    """Return a failure reason, or None when the studio package is usable.

    Declarative API 3 only: never imports package Python. Verifies exact
    studio identity and API 3 static+on-disk integrity via
    ``api3_error_for_dir`` against the exact application-owned release pin.
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


def _linter_gate(plugin: InstalledPlugin) -> str | None:
    """Return a failure reason, or None when the linter package is usable."""
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


def _wx_parent_for(editor_page):
    try:
        getter = getattr(editor_page, "GetParent", None)
        if callable(getter):
            return getter()
    except Exception:
        pass
    return None


def _wx_session_state(editor_page) -> dict:
    """Return the live main-window session state for authenticated SFTP."""
    cursor = editor_page
    seen: set[int] = set()
    while cursor is not None and id(cursor) not in seen:
        seen.add(id(cursor))
        for attr in ("session_state", "_session_state", "_wx_session_state"):
            try:
                state = getattr(cursor, attr, None)
            except Exception:
                state = None
            if isinstance(state, dict) and isinstance(state.get("session"), dict):
                return state
        getter = getattr(cursor, "GetParent", None)
        try:
            cursor = getter() if callable(getter) else None
        except Exception:
            break
    return {}


def _open_studio_page(plugin: InstalledPlugin, editor_page, *, action=None) -> bool:
    reason = _studio_gate(plugin)
    if reason:
        logger.warning("wx openfoam studio blocked for %s: %s", plugin.manifest.id, reason)
        return False
    try:
        from hpc_gui.plugins.application_tools import load_application_tool_for_plugin

        tool = load_application_tool_for_plugin(plugin)
        create_wx_page = tool.wx_page_factory
        if not callable(create_wx_page):
            return False
    except Exception as exc:
        logger.warning("wx openfoam studio unavailable: %s", exc, exc_info=exc)
        return False
    try:
        parent = _wx_parent_for(editor_page)
        session_state = _wx_session_state(editor_page)
        if parent is None:
            logger.warning("wx OpenFOAM Case Studio needs the active application frame")
            return False
        import wx

        frame_titles = {
            None: "OpenFOAM Case Studio",
            "new": "OpenFOAM Case Studio — New Case",
            "draft": "OpenFOAM Case Studio — Job Draft (review only)",
        }
        frame = wx.Frame(parent, title=frame_titles.get(action, "OpenFOAM Case Studio"))
        try:
            frame.SetSize((1200, 800))
        except Exception:
            pass
        page = create_wx_page(
            frame, plugin=plugin, session_state=session_state,
            initial_path=None, remote=False, action=action,
        )
        if page is None:
            frame.Destroy()
            return False
        frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        frame.GetSizer().Add(page, 1, wx.EXPAND)
        frame.Layout()
        frame.Show()
        return True
    except Exception as exc:
        logger.warning("wx openfoam studio failed for %s: %s", plugin.manifest.id, exc, exc_info=exc)
        return False


class WxPluginMenuHost:
    """wx implementation – routes only where a real wx path exists."""

    def __init__(self, editor_page=None, *, initial_paths=(), session_state=None):
        self._editor = editor_page
        self._initial_paths = tuple(str(path) for path in (initial_paths or ()))
        self._session_override = dict(session_state or {})

    def run_editor_lint(self, plugin_id: str) -> bool:
        # No verified wx lint pipeline – explicitly unsupported
        logger.info("wx run_editor_lint not supported for %s", plugin_id)
        return False

    def open_plugin_templates(self, plugin_id: str) -> bool:
        # Try to use wx editor's plugin-scoped template flow if it exists
        ed = self._editor
        if ed is None:
            return False
        # Check if plugin actually has templates
        try:
            from hpc_gui.plugins.job_templates import load_job_templates

            templates = load_job_templates(plugin_id=plugin_id)
            if not templates:
                return False
        except Exception:
            return False
        # Try wx editor's filtered entry point if available
        scoped = getattr(ed, "new_from_template_for_plugin", None)
        if callable(scoped):
            try:
                scoped(plugin_id)
                return True
            except Exception as exc:
                logger.warning("wx open_plugin_templates failed: %s", exc, exc_info=exc)
                return False
        # No real wx path – disable safely
        logger.info("wx open_plugin_templates has no real path for %s", plugin_id)
        return False

    def open_trusted_tool(self, plugin: InstalledPlugin) -> bool:
        # wx has no Qt dialog – explicitly unsupported, do not fabricate
        logger.info("wx open_trusted_tool not supported for %s", plugin.manifest.id)
        return False

    def run_openfoam_studio(self, plugin: InstalledPlugin) -> bool:
        """Open the page factory from the exact host-pinned Studio engine."""
        return _open_studio_page(plugin, self._editor, action=None)

    def new_openfoam_case(self, plugin: InstalledPlugin) -> bool:
        """Open Case Studio for a new case (review-only, no execution)."""
        return _open_studio_page(plugin, self._editor, action="new")

    def create_openfoam_job_draft(self, plugin: InstalledPlugin) -> bool:
        """Open Case Studio job-draft flow (review-only, no execution).

        Draft generation stays inside the page via validated
        workflow-generated scripts and the create-only Allrun store: an
        existing Allrun is never overwritten, and no scheduler
        submission, child-process, or network call runs here.
        """
        return _open_studio_page(plugin, self._editor, action="draft")

    def validate_with_openfoam_linter(self, plugin: InstalledPlugin) -> bool:
        """Validate via the verified-byte API 3 linter engine (read-only).

        Uses only ``linter_tools.load_tool_for_plugin`` (pin-verified
        bytes, no importlib/sys.path/CWD candidate load) and the verified
        ``create_plugin`` descriptor's ``wx_page_factory``. Empty
        release-pin mismatch fails closed before any import.
        """
        reason = _linter_gate(plugin)
        if reason:
            logger.warning(
                "wx openfoam validate blocked for %s: %s",
                getattr(getattr(plugin, "manifest", None), "id", "?"), reason,
            )
            return False
        try:
            from hpc_gui.plugins.linter_tools import load_tool_for_plugin
        except Exception as exc:
            logger.warning("wx openfoam linter loader unavailable: %s", exc, exc_info=exc)
            return False
        try:
            tool = load_tool_for_plugin(plugin)
        except Exception as exc:
            logger.warning(
                "wx openfoam validate failed to load %s: %s",
                plugin.manifest.id, exc, exc_info=exc,
            )
            return False
        if getattr(tool, "plugin_id", None) != _LINTER_ID:
            logger.warning("wx openfoam validate identity mismatch for %s", plugin.manifest.id)
            return False
        factory = getattr(tool, "wx_page_factory", None)
        if not callable(factory):
            logger.warning("wx openfoam validate has no wx page factory for %s", plugin.manifest.id)
            return False
        try:
            import wx

            parent = _wx_parent_for(self._editor)
            if parent is None or wx.GetApp() is None:
                logger.warning("wx OpenFOAM Linter needs the active application frame")
                return False
            frame = wx.Frame(parent, title=f"{tool.title} — {plugin.manifest.id}")
            frame.SetSize((1050, 700))
            page = factory(
                parent=frame,
                initial_paths=self._initial_paths,
                session_state=self._session_override or _wx_session_state(self._editor),
                action="validate",
            )
            if page is None:
                frame.Destroy()
                return False
            frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
            frame.GetSizer().Add(page, 1, wx.EXPAND)
            frame.Layout()
            frame.Show()
            return True
        except Exception as exc:
            logger.warning("wx openfoam validate failed for %s: %s", plugin.manifest.id, exc, exc_info=exc)
            return False
