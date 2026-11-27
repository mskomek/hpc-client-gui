"""Compatibility entrypoint for direct imports; V2 is always wxPython."""
from __future__ import annotations

from hpc_gui.wx_shell import main as main

__all__ = ["main"]
