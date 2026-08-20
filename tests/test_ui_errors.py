import socket
import unittest

import paramiko

from hpc_gui.core.i18n import load_language, t
from hpc_gui.core.ui_errors import describe_connection_error


class UiErrorTests(unittest.TestCase):
    def tearDown(self):
        load_language("tr")

    def test_error_code_label_is_translated(self):
        load_language("tr")
        self.assertEqual(t("common.error_code"), "Tanı kodu")

    def test_common_connection_failures_are_actionable(self):
        load_language("tr")
        cases = (
            (paramiko.AuthenticationException("Authentication failed"), "Kimlik doğrulama"),
            (socket.gaierror("Name not known"), "Sunucu adı"),
            (ConnectionRefusedError("refused"), "bağlantıyı reddetti"),
            (TimeoutError("timed out"), "zamanında yanıt vermedi"),
            (paramiko.SSHException("Error reading SSH protocol banner"), "karşılama bilgisini"),
        )
        for exc, expected in cases:
            with self.subTest(exc=type(exc).__name__):
                message = describe_connection_error(exc)
                self.assertIn(expected, message)
                self.assertIn("Teknik ayrıntı", message)


if __name__ == "__main__":
    unittest.main()
