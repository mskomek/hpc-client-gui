"""Lazy launcher for the configured desktop GUI runtime."""

from hpc_gui.runtime import DEFAULT_GUI_RUNTIME


def launch_gui() -> int:
    """Start the configured desktop GUI without importing it into CLI startup."""
    if DEFAULT_GUI_RUNTIME == "wx":
        from hpc_gui.wx_shell import main
    else:
        from hpc_gui.app import main

    return int(main())
