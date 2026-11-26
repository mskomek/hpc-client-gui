"""Recursive download, safe discovery, and stale-owner queue regression tests."""
from types import SimpleNamespace

import pytest

from hpc_gui.services.download_plan import build_download_plan
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.wx_shell_download import prepare_download
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def test_recursive_download_preserves_empty_folders_and_merge(tmp_path):
    files = MockFilesBackend()
    files.mkdir("/remote/case/empty")
    files.mkdir("/remote/case/nested")
    files.write_text("/remote/case/nested/readme.txt", "line\n")
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "keep").write_bytes(b"keep")
    items = build_download_plan(files, ["/remote/case", "/remote/case"], tmp_path)
    assert sum(item.op == "mkdir_local" for item in items) == 3
    assert sum(item.op == "download" for item in items) == 1
    assert not (tmp_path / "case" / "empty").exists()
    controller = _start_file_transfers(
        {"session": {"files": files}, "ftp_transfer_type": "binary"},
        None, items,
    )
    assert controller.engine.wait(5)
    assert not controller.engine.failed, controller.engine.failed
    assert (tmp_path / "case" / "empty").is_dir()
    assert (tmp_path / "case" / "nested" / "readme.txt").read_bytes() == b"line\n"
    assert (tmp_path / "case" / "keep").read_bytes() == b"keep"


@pytest.mark.parametrize("name,path", [("../escape", "/remote/escape"), ("bad", "/other/bad"), ("a\\b", "/remote/a\\b")])
def test_unsafe_listing_rejected_before_queue(tmp_path, name, path):
    files = SimpleNamespace(
        is_dir=lambda _: True,
        listdir_entries=lambda _: [RemoteEntry(name, path, False)],
    )
    with pytest.raises(ValueError):
        build_download_plan(files, ["/remote"], tmp_path)
    assert not list(tmp_path.iterdir())


def test_failed_listing_aborts_entire_plan(tmp_path):
    class Broken(MockFilesBackend):
        def listdir_entries(self, path):
            if path.endswith("/nested"):
                raise OSError("listing failed")
            return super().listdir_entries(path)

    files = Broken()
    files.mkdir("/remote/nested")
    session = {"files": files}
    started = []
    with pytest.raises(OSError, match="listing failed"):
        prepare_download({"session": session}, None, None, session, files, ["/remote"],
                         tmp_path, lambda *args, **kwargs: started.append(args), generation=None)
    assert not started and not list(tmp_path.iterdir())


def test_generation_change_during_discovery_does_not_start_queue(tmp_path):
    class Switching(MockFilesBackend):
        def listdir_entries(self, path):
            state["generation"] += 1
            return super().listdir_entries(path)

    files = Switching()
    files.mkdir("/remote/empty")
    session = {"files": files}
    state = {"session": session, "generation": 1}
    started = []
    prepare_download(state, None, None, session, files, ["/remote"], tmp_path,
                     lambda *args, **kwargs: started.append(args), generation=1)
    assert not started and not list(tmp_path.iterdir())


def test_directory_conflict_rejects_without_deleting_existing_file(tmp_path):
    files = MockFilesBackend()
    files.mkdir("/remote/case")
    target = tmp_path / "case"
    target.write_bytes(b"keep")
    with pytest.raises(NotADirectoryError):
        build_download_plan(files, ["/remote/case"], tmp_path)
    assert target.read_bytes() == b"keep"


def test_download_plan_preserves_listing_sizes_without_per_file_stat(tmp_path):
    files = MockFilesBackend()
    files.mkdir("/remote/child")
    files.write_text("/remote/root.txt", "abcd")
    files.write_text("/remote/child/nested.txt", "123456")
    files.write_text("/remote/child/zero", "")

    # Directory roots expose metadata through lstat; nested file sizes must
    # come from the listing, not a separate per-file stat.
    def unexpected_stat(path):
        raise AssertionError(f"unexpected stat: {path}")

    files.stat = unexpected_stat
    items = build_download_plan(files, ["/remote"], tmp_path)
    assert {it.src: it.cached_size for it in items if it.op == "download"} == {
        "/remote/root.txt": 4,
        "/remote/child/nested.txt": 6,
        "/remote/child/zero": 0,
    }
    assert all(it.cached_size is None for it in items if it.op == "mkdir_local")
