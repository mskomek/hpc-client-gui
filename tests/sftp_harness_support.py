"""In-process SFTP server harness for the W65 remote-file tests.

Each serve() call binds an ephemeral loopback port and serves the directory
named by the W65_SFTP_ROOT environment variable through the paramiko SFTP
subsystem, so tests drive the shipped SSHFilesBackend client code over a real
protocol instead of a mock.
"""
from __future__ import annotations

import os
import errno
import shlex
import shutil
import socket
import threading
import time
from contextlib import contextmanager

import hashlib
import paramiko

from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.ssh.client import SSHClientWrapper

USERNAME = "user"
PASSWORD = "secret"
ROOT_ENV = "W65_SFTP_ROOT"


def _resolve(path):
    root = os.path.realpath(os.environ[ROOT_ENV])
    target = os.path.realpath(os.path.join(root, str(path).lstrip("/")))
    if target != root and not target.startswith(root + os.sep):
        raise OSError("path escapes the test root")
    return target


def _failure(exc):
    """Map a local OSError to the SFTP status a real server would send."""
    return paramiko.SFTPServer.convert_errno(getattr(exc, "errno", None) or errno.EACCES)



def _resolve_nofollow(path):
    """Confine the parent directory but leave the final component unresolved.

    A real SFTP server's lstat must report the link itself; resolving the path
    first would turn every symlink into its target and hide link traps.
    """
    root = os.path.realpath(os.environ[ROOT_ENV])
    candidate = os.path.join(root, str(path).lstrip("/"))
    parent = os.path.realpath(os.path.dirname(candidate))
    if parent != root and not parent.startswith(root + os.sep):
        raise OSError("path escapes the test root")
    return os.path.join(parent, os.path.basename(candidate))


def _exec_local(command):
    """A tiny POSIX-ish shell for the commands SSHFilesBackend issues."""
    if isinstance(command, bytes):
        command = command.decode("utf-8", "replace")
    words = shlex.split(str(command))
    if not words:
        return 1, "", "empty command"
    verb, args = words[0], [word for word in words[1:] if word != "--"]
    if verb == "rm":
        recursive = any(arg in {"-r", "-rf", "-fr"} for arg in args)
        targets = [arg for arg in args if not arg.startswith("-")]
        for target in targets:
            local = _resolve(target)
            if os.path.isdir(local):
                if recursive:
                    shutil.rmtree(local)
            elif os.path.exists(local):
                os.remove(local)
        return 0, "", ""
    if verb == "mkdir":
        for arg in args:
            if not arg.startswith("-"):
                os.makedirs(_resolve(arg), exist_ok=True)
        return 0, "", ""
    if verb == "chmod":
        mode = int(args[0], 8)
        os.chmod(_resolve(args[-1]), mode)
        return 0, "", ""
    if verb == "sha256sum":
        local = _resolve(args[-1])
        with open(local, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        return 0, f"{digest}  {args[-1]}\n", ""
    if verb == "cp":
        sources = [arg for arg in args if not arg.startswith("-")]
        source, destination = _resolve(sources[0]), _resolve(sources[1])
        if os.path.isdir(source):
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        return 0, "", ""
    if verb == "mv":
        shutil.move(_resolve(args[0]), _resolve(args[1]))
        return 0, "", ""
    if verb == "test":
        return (0 if os.path.exists(_resolve(args[-1])) else 1), "", ""
    return 127, "", f"unsupported command: {verb}"


def _run_exec(channel, command):
    try:
        code, out, err = _exec_local(command)
    except Exception as exc:
        code, out, err = 1, "", str(exc)
    try:
        if out:
            channel.sendall(out.encode("utf-8"))
        if err:
            channel.sendall_stderr(err.encode("utf-8"))
        channel.send_exit_status(code)
    finally:
        channel.close()


class _Auth(paramiko.ServerInterface):
    def check_channel_request(self, kind, chanid):
        return (
            paramiko.OPEN_SUCCEEDED
            if kind == "session"
            else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        )

    def check_auth_password(self, username, password):
        allowed = (username, password) == (USERNAME, PASSWORD)
        return paramiko.AUTH_SUCCESSFUL if allowed else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_exec_request(self, channel, command):
        threading.Thread(target=_run_exec, args=(channel, command), daemon=True).start()
        return True

    # A real server grants an interactive shell; the wrapper opens one during
    # connect(), so the harness must not reject it.
    def check_channel_shell_request(self, channel):
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True


class _Sftp(paramiko.SFTPServerInterface):
    """Serve the configured root and refuse paths that escape it."""

    def _local(self, path):
        return _resolve(path)

    def list_folder(self, path):
        try:
            local = self._local(path)
            out = []
            for name in os.listdir(local):
                attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(local, name)))
                attr.filename = name
                out.append(attr)
            return out
        except OSError as exc:
            return _failure(exc)

    def stat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(self._local(path)))
        except OSError as exc:
            return _failure(exc)

    def lstat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(_resolve_nofollow(path)))
        except OSError as exc:
            return _failure(exc)

    def canonicalize(self, path):
        return "/" + path.lstrip("/")

    def rename(self, oldpath, newpath):
        denied = (os.environ.get("W65_SFTP_DENY_RENAME") or "").split(",")
        if any(needle and needle in oldpath for needle in denied) or any(
            needle and needle in newpath for needle in denied
        ):
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            os.replace(self._local(oldpath), self._local(newpath))
            return paramiko.SFTP_OK
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def remove(self, path):
        try:
            os.remove(self._local(path))
            return paramiko.SFTP_OK
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def mkdir(self, path, attr):
        try:
            os.mkdir(self._local(path))
            return paramiko.SFTP_OK
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def open(self, path, flags, attr):
        try:
            local = self._local(path)
            writable = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if writable:
                mode = "r+b" if os.path.exists(local) else "wb"
                if flags & os.O_TRUNC:
                    with open(local, "wb"):
                        pass
            else:
                mode = "rb"
            return _Handle(open(local, mode), flags)
        except OSError as exc:
            return _failure(exc)


class _Handle(paramiko.SFTPHandle):
    """Offset-addressed handle.

    The base class helpers (readfile/writefile) ignore the offset argument, so
    this harness replaces both. paramiko's client sends size-based offsets for
    append mode rather than an O_APPEND flag; the write path honours both
    signals.
    """

    def __init__(self, fileobj, flags):
        super().__init__(flags)
        self.fileobj = fileobj
        self.append = bool(flags & os.O_APPEND)

    def read(self, offset, length):
        try:
            self.fileobj.seek(offset)
            return self.fileobj.read(length)
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def write(self, offset, data):
        try:
            if self.append:
                self.fileobj.seek(0, os.SEEK_END)
            else:
                self.fileobj.seek(offset)
            self.fileobj.write(data)
            self.fileobj.flush()
            return paramiko.SFTP_OK
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def stat(self):
        try:
            return paramiko.SFTPAttributes.from_stat(os.fstat(self.fileobj.fileno()))
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def close(self):
        self.fileobj.close()
        return paramiko.SFTP_OK


@contextmanager
def serve():
    """Serve the configured root and yield the bound loopback port."""
    key = paramiko.RSAKey.generate(2048)
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    port = sock.getsockname()[1]

    def handle(client):
        transport = None
        try:
            transport = paramiko.Transport(client)
            # A registered subsystem handler owns accept(); calling
            # transport.accept() here would steal the SFTP channel.
            transport.set_subsystem_handler("sftp", paramiko.SFTPServer, _Sftp)
            transport.add_server_key(key)
            transport.start_server(server=_Auth())
            while transport.is_active():
                time.sleep(0.05)
        finally:
            if transport is not None:
                transport.close()
            client.close()

    def accept_loop():
        try:
            while True:
                client, _address = sock.accept()
                threading.Thread(target=handle, args=(client,), daemon=True).start()
        except OSError:
            return

    threading.Thread(target=accept_loop, daemon=True).start()
    try:
        yield port
    finally:
        sock.close()


@contextmanager
def remote_backend(port):
    """Yield an SSH files backend speaking to the harness server.

    The paramiko client is injected into SSHClientWrapper, so profile-driven
    connect() (host-key policy, jump hosts) stays outside this harness.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        "127.0.0.1",
        port=port,
        username=USERNAME,
        password=PASSWORD,
        look_for_keys=False,
        allow_agent=False,
    )
    wrapper = SSHClientWrapper()
    wrapper.client = client
    wrapper.sftp = client.open_sftp()
    try:
        yield SSHFilesBackend(wrapper)
    finally:
        client.close()
