"""Local, offline release gate for the ``doctor smoke`` SFTP artifact path.

Standard library only. Two disposable, fully local gates plus one artifact
save: (1) a Turkish-filename transfer round trip through a local stand-in
backend, and (2) the real ``run_sftp_smoke`` stage matrix against an
in-memory stand-in. On success the ``sftp-smoke/1`` JSON report is placed as
``sftp-smoke.json`` under ``<release-root>/v<version>/`` with an
exclusive-create open so an existing file is never overwritten. No network,
socket, or subprocess call to any remote host happens anywhere in this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from hpc_gui.services.sftp_smoke import run_sftp_smoke

SCHEMA = "sftp-smoke/1"

TURKISH_FILENAME = "Dosya_İçerik_ÇÖĞÜŞ_çöğüş_ı_veri.bin"
TURKISH_PAYLOAD = (
    b"truba-local-transfer-gate\x00\x01\x02binary\x00payload|"
    + TURKISH_FILENAME.encode("utf-8")
) * 8


def remove_temp_root(temp_root: Path) -> None:
    """Remove a disposable temp root, retrying transient Windows handles."""
    last_error: OSError | None = None
    for _attempt in range(20):
        try:
            shutil.rmtree(temp_root)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"temporary cleanup failed for {temp_root}: {last_error}")


class _DiskBackend:
    """Local-filesystem stand-in exposing the same six-method contract as the
    real SFTP backend: ``mkdir``, ``upload``, ``listdir_entries``, ``download``,
    ``sha256``, and ``remove``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve(self, remote_path: str) -> Path:
        return self.root.joinpath(*remote_path.replace("\\", "/").split("/"))

    def mkdir(self, remote_dir: str) -> None:
        self._resolve(remote_dir).mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        dest = self._resolve(remote_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dest)

    def listdir_entries(self, remote_dir: str):
        directory = self._resolve(remote_dir)
        return [
            type(
                "Entry",
                (),
                {"name": item.name, "path": str(item), "is_dir": item.is_dir()},
            )()
            for item in sorted(directory.iterdir())
        ]

    def download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        Path(local_path).write_bytes(self._resolve(remote_path).read_bytes())

    def sha256(self, remote_path: str) -> str:
        return hashlib.sha256(self._resolve(remote_path).read_bytes()).hexdigest()

    def remove(self, remote_dir: str, recursive: bool = False) -> None:
        target = self._resolve(remote_dir)
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()


class _InMemoryBackend:
    """In-memory six-method stand-in used only by the ``run_sftp_smoke`` gate."""

    def __init__(self) -> None:
        self.remote: dict[str, bytes | None] = {}

    def mkdir(self, path: str) -> None:
        self.remote.setdefault(path, None)

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self.remote[remote_path] = Path(local_path).read_bytes()

    def listdir_entries(self, path: str):
        prefix = path.rstrip("/") + "/"
        return [
            type("Entry", (), {"name": key[len(prefix):]})()
            for key in self.remote
            if key.startswith(prefix) and "/" not in key[len(prefix):]
        ]

    def download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        Path(local_path).write_bytes(self.remote[remote_path])

    def sha256(self, path: str) -> str:
        return hashlib.sha256(self.remote.get(path, b"")).hexdigest()

    def remove(self, path: str, recursive: bool = False) -> None:
        prefix = path.rstrip("/") + "/"
        for key in [
            key
            for key in self.remote
            if key == path or (recursive and key.startswith(prefix))
        ]:
            self.remote.pop(key, None)


def run_turkish_round_trip() -> dict[str, object]:
    """Gate one: disposable Turkish-filename upload/list/download round trip.

    Every temporary path this gate creates is removed in a ``finally`` block
    regardless of the outcome. Returns a PASS/FAIL result dict.
    """
    temp_root: Path | None = None
    try:
        temp_root = Path(tempfile.mkdtemp(prefix="truba_gate_one_"))
        source_dir = temp_root / "source"
        download_dir = temp_root / "download"
        remote_root = temp_root / "remote"
        source_dir.mkdir()
        download_dir.mkdir()
        remote_root.mkdir()

        source_path = source_dir / TURKISH_FILENAME
        source_path.write_bytes(TURKISH_PAYLOAD)

        backend = _DiskBackend(remote_root)
        remote_dir = "truba_gate_one_remote"
        remote_path = f"{remote_dir}/{TURKISH_FILENAME}"
        backend.mkdir(remote_dir)
        backend.upload(str(source_path), remote_path)

        names = [getattr(entry, "name", "") for entry in backend.listdir_entries(remote_dir)]
        if TURKISH_FILENAME not in names:
            return {
                "status": "FAIL",
                "gate": "turkish_round_trip",
                "detail": f"Turkish filename not reported unchanged: {names}",
            }

        dest_path = download_dir / TURKISH_FILENAME
        backend.download(remote_path, str(dest_path))
        if dest_path.read_bytes() != TURKISH_PAYLOAD:
            return {
                "status": "FAIL",
                "gate": "turkish_round_trip",
                "detail": "downloaded bytes differ from source bytes",
            }
        return {
            "status": "PASS",
            "gate": "turkish_round_trip",
            "filename": TURKISH_FILENAME,
            "bytes_verified": len(TURKISH_PAYLOAD),
        }
    finally:
        if temp_root is not None:
            remove_temp_root(temp_root)


def run_sftp_smoke_gate(
    *,
    temp_dir_name=None,
    local_content: bytes = b"truba-sftp-smoke",
    cleanup: bool = True,
) -> dict[str, object]:
    """Gate two: run the real ``run_sftp_smoke`` matrix against an in-memory
    stand-in and return its report payload unchanged."""
    backend = _InMemoryBackend()
    return run_sftp_smoke(
        backend,
        temp_dir_name=temp_dir_name,
        local_content=local_content,
        cleanup=cleanup,
    )


def save_artifact(
    report: dict[str, object],
    *,
    release_root: str,
    version: str,
) -> Path:
    """Serialize ``report`` with the literal ``sftp-smoke/1`` schema field into
    ``<release-root>/v<version>/sftp-smoke.json`` using exclusive create.

    The target version directory must already exist; it is never created here,
    and a pre-existing artifact file at the target path is never overwritten.
    """
    version_dir = Path(release_root) / f"v{version}"
    if not version_dir.is_dir():
        raise FileNotFoundError(
            f"release version directory does not exist: {version_dir}"
        )
    target = version_dir / "sftp-smoke.json"
    if target.exists():
        raise FileExistsError(
            f"artifact already exists and will not be overwritten: {target}"
        )
    payload = dict(report)
    payload["schema"] = SCHEMA
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        raise FileExistsError(
            f"artifact already exists and will not be overwritten: {target}"
        )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local, offline release gate: a disposable Turkish-filename "
            "transfer round trip plus an in-memory sftp-smoke/1 artifact "
            "placement under the target release version directory."
        )
    )
    parser.add_argument("--version", required=True, help="target release version, e.g. 1.1.14")
    parser.add_argument(
        "--release-root",
        default="dist/releases",
        help="release root that already contains v<version> (default: dist/releases)",
    )
    args = parser.parse_args(argv)

    try:
        round_trip = run_turkish_round_trip()
        if round_trip.get("status") != "PASS":
            print(json.dumps(round_trip, ensure_ascii=False, indent=2), file=sys.stderr)
            print("LOCAL TRANSFER GATE: FAIL", flush=True)
            return 1

        report = run_sftp_smoke_gate()
        if report.get("status") != "PASS":
            print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
            print("LOCAL TRANSFER GATE: FAIL", flush=True)
            return 1

        save_artifact(report, release_root=args.release_root, version=args.version)
    except Exception as exc:
        print(
            json.dumps({"status": "FAIL", "error": repr(exc)}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        print("LOCAL TRANSFER GATE: FAIL", flush=True)
        return 1

    print("LOCAL TRANSFER GATE: PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
