from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, QTimer, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget

from hpc_gui.services.terminal_bridge import TerminalBridge

class TerminalWidget(QWidget):
    ready = Signal()
    failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        try:
            from PySide6.QtWebChannel import QWebChannel
            from PySide6.QtWebEngineCore import QWebEnginePage
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError as exc:  # pragma: no cover - unsupported dev installs
            raise RuntimeError("Qt WebEngine is unavailable in this installation") from exc

        class LocalTerminalPage(QWebEnginePage):
            def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # type: ignore[override]
                del navigation_type
                return bool(url.isLocalFile() and is_main_frame)

        self.bridge = TerminalBridge(self)
        self.view = QWebEngineView(self)
        self.view.setPage(LocalTerminalPage(self.view))
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("terminal", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.loadFinished.connect(self._loaded)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._fit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.setUrl(QUrl.fromLocalFile(str(self._index_path())))

    @staticmethod
    def _index_path() -> Path:
        return Path(__file__).resolve().parents[2] / "assets" / "terminal" / "index.html"

    def _loaded(self, ok: bool) -> None:
        if not ok:
            self.failed.emit("terminal page failed to load")
            return
        self.ready.emit()
        self._fit()

    def _fit(self) -> None:
        self.view.page().runJavaScript("window.hpcFit && window.hpcFit();")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._resize_timer.start(50)

    @Slot()
    def focus_terminal(self) -> None:
        self.view.setFocus()
        self.view.page().runJavaScript("window.hpcFocus && window.hpcFocus();")

    def attach(self, ssh) -> None:
        self.bridge.attach(ssh)

    def detach(self) -> None:
        self.bridge.detach()

    def clear(self) -> None:
        self.view.page().runJavaScript("window.hpcClear && window.hpcClear();")
