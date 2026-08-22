"""Typed models for the declarative lint engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    severity: Severity
    message: str
    category: str = ""
    source: str = ""
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    explanation: str = ""
    suggested_fix: str = ""
    documentation_url: str = ""
    plugin_id: str = ""
    plugin_version: str = ""
    target_version: str = ""


@dataclass(frozen=True)
class LintContext:
    """Optional generic context fields; rules needing missing context skip."""

    platform: str = ""
    remote_platform: str = ""
    scheduler: str = ""
    application: str = ""
    application_version: str = ""
    headless: bool | None = None
    job_script_text: str = ""
    launch_command: str = ""
    cluster_profile_id: str = ""
    cluster_plugin_id: str = ""


@dataclass(frozen=True)
class CompiledRule:
    id: str
    severity: Severity
    kind: str  # normalized engine primitive
    message: str
    values: tuple[str, ...] = ()
    category: str = ""
    explanation: str = ""
    suggested_fix: str = ""
    documentation_url: str = ""
    when: dict = field(default_factory=dict)
    min_count: int | None = None
    max_count: int | None = None
    require_all: bool = True


@dataclass(frozen=True)
class RulePack:
    linter_id: str
    name: str
    plugin_id: str
    plugin_version: str
    file_patterns: tuple[str, ...]
    rules: tuple[CompiledRule, ...]

    def matches(self, file_name: str) -> bool:
        from fnmatch import fnmatch

        if not self.file_patterns:
            return True
        lowered = (file_name or "").lower()
        return any(fnmatch(lowered, pattern.lower()) for pattern in self.file_patterns)
