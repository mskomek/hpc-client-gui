"""Lazy launcher for the configured desktop GUI runtime (wx-only)."""


def launch_gui() -> int:
    """Start the configured desktop GUI without importing it into CLI startup."""
    from hpc_gui.wx_shell import main

    return int(main())
