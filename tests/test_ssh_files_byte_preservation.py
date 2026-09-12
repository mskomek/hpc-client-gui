import io
from types import SimpleNamespace

import pytest

from hpc_gui.services.files_ssh import SSHFilesBackend


@pytest.mark.unit
@pytest.mark.regression
def test_sftp_download_upload_roundtrip_preserves_arbitrary_bytes(tmp_path):
    payload = b"\x00\xff\x80utf-8-looking\xc3\x28\n"
    remote_files = {"/remote/source.bin": payload}
    channels = []

    class RemoteFile(io.BytesIO):
        def __init__(self, data=b"", save=None):
            super().__init__(data)
            self._save = save

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is None and self._save is not None:
                self._save(self.getvalue())
            self.close()
            return False

    class SFTP:
        def __init__(self):
            self.closed = False

        def stat(self, path):
            if path not in remote_files:
                raise FileNotFoundError(path)
            return SimpleNamespace(st_size=len(remote_files[path]))

        def open(self, path, mode):
            if mode == "rb":
                return RemoteFile(remote_files[path])
            if mode == "wb":
                return RemoteFile(save=lambda data: remote_files.__setitem__(path, data))
            raise AssertionError(f"unexpected SFTP mode: {mode}")

        def close(self):
            self.closed = True

    class SSH:
        def open_transfer_sftp(self):
            channel = SFTP()
            channels.append(channel)
            return channel

    backend = SSHFilesBackend.__new__(SSHFilesBackend)
    backend.ssh = SSH()
    local_path = tmp_path / "roundtrip.bin"

    backend.download("/remote/source.bin", str(local_path))
    assert local_path.read_bytes() == payload

    backend.upload(str(local_path), "/remote/copy.bin")
    assert remote_files["/remote/copy.bin"] == payload
    assert all(channel.closed for channel in channels)
