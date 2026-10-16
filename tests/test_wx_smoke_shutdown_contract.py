"""W55/W16 packaged shutdown evidence contract (no native wx needed)."""

import json
from types import SimpleNamespace

from hpc_gui.wx_lifecycle import WxLifecycleController
from hpc_gui.wx_runtime_observation import finalize_runtime_observation
from hpc_gui.wx_shell_smoke_finalize import (
    _frame_destroyed,
    finish_packaged_smoke,
)


def test_frame_destroyed_requires_removal_from_wx_top_level_registry():
    frame = object()
    windows = [frame]
    wx = SimpleNamespace(GetTopLevelWindows=lambda: windows)
    assert _frame_destroyed(wx, frame) is False
    windows.clear()
    assert _frame_destroyed(wx, frame) is True

    def broken_registry():
        raise RuntimeError("wx already unavailable")

    assert _frame_destroyed(
        SimpleNamespace(GetTopLevelWindows=broken_registry), frame
    ) is False


def _child_finish(tmp_path, *, remove_frame=True, cleanup_complete=True, check="PENDING"):
    windows = []
    timers = []
    exits = []
    app_exit_policy = []

    class Frame:
        def Close(self):
            if remove_frame:
                windows.remove(self)

    frame = Frame()
    windows.append(frame)
    wx = SimpleNamespace(
        GetTopLevelWindows=lambda: windows,
        CallLater=lambda ms, callback: timers.append((ms, callback)),
    )
    app = SimpleNamespace(
        GetAppName=lambda: "HPC GUI",
        SetExitOnFrameDelete=lambda value: app_exit_policy.append(value),
        ExitMainLoop=lambda: exits.append(True),
    )

    class Ssh:
        client = object()
        sftp = object()
        _shell_session = object()

        def close(self):
            self.client = None
            self.sftp = None
            self._shell_session = None

    ssh = Ssh()
    state = {
        "done": False,
        "result": "PASS",
        "phase": 4,
        "observation": {
            "transport_closed": False,
            "frame_destroyed": False,
            "cleanup_callbacks_drained": False,
        },
        "smoke_session": {"ssh": ssh},
    }
    checks = {"clean_shutdown": check, "pty_resize": "PENDING"}
    report_path = tmp_path / "wx-runtime.json"
    lifecycle = SimpleNamespace(
        cleanup_complete=cleanup_complete, cleanup_timed_out=False
    )
    finish_packaged_smoke(
        state, checks, None, report_path, app, wx, frame, {}, lifecycle
    )
    assert state["done"] is True
    assert app_exit_policy == [False]
    assert timers[0][0] == 100
    # Deferred registry observation must be persisted before exit.
    timers[0][1]()
    assert exits == [True]
    return json.loads(report_path.read_text(encoding="utf-8"))


def _parent_finalize(child):
    return finalize_runtime_observation(
        child,
        pty_initial_requested=(96, 31),
        pty_initial_observed=(96, 31),
        pty_resize_requested=(123, 45),
        pty_resize_observed=(123, 45),
        transport_closed=child["observation"]["transport_closed"],
        cleanup_callbacks_drained=child["observation"]["cleanup_callbacks_drained"],
        frame_destroyed=child["observation"]["frame_destroyed"],
        event_loop_exited=True,
        exit_code=0,
        timed_out=False,
        mandatory_checks=("pty_resize", "clean_shutdown"),
    )


def test_child_deferred_destroy_and_parent_can_complete_pending_shutdown(tmp_path):
    child = _child_finish(tmp_path)
    assert child["checks"]["clean_shutdown"] == "PENDING"
    assert child["observation"]["frame_destroyed"] is True
    assert child["observation"]["cleanup_callbacks_drained"] is True
    finalized = _parent_finalize(child)
    assert finalized["checks"]["clean_shutdown"] == "PASS"
    assert finalized["result"] == "PASS"


def test_live_frame_or_failed_cleanup_cannot_pass_shutdown(tmp_path):
    for remove_frame, cleanup_complete in [(False, True), (True, False)]:
        child = _child_finish(
            tmp_path, remove_frame=remove_frame, cleanup_complete=cleanup_complete
        )
        assert _parent_finalize(child)["checks"]["clean_shutdown"] == "FAIL"


def test_explicit_child_shutdown_failure_is_not_overridden(tmp_path):
    child = _child_finish(tmp_path, check="FAIL")
    assert child["checks"]["clean_shutdown"] == "FAIL"
    finalized = _parent_finalize(child)
    assert finalized["checks"]["clean_shutdown"] == "FAIL"
    assert finalized["result"] == "FAIL"


def test_cleanup_failure_diagnostics_include_no_exception_messages():
    def broken_cleanup():
        raise RuntimeError("private password/token details")

    for worker_safe in (False, True):
        lifecycle = WxLifecycleController()
        lifecycle.register_cleanup(broken_cleanup, worker_safe=worker_safe)
        lifecycle.shutdown()
        assert lifecycle.cleanup_complete is False
        assert lifecycle.cleanup_timed_out is False
        assert lifecycle.cleanup_failures == [{
            "callback": "test_cleanup_failure_diagnostics_include_no_exception_messages"
            ".<locals>.broken_cleanup",
            "error_type": "RuntimeError",
        }]
        assert "private password" not in json.dumps(lifecycle.cleanup_failures)
