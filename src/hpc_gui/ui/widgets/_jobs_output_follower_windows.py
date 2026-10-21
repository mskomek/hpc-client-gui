from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QMainWindow

from ._jobs_output_follower_views import _OutputFollowerWidget


class _SingleFileFollowerWidget(_OutputFollowerWidget):
    """Dedicated one-file follower used by the generic new-window action."""

    def __init__(self, remote_path: str):
        super().__init__()
        self._single_slot_mode = True
        # This is the address bar shown in the standalone "Follow: file"
        # window. Keep its editable contract explicit even if the shared
        # two-slot follower changes later.
        self.path_out.setReadOnly(False)
        self.open_in_output_slot(0, remote_path)
        self.err_box.hide()
        self.out_box.setTitle(remote_path.rstrip("/").rsplit("/", 1)[-1] or remote_path)


class _FollowerWindow(QMainWindow):
    """Top-level follower window that propagates minimize/restore state."""

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            follower = self.centralWidget()
            if isinstance(follower, _OutputFollowerWidget):
                follower.set_window_minimized(self.isMinimized())
