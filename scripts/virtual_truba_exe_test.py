"""Disposable local TRUBA-like SSH/SFTP + FTP server for release EXE tests."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from support.mock_ssh_server import MockSSHServer  # noqa: E402

from hpc_gui.config.storage import (
    _config_path,
    set_cli_external_access_enabled,
    upsert_profile,
)  # noqa: E402
from hpc_gui.config.system_profile import GENERIC_SLURM_DEFAULTS  # noqa: E402
from hpc_gui.core.secret_store import protect_secret  # noqa: E402
from hpc_gui.services.files_ftp import FTPFilesBackend  # noqa: E402
from hpc_gui.services.files_ssh import SSHFilesBackend  # noqa: E402
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo  # noqa: E402


def start_ftp(root: Path, port: int) -> tuple[FTPServer, threading.Thread, int]:
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", str(root), perm="elradfmwMT")
    handler = type("VirtualTrubaFTPHandler", (FTPHandler,), {})
    handler.authorizer = authorizer
    handler.banner = "Virtual TRUBA FTP"
    server = FTPServer(("127.0.0.1", port), handler)
    actual_port = int(server.socket.getsockname()[1])
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"timeout": 0.1, "blocking": True, "handle_exit": False},
        daemon=True,
    )
    thread.start()
    return server, thread, actual_port


def save_test_profile(port: int) -> None:
    profile = {
        "name": "test",
        "host": "127.0.0.1",
        "port": port,
        "username": "test",
        "key_path": "",
        "host_key_policy": "accept-new",
        "x11_forwarding": False,
        "cli_allowed": True,
        "password_dpapi": protect_secret("test"),
        "system": dict(GENERIC_SLURM_DEFAULTS),
    }
    upsert_profile(profile)
    set_cli_external_access_enabled(True)


def run_exe(exe: Path, args: list[str]) -> None:
    command = [str(exe), "--format", "json", "--profile", "test", *args]
    result = subprocess.run(
        command,
        cwd=exe.parent,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    if result.returncode:
        raise RuntimeError(
            f"EXE failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    print(f"PASS EXE: {' '.join(args)}")


def run_ftp(ftp_port: int, root: Path) -> None:
    source = root / "ftp-source.txt"
    target = root / "ftp-download.txt"
    source.write_text("virtual-truba-ftp-test: çğıİöşü\n", encoding="utf-8")
    backend = FTPFilesBackend(
        "127.0.0.1", port=ftp_port, username="test", password="test"
    )
    try:
        backend.mkdir("/scratch")
        backend.upload(str(source), "/scratch/ftp-source.txt")
        assert any(item.name == "ftp-source.txt" for item in backend.listdir_entries("/scratch"))
        backend.download("/scratch/ftp-source.txt", str(target))
        assert target.read_bytes() == source.read_bytes()
    finally:
        backend.close()
    print("PASS FTP: upload/list/download byte-for-byte")


def run_terminal(ssh_port: int) -> None:
    output: list[str] = []
    client = SSHClientWrapper(
        SSHConnInfo(
            host="127.0.0.1",
            port=ssh_port,
            username="test",
            password="test",
            host_key_policy="accept-new",
        ),
        shell_output_cb=output.append,
    )
    try:
        client.connect(shell_size=(80, 24))
        assert client.send_shell_text("sh -c 'echo virtual-shell-ok'")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and "virtual-shell-ok" not in "".join(output):
            time.sleep(0.05)
        assert "virtual-shell-ok" in "".join(output)
    finally:
        client.close()
    print("PASS terminal: interactive sh command")


def run_remote_edit(ssh_port: int) -> None:
    client = SSHClientWrapper(
        SSHConnInfo(
            host="127.0.0.1",
            port=ssh_port,
            username="test",
            password="test",
            host_key_policy="accept-new",
        )
    )
    try:
        client.connect()
        files = SSHFilesBackend(client)
        files.write_text("/roundtrip/edited.txt", "before\n")
        assert files.read_text("/roundtrip/edited.txt") == "before\n"
        files.write_text("/roundtrip/edited.txt", "after\n")
        assert files.read_text("/roundtrip/edited.txt") == "after\n"
    finally:
        client.close()
    print("PASS remote edit: SFTP read/write/read")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--ssh-port", type=int, default=22222)
    parser.add_argument("--ftp-port", type=int, default=2121)
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument("--preserve-profile", action="store_true")
    args = parser.parse_args()
    exe = args.exe.resolve()
    if not exe.is_file():
        raise SystemExit(f"EXE not found: {exe}")

    config_path = _config_path()
    original_config = config_path.read_bytes() if config_path.exists() else None
    preserve = args.preserve_profile or args.keep_alive
    try:
        with tempfile.TemporaryDirectory(prefix="virtual_truba_") as temp:
            root = Path(temp)
            ssh_root = root / "ssh"
            ftp_root = root / "ftp"
            ssh_root.mkdir()
            ftp_root.mkdir()
            ftp_server, ftp_thread, ftp_port = start_ftp(ftp_root, args.ftp_port)
            with MockSSHServer(
                ssh_root, username="test", password="test", port=args.ssh_port
            ) as ssh_server:
                save_test_profile(ssh_server.port)
                for command in (
                ["doctor", "connection"],
                ["doctor", "smoke"],
                ["files", "ls", "/"],
                ["files", "mkdir", "/roundtrip"],
                ["files", "upload", str(exe.parent / "help" / "CLI_GUIDE_en.md"), "/roundtrip/guide.md", "--verify"],
                ["files", "stat", "/roundtrip/guide.md"],
                ["files", "checksum", "/roundtrip/guide.md"],
                ["files", "download", "/roundtrip/guide.md", str(root / "guide-copy.md"), "--verify"],
                ["files", "cp", "/roundtrip/guide.md", "/roundtrip/guide-copy-remote.md"],
                ["files", "mv", "/roundtrip/guide-copy-remote.md", "/roundtrip/guide-moved.md"],
                ["files", "rm", "/roundtrip/guide-moved.md", "--yes"],
                ["jobs", "list"],
                ["jobs", "status", "12345"],
                ["jobs", "accounting"],
                ["jobs", "lssrv"],
                ["jobs", "submit", str(exe.parent / "help" / "CLI_GUIDE_en.md"), "--yes"],
                ["jobs", "cancel", "12345", "--yes"],
                ):
                    run_exe(exe, command)
                run_remote_edit(ssh_server.port)
                run_terminal(ssh_server.port)
                run_ftp(ftp_port, root)
                print(json.dumps({"status": "PASS", "ssh_port": ssh_server.port, "ftp_port": ftp_port}))
                if args.keep_alive:
                    print("Virtual TRUBA running. Press Ctrl+C to stop.", flush=True)
                    while True:
                        time.sleep(1)
            ftp_server.close_all()
            ftp_thread.join(timeout=5)
    finally:
        if not preserve:
            if original_config is None:
                config_path.unlink(missing_ok=True)
            else:
                config_path.write_bytes(original_config)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
