from __future__ import annotations

import hashlib
import os
import posixpath
import sys
from pathlib import Path
from typing import Callable

from truba_gui.services.transfer_mode import BINARY, normalize_transfer_mode, upload_with_mode, download_with_mode


IF_EXISTS_CHOICES = ("overwrite", "skip", "rename", "resume")


def normalize_if_exists(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in IF_EXISTS_CHOICES else "overwrite"


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


def _unique_destination(exists_fn: Callable[[str], bool], base: str) -> str:
    if "/" in base:
        directory = posixpath.dirname(base)
        stem, suffix = posixpath.splitext(posixpath.basename(base))

        def join(name: str) -> str:
            return posixpath.join(directory, name)
    else:
        path = Path(base)
        directory = path.parent
        stem, suffix = path.stem, path.suffix

        def join(name: str) -> str:
            return str(directory / name)

    if not exists_fn(base):
        return base
    index = 1
    while True:
        if index > 10000:
            raise RuntimeError(f"no free destination path found for {base}")
        candidate = join(f"{stem} ({index}){suffix}")
        if not exists_fn(candidate):
            return candidate
        index += 1


def upload(files, local_path: str, remote_path: str, *, recursive: bool, mode: str, verify: bool, quiet: bool, if_exists: str = "overwrite") -> dict:
    source = Path(local_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(str(source))
    mode = normalize_transfer_mode(mode, BINARY)
    policy = normalize_if_exists(if_exists)
    callback = progress_callback("upload", quiet=quiet)
    uploaded = 0
    skipped = 0
    renames: list[dict[str, str]] = []
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
                if policy == "skip" and files.exists(remote_file):
                    skipped += 1
                    continue
                if policy == "rename" and files.exists(remote_file):
                    effective = _unique_destination(files.exists, remote_file)
                    renames.append({"from": remote_file, "to": effective})
                    upload_with_mode(files, str(local_file), effective, mode, progress_cb=callback)
                    if verify:
                        _verify(files, local_file, effective)
                    uploaded += 1
                    continue
                if policy == "overwrite" and files.exists(remote_file):
                    files.remove(remote_file)
                upload_with_mode(files, str(local_file), remote_file, mode, progress_cb=callback)
                if verify:
                    _verify(files, local_file, remote_file)
                uploaded += 1
        payload: dict = {
            "operation": "upload",
            "source": str(source),
            "destination": base,
            "files": uploaded,
            "verified": verify,
            "policy": policy,
        }
        if skipped:
            payload["skipped"] = skipped
        if renames:
            payload["renames"] = renames
        return payload

    if policy == "skip" and files.exists(remote_path):
        return {
            "operation": "upload",
            "source": str(source),
            "destination": remote_path,
            "files": 0,
            "verified": verify,
            "policy": policy,
            "skipped": 1,
        }
    if policy == "rename" and files.exists(remote_path):
        effective = _unique_destination(files.exists, remote_path)
        renames.append({"from": remote_path, "to": effective})
        upload_with_mode(files, str(source), effective, mode, progress_cb=callback)
        if verify:
            _verify(files, source, effective)
        return {
            "operation": "upload",
            "source": str(source),
            "destination": remote_path,
            "files": 1,
            "verified": verify,
            "policy": policy,
            "renames": renames,
        }
    if policy == "overwrite" and files.exists(remote_path):
        files.remove(remote_path)
    upload_with_mode(files, str(source), remote_path, mode, progress_cb=callback)
    if verify:
        _verify(files, source, remote_path)
    return {
        "operation": "upload",
        "source": str(source),
        "destination": remote_path,
        "files": 1,
        "verified": verify,
        "policy": policy,
    }


def download(files, remote_path: str, local_path: str, *, recursive: bool, mode: str, verify: bool, quiet: bool, if_exists: str = "overwrite") -> dict:
    mode = normalize_transfer_mode(mode, BINARY)
    policy = normalize_if_exists(if_exists)
    target = Path(local_path).expanduser()
    if files.is_dir(remote_path):
        if not recursive:
            raise IsADirectoryError(f"{remote_path} is a directory; use --recursive")
        base = target / posixpath.basename(remote_path.rstrip("/"))
        base.mkdir(parents=True, exist_ok=True)
        queue = [(remote_path.rstrip("/") or "/", base)]
        downloaded = 0
        skipped = 0
        renames: list[dict[str, str]] = []
        while queue:
            remote_dir, local_dir = queue.pop(0)
            for entry in files.listdir_entries(remote_dir):
                remote_entry = entry.path
                local_entry = local_dir / entry.name
                if entry.is_dir:
                    local_entry.mkdir(parents=True, exist_ok=True)
                    queue.append((remote_entry, local_entry))
                else:
                    if policy == "skip" and local_entry.exists():
                        skipped += 1
                        continue
                    if policy == "rename" and local_entry.exists():
                        effective = _unique_destination(lambda candidate: Path(candidate).exists(), str(local_entry))
                        renames.append({"from": str(local_entry), "to": effective})
                        download_one(files, remote_entry, Path(effective), mode, verify, quiet)
                        downloaded += 1
                        continue
                    if policy == "overwrite" and local_entry.exists():
                        local_entry.unlink()
                    download_one(files, remote_entry, local_entry, mode, verify, quiet)
                    downloaded += 1
        payload: dict = {
            "operation": "download",
            "source": remote_path,
            "destination": str(base),
            "files": downloaded,
            "verified": verify,
            "policy": policy,
        }
        if skipped:
            payload["skipped"] = skipped
        if renames:
            payload["renames"] = renames
        return payload

    if policy == "skip" and target.exists():
        return {
            "operation": "download",
            "source": remote_path,
            "destination": str(target),
            "files": 0,
            "verified": verify,
            "policy": policy,
            "skipped": 1,
        }
    if policy == "rename" and target.exists():
        effective = _unique_destination(lambda candidate: Path(candidate).exists(), str(target))
        download_one(files, remote_path, Path(effective), mode, verify, quiet)
        return {
            "operation": "download",
            "source": remote_path,
            "destination": str(target),
            "files": 1,
            "verified": verify,
            "policy": policy,
            "renames": [{"from": str(target), "to": effective}],
        }
    if policy == "overwrite" and target.exists():
        target.unlink()
    download_one(files, remote_path, target, mode, verify, quiet)
    return {
        "operation": "download",
        "source": remote_path,
        "destination": str(target),
        "files": 1,
        "verified": verify,
        "policy": policy,
    }


def download_one(files, remote_path: str, local_path: Path, mode: str, verify: bool, quiet: bool) -> None:
    callback = progress_callback("download", quiet=quiet)
    download_with_mode(files, remote_path, str(local_path), mode, progress_cb=callback)
    if verify:
        _verify(files, local_path, remote_path)
