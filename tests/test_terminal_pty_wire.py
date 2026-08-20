import tempfile
import time
import unittest
from pathlib import Path

from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo

from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer


class TerminalPtyWireTests(unittest.TestCase):
    def test_real_ssh_pty_and_resize_reach_disposable_server(self):
        with tempfile.TemporaryDirectory(prefix="terminal_pty_") as directory:
            root = Path(directory)
            with MockSSHServer(root) as server:
                ssh = SSHClientWrapper(
                    SSHConnInfo(
                        host="127.0.0.1",
                        port=server.port,
                        username=MOCK_USERNAME,
                        password=MOCK_PASSWORD,
                        known_hosts_path=str(root / "known_hosts"),
                    )
                )
                try:
                    ssh.connect(shell_size=(96, 31))
                    ssh.resize_shell_pty(123, 45)
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline and not server.resize_sizes:
                        time.sleep(0.01)
                    self.assertEqual(server.pty_sizes[-1][0:2], (96, 31))
                    self.assertEqual(server.pty_sizes[-1][4], "xterm-256color")
                    self.assertIn((123, 45, 0, 0), server.resize_sizes)
                finally:
                    ssh.close()


if __name__ == "__main__":
    unittest.main()
