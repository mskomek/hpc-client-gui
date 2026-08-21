"""Measure SFTP upload/download throughput on the local disposable mock server.

Wire-level companion to ``benchmark_sftp_listing.py``: this one exercises the
real transfer paths (``SSHFilesBackend.upload`` overwrite mode and
``download``) against the in-repo mock SSH/SFTP server, so Paramiko features
such as write pipelining can be compared before/after a production change.

Local synthetic numbers only; never presented as HPC or FileZilla performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

import paramiko  # noqa: E402

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _median_ms(values: list[float]) -> float:
    return round(statistics.median(values), 3)


def run(sizes_mib: list[int], repeats: int) -> dict:
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="truba_sftp_transfer_bench_") as tmp:
        root = Path(tmp)
        server = MockSSHServer(root)
        server.__enter__()
        ssh = SSHClientWrapper()
        try:
            ssh.connect(
                SSHConnInfo(
                    host="127.0.0.1",
                    port=server.port,
                    username=MOCK_USERNAME,
                    password=MOCK_PASSWORD,
                    host_key_policy="accept-new",
                    known_hosts_path=str(root / "known_hosts"),
                )
            )
            backend = SSHFilesBackend(ssh)
            workdir = root / "bench_src"
            workdir.mkdir()

            for size_mib in sizes_mib:
                source = workdir / f"payload_{size_mib}mib.bin"
                source.write_bytes(os.urandom(1 << 20) * size_mib)
                source_sha = _sha256_file(source)
                size_bytes = source.stat().st_size
                remote_path = f"/results/payload_{size_mib}mib.bin"
                download_target = workdir / f"download_{size_mib}mib.bin"

                upload_ms: list[float] = []
                download_ms: list[float] = []
                verified_bytes = 0
                for _ in range(repeats):
                    # Re-create the remote so every repeat measures a full
                    # overwrite upload instead of an equal-size no-op.
                    try:
                        backend.remove(remote_path)
                    except Exception:
                        pass
                    started = time.perf_counter()
                    backend.upload(str(source), remote_path)
                    upload_ms.append((time.perf_counter() - started) * 1000)

                    started = time.perf_counter()
                    backend.download(remote_path, str(download_target))
                    download_ms.append((time.perf_counter() - started) * 1000)

                    if _sha256_file(download_target) == source_sha:
                        verified_bytes += size_bytes

                results.append(
                    {
                        "size_mib": size_mib,
                        "bytes": size_bytes,
                        "upload_overwrite_ms": upload_ms,
                        "download_ms": download_ms,
                        "upload_overwrite_median_ms": _median_ms(upload_ms),
                        "download_median_ms": _median_ms(download_ms),
                        "verified_repeats": verified_bytes // size_bytes if size_bytes else 0,
                    }
                )
                download_target.unlink(missing_ok=True)
        finally:
            try:
                ssh.close()
            except Exception:
                pass
            server.__exit__()

    return {
        "schema": 1,
        "label": "synthetic-local-transfer",
        "description": (
            "SSHFilesBackend.upload (overwrite mode) and .download against the "
            "in-repo disposable mock SSH/SFTP server; excludes GUI and real network."
        ),
        "repeats": repeats,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "paramiko_version": paramiko.__version__,
        "measurements": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=str, default="1,32", help="comma separated MiB sizes")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    sizes = [int(part) for part in args.sizes.split(",") if part.strip()]
    if not sizes or any(size < 1 for size in sizes):
        parser.error("--sizes must be positive MiB integers")

    report = run(sizes, args.repeats)
    for measurement in report["measurements"]:
        print(
            f"{measurement['size_mib']:>4} MiB:"
            f" upload {measurement['upload_overwrite_median_ms']:.1f} ms,"
            f" download {measurement['download_median_ms']:.1f} ms"
            f" (medians of {args.repeats})"
        )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
