"""Final transfer/readback/reconnect phase of the packaged wx smoke."""

from __future__ import annotations

from hpc_gui.wx_shell_smoke_reconnect import reconnect_packaged_smoke_session


def finish_terminal_acceptance_phase(
    state, checks, session_state, frame, lifecycle, panel, retry, finish
):
    transfer_panel = session_state.get("embedded_transfers_panel")
    controls = getattr(transfer_panel, "_wx_transfer_controls", {})
    queue = controls.get("queue") if transfer_panel else None
    item = state.get("transfer_item")
    state["queue_count"] = queue.GetItemCount() if queue is not None else None
    state["queue_text"] = (
        queue.GetItemText(0) if queue is not None and queue.GetItemCount() else None
    )
    if queue is None or queue.GetItemCount() < 1 or queue.GetItemText(0) != item.src:
        retry()
        return
    checks["transfer_queue_render"] = "PASS"
    checks["terminal_readback"] = "PASS"
    try:
        evidence = reconnect_packaged_smoke_session(
            session_state, frame, lifecycle, panel, state["smoke_session"]
        )
        state["smoke_session"] = evidence["session"]
        state["reconnect_evidence"] = {
            key: value for key, value in evidence.items() if key != "session"
        }
        if not all(value is True for key, value in evidence.items() if key != "session"):
            finish("reconnect_fresh_identity:state_mismatch")
            return
        checks["reconnect_fresh_identity"] = "PASS"
    except Exception as exc:
        finish(f"reconnect_fresh_identity:{type(exc).__name__}")
        return
    state["result"] = "PASS"
    finish()
