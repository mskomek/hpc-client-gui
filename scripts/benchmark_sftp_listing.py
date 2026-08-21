"""Measure synthetic local SFTP directory-listing behavior.

The disposable Paramiko server is local and has no network or cluster access.
Results are evidence for regression comparison, not real-HPC performance claims.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer  # noqa: E402

from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402


def timed_listing(backend: SSHFilesBackend, path: str) -> tuple[float, float, int]:
    started = time.perf_counter()
    stream = backend.iterdir_entries(path)
    first_started = time.perf_counter()
    try:
        first = next(stream)
        first_ms = (time.perf_counter() - first_started) * 1000
        count = 1 + sum(1 for _ in stream)
    finally:
        stream.close()
    return (first_ms, (time.perf_counter() - started) * 1000, count)


def create_fixture(root: Path, size: int) -> str:
    directory = root / f"listing-{size}"
    directory.mkdir()
    (directory / "child").mkdir()
    (directory / "child" / "entry.dat").write_bytes(b"x")
    for index in range(max(0, size - 1)):
        (directory / f"entry-{index:05d}.dat").write_bytes(b"x")
    return f"/listing-{size}"


def run(repeats: int) -> dict:
    sizes = (100, 1000, 10000)
    with tempfile.TemporaryDirectory(prefix="hpc_client_sftp_benchmark_") as temp:
        root = Path(temp)
        paths = {size: create_fixture(root, size) for size in sizes}
        with MockSSHServer(root) as server:
            ssh = SSHClientWrapper()
            ssh.connect(SSHConnInfo(
                host="127.0.0.1", port=server.port, username=MOCK_USERNAME,
                password=MOCK_PASSWORD, host_key_policy="accept-new",
                known_hosts_path=str(root / "known_hosts"),
            ))
            try:
                backend = SSHFilesBackend(ssh)
                establishment = []
                for _ in range(repeats):
                    started = time.perf_counter()
                    channel = ssh.open_transfer_sftp()
                    establishment.append((time.perf_counter() - started) * 1000)
                    channel.close()

                measurements = []
                for size, path in paths.items():
                    cold = timed_listing(backend, path)
                    warm = [timed_listing(backend, path) for _ in range(repeats)]
                    child_path = path + "/child"
                    navigation = [timed_listing(backend, item) for item in (path, child_path, path)]
                    measurements.append({
                        "entries": size,
                        "cold": {"first_entry_ms": cold[0], "total_ms": cold[1], "count": cold[2]},
                        "warm": [{"first_entry_ms": row[0], "total_ms": row[1], "count": row[2]} for row in warm],
                        "parent_child_parent": [{"first_entry_ms": row[0], "total_ms": row[1], "count": row[2]} for row in navigation],
                    })
                return {
                    "schema": 2,
                    "label": "synthetic-local",
                    "description": "Local disposable Paramiko server; excludes GUI rendering and real network time.",
                    "repeats": repeats,
                    "repeat_count": repeats,
                    "python_version": platform.python_version(),
                    "platform": platform.platform(),
                    "paramiko_version": _package_version("paramiko"),
                    "channel_establishment_ms": establishment,
                    "measurements": measurements,
                }
            finally:
                ssh.close()


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def summary(report: dict) -> str:
    lines = ["Synthetic/local SFTP directory-listing benchmark", "(Paramiko wire, GUI rendering excluded)"]
    establish = statistics.median(report["channel_establishment_ms"])
    lines.append(f"channel establishment median: {establish:.2f} ms")
    for item in report["measurements"]:
        warm_total = statistics.median(row["total_ms"] for row in item["warm"])
        warm_first = statistics.median(row["first_entry_ms"] for row in item["warm"])
        lines.append(f"{item['entries']:>5} entries: warm first {warm_first:.2f} ms, warm total {warm_total:.2f} ms")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--json", type=Path, help="Write machine-readable results to this path")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    report = run(args.repeats)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(summary(report))
    if args.json:
        print(f"JSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
