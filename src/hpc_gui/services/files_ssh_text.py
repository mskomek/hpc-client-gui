"""Text read/write methods for the SSH files backend."""
from __future__ import annotations
from .files_ssh_support import _translate_remote_errors


class SSHTextMixin:
    """Remote text access that keeps strict and display modes apart.

    The host class must provide self.ssh with sftp and open_transfer_sftp();
    the mixin holds no state of its own.
    """

    def read_text(self, remote_path: str) -> str:
        """Decode remote log/output text with replacement for display."""
        return self._read_text(remote_path, errors="replace")

    def read_text_for_edit(self, remote_path: str) -> str:
        """Read editable text strictly to prevent replacement-byte data loss."""
        return self._read_text(remote_path, errors="strict")

    def _read_text(self, remote_path: str, *, errors: str) -> str:
        with _translate_remote_errors(remote_path):
            sftp = self.ssh.open_transfer_sftp()
            try:
                with sftp.open(remote_path, "rb") as f:
                    data = f.read()
                return bytes(data).decode("utf-8", errors=errors)
            finally:
                sftp.close()

    def read_text_document(self, remote_path: str) -> tuple[str, str]:
        from hpc_gui.services.file_open import decode_text_with_encoding

        with _translate_remote_errors(remote_path):
            sftp = self.ssh.open_transfer_sftp()
            try:
                with sftp.open(remote_path, "rb") as source:
                    data = bytes(source.read())
                return decode_text_with_encoding(data, name=remote_path)
            finally:
                sftp.close()

    def write_text(self, remote_path: str, text: str) -> None:
        with self.ssh.sftp.open(remote_path, "wb") as f:
            f.write(text.encode("utf-8"))

    def write_text_document(self, remote_path: str, text: str, encoding: str) -> None:
        payload = text.encode(encoding)
        with self.ssh.sftp.open(remote_path, "wb") as target:
            target.write(payload)

