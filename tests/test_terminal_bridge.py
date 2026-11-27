import unittest

import pytest

from hpc_gui.services.terminal_bridge import TerminalBridge


class _FakeSsh:
    def __init__(self):
        self.inputs = []
        self.sizes = []

    def send_shell_input(self, text):
        self.inputs.append(text)
        return True

    def resize_shell_pty(self, columns, rows):
        self.sizes.append((columns, rows))


@pytest.mark.unit
class TerminalBridgeTests(unittest.TestCase):
    def test_orders_events_and_detach_is_idempotent(self):
        ssh = _FakeSsh()
        output = []
        states = []
        bridge = TerminalBridge(on_output=output.append, on_state=states.append)

        bridge.attach(ssh)
        bridge.receive_output("one")
        bridge.send_input("two")
        bridge.resize(80, 24)
        bridge.detach()
        bridge.detach()
        bridge.send_input("ignored")

        self.assertEqual(output, ["one"])
        self.assertEqual(states, ["open", "closed"])
        self.assertEqual(ssh.inputs, ["two"])
        self.assertEqual(ssh.sizes, [(80, 24)])


    def test_readiness_errors_minimum_size_and_replacement(self):
        states, errors, ready = [], [], []
        bridge = TerminalBridge(
            on_state=states.append, on_error=errors.append, on_ready=lambda: ready.append(True),
        )
        ssh = _FakeSsh()
        bridge.attach(ssh)
        bridge.terminal_ready()
        bridge.resize(0, -1)
        self.assertEqual(ssh.sizes, [(1, 1)])
        ssh.send_shell_input = lambda _text: False
        bridge.send_input("input")
        self.assertEqual(errors, ["interactive shell unavailable"])

        def fail(*args):
            raise OSError("closed")

        ssh.resize_shell_pty = fail
        bridge.resize(80, 24)
        self.assertEqual(errors[-1], "closed")
        bridge.attach(_FakeSsh())
        bridge.detach()
        self.assertEqual(states, ["open", "closed", "open", "closed"])
        self.assertEqual(ready, [True])


if __name__ == "__main__":
    unittest.main()
