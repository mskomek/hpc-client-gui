"""Qt-independent worker task for bounded OpenFOAM scans."""

from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from hpc_gui.openfoam_core.cancellation import ScanCancelledError, raise_if_cancelled
from .rules import LintResult


class LintSignals(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)
    cancelled = Signal(int)


class LintTask(QRunnable):
    """Run local or SFTP lint without blocking the GUI thread."""

    def __init__(self, token: int, paths: tuple[str, ...], *, remote_files=None,
                 cancel_event: Event | None = None,
                 release: str = "v2312") -> None:
        super().__init__()
        self.token = token
        self.paths = paths
        self.remote_files = remote_files
        self.cancel_event = cancel_event or Event()
        self.release = release
        self.signals = LintSignals()

    @Slot()
    def run(self) -> None:
        try:
            raise_if_cancelled(self.cancel_event)
            if self.remote_files is None:
                from .api import lint_paths

                result = lint_paths(
                    self.paths, cancel_event=self.cancel_event,
                    release=self.release,
                )
            else:
                from .remote_case import lint_remote_path

                runs = [
                    lint_remote_path(
                        path, self.remote_files, cancel_event=self.cancel_event,
                        release=self.release,
                    )
                    for path in self.paths
                ]
                result = LintResult(
                    tuple(item for run in runs for item in run.diagnostics),
                    tuple(path for run in runs for path in run.files_checked),
                    version=self.release,
                )
            raise_if_cancelled(self.cancel_event)
        except ScanCancelledError:
            self.signals.cancelled.emit(self.token)
        except Exception as exc:  # UI receives a bounded error string, never a traceback.
            self.signals.failed.emit(self.token, f"{type(exc).__name__}: {exc}")
        else:
            self.signals.finished.emit(self.token, result)
