from __future__ import annotations

import os
import unittest
from unittest import mock

from hpc_gui.services import x11_runner
from hpc_gui.services.x11_runner import X11Runner
from hpc_gui.services import xserver_manager


def _runner() -> X11Runner:
    return X11Runner(log_cb=lambda msg: None)


class LinuxX11PreflightTest(unittest.TestCase):
    def test_linux_preflight_requires_ssh(self) -> None:
        with mock.patch.object(x11_runner, "_is_windows", return_value=False):
            with mock.patch.object(x11_runner.shutil, "which", return_value=None):
                with mock.patch.object(x11_runner, "ensure_x_server_running", return_value=True):
                    self.assertFalse(_runner().preflight(enabled=True))

    def test_linux_preflight_requires_display(self) -> None:
        with mock.patch.object(x11_runner, "_is_windows", return_value=False):
            with mock.patch.object(x11_runner.shutil, "which", return_value="/usr/bin/ssh"):
                with mock.patch.object(x11_runner, "ensure_x_server_running", return_value=False):
                    self.assertFalse(_runner().preflight(enabled=True))

    def test_linux_preflight_passes_with_ssh_and_display(self) -> None:
        with mock.patch.object(x11_runner, "_is_windows", return_value=False):
            with mock.patch.object(x11_runner.shutil, "which", return_value="/usr/bin/ssh"):
                with mock.patch.object(x11_runner, "ensure_x_server_running", return_value=True):
                    self.assertTrue(_runner().preflight(enabled=True))

    def test_disabled_preflight_passes_anyway(self) -> None:
        with mock.patch.object(x11_runner, "_is_windows", return_value=False):
            with mock.patch.object(x11_runner.shutil, "which", return_value=None):
                with mock.patch.object(x11_runner, "ensure_x_server_running", return_value=False):
                    self.assertTrue(_runner().preflight(enabled=False))


class LinuxXServerTest(unittest.TestCase):
    def test_ensure_x_server_returns_false_without_display(self) -> None:
        with mock.patch.object(xserver_manager, "_is_windows", return_value=False):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DISPLAY", None)
                self.assertFalse(xserver_manager.ensure_x_server_running(log=lambda m: None))

    def test_ensure_x_server_returns_true_with_display(self) -> None:
        with mock.patch.object(xserver_manager, "_is_windows", return_value=False):
            with mock.patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
                self.assertTrue(xserver_manager.ensure_x_server_running(log=lambda m: None))


if __name__ == "__main__":
    unittest.main()
