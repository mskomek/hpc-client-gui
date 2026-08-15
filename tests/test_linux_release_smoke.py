from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import linux_release_smoke as smoke


def _ok_proc(returncode: int = 0, stdout: str = "", stderr: str = ""):
    proc = mock.Mock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class LinuxReleaseSmokeTest(unittest.TestCase):
    def test_missing_binary_returns_1(self) -> None:
        with mock.patch.object(smoke, "print"):
            self.assertEqual(smoke.main(["--binary", "does/not/exist"]), 1)

    def test_cli_surface_passes(self) -> None:
        # A fake binary file so the X_OK check passes, then subprocess is mocked.
        with mock.patch.object(smoke, "print"):
            with mock.patch.object(
                smoke.subprocess,
                "run",
                return_value=_ok_proc(stdout="hpc-client-gui 1.2.4\nconfig_dir=/tmp/x\n"),
            ) as run:
                with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
                    os, "access", return_value=True
                ):
                    self.assertEqual(smoke.main(["--binary", "/tmp/fake-bin"]), 0)
        labels = [c.args[0][1] for c in run.call_args_list if c.args and len(c.args[0]) > 1]
        self.assertIn("--help", labels)
        self.assertIn("version", labels)

    def test_nonzero_exit_fails(self) -> None:
        with mock.patch.object(smoke, "print"):
            with mock.patch.object(
                smoke.subprocess,
                "run",
                return_value=_ok_proc(returncode=3, stderr="boom"),
            ):
                with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
                    os, "access", return_value=True
                ):
                    self.assertEqual(smoke.main(["--binary", "/tmp/fail-bin"]), 1)

    def test_gui_waits_then_terminates(self) -> None:
        with mock.patch.object(smoke, "print"):
            proc = mock.Mock()
            proc.wait.side_effect = iter(
                [subprocess.TimeoutExpired(cmd=["gui"], timeout=20), None, None]
            )
            with mock.patch.object(smoke.subprocess, "Popen", return_value=proc) as popen:
                with mock.patch.object(
                    smoke.subprocess,
                    "run",
                    return_value=_ok_proc(stdout="hpc-client-gui 1.2.4\nconfig_dir=/tmp/x\n"),
                ):
                    with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
                        os, "access", return_value=True
                    ):
                        self.assertEqual(smoke.main(["--binary", "/tmp/gui-bin", "--gui"]), 0)
            popen.assert_called_once()
            proc.terminate.assert_called_once()
            proc.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
