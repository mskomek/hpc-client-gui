"""wx logs/diagnostics model using the existing bounded redaction services."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from hpc_gui.core.diagnostics import MAX_LOG_LINES, create_diagnostic_bundle
from hpc_gui.core.log_redaction import redact_text

_LOG_TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ")


def collapse_repeated_log_lines(text: str, summary: str) -> str:
    """Collapse adjacent identical messages while preserving their first line."""
    lines = str(text or "").splitlines(keepends=True)
    collapsed: list[str] = []
    index = 0
    while index < len(lines):
        first = lines[index]
        content = first.rstrip("\r\n")
        key = _LOG_TIMESTAMP_PREFIX.sub("", content)
        end = index + 1
        while end < len(lines):
            next_content = lines[end].rstrip("\r\n")
            if _LOG_TIMESTAMP_PREFIX.sub("", next_content) != key:
                break
            end += 1
        count = end - index
        if count > 1:
            ending = "\n" if first.endswith(("\n", "\r")) else ""
            collapsed.append(f"{content}  [{summary.format(count=count - 1)}]{ending}")
        else:
            collapsed.append(first)
        index = end
    return "".join(collapsed)


class WxLogsModel:
    def __init__(self, log_path: str | Path, *, bundle: Callable[[str], Path] | None = None) -> None:
        self.log_path = Path(log_path)
        self.bundle = bundle or create_diagnostic_bundle
        self.text = ""

    def logs_dir(self) -> Path:
        """Return the actual active log directory for the current runtime.

        Resolved lazily at call time (not cached at construction) so the
        value stays correct after wx reparenting/runtime migration or an
        isolated-config-root switch changes the active log location.
        """
        return Path(self.log_path).expanduser().resolve().parent

    def refresh(self) -> str:
        if not self.log_path.is_file():
            self.text = ""
            return self.text
        lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        self.text = redact_text("".join(lines[-MAX_LOG_LINES:]))
        return self.text

    def copy_all(self) -> str:
        return self.text

    def collapsed_text(self, summary: str) -> str:
        return collapse_repeated_log_lines(self.text, summary)

    def copy_selection(self, start: int, end: int) -> str:
        return self.text[max(0, start):max(0, end)]

    def export_bundle(self, destination: str) -> Path:
        return self.bundle(destination)


def resolve_active_logs_dir() -> Path:
    """Return the current active log directory (fresh, never cached).

    Evaluated at call time so the result reflects runtime migration and
    isolated-config-root switches instead of a stale construction-time path.
    """
    from hpc_gui.core.logging import log_path as default_log_path

    return Path(default_log_path()).expanduser().resolve().parent


__all__ = ["WxLogsModel", "collapse_repeated_log_lines", "resolve_active_logs_dir"]
