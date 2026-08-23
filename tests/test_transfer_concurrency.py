"""Transfer concurrency regression tests (stabilization pass).

Covers:

- the FTP backend truthfully declares parallel capability via isolated
  per-transfer connections;
- two FTP transfers actually overlap using distinct connections;
- the transfer dialog closes every isolated backend on success, failure,
  and cancellation, and retry creates fresh resources;
- SFTP transfers use distinct channel objects;
- a backend capability downgrade results in effective parallelism one;
- the transfer dialog shows configured vs effective limits.
"""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hpc_gui.services.files_ftp import FTPFilesBackend
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.transfer_controller import TransferController, TransferItem


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _TrackingFTPBackend(FTPFilesBackend):
    """FTP backend that records close() calls for resource-release asserts."""

    def __init__(self, *args, registry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry = registry if registry is not None else []

    def open_transfer_backend(self) -> "_TrackingFTPBackend":
        backend = _TrackingFTPBackend(
            self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            timeout=self._timeout,
            registry=self._registry,
        )
        self._registry.append(backend)
        return backend

    def close(self) -> None:
        self._registry_closed = True
        super().close()


@pytest.fixture()
def ftp_server(tmp_path: Path):
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer

    root = tmp_path / "ftp-root"
    root.mkdir()
    authorizer = DummyAuthorizer()
    authorizer.add_user("user", "pw", str(root), perm="elradfmwMT")
    handler = type("H", (FTPHandler,), {})
    handler.authorizer = authorizer
    server = FTPServer(("127.0.0.1", 0), handler)
    sock = server.socket.getsockname()
    thread = threading.Thread(target=server.serve_forever, kwargs={"timeout": 0.1, "blocking": True, "handle_exit": False}, daemon=True)
    thread.start()
    yield SimpleNamespace(host="127.0.0.1", port=sock[1], root=root)
    server.close_all()


def _backend(server) -> FTPFilesBackend:
    return FTPFilesBackend(server.host, port=server.port, username="user", password="pw")


# ---------------------------------------------------------------------------
# FTP capability and isolation
# ---------------------------------------------------------------------------


def test_ftp_backend_declares_parallel_capability():
    assert FTPFilesBackend.supports_parallel_transfers is True


def test_ftp_transfer_backends_are_isolated_and_close_is_idempotent(ftp_server):
    main = _backend(ftp_server)
    try:
        transfer = main.open_transfer_backend()
        try:
            assert transfer is not main
            assert transfer.ftp is not main.ftp
            transfer.close()
            first_state = transfer._closed
            transfer.close()  # second close must be a no-op, not an error
            assert first_state is True and transfer._closed is True
        finally:
            pass
    finally:
        main.close()


def test_two_ftp_transfers_overlap_with_distinct_connections(ftp_server, tmp_path):
    """Two uploads through isolated backends must genuinely overlap."""
    main = _backend(ftp_server)
    payload = b"x" * (512 * 1024)
    sources = []
    for index in range(2):
        source = tmp_path / f"src{index}.bin"
        source.write_bytes(payload + bytes([index]) * 1024)
        sources.append(source)

    active = []
    peak = {"value": 0}
    lock = threading.Lock()
    import ftplib

    original_storbinary = ftplib.FTP.storbinary
    both_running = threading.Event()

    def counting_storbinary(self, command, handle, *args, **kwargs):
        with lock:
            active.append(self)
            peak["value"] = max(peak["value"], len(active))
        if len(active) >= 2:
            both_running.set()
        try:
            # Give the other worker a real chance to join concurrently.
            both_running.wait(3)
            return original_storbinary(self, command, handle, *args, **kwargs)
        finally:
            with lock:
                if self in active:
                    active.remove(self)

    workers = []
    errors = []
    try:
        ftplib.FTP.storbinary = counting_storbinary
        for index, source in enumerate(sources):

            def work(index=index, source=source):
                backend = main.open_transfer_backend()
                try:
                    backend.upload(str(source), f"/remote{index}.bin")
                except Exception as exc:  # pragma: no cover - surfaced below
                    errors.append(exc)
                finally:
                    backend.close()

            thread = threading.Thread(target=work)
            thread.start()
            workers.append(thread)

        for thread in workers:
            thread.join(timeout=15)
            assert not thread.is_alive()
    finally:
        ftplib.FTP.storbinary = original_storbinary
        main.close()

    assert not errors
    assert peak["value"] == 2, "transfers did not overlap"
    for index in range(2):
        data = (ftp_server.root / f"remote{index}.bin").read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashlib.sha256(
            sources[index].read_bytes()
        ).hexdigest()


# ---------------------------------------------------------------------------
# TransferDialog backend lifecycle (success / cancel / retry)
# ---------------------------------------------------------------------------


@pytest.fixture()
def qapp():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _FakeBackend:
    def __init__(self, *, fail=False, hang_until=None):
        self.closed = False
        self.fail = fail
        self.hang_until = hang_until

    def upload(self, local_path, remote_path, progress_cb=None):
        if self.hang_until is not None:
            progress_cb(1, 10)
            self.hang_until.wait(5)
            raise _SimulatedCancel()
        if self.fail:
            raise OSError("simulated failure")
        progress_cb(1, 1)

    def close(self):
        self.closed = True


class _SimulatedCancel(Exception):
    pass


def _make_dialog(qapp, factory, items):
    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog

    return TransferDialog(
        None,
        title="t",
        items=items,
        run_item=lambda item, progress=None, files=None: files.upload(
            item.src, item.dst, progress
        ),
        parallel_limit=2,
        max_parallel_limit=10,
        backend_context_factory=factory,
    )


def test_dialog_closes_isolated_backend_on_success(qapp, tmp_path):
    created = []
    source = tmp_path / "a.txt"
    source.write_text("data")

    def factory():
        backend = _FakeBackend()
        created.append(backend)
        return backend

    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog
    from hpc_gui.services.transfer_controller import TransferItem as TI

    dialog = TransferDialog(
        None,
        title="t",
        items=[TI("upload", str(source), "/remote/a.txt")],
        run_item=lambda item, progress=None, files=None: files.upload(
            item.src, item.dst, progress
        ),
        parallel_limit=2,
        max_parallel_limit=10,
        backend_context_factory=factory,
    )
    dialog.start()
    assert dialog._thread._controller.wait(5)
    assert len(created) == 1
    assert created[0].closed is True


def test_dialog_closes_isolated_backend_on_failure(qapp):
    created = []

    def factory():
        backend = _FakeBackend(fail=True)
        created.append(backend)
        return backend

    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog

    dialog = TransferDialog(
        None,
        title="t",
        items=[TransferItem("upload", "a", "/remote/a")],
        run_item=lambda item, progress=None, files=None: files.upload(
            item.src, item.dst, progress
        ),
        parallel_limit=2,
        max_parallel_limit=10,
        backend_context_factory=factory,
    )
    dialog.start()
    assert dialog._thread._controller.wait(5)
    assert len(created) == 1
    assert created[0].closed is True
    assert dialog._thread._controller.failed and dialog._thread._controller.failed[0][1]


def test_cancelled_transfer_releases_isolated_backend(qapp):
    release = threading.Event()
    created = []

    def factory():
        backend = _FakeBackend(hang_until=release)
        created.append(backend)
        return backend

    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog

    dialog = TransferDialog(
        None,
        title="t",
        items=[TransferItem("upload", "a", "/remote/a")],
        run_item=lambda item, progress=None, files=None: files.upload(
            item.src, item.dst, progress
        ),
        parallel_limit=1,
        max_parallel_limit=1,
        backend_context_factory=factory,
    )
    dialog.start()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not created:
        time.sleep(0.01)
    time.sleep(0.05)  # let the worker block inside upload
    dialog.cancel_all()
    release.set()
    assert dialog._thread._controller.wait(5)
    assert created and created[0].closed is True


def test_retry_creates_fresh_backend_resources(qapp):
    class _FlakyFactory:
        def __init__(self):
            self.backends = []

        def __call__(self):
            backend = _FakeBackend(fail=len(self.backends) == 0)
            self.backends.append(backend)
            return backend

    factory = _FlakyFactory()

    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog

    dialog = TransferDialog(
        None,
        title="t",
        items=[TransferItem("upload", "a", "/remote/a")],
        run_item=lambda item, progress=None, files=None: files.upload(
            item.src, item.dst, progress
        ),
        parallel_limit=1,
        max_parallel_limit=1,
        backend_context_factory=factory,
    )
    dialog.start()
    assert dialog._thread._controller.wait(5)
    assert len(factory.backends) == 1 and factory.backends[0].closed is True

    # Retry must create a healthy new resource, not reuse the failed one.
    controller = dialog._thread._controller
    assert controller.retry_failed() == 1
    controller.start()
    assert controller.wait(5)
    assert len(controller.completed) == 1
    assert len(factory.backends) == 2
    assert factory.backends[0].closed is True
    assert factory.backends[1].closed is True


def test_effective_limit_label_shows_configured_and_effective(qapp):
    from hpc_gui.core.i18n import load_language, t
    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog

    load_language("en")
    dialog = TransferDialog(
        None,
        title="t",
        items=[],
        run_item=lambda item, progress=None: None,
        parallel_limit=1,
        max_parallel_limit=1,
        configured_limit=4,
    )
    try:
        text = dialog.lbl_parallel_hint.text()
        assert "4" in text and "1" in text
        assert t("transfer.parallel_reduced_backend") in text
    finally:
        dialog.deleteLater()


def test_effective_limit_label_when_matching(qapp):
    from hpc_gui.ui.dialogs.transfer_dialog import TransferDialog
    from hpc_gui.core.i18n import load_language, t

    load_language("en")
    dialog = TransferDialog(
        None,
        title="t",
        items=[],
        run_item=lambda item, progress=None: None,
        parallel_limit=4,
        max_parallel_limit=10,
        configured_limit=4,
    )
    try:
        text = dialog.lbl_parallel_hint.text()
        assert text.count("4") >= 2
        assert t("transfer.parallel_reduced_server") not in text
    finally:
        dialog.deleteLater()


# ---------------------------------------------------------------------------
# SFTP distinct channels under parallel execution
# ---------------------------------------------------------------------------


class _FakeSFTPChannel:
    def __init__(self):
        self.closed = False

    def stat(self, path):
        return SimpleNamespace(st_size=0)

    def open(self, path, mode):
        channel_file = MagicMock()
        channel_file.write = lambda data: None
        channel_file.__enter__ = lambda self: channel_file
        channel_file.__exit__ = lambda *args: False
        channel_file.read = lambda size=0: b""
        return MagicMock()

    def close(self):
        self.closed = True


class _FakeSSHWrapper:
    def __init__(self):
        self.channels = []
        self.sftp = _FakeSFTPChannel()

    def supports_transfer_sftp_channels(self):
        return True

    def open_transfer_sftp(self):
        channel = _FakeSFTPChannel()
        self.channels.append(channel)
        return channel


def test_sftp_parallel_transfers_use_distinct_channels(tmp_path):
    wrapper = _FakeSSHWrapper()
    backend = SSHFilesBackend(wrapper)

    sources = []
    for index in range(2):
        source = tmp_path / f"s{index}.bin"
        source.write_bytes(b"data" * 1024)
        sources.append(source)

    controller = TransferController(
        [TransferItem("upload", str(path), f"/remote/{path.name}") for path in sources],
        backend.upload,
        parallel_limit=2,
    )
    controller.start()
    assert controller.wait(10)

    # Each transfer opened its own channel object.
    assert len(wrapper.channels) == 2
    assert wrapper.channels[0] is not wrapper.channels[1]
    assert all(channel.closed for channel in wrapper.channels)

