import codecs
import unittest

from hpc_gui.ssh.client import SSHClientWrapper


class _PartialChannel:
    closed = False

    def __init__(self, chunk=1, zero_at=None):
        self.chunk = chunk
        self.zero_at = zero_at
        self.sent = bytearray()
        self.calls = 0

    def send(self, payload):
        self.calls += 1
        if self.zero_at == self.calls:
            return 0
        piece = payload[: self.chunk]
        self.sent.extend(piece)
        return len(piece)


def _wrapper(channel, output):
    wrapper = SSHClientWrapper(shell_output_cb=output.append)
    wrapper._shell_channel = channel
    return wrapper


class SshTerminalStreamTests(unittest.TestCase):
    def test_utf8_split_at_each_byte_boundary(self):
        value = "Türkçe 🐍 terminal"
        expected = value
        raw = value.encode("utf-8")
        for split in range(len(raw) + 1):
            output = []
            wrapper = SSHClientWrapper(shell_output_cb=output.append)
            wrapper._shell_decoder = codecs.getincrementaldecoder("utf-8")("replace")
            wrapper._decode_shell_bytes(raw[:split])
            wrapper._decode_shell_bytes(raw[split:], final=True)
            self.assertEqual("".join(output), expected)

    def test_partial_send_loops_until_complete(self):
        channel = _PartialChannel(chunk=2)
        wrapper = _wrapper(channel, [])
        self.assertTrue(wrapper.send_shell_input("çok uzun 🐍"))
        self.assertEqual(bytes(channel.sent), "çok uzun 🐍".encode("utf-8"))
        self.assertGreater(channel.calls, 1)

    def test_zero_send_is_failure_without_truncation_claim(self):
        channel = _PartialChannel(chunk=2, zero_at=2)
        wrapper = _wrapper(channel, [])
        self.assertFalse(wrapper.send_shell_input("abcdef"))
        self.assertEqual(bytes(channel.sent), b"ab")

    def test_large_ordered_output_burst_is_not_rewritten(self):
        output = []
        wrapper = SSHClientWrapper(shell_output_cb=output.append)
        chunks = [f"\x1b[32m{i}\x1b[0m\r\n" for i in range(20_000)]
        for chunk in chunks:
            wrapper._decode_shell_bytes(chunk.encode("utf-8"))
        self.assertEqual("".join(output), "".join(chunks))

    def test_resize_after_close_is_ignored(self):
        wrapper = SSHClientWrapper()
        wrapper._shell_channel = None
        wrapper.resize_shell_pty(0, 0)
        self.assertEqual(wrapper._shell_geometry, (1, 1))


if __name__ == "__main__":
    unittest.main()
