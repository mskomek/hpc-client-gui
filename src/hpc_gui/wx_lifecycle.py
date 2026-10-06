"""wx lifecycle model for updates, splash, tray notifications, and shutdown."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Callable


@dataclass(frozen=True)
class UpdateProgress:
    percent: int = 0
    downloaded: int = 0
    total: int = 0
    phase: str = "idle"


class WxLifecycleController:
    # Bounded-shutdown budget (W55 PKGREG-SHUTDOWN-BISTABLE-NON-TERMINATION).
    # Each registered cleanup runs on a daemon thread with this join timeout
    # so one blocking network/native teardown cannot hold process exit.
    CLEANUP_TIMEOUT_S = 2.0

    def __init__(self, *, tray_notify: Callable[[str], None] | None = None) -> None:
        self.progress = UpdateProgress()
        self.cancel_token = Event()
        self.tray_notify = tray_notify
        self._notified_jobs: set[str] = set()
        self._cleanup: list[Callable[[], None]] = []
        self.splash_message = ""
        self.shutdown_started = False

    def set_splash(self, message: str) -> str:
        self.splash_message = str(message)
        return self.splash_message

    def begin_update(self, phase: str = "checking") -> None:
        self.cancel_token.clear()
        self.progress = UpdateProgress(0, 0, 0, phase)

    def update_progress(self, downloaded: int, total: int, phase: str = "downloading") -> UpdateProgress:
        total = max(0, int(total))
        downloaded = max(0, int(downloaded))
        percent = min(100, int(downloaded * 100 / total)) if total else 0
        self.progress = UpdateProgress(percent, downloaded, total, phase)
        return self.progress

    def cancel_update(self) -> None:
        self.cancel_token.set()
        self.progress = UpdateProgress(self.progress.percent, self.progress.downloaded, self.progress.total, "cancelled")

    def register_cleanup(self, cleanup: Callable[[], None]) -> None:
        self._cleanup.append(cleanup)

    def set_tray_notifier(self, notifier: Callable[[str], None] | None) -> None:
        self.tray_notify = notifier

    def notify_job(self, message: str, *, job_id: str | None = None) -> bool:
        if self.tray_notify is None:
            return False
        if job_id is not None and str(job_id) in self._notified_jobs:
            return False
        if job_id is not None:
            self._notified_jobs.add(str(job_id))
        self.tray_notify(str(message))
        return True

    def shutdown(self) -> None:
        if self.shutdown_started:
            return
        self.shutdown_started = True
        import threading

        for cleanup in reversed(self._cleanup):
            worker = threading.Thread(target=self._run_cleanup, args=(cleanup,), daemon=True)
            worker.start()
            worker.join(timeout=self.CLEANUP_TIMEOUT_S)
            # Daemon thread left running on timeout: never join again, never
            # block process termination on it.
        self._cleanup.clear()

    @staticmethod
    def _run_cleanup(cleanup: Callable[[], None]) -> None:
        try:
            cleanup()
        except Exception:
            pass


__all__ = ["UpdateProgress", "WxLifecycleController"]
