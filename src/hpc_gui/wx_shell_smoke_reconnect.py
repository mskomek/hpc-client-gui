"""Loopback reconnect probe for the packaged wx runtime smoke."""

from __future__ import annotations


def reconnect_packaged_smoke_session(session_state, frame, lifecycle, terminal, old_session):
    """Disconnect the real smoke session and attach a fresh loopback SSH one.

    Returns only booleans and the new session object; no terminal bytes or
    credentials enter the runtime observation report.
    """
    import wx

    from hpc_gui.wx_shell_connections import _connection_callbacks
    from hpc_gui.wx_shell_smoke_session import _connect_packaged_smoke_session

    old_ssh = old_session["ssh"]
    stale_subscriber = terminal._subscriber
    generation_before = terminal._generation
    callbacks = _connection_callbacks(session_state, frame, lifecycle)
    callbacks["on_disconnected"](old_session)
    old_ssh.close()
    disconnected = session_state.get("session") is None
    disconnected = disconnected and terminal._ssh is None
    disconnect_generation = terminal._generation

    new_session = _connect_packaged_smoke_session(
        session_state,
        frame,
        lifecycle,
        profile_name="packaged-smoke-reconnect",
    )
    if new_session is None:
        raise RuntimeError("fresh loopback reconnect session was not created")
    new_ssh = new_session["ssh"]
    new_transport = new_ssh.client.get_transport()
    attached = session_state.get("session") is new_session and terminal._ssh is new_ssh
    connected = bool(new_transport and new_transport.is_active())
    generation_advanced = (
        disconnect_generation > generation_before
        and terminal._generation > disconnect_generation
    )

    if stale_subscriber is not None:
        stale_subscriber("PACKAGED-STALE-OUTPUT-MUST-DROP")
        wx.Yield()
    buffer = terminal.hpc_get_buffer_text() or ""
    stale_output_rejected = "PACKAGED-STALE-OUTPUT-MUST-DROP" not in buffer
    return {
        "session": new_session,
        "disconnected_state_cleared": disconnected,
        "fresh_session_attached": attached,
        "fresh_ssh_transport_active": connected,
        "terminal_generation_advanced": generation_advanced,
        "stale_output_rejected": stale_output_rejected,
    }
