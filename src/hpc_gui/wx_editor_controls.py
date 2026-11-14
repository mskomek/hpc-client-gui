"""Availability policy for editor header actions."""

from __future__ import annotations


def update_action_buttons(bindings, resolve_callback, *, in_flight: bool) -> None:
    """Enable only editor actions with a usable host callback."""
    for button, name, direct in bindings:
        callback = resolve_callback(name, direct)
        try:
            button.Enable(bool(callback) and not in_flight)
        except Exception:
            try:
                button.Disable()
            except Exception:
                pass
