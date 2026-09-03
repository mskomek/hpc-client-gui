"""Ownership for reusable and standalone wx editor windows."""

from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_editor_view import show_editor


class WxEditorWindowManager:
    def __init__(self, parent=None, *, save_remote=None, on_submit=None, on_run=None, action_factory=None, lifecycle=None):
        self.parent = parent
        self.save_remote = save_remote
        self.on_submit = on_submit
        self.on_run = on_run
        self.action_factory = action_factory
        self.lifecycle = lifecycle
        self.primary_frame = None
        self.primary_model = None
        self.standalone_frames = set()
        self._primary_request_generation = 0
        self._pending_primary_request = None
        if lifecycle is not None:
            lifecycle.register_cleanup(self.close_all)

    def _callbacks(self):
        return {"save_remote": self.save_remote, "on_submit": self.on_submit, "on_run": self.on_run}

    def begin_primary_request(self):
        self._primary_request_generation += 1
        return self._primary_request_generation

    def _forget(self, frame):
        if frame is self.primary_frame:
            self.primary_frame = None
            self.primary_model = None
            self._pending_primary_request = None
        self.standalone_frames.discard(frame)

    def open_primary(self, path, content="", *, is_local=False, request_id=None):
        import wx

        frame = self.primary_frame
        request_id = self.begin_primary_request() if request_id is None else request_id
        if request_id < self._primary_request_generation:
            return frame
        self._primary_request_generation = request_id
        if frame is None or frame.IsBeingDeleted():
            model = WxEditorModel()
            frame = show_editor(self.parent, model=model, path=path, content=content, is_local=is_local, on_destroy=self._forget, action_factory=self.action_factory, **self._callbacks())
            self.primary_frame, self.primary_model = frame, model
            return frame
        active = self.primary_model.controller.active
        request = (request_id, str(path), content, is_local)
        if active and active.path == str(path) and active.dirty:
            return frame
        if frame._wx_editor_state["in_flight"]:
            self._pending_primary_request = request
            return frame
        if active and active.dirty:
            choice = wx.MessageBox(t("common.save_changes"), t("tabs.editor"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
            if choice == wx.CANCEL:
                return frame
            if choice == wx.YES:
                callbacks = self.action_factory(active) if self.action_factory else self._callbacks()
                if not (active.is_local and active.path) and not callbacks["save_remote"]:
                    frame._wx_editor_controls["status"].SetLabel(t("editor.action_requires_save"))
                    return frame
                self._pending_primary_request = request
                frame._wx_editor_save_for_replacement(lambda: self._finish_replacement(frame, request))
                return frame
        self._replace_primary(frame, path, content, is_local)
        return frame

    def _finish_replacement(self, frame, requested):
        pending = self._pending_primary_request
        self._pending_primary_request = None
        target = pending or requested
        if target[0] == self._primary_request_generation and frame is self.primary_frame and not frame._wx_editor_state["closed"]:
            self._replace_primary(frame, target[1], target[2], target[3])

    @staticmethod
    def _replace_primary(frame, path, content, is_local):
        frame._wx_editor_load_document(path, content, is_local=is_local)

    def open_new_window(self, path, content="", *, is_local=False):
        model = WxEditorModel()
        frame = show_editor(self.parent, model=model, path=path, content=content, is_local=is_local, on_destroy=self._forget, action_factory=self.action_factory, **self._callbacks())
        self.standalone_frames.add(frame)
        return frame

    def close_all(self):
        frames = [frame for frame in (self.primary_frame, *self.standalone_frames) if frame and not frame.IsBeingDeleted()]
        for frame in frames:
            frame.Destroy()
        self.primary_frame = None
        self.primary_model = None
        self.standalone_frames.clear()


__all__ = ["WxEditorWindowManager"]
