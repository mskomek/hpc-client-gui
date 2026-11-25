"""Transfer concurrency regression tests (stabilization pass).

Covers:

- FTP safely caps queued transfers at one despite isolated connections;
- two FTP transfers actually overlap using distinct connections;
- the wx transfer session closes every isolated backend on success, failure,
  and cancellation, and retry creates fresh resources;
- SFTP transfers use distinct channel objects;
- a backend capability downgrade results in effective parallelism one;
- the transfer dialog shows configured vs effective limits.
"""

from __future__ import annotations

import hashlib
import threading
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


@pytest.mark.contract
def test_ftp_backend_forces_serial_queueing():
    assert FTPFilesBackend.supports_parallel_transfers is False


@pytest.mark.integration
@pytest.mark.resource
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


@pytest.mark.integration
@pytest.mark.resource
@pytest.mark.concurrency
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
    connection_ids = set()
    peak = {"value": 0}
    lock = threading.Lock()
    import ftplib

    original_storbinary = ftplib.FTP.storbinary
    both_running = threading.Event()

    def counting_storbinary(self, command, handle, *args, **kwargs):
        with lock:
            active.append(self)
            connection_ids.add(id(self))
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
    assert len(connection_ids) == 2, "overlapping transfers shared an FTP connection"
    for index in range(2):
        data = (ftp_server.root / f"remote{index}.bin").read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashlib.sha256(
            sources[index].read_bytes()
        ).hexdigest()


# ---------------------------------------------------------------------------
# wx transfer session backend lifecycle (success / failure / cancellation).
# The queue runs the production wx shell workflow without a GUI parent.
# ---------------------------------------------------------------------------


@pytest.fixture()
def qapp():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _FakeBackend:
    def __init__(self, *, fail=False, release=None, entered=None):
        self.closed = False
        self.fail = fail
        self.release = release
        self.entered = entered

    def upload(self, local_path, remote_path, progress_cb=None):
        if self.entered is not None:
            self.entered.set()
            if not self.release.wait(5):
                raise TimeoutError("test did not release blocked worker")
        if self.fail:
            raise OSError("simulated failure")
        if progress_cb:
            progress_cb(1, 1)

    def close(self):
        self.closed = True


class _FactoryBackend:
    supports_parallel_transfers = False

    def __init__(self, factory):
        self.open_transfer_backend = factory

    def exists(self, path):
        return False

    def upload(self, *args, **kwargs):
        pytest.fail("transfer must not use the shared browser backend")


def _start_wx_transfer(files, items=None):
    from hpc_gui.wx_shell_file_transfer import _start_file_transfers

    state = {"session": {"files": files, "profile": {"transfer_parallelism": 4}}}
    return _start_file_transfers(
        state, None, items or [TransferItem("upload", "a", "/remote/a")]
    )


@pytest.mark.integration
@pytest.mark.resource
def test_wx_transfer_closes_isolated_backend_on_success():
    created = []

    def factory():
        backend = _FakeBackend()
        created.append(backend)
        return backend

    controller = _start_wx_transfer(_FactoryBackend(factory))
    assert controller.engine.wait(5)
    assert len(controller.engine.completed) == 1
    assert not controller.engine.failed
    assert len(created) == 1 and created[0].closed


@pytest.mark.integration
@pytest.mark.resource
def test_wx_transfer_closes_isolated_backend_on_failure():
    created = []

    def factory():
        backend = _FakeBackend(fail=True)
        created.append(backend)
        return backend

    controller = _start_wx_transfer(_FactoryBackend(factory))
    assert controller.engine.wait(5)
    assert len(controller.engine.failed) == 1
    assert "simulated failure" in controller.engine.failed[0][1]
    assert len(created) == 1 and created[0].closed


@pytest.mark.integration
@pytest.mark.resource
def test_cancelled_wx_transfer_releases_isolated_backend():
    release = threading.Event()
    entered = threading.Event()
    created = []

    def factory():
        backend = _FakeBackend(release=release, entered=entered)
        created.append(backend)
        return backend

    controller = _start_wx_transfer(_FactoryBackend(factory))
    try:
        assert entered.wait(5), "upload worker did not reach the blocked operation"
        controller.cancel()
    finally:
        release.set()
        assert controller.engine.wait(5)
    assert len(controller.engine.failed) == 1
    assert controller.engine.failed[0][1] == "cancelled"
    assert created and created[0].closed


@pytest.mark.integration
@pytest.mark.resource
def test_wx_retry_creates_fresh_backend_resources():
    created = []

    def factory():
        backend = _FakeBackend(fail=not created)
        created.append(backend)
        return backend

    controller = _start_wx_transfer(_FactoryBackend(factory))
    assert controller.engine.wait(5)
    assert len(controller.engine.failed) == 1
    assert len(created) == 1 and created[0].closed

    assert controller.engine.retry_failed() == 1
    controller.start()
    assert controller.engine.wait(5)
    assert not controller.engine.failed
    assert len(controller.engine.completed) == 1
    assert len(created) == 2
    assert created[1].closed and created[1] is not created[0]


@pytest.mark.integration
@pytest.mark.resource
def test_wx_transfer_factory_failure_does_not_fall_back_to_shared_backend():
    def factory():
        raise OSError("isolated connection unavailable")

    controller = _start_wx_transfer(_FactoryBackend(factory))
    assert controller.engine.wait(5)
    assert not controller.engine.completed
    assert len(controller.engine.failed) == 1
    assert "isolated connection unavailable" in controller.engine.failed[0][1]


@pytest.mark.integration
@pytest.mark.resource
def test_wx_ftp_queue_uses_isolated_connections_and_serial_limit(ftp_server, tmp_path):
    registry = []
    main = _TrackingFTPBackend(
        ftp_server.host, port=ftp_server.port, username="user", password="pw",
        registry=registry,
    )
    items = []
    for index in range(2):
        source = tmp_path / f"wx-{index}.bin"
        source.write_bytes(bytes([index]) * 8192)
        items.append(TransferItem("upload", str(source), f"/wx-{index}.bin"))
    try:
        controller = _start_wx_transfer(main, items)
        assert controller.engine.parallel_limit == 1
        assert controller.engine.wait(15)
        assert not controller.engine.failed
        assert len(controller.engine.completed) == 2
        assert len(registry) == 2 and registry[0] is not registry[1]
        assert all(backend._registry_closed for backend in registry)
        assert all(backend.ftp is not main.ftp for backend in registry)
        assert not main._closed
        for item in items:
            assert (ftp_server.root / item.dst.lstrip("/")).read_bytes() == Path(item.src).read_bytes()
    finally:
        main.close()


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.integration
@pytest.mark.resource
@pytest.mark.concurrency
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

