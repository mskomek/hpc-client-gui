"""Native template entry point: select, validate and open a fresh unsaved document."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.services.editor_controller import EditorCommandService


def open_template(ctx, *, plugin_id=None, templates=None):
    import wx

    from hpc_gui.plugins.job_templates import load_job_templates
    from hpc_gui.wx_template_browser import choose_template

    state, model, host = ctx["state"], ctx["model"], ctx["host"]
    if state["closed"] or state["in_flight"]:
        return False
    try:
        templates = list(load_job_templates(plugin_id=plugin_id) if templates is None else templates)
        if plugin_id is not None:
            templates = [tpl for tpl in templates if tpl.plugin_id == plugin_id]
        if not templates:
            wx.MessageBox(t("templates.none_installed"), t("editor.new_from_template"), wx.OK | wx.ICON_INFORMATION, host)
            return False
        active = model.controller.active
        callbacks = ctx["action_factory"](active) if ctx.get("action_factory") else {}
        identity = (callbacks or {}).get("template_context") or {}
        selected = choose_template(host, templates, provider_template=identity.get("provider_template"))
        if selected is None or state["closed"] or state["in_flight"] or model.controller.active is not active:
            return False
        if active is not None and ctx.get("action_factory"):
            live = (ctx["action_factory"](active) or {}).get("template_context") or {}
            if live.get("session_key") != identity.get("session_key"):
                return False
        template, values = selected
        model.render_template(template, values, provider=identity.get("provider", ""),
                              profile=identity.get("profile", ""), session_key=identity.get("session_key", ""))
        doc = model.controller.active
        ctx["editor"].ChangeValue(doc.content)
        ctx["editor"].SetEditable(True)
        state["binary_refused"] = False
        ctx["remote_path"].ChangeValue("")
        host.set_host_title(EditorCommandService.suggested_filename(doc.suggested_filename))
        ctx["refresh_tabs"]()
        ctx["update_header_enabled"]()
        return True
    except Exception as exc:
        if not state["closed"]:
            ctx["status"].SetLabel(str(exc))
        return False
