"""Lazy launcher for the configured desktop GUI runtime."""

from hpc_gui.runtime import DEFAULT_GUI_RUNTIME


def launch_gui() -> int:
    """Start the configured desktop GUI without importing it into CLI startup."""
    if DEFAULT_GUI_RUNTIME != "wx":
        raise RuntimeError("V2 requires the wx GUI runtime")
    from hpc_gui.wx_shell import main

    return int(main())
