"""Packaged wx summary verdicts come only from final observations."""

from __future__ import annotations

from hpc_gui.wx_runtime_observation import finalize_runtime_observation


def _runtime(**checks):
    return {"result": "PASS", "checks": {"workflow": "PASS", **checks}}


def _finalize(runtime, **overrides):
    facts = {
        "pty_initial_requested": (96, 31),
        "pty_initial_observed": (96, 31),
        "pty_resize_requested": (123, 45),
        "pty_resize_observed": (123, 45),
        "transport_closed": True,
        "cleanup_callbacks_drained": True,
        "frame_destroyed": True,
        "event_loop_exited": True,
        "exit_code": 0,
        "timed_out": False,
    }
    facts.update(overrides)
    return finalize_runtime_observation(runtime, **facts)


def test_raw_clean_shutdown_failure_prevents_overall_pass():
    result = _finalize(_runtime(clean_shutdown="FAIL"))
    assert result["checks"]["clean_shutdown"] == "FAIL"
    assert result["result"] == "FAIL"


def test_raw_pty_failure_prevents_overall_pass():
    result = _finalize(_runtime(pty_resize="FAIL"))
    assert result["checks"]["pty_resize"] == "FAIL"
    assert result["result"] == "FAIL"


def test_requested_resize_without_observed_resize_fails():
    result = _finalize(
        _runtime(pty_resize="PENDING"), pty_resize_observed=None
    )
    assert result["observation"]["pty_resize_requested"] == (123, 45)
    assert result["observation"]["pty_resize_observed"] is None
    assert result["observation"]["pty_resize_verified"] is False
    assert result["checks"]["pty_resize"] == "FAIL"
    assert result["result"] == "FAIL"


def test_matching_server_readback_proves_resize():
    result = _finalize(_runtime(pty_resize="PENDING", clean_shutdown="PENDING"))
    assert result["checks"]["pty_resize"] == "PASS"
    assert result["observation"]["pty_resize_verified"] is True


def test_timeout_or_kill_never_proves_clean_shutdown():
    result = _finalize(_runtime(clean_shutdown="PENDING"), timed_out=True)
    assert result["checks"]["clean_shutdown"] == "FAIL"
    assert result["result"] == "FAIL"


def test_undrained_cleanup_callback_prevents_clean_shutdown():
    result = _finalize(
        _runtime(clean_shutdown="PENDING"), cleanup_callbacks_drained=False
    )
    assert result["checks"]["clean_shutdown"] == "FAIL"
    assert result["observation"]["cleanup_callbacks_drained"] is False


def test_normal_teardown_and_zero_exit_prove_clean_shutdown():
    result = _finalize(_runtime(clean_shutdown="PENDING"))
    assert result["checks"]["clean_shutdown"] == "PASS"
    assert result["observation"]["child_exit_code"] == 0
