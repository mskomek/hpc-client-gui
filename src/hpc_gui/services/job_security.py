"""Secret-safe handling for persisted job scripts and snapshots."""

from __future__ import annotations

import re


_SENSITIVE_KEY = re.compile(
    r"(?i)(password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key|credential)"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?ix)(?P<prefix>"
    r"--[\w.-]*(?:password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key)"
    r"[\w.-]*\s*(?:=\s*|\s+)|"
    r"[\"']?\b[\w.-]*(?:password|passwd|token|secret|api[_-]?key|access[_-]?key|private[_-]?key)"
    r"[\w.-]*\b[\"']?\s*(?:=|:)\s*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)"
)


def is_sensitive_key(value: str) -> bool:
    return bool(_SENSITIVE_KEY.search(str(value or "")))


def redact_sensitive_text(value: str) -> str:
    """Redact sensitive assignments/options while preserving quote shape."""
    def replace(match: re.Match[str]) -> str:
        secret = match.group("value")
        quote = secret[0] if len(secret) >= 2 and secret[0] == secret[-1] and secret[0] in "\"'" else ""
        return f"{match.group('prefix')}{quote}[REDACTED]{quote}"

    return _SECRET_ASSIGNMENT.sub(replace, str(value or ""))


__all__ = ["is_sensitive_key", "redact_sensitive_text"]
