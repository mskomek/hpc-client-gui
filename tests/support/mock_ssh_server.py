"""A local, in-process SSH/SFTP server used only for offline integration
tests. Binds to 127.0.0.1 on an ephemeral port with a freshly generated,
never-persisted host key and a fixed, clearly-fake test account
(``mockuser`` / ``mockpass123``) — there is no real cluster, no real
credential, and no network egress involved anywhere in this module.

Exercises the exact same wire protocol (SSH exec + SFTP subsystem) that
``truba_gui.ssh.client.SSHClientWrapper`` speaks against a real host, so
tests using this server prove a real round trip rather than a mocked
service-layer stand-in.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import socket
import threading
import time
from pathlib import Path

import paramiko

MOCK_USERNAME = "mockuser"
MOCK_PASSWORD = "mockpass123"  # noqa: test-only fixture credential, not a real secret


class _MockShell:
    """Executes the exact small set of POSIX shell commands this project's
    SSH backend shells out to (``mkdir -p``, ``rm``, ``chmod``, ``sha256sum``,
    ``cp``, ``mv`` from ``truba_gui.services.files_ssh``; ``squeue``/``sbatch``/
    ``scancel``/``sacct``/``scontrol`` from ``truba_gui.services.slurm_ssh``)
    against a real, disposable local directory, plus canned Slurm text for the
    scheduler commands. Anything else is reported as unrecognized rather than
    guessed at."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _resolve(self, remote_path: str) -> Path:
        return self.root.joinpath(*remote_path.replace("\\", "/").lstrip("/").split("/"))

    def respond(self, command: str) -> tuple[int, str, str]:
        lowered = command.lower()
        if "squeue" in lowered:
            return 0, "JOBID PARTITION NAME USER ST TIME NODES\n12345 short mockjob mockuser R 0:05 1\n", ""
        if "sbatch" in lowered:
            return 0, "Submitted batch job 12345\n", ""
        if "scancel" in lowered:
            return 0, "", ""
        if "sacct" in lowered:
            return 0, "JobID JobName Partition Account AllocCPUS State ExitCode\n12345 mockjob short mock 1 COMPLETED 0:0\n", ""
        if "scontrol show job" in lowered or "scontrol" in lowered:
            return 0, "JobId=12345 JobName=mockjob JobState=RUNNING\n", ""
        if lowered.strip() == "command -v sha256sum":
            return 0, "/usr/bin/sha256sum\n", ""
        if lowered.strip() == "pwd":
            return 0, "/\n", ""
        if lowered.startswith("sh -c ") or lowered.startswith("bash -c "):
            try:
                parts = shlex.split(command)
                script = parts[2] if len(parts) > 2 else ""
                return self.respond(script)
            except ValueError as exc:
                return 1, "", str(exc)
        if lowered.startswith("echo "):
            return 0, command.strip()[5:] + "\n", ""
        if lowered.strip() == "lssrv":
            return 0, "mock-login-node: OK\n", ""

        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return 1, "", f"mock server: cannot parse command: {exc}"
        if not argv:
            return 1, "", "mock server: empty command"
        program, args = argv[0], argv[1:]
        try:
            if program == "mkdir":
                paths = [a for a in args if a != "-p"]
                for path in paths:
                    self._resolve(path).mkdir(parents=True, exist_ok=True)
                return 0, "", ""
            if program == "rm":
                recursive = "-r" in args or "-rf" in args or "-fr" in args
                paths = [a for a in args if not a.startswith("-")]
                for path in paths:
                    target = self._resolve(path)
                    if target.is_dir() and not target.is_symlink():
                        if recursive:
                            shutil.rmtree(target)
                        else:
                            target.rmdir()
                    elif target.exists():
                        target.unlink()
                return 0, "", ""
            if program == "chmod":
                mode_str, *paths = args
                for path in paths:
                    os.chmod(self._resolve(path), int(mode_str, 8))
                return 0, "", ""
            if program == "sha256sum":
                paths = [a for a in args if a != "--"]
                digests = []
                for path in paths:
                    digest = hashlib.sha256(self._resolve(path).read_bytes()).hexdigest()
                    digests.append(f"{digest}  {path}")
                return 0, "\n".join(digests) + "\n", ""
            if program == "cp":
                recursive = "-r" in args
                paths = [a for a in args if not a.startswith("-")]
                src, dst = paths[0], paths[1]
                src_real, dst_real = self._resolve(src), self._resolve(dst)
                if src_real.is_dir():
                    shutil.copytree(src_real, dst_real, dirs_exist_ok=True)
                else:
                    dst_real.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src_real, dst_real)
                return 0, "", ""
            if program == "mv":
                src, dst = args[0], args[1]
                src_real, dst_real = self._resolve(src), self._resolve(dst)
                dst_real.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_real), str(dst_real))
                return 0, "", ""
        except OSError as exc:
            return 1, "", str(exc)
        return 1, "", f"mock server: unrecognized command: {command}"


class _ServerInterface(paramiko.ServerInterface):
    def __init__(self, shell: _MockShell, username: str, password: str) -> None:
        self.event = threading.Event()
        self.shell = shell
        self.username = username
        self.password = password

    def check_channel_request(self, kind: str, chanid: int) -> int:
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username: str, password: str) -> int:
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        cmd = command.decode("utf-8", errors="replace")
        code, out, err = self.shell.respond(cmd)
        channel.send(out.encode("utf-8"))
        if err:
            channel.send_stderr(err.encode("utf-8"))
        channel.send_exit_status(code)
        threading.Thread(target=self._close_after, args=(channel,), daemon=True).start()
        return True

    @staticmethod
    def _close_after(channel: paramiko.Channel) -> None:
        time.sleep(0.2)
        try:
            channel.close()
        except Exception:
            pass

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        threading.Thread(target=self._shell_loop, args=(channel,), daemon=True).start()
        return True

    def check_channel_pty_request(
        self,
        channel: paramiko.Channel,
        term: bytes,
        width: int,
        height: int,
        pixelwidth: int,
        pixelheight: int,
        modes: bytes,
    ) -> bool:
        return True

    def check_channel_window_change_request(
        self,
        channel: paramiko.Channel,
        width: int,
        height: int,
        pixelwidth: int,
        pixelheight: int,
    ) -> bool:
        return True

    def _shell_loop(self, channel: paramiko.Channel) -> None:
        channel.send(b"virtual-truba$ ")
        buffer = b""
        while True:
            try:
                data = channel.recv(4096)
            except Exception:
                return
            if not data:
                return
            buffer += data
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                command = raw.decode("utf-8", errors="replace").strip()
                if not command:
                    channel.send(b"virtual-truba$ ")
                    continue
                code, output, error = self.shell.respond(command)
                if output:
                    channel.send(output.encode("utf-8"))
                if error:
                    channel.send_stderr(error.encode("utf-8"))
                if code:
                    channel.send(f"[exit={code}]\n".encode("utf-8"))
                channel.send(b"virtual-truba$ ")

    # Deliberately no check_channel_subsystem_request override: the base
    # ServerInterface implementation looks up the transport's subsystem
    # table (populated via Transport.set_subsystem_handler in
    # MockSSHServer._handle_client) and both instantiates *and starts* the
    # handler thread itself. An earlier version of this class overrode the
    # method to just re-register the handler and return True without ever
    # starting it, which silently orphaned the SFTP channel (client saw
    # "EOF during negotiation" immediately after the subsystem request was
    # accepted).


class _StubSFTPHandle(paramiko.SFTPHandle):
    def stat(self):
        return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))


class _StubSFTPServer(paramiko.SFTPServerInterface):
    """Backs SFTP requests onto a real local directory (the mock server's
    disposable root), so upload/download/list/stat/checksum all touch real
    files on disk rather than an in-memory stand-in."""

    ROOT: Path = Path(".")

    def _realpath(self, path: str) -> str:
        return str(self.ROOT / path.lstrip("/"))

    def list_folder(self, path):
        real = self._realpath(path)
        out = []
        for name in os.listdir(real):
            attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(real, name)))
            attr.filename = name
            out.append(attr)
        return out

    def stat(self, path):
        return paramiko.SFTPAttributes.from_stat(os.stat(self._realpath(path)))

    def lstat(self, path):
        return self.stat(path)

    def open(self, path, flags, attr):
        real = self._realpath(path)
        binary_flag = getattr(os, "O_BINARY", 0)
        mode = "ab+" if flags & os.O_APPEND else ("rb+" if flags & os.O_RDWR else ("wb+" if flags & (os.O_WRONLY | os.O_CREAT) else "rb"))
        os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
        fd = os.open(real, flags | binary_flag, 0o644) if (flags & os.O_CREAT) else os.open(real, flags | binary_flag)
        handle = _StubSFTPHandle(flags)
        handle.filename = real
        handle.readfile = os.fdopen(fd, mode)
        handle.writefile = handle.readfile
        return handle

    def remove(self, path):
        os.remove(self._realpath(path))
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        os.rename(self._realpath(oldpath), self._realpath(newpath))
        return paramiko.SFTP_OK

    def mkdir(self, path, attr):
        os.makedirs(self._realpath(path), exist_ok=True)
        return paramiko.SFTP_OK

    def rmdir(self, path):
        os.rmdir(self._realpath(path))
        return paramiko.SFTP_OK

    def canonicalize(self, path):
        return path if path.startswith("/") else "/" + path


class MockSSHServer:
    """Context-manager wrapper: start a local SSH+SFTP server backed by
    ``root_dir`` on ``127.0.0.1``:<ephemeral port>, stop it on exit."""

    def __init__(
        self,
        root_dir: Path,
        *,
        username: str = MOCK_USERNAME,
        password: str = MOCK_PASSWORD,
        port: int = 0,
    ) -> None:
        self.root_dir = root_dir
        self.username = username
        self.password = password
        self.listen_port = int(port)
        self._host_key = paramiko.RSAKey.generate(2048)
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.port = 0

    def __enter__(self) -> "MockSSHServer":
        _StubSFTPServer.ROOT = self.root_dir
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", self.listen_port))
        self._sock.listen(5)
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._thread.start()
        return self

    def _serve_forever(self) -> None:
        self._sock.settimeout(0.5)
        while not self._stop.is_set():
            try:
                client_sock, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()

    def _handle_client(self, client_sock: socket.socket) -> None:
        transport = paramiko.Transport(client_sock)
        transport.add_server_key(self._host_key)
        transport.set_subsystem_handler("sftp", paramiko.SFTPServer, _StubSFTPServer)
        server = _ServerInterface(
            _MockShell(self.root_dir),
            self.username,
            self.password,
        )
        try:
            transport.start_server(server=server)
            channel = transport.accept(20)
            if channel is None:
                return
            server.event.wait(20)
        except Exception:
            pass
        finally:
            try:
                transport.close()
            except Exception:
                pass

    def __exit__(self, *exc_info) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
