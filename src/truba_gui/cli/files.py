from __future__ import annotations

import hashlib
import os
import posixpath
import sys
from pathlib import Path
from typing import Callable

from truba_gui.services.transfer_mode import BINARY, normalize_transfer_mode, upload_with_mode, download_with_mode


def local_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def progress_callback(label: str, *, quiet: bool = False) -> Callable[[int, int], None] | None:
    if quiet:
        return None

    def report(done: int, total: int) -> None:
        if total > 0:
            percent = min(100, int(done * 100 / total))
            text = f"\r{label}: {percent:3d}% ({done}/{total} bytes)"
        else:
            text = f"\r{label}: {done} bytes"
        print(text, end="", file=sys.stderr, flush=True)
        if total > 0 and done >= total:
            print(file=sys.stderr)

    return report


def _remote_child(parent: str, name: str) -> str:
    return posixpath.join(parent.rstrip("/") or "/", name)


def _verify(files, local_path: str | Path, remote_path: str) -> None:
    remote_hash = getattr(files, "sha256", None)
    if not callable(remote_hash):
        raise RuntimeError("SHA-256 verification is not supported by this remote backend.")
    local_digest = local_sha256(local_path)
    remote_digest = str(remote_hash(remote_path) or "").strip().lower()
    if local_digest != remote_digest:
        raise RuntimeError(
            f"SHA-256 mismatch for {remote_path}: local={local_digest}, remote={remote_digest}"
        )


def upload(files, local_path: str, remote_path: str, *, recursive: bool, mode: str, verify: bool, quiet: bool) -> dict:
    source = Path(local_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(str(source))
    mode = normalize_transfer_mode(mode, BINARY)
    callback = progress_callback("upload", quiet=quiet)
    uploaded = 0
    if source.is_dir():
        if not recursive:
            raise IsADirectoryError(f"{source} is a directory; use --recursive")
        base = _remote_child(remote_path, source.name)
        files.mkdir(base)
        for root, dirs, names in os.walk(source):
            root_path = Path(root)
            relative = root_path.relative_to(source)
            remote_root = base if str(relative) == "." else _remote_child(base, relative.as_posix())
            for directory in dirs:
                files.mkdir(_remote_child(remote_root, directory))
            for name in names:
                local_file = root_path / name
                remote_file = _remote_child(remote_root, name)
                upload_with_mode(files, str(local_file), remote_file, mode, progress_cb=callback)
                if verify:
                    _verify(files, local_file, remote_file)
                uploaded += 1
        return {"operation": "upload", "source": str(source), "destination": base, "files": uploaded, "verified": verify}

    upload_with_mode(files, str(source), remote_path, mode, progress_cb=callback)
    if verify:
        _verify(files, source, remote_path)
    return {"operation": "upload", "source": str(source), "destination": remote_path, "files": 1, "verified": verify}


def download(files, remote_path: str, local_path: str, *, recursive: bool, mode: str, verify: bool, quiet: bool) -> dict:
    mode = normalize_transfer_mode(mode, BINARY)
    target = Path(local_path).expanduser()
    if files.is_dir(remote_path):
        if not recursive:
            raise IsADirectoryError(f"{remote_path} is a directory; use --recursive")
        base = target / posixpath.basename(remote_path.rstrip("/"))
        base.mkdir(parents=True, exist_ok=True)
        queue = [(remote_path.rstrip("/") or "/", base)]
        downloaded = 0
        while queue:
            remote_dir, local_dir = queue.pop(0)
            for entry in files.listdir_entries(remote_dir):
                remote_entry = entry.path
                local_entry = local_dir / entry.name
                if entry.is_dir:
                    local_entry.mkdir(parents=True, exist_ok=True)
                    queue.append((remote_entry, local_entry))
                else:
                    download_one(files, remote_entry, local_entry, mode, verify, quiet)
                    downloaded += 1
        return {"operation": "download", "source": remote_path, "destination": str(base), "files": downloaded, "verified": verify}

    download_one(files, remote_path, target, mode, verify, quiet)
    return {"operation": "download", "source": remote_path, "destination": str(target), "files": 1, "verified": verify}


def download_one(files, remote_path: str, local_path: Path, mode: str, verify: bool, quiet: bool) -> None:
    callback = progress_callback("download", quiet=quiet)
    download_with_mode(files, remote_path, str(local_path), mode, progress_cb=callback)
    if verify:
        _verify(files, local_path, remote_path)
