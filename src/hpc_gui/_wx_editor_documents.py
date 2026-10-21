"""Document/tab leaf for the wx editor.

Owns tab labels, tab strip sync, tab switching, reorder/close, and the
guarded async-safe document open path. Operates only on explicitly passed
model/widget/state handles; never imports the editor facade, find leaf,
or save leaf.
"""

from __future__ import annotations

from hpc_gui.services.editor_controller import DocumentModel, detect_newline
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.wx_editor_guards import _disk_baseline, editor_binary_guard_reason


def tab_label(doc, fallback_title: str):
    base = doc.path.rsplit("/", 1)[-1] if doc.path else fallback_title
    return f"{base} *" if getattr(doc, "dirty", False) else base


def note_disk_baseline(state: dict, doc) -> None:
    """Record the at-open disk state for external-change detection."""
    try:
        if doc is not None and getattr(doc, "is_local", False) and doc.path:
            state["disk_baseline"][doc.path] = _disk_baseline(doc.path)
    except Exception:
        pass


def refresh_tabs(doc_tabs, model, label_fallback: str) -> None:
    try:
        while doc_tabs.GetPageCount() < len(model.controller.documents):
            try:
                import wx
            except ImportError:
                return
            _p = wx.Panel(doc_tabs)
            doc_tabs.AddPage(_p, "")
        while doc_tabs.GetPageCount() > len(model.controller.documents):
            doc_tabs.DeletePage(doc_tabs.GetPageCount() - 1)
        for idx, doc in enumerate(model.controller.documents):
            if idx < doc_tabs.GetPageCount():
                doc_tabs.SetPageText(idx, tab_label(doc, label_fallback))
        try:
            doc_tabs.SetSelection(model.controller.active_index if 0 <= model.controller.active_index < doc_tabs.GetPageCount() else 0)
        except Exception:
            pass
    except Exception:
        pass


def on_tab_changed(event, model, editor, remote_path, doc_tabs, host) -> None:
    idx = event.GetSelection()
    if 0 <= idx < len(model.controller.documents):
        try:
            model.controller.active_index = idx
            doc = model.controller.active
            if doc is not None:
                editor.ChangeValue(doc.content)
                try:
                    remote_path.SetValue(doc.path)
                except Exception:
                    pass
                host.set_host_title(EditorCommandService.suggested_filename(doc.path or "untitled.sh"))
        except Exception:
            pass
    event.Skip()


def update_dirty_marker(doc_tabs, model, label_fallback: str) -> None:
    try:
        idx = model.controller.active_index
        if 0 <= idx < doc_tabs.GetPageCount() and idx < len(model.controller.documents):
            doc = model.controller.documents[idx]
            doc_tabs.SetPageText(idx, tab_label(doc, label_fallback))
    except Exception:
        pass


def reorder_tabs(model, doc_tabs, label_fallback: str, from_idx: int, to_idx: int) -> bool:
    try:
        docs = list(model.controller.documents)
        if 0 <= from_idx < len(docs) and 0 <= to_idx < len(docs):
            doc = docs.pop(from_idx)
            docs.insert(to_idx, doc)
            model.controller.documents = docs
            if model.controller.active_index == from_idx:
                model.controller.active_index = to_idx
            elif from_idx < model.controller.active_index <= to_idx:
                model.controller.active_index -= 1
            elif to_idx <= model.controller.active_index < from_idx:
                model.controller.active_index += 1
            refresh_tabs(doc_tabs, model, label_fallback)
            return True
    except Exception:
        pass
    return False


def begin_open_request(state: dict) -> int:
    """Allocate a monotonic open-request sequence."""
    try:
        state["open_seq"] = int(state.get("open_seq", 0)) + 1
        return int(state["open_seq"])
    except Exception:
        return 0


def load_document(model, editor, remote_path, doc_tabs, host, status, state, label_fallback: str, new_path, new_content, *, is_local=False, provider="", profile="", session_key="", encoding="utf-8", newline=None, version="", request_seq=None):
    from hpc_gui._wx_editor_find import set_find_status

    if request_seq is None:
        request_seq = begin_open_request(state)
    try:
        if int(request_seq) < int(state.get("open_seq", 0)):
            set_find_status(status, "editor.stale_open_ignored", "Ignored a stale editor-open request.")
            return "stale-ignored"
        state["open_applied"] = int(request_seq)
    except Exception:
        pass
    guard_reason = editor_binary_guard_reason(new_path, new_content)
    if guard_reason:
        try:
            status.SetLabel(guard_reason)
        except Exception:
            pass
        return "refused-binary"
    style = newline if newline in ("\n", "\r\n") else detect_newline(new_content)
    probe = DocumentModel(new_path, new_content, new_content, is_local, encoding, suggested_filename=EditorCommandService.suggested_filename(new_path), provider=provider, profile=profile, session_key=session_key, newline=style, version=version)
    for idx, doc in enumerate(model.controller.documents):
        if doc.canonical_key == probe.canonical_key and probe.canonical_key[4]:
            try:
                model.controller.active_index = idx
                editor.ChangeValue(doc.content)
                try:
                    remote_path.SetValue(doc.path)
                except Exception:
                    pass
                host.set_host_title(EditorCommandService.suggested_filename(doc.path or "untitled.sh"))
                note_disk_baseline(state, doc)
                refresh_tabs(doc_tabs, model, label_fallback)
            except Exception:
                pass
            return "activated"
    opened = probe
    model.controller.open(opened)
    note_disk_baseline(state, opened)
    editor.ChangeValue(new_content)
    try:
        state["binary_refused"] = False
        editor.SetEditable(True)
    except Exception:
        pass
    try:
        remote_path.SetValue(new_path)
    except Exception:
        pass
    host.set_host_title(EditorCommandService.suggested_filename(new_path or "untitled.sh"))
    refresh_tabs(doc_tabs, model, label_fallback)
    return "opened"


def close_tab(model, editor, remote_path, doc_tabs, host, label_fallback: str, index=None, *, force=False) -> bool:
    from hpc_gui.core.i18n import t

    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if len(model.controller.documents) <= 1 and not force:
        return False
    idx = int(index) if index is not None else int(model.controller.active_index)
    if not (0 <= idx < len(model.controller.documents)):
        return False
    doc = model.controller.documents[idx]
    if doc.dirty and not force:
        choice = wx.MessageBox(t("common.save_changes"), t("tabs.editor"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
        if choice == wx.CANCEL:
            return False
        if choice == wx.YES:
            try:
                docs = list(model.controller.documents)
                cur = docs[idx]
                docs[idx] = cur.mark_saved()
                model.controller.documents = docs
            except Exception:
                pass
    try:
        docs = list(model.controller.documents)
        docs.pop(idx)
        model.controller.documents = docs
        if model.controller.active_index >= len(docs):
            model.controller.active_index = max(0, len(docs) - 1)
        elif model.controller.active_index > idx:
            model.controller.active_index -= 1
        refresh_tabs(doc_tabs, model, label_fallback)
        active = model.controller.active
        if active is not None:
            editor.ChangeValue(active.content)
            try:
                remote_path.SetValue(active.path)
            except Exception:
                pass
            host.set_host_title(EditorCommandService.suggested_filename(active.path or "untitled.sh"))
        else:
            editor.Clear()
        return True
    except Exception:
        return False


__all__ = [
    "begin_open_request",
    "close_tab",
    "load_document",
    "note_disk_baseline",
    "on_tab_changed",
    "refresh_tabs",
    "reorder_tabs",
    "tab_label",
    "update_dirty_marker",
]
