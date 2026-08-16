from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication

from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel

_IS_DIR_ROLE = Qt.ItemDataRole.UserRole + 1


def _entries(count: int) -> list[RemoteEntry]:
    return [
        RemoteEntry(f"f{i:05d}", f"/work/f{i:05d}", i % 3 == 0, size=i, mtime=i)
        for i in range(count)
    ]


class _StreamingFiles:
    """Progressive backend that records how it was consumed."""

    supports_progressive_listing = True

    def __init__(self, entries: list[RemoteEntry]) -> None:
        self.entries = entries
        self.iter_calls = 0
        self.abandoned = 0

    def listdir_entries(self, _path: str) -> list[RemoteEntry]:
        return list(self.entries)

    def iterdir_entries(self, _path: str):
        self.iter_calls += 1
        delivered = 0
        try:
            for entry in self.entries:
                yield entry
                delivered += 1
        finally:
            if delivered < len(self.entries):
                self.abandoned += 1


class RemoteDirectoryListingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self, files) -> RemoteDirPanel:
        panel = RemoteDirPanel()
        panel.set_session({"connected": True, "files": files})
        self.addCleanup(panel.deleteLater)
        return panel

    def _drain(self) -> None:
        self.assertTrue(QThreadPool.globalInstance().waitForDone(15000))
        for _ in range(50):
            self.app.processEvents()

    def test_streaming_listing_clears_once_and_renders_every_entry(self) -> None:
        entries = _entries(1500)
        files = _StreamingFiles(entries)
        panel = self._panel(files)
        clears: list[str] = []
        original = panel._begin_render

        def counted(category_dir: str) -> None:
            clears.append(category_dir)
            original(category_dir)

        panel._begin_render = counted  # type: ignore[method-assign]
        panel.set_dir("/work")
        self._drain()

        # ".." plus every entry, and the tree is built exactly once.
        self.assertEqual(panel.views["all"].topLevelItemCount(), len(entries) + 1)
        self.assertEqual(clears, ["/work"])
        self.assertEqual(files.iter_calls, 1)

    def test_default_sort_groups_folders_before_files(self) -> None:
        panel = self._panel(_StreamingFiles(_entries(30)))
        panel.set_dir("/work")
        self._drain()

        view = panel.views["all"]
        self.assertEqual(view.topLevelItem(0).text(0), "..")
        flags = [
            bool(view.topLevelItem(i).data(0, _IS_DIR_ROLE))
            for i in range(1, view.topLevelItemCount())
        ]
        self.assertEqual(flags, sorted(flags, reverse=True))
        names = [
            view.topLevelItem(i).text(0)
            for i in range(1, view.topLevelItemCount())
            if view.topLevelItem(i).data(0, _IS_DIR_ROLE)
        ]
        self.assertEqual(names, sorted(names))

    def test_stale_navigation_is_cancelled(self) -> None:
        files = _StreamingFiles(_entries(20000))
        panel = self._panel(files)
        panel.set_dir("/work/a")
        panel.set_dir("/work/b")
        self._drain()

        self.assertEqual(files.iter_calls, 2)
        self.assertGreaterEqual(files.abandoned, 1)
        self.assertIsNone(panel._listing_worker)

    def test_cached_directory_skips_the_network(self) -> None:
        files = _StreamingFiles(_entries(10))
        panel = self._panel(files)
        panel.set_dir("/work")
        self._drain()
        panel.refresh_async()
        self._drain()

        self.assertEqual(files.iter_calls, 1)
        self.assertEqual(panel.views["all"].topLevelItemCount(), 11)


class _FakeAttr:
    def __init__(self, name: str, mode: int) -> None:
        self.filename = name
        self.st_mode = mode
        self.st_size = 7
        self.st_mtime = 11


class _FakeSFTP:
    def __init__(self) -> None:
        self.closed = False

    def listdir_iter(self, _path: str, read_aheads: int = 50):
        yield _FakeAttr("dir", 0o040755)
        yield _FakeAttr("file", 0o100644)

    def close(self) -> None:
        self.closed = True


class ListingChannelTests(unittest.TestCase):
    def _wrapper(self):
        from hpc_gui.ssh.client import SSHClientWrapper

        ssh = SSHClientWrapper()
        opened: list[_FakeSFTP] = []

        def open_transfer_sftp():
            sftp = _FakeSFTP()
            opened.append(sftp)
            return sftp

        ssh.open_transfer_sftp = open_transfer_sftp  # type: ignore[method-assign]
        ssh.sftp = object()
        return ssh, opened

    def _backend(self, ssh, opened):
        from hpc_gui.services.files_ssh import SSHFilesBackend

        backend = SSHFilesBackend(ssh)
        # Construction probes channel support once; ignore that channel.
        opened.clear()
        return backend

    def test_channel_is_reused_across_completed_listings(self) -> None:
        ssh, opened = self._wrapper()
        backend = self._backend(ssh, opened)
        for _ in range(5):
            entries = list(backend.iterdir_entries("/work"))
        self.assertEqual(len(opened), 1)
        self.assertEqual([e.name for e in entries], ["dir", "file"])
        self.assertTrue(entries[0].is_dir)
        self.assertEqual(entries[0].path, "/work/dir")

    def test_abandoned_listing_drops_the_channel(self) -> None:
        ssh, opened = self._wrapper()
        backend = self._backend(ssh, opened)
        stream = backend.iterdir_entries("/work")
        next(stream)
        stream.close()
        self.assertTrue(opened[0].closed)
        list(backend.iterdir_entries("/work"))
        self.assertEqual(len(opened), 2)


if __name__ == "__main__":
    unittest.main()
