"""Keep selected two-pane splitters at a saved proportion across resizes."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QSplitter

from hpc_gui.config.storage import load_settings, update_settings


def _valid_ratio(value: object, default: float = 0.5) -> float:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return default
    return ratio if 0.05 <= ratio <= 0.95 else default


def _initial_ratio(key: str, settings: dict) -> float:
    ratios = settings.get("splitter_ratios")
    if isinstance(ratios, dict) and key in ratios:
        return _valid_ratio(ratios[key])
    if key == "files_local_remote":
        legacy_sizes = settings.get("ftp_splitter_sizes")
        if isinstance(legacy_sizes, list) and len(legacy_sizes) == 2:
            try:
                sizes = [max(0, int(value)) for value in legacy_sizes]
                total = sum(sizes)
                if total:
                    return _valid_ratio(sizes[0] / total)
            except (TypeError, ValueError):
                pass
    return 0.5


class SplitterRatioKeeper(QObject):
    """Apply a two-pane ratio on resize and save only deliberate user moves."""

    def __init__(self, splitter: QSplitter, key: str, ratio: float):
        super().__init__(splitter)
        self.splitter = splitter
        self.key = key
        self.ratio = ratio
        self._apply_pending = False
        self._user_interaction = False
        self._user_moved = False
        splitter.installEventFilter(self)
        splitter.splitterMoved.connect(self._on_splitter_moved)
        handle = splitter.handle(1)
        if handle is not None:
            handle.installEventFilter(self)
        self._schedule_apply()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        event_type = event.type()
        if watched is self.splitter:
            if event_type in (QEvent.Type.Resize, QEvent.Type.Show):
                self._schedule_apply()
            return False

        if event_type == QEvent.Type.MouseButtonPress:
            if getattr(event, "button", lambda: None)() == Qt.MouseButton.LeftButton:
                self._begin_interaction()
        elif event_type == QEvent.Type.MouseButtonRelease and self._user_interaction:
            QTimer.singleShot(0, self._finish_interaction)
        elif event_type == QEvent.Type.KeyPress:
            self._begin_interaction()
            QTimer.singleShot(0, self._finish_interaction)
        return False

    def _begin_interaction(self) -> None:
        self._user_interaction = True
        self._user_moved = False

    def _finish_interaction(self) -> None:
        if self._user_moved:
            self._capture_ratio()
            settings = load_settings()
            ratios = settings.get("splitter_ratios")
            ratios = dict(ratios) if isinstance(ratios, dict) else {}
            ratios[self.key] = round(self.ratio, 6)
            update_settings({"splitter_ratios": ratios})
        self._user_interaction = False
        self._user_moved = False

    def _on_splitter_moved(self, _position: int, _index: int) -> None:
        if self._user_interaction:
            self._user_moved = True
            self._capture_ratio()

    def _capture_ratio(self) -> None:
        sizes = self.splitter.sizes()
        total = sum(sizes)
        if total > 0 and len(sizes) == 2:
            self.ratio = _valid_ratio(sizes[0] / total, self.ratio)

    def _schedule_apply(self) -> None:
        if self._apply_pending:
            return
        self._apply_pending = True
        QTimer.singleShot(0, self._apply_ratio)

    def _apply_ratio(self) -> None:
        self._apply_pending = False
        if not self.splitter.isVisible():
            return
        sizes = self.splitter.sizes()
        total = sum(sizes)
        if total <= 1:
            total = self.splitter.width() - self.splitter.handleWidth()
        if total <= 1:
            return
        first = max(1, min(total - 1, round(total * self.ratio)))
        desired = [first, total - first]
        if sizes == desired:
            return
        signals_were_blocked = self.splitter.blockSignals(True)
        try:
            self.splitter.setSizes(desired)
        finally:
            self.splitter.blockSignals(signals_were_blocked)


def install_main_browser_splitter_ratios(window) -> None:
    """Center Directories and Files panes unless the user saved another ratio."""
    settings = load_settings()
    splitters = (
        (window.directories.splitter, "directories_remote_panels"),
        (window.ftp.splitter, "files_local_remote"),
    )
    keepers = []
    for splitter, key in splitters:
        keeper = SplitterRatioKeeper(splitter, key, _initial_ratio(key, settings))
        keepers.append(keeper)
    window._browser_splitter_ratio_keepers = keepers
