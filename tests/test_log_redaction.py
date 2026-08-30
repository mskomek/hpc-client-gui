import unittest
from unittest.mock import patch

from hpc_gui.core.log_redaction import redact_command_args, redact_text


class LogRedactionTests(unittest.TestCase):
    def test_redacts_local_and_remote_usernames_and_hosts(self) -> None:
        with patch("getpass.getuser", return_value="mkomek"), patch(
            "hpc_gui.config.storage.load_profiles",
            return_value=[{"username": "mkomek", "host": "arf.truba.gov.tr"}],
        ):
            text = (
                r"C:\Users\mkomek\AppData\Local\app.log"
                " /arf/scratch/mkomek/predataset/DP_53.jou"
                " connecting to arf.truba.gov.tr as mkomek"
            )
            out = redact_text(text)

        self.assertNotIn("mkomek", out)
        self.assertNotIn("arf.truba.gov.tr", out)
        self.assertIn("<user>", out)
        self.assertIn("<host>", out)
        # Redaction must not touch unrelated filenames.
        self.assertIn("DP_53.jou", out)

    def test_empty_text_and_no_secrets_are_noops(self) -> None:
        with patch("getpass.getuser", side_effect=Exception("no user")), patch(
            "hpc_gui.config.storage.load_profiles", return_value=[]
        ):
            self.assertEqual(redact_text(""), "")
            self.assertEqual(redact_text("hello world"), "hello world")

    def test_does_not_partially_redact_overlapping_usernames(self) -> None:
        with patch("getpass.getuser", return_value="user"), patch(
            "hpc_gui.config.storage.load_profiles",
            return_value=[{"username": "user2", "host": ""}],
        ):
            out = redact_text("path/user2/file and path/user/file")

        self.assertNotIn("user2", out)
        self.assertIn("<user>/file and path/<user>/file", out)

    def test_redacts_credential_forms(self) -> None:
        text = redact_text(
            "Authorization: Bearer abc.def.ghi\n"
            "https://user:secret@example.com/\n"
            "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
        )
        self.assertNotIn("abc.def.ghi", text)
        self.assertNotIn("user:secret", text)
        self.assertNotIn("\nsecret\n", text)

    def test_redacts_plink_argv_without_mutating_launch_args(self) -> None:
        args = ["-ssh", "-pw", "fake-password", "user@example.com"]
        self.assertEqual(redact_command_args(args)[2], "<redacted>")
        self.assertEqual(args[2], "fake-password")


if __name__ == "__main__":
    unittest.main()
