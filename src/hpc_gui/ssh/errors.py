"""Shared SSH session exception contracts."""


class X11Unavailable(RuntimeError):
    """A local display or authenticated SSH X11 request is unavailable."""
