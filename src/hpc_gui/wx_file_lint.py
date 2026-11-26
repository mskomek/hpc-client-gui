"""Native menu actions and asynchronous file-lint workflow."""
from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.services.file_lint import (
    FileLintCancelled, collect_documents, lint_documents, load_catalog,
)


def append_file_lint_actions(menu, selection, callback, owner, *, current=lambda: True):
    """Capture explicit menu-time selection rather than reading later UI state."""
    if not callable(callback) or not selection.effective_paths:
        return {}
    paths = tuple(zip(selection.effective_paths, selection.effective_types, strict=True))
    import wx

    controls = {}
    for label, tool_only in (("editor.lint", False), ("files.send_to_plugin", True)):
        item = menu.Append(wx.ID_ANY, t(label))

        def invoke(_event, tool_only=tool_only):
            if current():
                callback(owner, paths, tool_only=tool_only, current=current)

        menu.Bind(wx.EVT_MENU, invoke, id=item.GetId())
        controls[label] = item
    return controls


def start_file_lint(owner, selection, *, files=None, tool_only=False, current=lambda: True, lifecycle=None):
    import wx

    if not current() or owner.IsBeingDeleted():
        return False
    # A new request supersedes an earlier worker for this view.
    previous = getattr(owner, "_wx_file_lint_request", None)
    if previous is not None:
        previous["cancelled"] = True
    request = {"cancelled": False}
    owner._wx_file_lint_request = request
    selection = tuple(selection)

    def valid():
        return not request["cancelled"] and current()

    def gui_valid():
        if not valid():
            return False
        try:
            return not owner.IsBeingDeleted()
        except RuntimeError:
            return False

    def destroyed(event):
        if event.GetEventObject() is owner:
            request["cancelled"] = True
        event.Skip()

    owner.Bind(wx.EVT_WINDOW_DESTROY, destroyed)

    def open_tool(documents, tools):
        if not gui_valid():
            return
        if not tools:
            wx.MessageBox(t("files.no_supported_remote_lint_files"), t("ansyslint.title"),
                          wx.OK | wx.ICON_INFORMATION, owner)
            return
        tool = tools[0]
        if len(tools) > 1:
            picker = wx.SingleChoiceDialog(owner, t("files.send_to_plugin"), t("ansyslint.title"),
                                           [f"{tool.title} ({tool.plugin_id})" for tool in tools])
            try:
                if picker.ShowModal() != wx.ID_OK:
                    return
                tool = tools[picker.GetSelection()]
            finally:
                picker.Destroy()
        if not gui_valid():
            return
        from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation
        from hpc_gui.wx_ansys_view import show_ansys_lint

        show_ansys_lint(owner, AnsysToolPresentation(tool), lifecycle=lifecycle,
                        initial_documents=tuple((doc.path, doc.text) for doc in documents))

    def finish(documents, tools, results, error):
        try:
            if not gui_valid():
                return
            if error is not None:
                wx.MessageBox(str(error), t("ansyslint.title"), wx.OK | wx.ICON_ERROR, owner)
                return
            if tool_only:
                open_tool(documents, tools)
                return
            from hpc_gui.wx_lint_results import show_lint_results

            fix = (lambda: open_tool(documents, tools)) if tools else None
            show_lint_results(owner, t("ansyslint.title"), results, open_in_tool=fix)
        finally:
            try:
                owner.Unbind(wx.EVT_WINDOW_DESTROY, handler=destroyed)
            except RuntimeError:
                pass
            if getattr(owner, "_wx_file_lint_request", None) is request:
                owner._wx_file_lint_request = None

    def worker():
        try:
            catalog = load_catalog()
            docs = collect_documents(selection, catalog, files=files, current=valid, tool_only=tool_only)
            tools = catalog.common_tools(docs)
            results = None if tool_only else lint_documents(docs, catalog, current=valid)
            wx.CallAfter(finish, docs, tools, results, None)
        except FileLintCancelled:
            wx.CallAfter(finish, (), (), None, None)
        except Exception as exc:
            wx.CallAfter(finish, (), (), None, exc)

    Thread(target=worker, daemon=True).start()
    return True
