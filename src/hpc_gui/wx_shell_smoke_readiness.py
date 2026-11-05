"""Bounded WebView startup timing for the real packaged wx smoke gate."""

from __future__ import annotations

from typing import Any


def observe_terminal_readiness(
    state: dict[str, Any], session_state: dict[str, Any], now: float,
):
    """Return current terminal, allowing one post-ready functional-test window.

    A bridge-ready message can arrive at the deadline on a busy Windows
    runner. The real PTY/SSH checks still run, and a terminal that never
    becomes ready cannot extend its deadline.
    """
    panel = session_state.get("_embedded_terminal_panel")
    if (state.get("phase") == 0 and panel is not None
            and getattr(panel, "_ready", False)
            and getattr(panel, "_is_parity", False)
            and not state.get("terminal_ready_budget_granted", False)):
        state["terminal_ready_budget_granted"] = True
        state["deadline"] = now + 25
    return panel
