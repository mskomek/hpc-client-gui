"""Qt-free file backends shared by FTP and transfer tests."""

from pathlib import Path

from hpc_gui.services.files_base import RemoteEntry

__all__ = [
    "RemoteEntry",
    "_CountingFiles",
    "_Files",
    "_ProgressUploadFiles",
    "_ResumableFiles",
]


class _Files:
    def __init__(self) -> None:
        self.remote: dict[str, bytes] = {}

    def listdir_entries(self, _path: str):
        return [
            RemoteEntry(
                name=Path(path).name,
                path=path,
                is_dir=False,
                size=len(data),
                mtime=1,
            )
            for path, data in self.remote.items()
        ]

    def exists(self, path: str) -> bool:
        return path in self.remote

    def is_dir(self, _path: str) -> bool:
        return False

    def upload(self, local_path: str, remote_path: str) -> None:
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path: str, local_path: str) -> None:
        Path(local_path).write_bytes(self.remote[remote_path])

    def stat(self, remote_path: str):
        data = self.remote.get(remote_path, b"")
        return len(data), 1

    def rename(self, old_path: str, new_path: str) -> None:
        self.remote[new_path] = self.remote.pop(old_path, b"")


class _CountingFiles:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.dirs = {"/remote", "/remote/child"}
        self.entries = {
            "/remote": [
                RemoteEntry("child", "/remote/child", True, 0, 1),
                RemoteEntry("root.txt", "/remote/root.txt", False, 4, 1),
            ],
            "/remote/child": [
                RemoteEntry("nested.txt", "/remote/child/nested.txt", False, 6, 1),
            ],
        }

    def listdir_entries(self, path: str):
        key = (path or "/").rstrip("/") or "/"
        self.calls.append(key)
        return list(self.entries.get(key, []))

    def exists(self, path: str) -> bool:
        key = (path or "/").rstrip("/") or "/"
        return key in self.dirs

    def is_dir(self, path: str) -> bool:
        key = (path or "/").rstrip("/") or "/"
        return key in self.dirs


class _ResumableFiles:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.calls: list[str] = []

    def download(self, _remote_path: str, local_path: str, progress_cb=None) -> None:
        self.calls.append(local_path)
        existing = Path(local_path).read_bytes() if Path(local_path).exists() else b""
        Path(local_path).write_bytes(existing + self.data[len(existing):])
        if progress_cb is not None:
            progress_cb(len(self.data), len(self.data))


class _ProgressUploadFiles:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self.calls.append((local_path, remote_path))
        size = Path(local_path).stat().st_size
        if progress_cb is not None:
            progress_cb(size, size)
