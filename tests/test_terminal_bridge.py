import unittest

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


class TerminalBridgeTests(unittest.TestCase):
    def test_orders_events_and_detach_is_idempotent(self):
        bridge = TerminalBridge()
        ssh = _FakeSsh()
        output = []
        states = []
        bridge.output.connect(output.append)
        bridge.state_changed.connect(states.append)

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


if __name__ == "__main__":
    unittest.main()
