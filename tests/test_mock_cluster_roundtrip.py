"""Wave 9 stand-in: proves the real CLI round-trips over an actual SSH/SFTP
wire connection, against a local, disposable, fully-fake mock server
(``tests/support/mock_ssh_server.py``) instead of a real TRUBA cluster.

No real host, account, or credential is used anywhere in this file. This
does not satisfy Wave 9's live-cluster manifest (which requires a real,
authorized, isolated cluster account) and is not a substitute for it — it is
a safe, fully local integration check that the CLI's actual network code
path (paramiko SSH + SFTP) works end to end, chosen instead of live-cluster
verification per explicit user direction.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


class MockClusterRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="truba_mock_cluster_")
        self.root_dir = Path(self._temp.name)
        self.server = MockSSHServer(self.root_dir)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.addCleanup(self._temp.cleanup)

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = {"PYTHONPATH": str(REPO_ROOT / "src")}
        import os

        env = {**os.environ, **env}
        cmd = [
            sys.executable,
            "-m",
            "truba_gui",
            "--format",
            "json",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.server.port),
            "--user",
            MOCK_USERNAME,
            "--password-stdin",
            *args,
        ]
        return subprocess.run(
            cmd,
            input=MOCK_PASSWORD + "\n",
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            timeout=30,
        )

    def test_files_round_trip_over_real_ssh_wire(self) -> None:
        local_source = self.root_dir.parent / "local_upload.txt"
        local_source.write_text("mock-cluster-round-trip-payload", encoding="utf-8")
        local_download = self.root_dir.parent / "local_download.txt"

        mkdir_proc = self._run_cli("files", "mkdir", "roundtrip")
        self.assertEqual(mkdir_proc.returncode, 0, mkdir_proc.stderr + mkdir_proc.stdout)

        upload_proc = self._run_cli(
            "files", "upload", str(local_source), "roundtrip/payload.txt", "--verify"
        )
        self.assertEqual(upload_proc.returncode, 0, upload_proc.stderr)

        ls_proc = self._run_cli("files", "ls", "roundtrip")
        self.assertEqual(ls_proc.returncode, 0, ls_proc.stderr)
        listing = json.loads(ls_proc.stdout)
        names = [entry.get("name") for entry in listing.get("result", listing) if isinstance(entry, dict)] if isinstance(listing, dict) else []
        self.assertTrue(any("payload.txt" in str(n) for n in names) or "payload.txt" in ls_proc.stdout)

        checksum_proc = self._run_cli("files", "checksum", "roundtrip/payload.txt")
        self.assertEqual(checksum_proc.returncode, 0, checksum_proc.stderr)

        download_proc = self._run_cli(
            "files", "download", "roundtrip/payload.txt", str(local_download), "--verify"
        )
        self.assertEqual(download_proc.returncode, 0, download_proc.stderr)
        self.assertEqual(local_download.read_text(encoding="utf-8"), "mock-cluster-round-trip-payload")

        rm_proc = self._run_cli("files", "rm", "roundtrip", "--recursive", "--yes")
        self.assertEqual(rm_proc.returncode, 0, rm_proc.stderr)

    def test_jobs_commands_round_trip_over_real_ssh_wire(self) -> None:
        list_proc = self._run_cli("jobs", "list")
        self.assertEqual(list_proc.returncode, 0, list_proc.stderr)

        lssrv_proc = self._run_cli("jobs", "lssrv")
        self.assertEqual(lssrv_proc.returncode, 0, lssrv_proc.stderr)

        accounting_proc = self._run_cli("jobs", "accounting")
        self.assertEqual(accounting_proc.returncode, 0, accounting_proc.stderr)

        cancel_proc = self._run_cli("jobs", "cancel", "12345", "--yes")
        self.assertEqual(cancel_proc.returncode, 0, cancel_proc.stderr)


if __name__ == "__main__":
    unittest.main()
