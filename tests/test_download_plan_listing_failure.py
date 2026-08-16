"""Regression test: a failed remote listing must not yield a silent empty plan.

Downloading a folder walks it with ``listdir_entries``. That call used to be
wrapped in a bare ``except Exception: entries = []``, so a listing failure
dropped every file from the plan without a word. The queue then ran only the
``mkdir_local`` ops and reported success while nothing was downloaded, which
is what "cancel, then it never really restarts" looked like from the UI.
"""

from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel


class _Worker:
    cancelled = False


class _Files:
    def __init__(self, *, fail: bool) -> None:
        self.fail = fail

    def is_dir(self, _path: str) -> bool:
        return True

    def listdir_entries(self, path: str):
        if self.fail:
            raise OSError("SFTP channel is not available")
        return [RemoteEntry("data.bin", f"{path}/data.bin", False, size=42, mtime=1)]


class DownloadPlanListingFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.panel = RemoteDirPanel()
        self.addCleanup(self.panel.deleteLater)
        self._temp = tempfile.TemporaryDirectory(prefix="truba_plan_")
        self.addCleanup(self._temp.cleanup)

    def _plan(self, files):
        return self.panel._build_remote_download_plan_background(
            _Worker(), files, ["/remote/results"], self._temp.name
        )

    def test_listing_failure_surfaces_instead_of_planning_only_mkdirs(self) -> None:
        with self.assertRaises(OSError):
            self._plan(_Files(fail=True))

    def test_successful_listing_still_plans_the_files(self) -> None:
        result = self._plan(_Files(fail=False))
        ops = [(op.op, op.src) for op in result["plan"]]
        self.assertIn(("mkdir_local", ""), [(op, src) for op, src in ops])
        self.assertIn(("download", "/remote/results/data.bin"), ops)


if __name__ == "__main__":
    unittest.main()
