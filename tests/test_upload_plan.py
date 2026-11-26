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
