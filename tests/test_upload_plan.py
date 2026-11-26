"""Headless upload planning and native preflight contract coverage."""
from types import SimpleNamespace

import pytest

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.upload_plan import build_upload_plan, summarize_upload_plan, transfer_limits
from hpc_gui.wx_shell_upload import prepare_upload


def test_plan_preserves_empty_directories_and_deduplicates(tmp_path):
    root = tmp_path / "case"
    (root / "empty").mkdir(parents=True)
    (root / "input.txt").write_text("input")
    items = build_upload_plan([root, root], "/remote")
    assert [(i.op, i.dst) for i in items] == [
        ("mkdir_remote", "/remote/case"),
        ("mkdir_remote", "/remote/case/empty"),
        ("upload", "/remote/case/input.txt"),
    ]
    assert items[-1].src == str(root / "input.txt")


def test_summary_limits_rows_without_truncating_plan():
    items = [TransferItem("upload", str(i), f"/remote/{i}") for i in range(250)]
    summary = summarize_upload_plan(items, 2)
    assert (summary.files, summary.folders, summary.steps, summary.parallel) == (250, 0, 250, 2)
    assert len(summary.visible) == 200 and summary.hidden == 50
    assert len(items) == 250


def test_backend_limit_is_shared_by_confirmation_and_engine():
    assert transfer_limits(SimpleNamespace(supports_parallel_transfers=False), {"transfer_parallelism": 4}) == (4, 1)
    assert transfer_limits(SimpleNamespace(supports_parallel_transfers=True), {"transfer_parallelism": 4}) == (4, 4)


def test_missing_source_never_becomes_upload(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_upload_plan([tmp_path / "missing"], "/remote")


@pytest.mark.parametrize("change", ["session", "generation", "shutdown", None])
def test_plan_rejects_stale_owner(tmp_path, change):
    source = tmp_path / "source"
    source.write_text("x")
    files = object()
    session = {"files": files}
    state = {"session": session, "generation": 1}
    lifecycle = SimpleNamespace(shutdown_started=False)
    started = []
    if change == "session":
        state["session"] = {"files": files}
    elif change == "generation":
        state["generation"] = 2
    elif change == "shutdown":
        lifecycle.shutdown_started = True
    prepare_upload(state, lifecycle, None, session, files, [source], "/remote",
                   lambda *args, **kwargs: started.append(args), generation=1)
    assert len(started) == (1 if change is None else 0)


def test_preflight_preference_round_trips_through_wx_settings(tmp_path, monkeypatch):
    from hpc_gui.config.storage import get_upload_preflight_confirmation_enabled
    from hpc_gui.wx_settings import build_model_from_storage, persist_model_snapshot

    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path))
    model = build_model_from_storage()
    assert model.global_settings["upload_preflight_confirmation"] is True
    model.set_global("upload_preflight_confirmation", False)
    persist_model_snapshot(model.snapshot())
    assert get_upload_preflight_confirmation_enabled() is False
    assert build_model_from_storage().global_settings["upload_preflight_confirmation"] is False


@pytest.mark.parametrize("backend_kind", ["ftp", "mock"])
@pytest.mark.parametrize("nested", [False, True])
def test_upload_directory_collision_preserves_remote_file(tmp_path, backend_kind, nested):
    from hpc_gui.services.files_mock import MockFilesBackend
    from hpc_gui.wx_shell_file_transfer import _start_file_transfers
    from test_transfer_resume_semantics import ftp_backend

    occupied = "/remote/occupied"
    created = []
    if backend_kind == "ftp":
        files = ftp_backend({occupied: b"original"})
        store = files.ftp.files

        def mkdir(path):
            created.append(path)
            assert path not in store
            files.ftp.dirs.add(path)

        files.ftp.mkd = mkdir
    else:
        files = MockFilesBackend()
        files.mkdir("/remote")
        store = files._files
        store[occupied] = b"original"

    directory = occupied + "/nested" if nested else occupied
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    target = directory + "/file"
    items = [TransferItem("mkdir_remote", "", directory),
             TransferItem("upload", str(source), target)]
    state = {"session": {"files": files}, "ftp_transfer_type": "binary"}
    controller = _start_file_transfers(state, None, items)
    assert controller.engine.wait(5)
    assert len(controller.engine.failed) == 2
    assert not controller.engine.completed
    assert store[occupied] == b"original" and target not in store
    assert not files.is_dir(occupied)
    assert not created


@pytest.mark.parametrize("backend_kind", ["ftp", "mock"])
def test_existing_remote_directory_is_safe_to_merge(backend_kind):
    from hpc_gui.services.files_mock import MockFilesBackend
    from test_transfer_resume_semantics import ftp_backend

    if backend_kind == "ftp":
        files = ftp_backend()
        created = []

        def mkdir(path):
            created.append(path)
            files.ftp.dirs.add(path)

        files.ftp.mkd = mkdir
    else:
        files = MockFilesBackend()
        files.mkdir("/remote")

    files.mkdir("/remote")
    files.mkdir("/remote/nested")
    files.mkdir("/remote/nested")
    assert files.is_dir("/remote/nested")
    if backend_kind == "ftp":
        assert created == ["/remote/nested"]


def test_shell_upload_plans_on_worker_and_serial_backend_keeps_folder_order(tmp_path, monkeypatch):
    from threading import Event, get_ident
    from contextlib import contextmanager

    from hpc_gui import wx_shell_files, wx_shell_upload
    from hpc_gui.services.files_mock import MockFilesBackend

    main_thread = get_ident()
    planning, release, started = Event(), Event(), Event()
    thread_ids = []
    calls = []

    class SerialFiles(MockFilesBackend):
        supports_parallel_transfers = False
        active = 0
        max_active = 0

        @contextmanager
        def operation(self, op, path):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            calls.append((op, path, get_ident()))
            try:
                yield
            finally:
                self.active -= 1

        def mkdir(self, path):
            with self.operation("mkdir", path):
                super().mkdir(path)

        def upload(self, src, dst):
            with self.operation("upload", dst):
                super().upload(src, dst)

    files = SerialFiles()
    session = {"files": files, "profile": {"transfer_parallelism": 5}}
    state = {"session": session, "generation": 1,
             "_embedded_remote_files_panel": SimpleNamespace(
                 _wx_remote_model=SimpleNamespace(current_path="/remote"))}
    controllers = []
    original_plan = wx_shell_upload.build_upload_plan
    original_start = wx_shell_files._start_file_transfers

    def slow_plan(paths, destination):
        thread_ids.append(get_ident())
        planning.set()
        assert release.wait(5)
        return original_plan(paths, destination)

    def start(*args, **kwargs):
        controllers.append(original_start(*args, **kwargs))
        started.set()

    monkeypatch.setattr(wx_shell_upload, "build_upload_plan", slow_plan)
    monkeypatch.setattr(wx_shell_files, "_start_file_transfers", start)
    monkeypatch.setattr(wx_shell_files, "_get_editor_manager", lambda *args: None)
    roots = []
    for name in ("first", "second"):
        root = tmp_path / name
        root.mkdir()
        (root / "input.txt").write_text(name)
        roots.append(root)

    callbacks = wx_shell_files._local_files_callbacks(state, None, None)
    try:
        callbacks["upload"](roots)
        assert planning.wait(5)
        assert thread_ids[0] != main_thread
        assert not calls and not started.is_set()
    finally:
        release.set()
    assert started.wait(5)
    assert controllers[0].engine.wait(5)
    assert not controllers[0].engine.failed
    assert controllers[0].configured_parallel_limit == 5
    assert files.max_active == 1
    assert [(op, path) for op, path, _thread in calls] == [
        ("mkdir", "/remote/first"), ("upload", "/remote/first/input.txt"),
        ("mkdir", "/remote/second"), ("upload", "/remote/second/input.txt"),
    ]
    assert all(thread != main_thread for _, _, thread in calls)
