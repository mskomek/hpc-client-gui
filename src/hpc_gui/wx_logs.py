"""wx logs/diagnostics model using the existing bounded redaction services."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hpc_gui.core.diagnostics import MAX_LOG_LINES, create_diagnostic_bundle
from hpc_gui.core.log_redaction import redact_text

_LOG_TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ")
_LOG_RECORD = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| "
    r"(?P<level>[A-Z]+) \| [^|]+ \| (?P<message>.*)$"
)
_DIRECT_TIMESTAMP = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (?P<message>.*)$"
)
_SSH_COMMAND = re.compile(r"^SSH\$\s+(?P<command>.+?)\s*$")
_SSH_SUCCESS = re.compile(r"^\[exit=0 duration=[0-9]+(?:\.[0-9]+)?s\]$")
_SSH_RESULT = re.compile(r"^\[(?:exit=\d+|timeout\b.*exit=\d+).*$", re.IGNORECASE)
_SSH_FAMILY = frozenset({"squeue", "sacct", "tail"})
_SHELL_OPERATORS = frozenset({";", "&", "&&", "|", "||", ">", ">>", "<", "<<", "2>&1", "2>", "1>"})
_ERROR_TEXT = re.compile(
    r"\b(?:channel open failed|authentication (?:failure|failed|timeout)|"
    r"connection (?:failure|failed|timeout|lost)|timed out|reconnecting|"
    r"traceback \(most recent call last\))\b",
    re.IGNORECASE,
)
_SEVERITY_TEXT = re.compile(r"^\s*(?:WARNING|WARN|ERROR|CRITICAL|FATAL)(?:\b|:)", re.IGNORECASE)


@dataclass(frozen=True)
class LogDisplayEntry:
    """One raw log line or an expandable run of successful polling commands."""

    raw_lines: tuple[str, ...]
    command_family: str | None = None
    command_count: int = 1
    first_timestamp: str | None = None
    last_timestamp: str | None = None

    @property
    def is_group(self) -> bool:
        return self.command_family is not None


@dataclass(frozen=True)
class _SuccessfulCommand:
    family: str
    raw_lines: tuple[str, ...]
    timestamp: str | None
    end_index: int


def _log_parts(line: str) -> tuple[str | None, str | None, str]:
    content = line.rstrip("\r\n")
    match = _LOG_RECORD.match(content)
    if match:
        return match.group("timestamp"), match.group("level"), match.group("message")
    match = _DIRECT_TIMESTAMP.match(content)
    if match:
        return match.group("timestamp"), None, match.group("message")
    return None, None, content


def _command_family(command: str) -> str | None:
    """Return a supported direct command, rejecting shell composition."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    if not tokens or tokens[0] not in _SSH_FAMILY:
        return None
    if any(
        token in _SHELL_OPERATORS
        or (token and all(character in ";&|<>" for character in token))
        or "$(" in token
        or "`" in token
        for token in tokens
    ):
        return None
    return tokens[0]


def _is_error_record(level: str | None, message: str) -> bool:
    if level and level.upper() in {"WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}:
        return True
    return bool(
        _SEVERITY_TEXT.match(message)
        or message.lstrip().upper().startswith("STDERR:")
        or _ERROR_TEXT.search(message)
    )


def _successful_command_at(lines: list[str], start: int) -> _SuccessfulCommand | None:
    timestamp, _level, message = _log_parts(lines[start])
    command_match = _SSH_COMMAND.match(message)
    if command_match is None:
        return None
    family = _command_family(command_match.group("command"))
    if family is None:
        return None

    for index in range(start + 1, len(lines)):
        _line_timestamp, level, next_message = _log_parts(lines[index])
        if next_message.startswith("SSH$") or _is_error_record(level, next_message):
            return None
        if _SSH_SUCCESS.fullmatch(next_message.strip()):
            return _SuccessfulCommand(family, tuple(lines[start:index + 1]), timestamp, index)
        if _SSH_RESULT.match(next_message.strip()):
            return None
    return None


def group_repeated_ssh_commands(text: str) -> tuple[LogDisplayEntry, ...]:
    """Group adjacent successful squeue/sacct/tail calls without dropping lines.

    Command and result records must form an unambiguous, successful pair. Any
    other line, command family, warning, error, timeout, or stderr flushes the
    pending run. Each grouped entry retains every original physical line.
    """
    lines = str(text or "").splitlines(keepends=True)
    entries: list[LogDisplayEntry] = []
    pending: list[_SuccessfulCommand] = []

    def flush_pending() -> None:
        if len(pending) >= 2:
            entries.append(
                LogDisplayEntry(
                    raw_lines=tuple(line for command in pending for line in command.raw_lines),
                    command_family=pending[0].family,
                    command_count=len(pending),
                    first_timestamp=pending[0].timestamp,
                    last_timestamp=pending[-1].timestamp,
                )
            )
        else:
            for command in pending:
                entries.extend(LogDisplayEntry((line,)) for line in command.raw_lines)
        pending.clear()

    index = 0
    while index < len(lines):
        command = _successful_command_at(lines, index)
        if command is None:
            flush_pending()
            entries.append(LogDisplayEntry((lines[index],)))
            index += 1
            continue
        if pending and pending[0].family != command.family:
            flush_pending()
        pending.append(command)
        index = command.end_index + 1

    flush_pending()
    return tuple(entries)


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


__all__ = [
    "LogDisplayEntry",
    "WxLogsModel",
    "collapse_repeated_log_lines",
    "group_repeated_ssh_commands",
    "resolve_active_logs_dir",
]
