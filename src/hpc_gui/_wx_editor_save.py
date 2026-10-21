"""Save/lint/header-action leaf for the wx editor.

Owns overwrite/external-change confirms, the threaded save/submit/run
worker, header button enablement, and open/template/lint dispatch.
Operates only on explicitly passed handles; never imports the facade,
find leaf, or document leaf.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from threading import Thread

from hpc_gui.services.editor_controller import normalize_newlines_for_save
from hpc_gui.wx_editor_guards import _disk_baseline, _write_local_text


def resolve_callback(model, action_factory, name, direct):
    try:
        cur = model.controller.active
        if action_factory and cur is not None:
            cbs = action_factory(cur)
            if isinstance(cbs, dict) and cbs.get(name):
                return cbs[name]
    except Exception:
        pass
    return direct


def collect_lint_issues(lpath, text):
    from hpc_gui.core.i18n import t

    issues = []
    is_slurm = lpath.lower().endswith((".slurm", ".sbatch"))
    if not is_slurm:
        return issues
    stripped = text.lstrip()
    if not stripped.startswith("#!"):
        issues.append(t("editor.validation_missing_shebang") if t("editor.validation_missing_shebang") != "[editor.validation_missing_shebang]" else "- Missing shebang")
    if "#SBATCH" not in text:
        issues.append(t("editor.validation_missing_sbatch") if t("editor.validation_missing_sbatch") != "[editor.validation_missing_sbatch]" else "- No #SBATCH")
    if "USERNAME" in text or "<partition>" in text:
        issues.append(t("editor.validation_placeholders") if t("editor.validation_placeholders") != "[editor.validation_placeholders]" else "- placeholders")
    if "--time=" not in text and "\n#SBATCH -t " not in text:
        issues.append(t("editor.validation_missing_time") if t("editor.validation_missing_time") != "[editor.validation_missing_time]" else "- Time limit not set")
    if "--output=" not in text and "\n#SBATCH -o " not in text:
        issues.append(t("editor.validation_missing_output") if t("editor.validation_missing_output") != "[editor.validation_missing_output]" else "- Output not set")
    return issues


def show_lint_dialog(host, lpath, issues) -> None:
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    title = t("editor.lint_results_title") if t("editor.lint_results_title") != "[editor.lint_results_title]" else "Lint results"
    if not issues:
        msg = t("editor.lint_ok") if t("editor.lint_ok") != "[editor.lint_ok]" else "Lint passed."
        wx.MessageBox(msg, title, wx.OK | wx.ICON_INFORMATION, host)
        return
    dlg = wx.Dialog(host, title=title, size=(540, 360))
    sizer = wx.BoxSizer(wx.VERTICAL)
    lst = wx.ListBox(dlg)
    for iss in issues:
        lst.Append(iss)
    sizer.Add(lst, 1, wx.EXPAND | wx.ALL, 8)
    btn = wx.Button(dlg, label=t("common.close"))
    sizer.Add(btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    dlg.SetSizer(sizer)
    btn.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_OK))
    dlg.ShowModal()
    dlg.Destroy()


def ask_overwrite(host, title_key: str, message: str) -> bool:
    from hpc_gui.core.i18n import t

    try:
        import wx

        title = t(title_key)
        if title == f"[{title_key}]":
            title = title_key
        return wx.MessageBox(message, title, wx.YES_NO | wx.ICON_WARNING, host) == wx.ID_YES
    except Exception:
        return False


def confirm_save_as(host, target: str, is_local: bool, target_exists) -> bool:
    """Save As to an existing target needs an explicit prompt."""
    from hpc_gui.core.i18n import t

    exists = False
    if is_local:
        try:
            exists = os.path.exists(target)
        except Exception:
            exists = False
    elif callable(target_exists):
        try:
            exists = bool(target_exists(target))
        except Exception:
            exists = False
    if not exists:
        return True
    message = t("editor.save_as_exists").format(path=target)
    return ask_overwrite(host, "editor.save_as_title", message)


def confirm_external_change(host, state: dict, path: str, saved_content: str, new_content: str) -> bool:
    from hpc_gui.core.i18n import t

    baseline = state["disk_baseline"].get(path, _disk_baseline(path))
    if path not in state["disk_baseline"]:
        state["disk_baseline"][path] = baseline
        return True
    current = _disk_baseline(path)
    if current == baseline:
        return True
    if current is None:
        if baseline is not None and saved_content:
            message = t("editor.external_deleted_message").format(path=path)
            return ask_overwrite(host, "editor.external_change_title", message)
        return True
    if baseline is None:
        message = t("editor.save_as_exists").format(path=path)
        return ask_overwrite(host, "editor.save_as_title", message)
    try:
        if os.path.getsize(path) > 10 * 1024 * 1024:
            return True
        disk = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return True
    if disk == saved_content or disk == new_content:
        return True
    message = t("editor.external_change_message").format(path=path)
    return ask_overwrite(host, "editor.external_change_title", message)


def save_document(ctx, mode="save", on_done=None) -> None:
    """Threaded save/submit/run; marshals completion via wx.CallAfter."""
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    from hpc_gui._wx_editor_find import set_find_status

    model = ctx["model"]
    editor = ctx["editor"]
    remote_path = ctx["remote_path"]
    status = ctx["status"]
    state = ctx["state"]
    save = ctx["save"]
    submit = ctx["submit"]
    run = ctx["run"]
    btn_open = ctx["btn_open"]
    btn_template = ctx["btn_template"]
    btn_lint = ctx["btn_lint"]
    action_factory = ctx.get("action_factory")
    save_remote = ctx.get("save_remote")
    on_submit = ctx.get("on_submit")
    on_run = ctx.get("on_run")
    update_header_enabled = ctx["update_header_enabled"]
    if state["closed"] or state["in_flight"]:
        return
    if state.get("binary_refused"):
        set_find_status(status, "editor.binary_save_blocked", "Binary or oversize file is not saved as text.")
        return
    try:
        hdr_path = remote_path.GetValue().strip()
    except Exception:
        hdr_path = ""
    active = model.controller.update_content(editor.GetValue())
    snapshot = active
    target = hdr_path or snapshot.path
    save_as = bool(hdr_path and hdr_path != (snapshot.path or ""))
    operation_callbacks = action_factory(active) if action_factory else None
    operation_save_remote = operation_callbacks["save_remote"] if operation_callbacks else save_remote
    operation_target_exists = operation_callbacks.get("target_exists") if isinstance(operation_callbacks, dict) else None
    operation_submit = operation_callbacks["on_submit"] if operation_callbacks else on_submit
    operation_run = operation_callbacks["on_run"] if operation_callbacks else on_run
    host = ctx["host"]
    if save_as and target:
        snapshot = replace(snapshot, path=target)
        if not confirm_save_as(host, target, snapshot.is_local, operation_target_exists):
            status.SetLabel(t("editor.save_as_cancelled"))
            return
    elif snapshot.is_local and snapshot.path and target:
        if not confirm_external_change(host, state, snapshot.path, snapshot.saved_content, snapshot.content):
            status.SetLabel(t("editor.external_change_cancelled"))
            return
    state["in_flight"] = True
    editor.Enable(False)
    for button in (save, submit, run, btn_open, btn_template, btn_lint):
        button.Enable(False)

    def worker(snapshot=snapshot):
        saved = False
        try:
            if snapshot.is_local and snapshot.path:
                payload = normalize_newlines_for_save(snapshot.content, snapshot.newline)
                _write_local_text(snapshot.path, payload, snapshot.encoding)
                saved = True
            elif operation_save_remote and snapshot.path:
                operation_save_remote(snapshot.path, normalize_newlines_for_save(snapshot.content, snapshot.newline))
                saved = True
            if mode in {"submit", "run"} and not saved:
                raise RuntimeError(t("editor.action_requires_save"))
            if mode == "submit" and operation_submit:
                operation_submit(snapshot)
            elif mode == "run" and operation_run:
                operation_run(snapshot)
            wx.CallAfter(done, None, saved, on_done)
        except Exception as error:
            wx.CallAfter(done, error, saved, None)

    def done(error, saved, callback):
        state["in_flight"] = False
        if state["closed"] and callback is None:
            return
        editor.Enable(True)
        for button in (save, submit, run, btn_open, btn_template, btn_lint):
            button.Enable(True)
        update_header_enabled()
        if saved:
            if save_as and target:
                try:
                    idx = model.controller.active_index
                    if 0 <= idx < len(model.controller.documents):
                        model.controller.documents[idx] = replace(
                            model.controller.documents[idx], path=target
                        )
                    try:
                        remote_path.SetValue(target)
                    except Exception:
                        pass
                except Exception:
                    pass
            model.controller.mark_saved(snapshot.content)
            try:
                if snapshot.is_local and snapshot.path:
                    state["disk_baseline"][snapshot.path] = _disk_baseline(snapshot.path)
            except Exception:
                pass
        if error:
            status.SetLabel(str(error))
            return
        status.SetLabel("")
        if callback:
            callback()

    Thread(target=worker, daemon=True).start()


def update_header_enabled(ctx) -> None:
    model = ctx["model"]
    state = ctx["state"]
    action_factory = ctx.get("action_factory")
    on_open = ctx.get("on_open")
    on_new_template = ctx.get("on_new_template")
    on_lint = ctx.get("on_lint")
    for btn, name, direct in ((ctx["btn_open"], "on_open", on_open), (ctx["btn_template"], "on_new_template", on_new_template), (ctx["btn_lint"], "on_lint", on_lint)):
        cb = resolve_callback(model, action_factory, name, direct)
        if cb is None:
            try:
                btn.Disable()
            except Exception:
                pass
        else:
            try:
                btn.Enable(not state["in_flight"])
            except Exception:
                pass


def on_open_action(ctx) -> None:
    from hpc_gui.core.i18n import t  # noqa: F401

    model = ctx["model"]
    action_factory = ctx.get("action_factory")
    on_open = ctx.get("on_open")
    remote_path = ctx["remote_path"]
    status = ctx["status"]
    cb = resolve_callback(model, action_factory, "on_open", on_open)
    if cb:
        try:
            hdr = remote_path.GetValue().strip()
            cb(hdr)
        except Exception as err:
            status.SetLabel(str(err))
        return
    status.SetLabel("")


def on_template_action(ctx) -> None:
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = ctx["model"]
    action_factory = ctx.get("action_factory")
    on_new_template = ctx.get("on_new_template")
    remote_path = ctx["remote_path"]
    editor = ctx["editor"]
    status = ctx["status"]
    host = ctx["host"]
    cb = resolve_callback(model, action_factory, "on_new_template", on_new_template)
    if cb:
        try:
            cb()
        except Exception as err:
            status.SetLabel(str(err))
        return
    try:
        from hpc_gui.plugins.job_templates import load_job_templates
        templates = load_job_templates()
    except Exception:
        templates = []
    if not templates:
        wx.MessageBox(t("templates.none_installed"), t("editor.new_from_template"), wx.OK | wx.ICON_INFORMATION, host)
        return
    try:
        from hpc_gui.plugins.job_templates import render_template
        tpl = templates[0]
        rendered = render_template(tpl, {})
        editor.SetValue(rendered)
        model.controller.update_content(rendered)
        remote_path.SetValue(tpl.file_name or "")
    except Exception as err:
        status.SetLabel(str(err))


def on_lint_action(ctx) -> None:
    from hpc_gui.core.i18n import t

    try:
        import wx  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = ctx["model"]
    action_factory = ctx.get("action_factory")
    on_lint = ctx.get("on_lint")
    remote_path = ctx["remote_path"]
    editor = ctx["editor"]
    status = ctx["status"]
    host = ctx["host"]
    cb = resolve_callback(model, action_factory, "on_lint", on_lint)
    if cb:
        try:
            hdr = remote_path.GetValue().strip()
            cb(hdr, editor.GetValue())
        except Exception as err:
            status.SetLabel(str(err))
        return
    hdr = remote_path.GetValue().strip()
    if not hdr:
        wx.MessageBox(
            t("editor.lint_need_path"),
            t("editor.lint_results_title"),
            wx.OK | wx.ICON_INFORMATION,
            host,
        )
        return
    issues = collect_lint_issues(hdr, editor.GetValue())
    show_lint_dialog(host, hdr, issues)


__all__ = [
    "ask_overwrite",
    "collect_lint_issues",
    "confirm_external_change",
    "confirm_save_as",
    "on_lint_action",
    "on_open_action",
    "on_template_action",
    "resolve_callback",
    "save_document",
    "show_lint_dialog",
    "update_header_enabled",
]
