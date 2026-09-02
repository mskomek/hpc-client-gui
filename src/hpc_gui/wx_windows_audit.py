"""Offline Windows wx migration audit checks."""

from __future__ import annotations

import importlib
from dataclasses import dataclass

from hpc_gui.services.geometry_policy import LAYOUT_ACCEPTANCE_MATRIX
from hpc_gui.wx_local_files import file_url_payload
from hpc_gui.wx_terminal import TerminalModel


@dataclass(frozen=True)
class AuditResult:
    name: str
    passed: bool
    detail: str = ""


def run_audit() -> tuple[AuditResult, ...]:
    checks = []
    try:
        wx = importlib.import_module("wx")
        checks.append(AuditResult("wx import", True, wx.version()))
    except ImportError:
        checks.append(AuditResult("wx import", False, "wxPython unavailable"))
    checks.append(AuditResult("geometry matrix", len(LAYOUT_ACCEPTANCE_MATRIX) >= 5))
    checks.append(AuditResult("file URL payload", file_url_payload([]) == ""))
    sent = []
    TerminalModel(sent.append).key_input("C")
    checks.append(AuditResult("terminal interrupt", sent == ["\x03"]))
    return tuple(checks)


__all__ = ["AuditResult", "run_audit"]
