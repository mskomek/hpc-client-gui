"""Rule-pack parsing for the declarative lint engine.

Converts installed plugin lint indexes and rule files into compiled,
engine-ready rule packs. All validation happens here; malformed packs are
rejected with :class:`RulePackError` instead of crashing callers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hpc_gui import __version__
from hpc_gui.lint.engine import LintError
from hpc_gui.lint.models import CompiledRule, RulePack, Severity
from hpc_gui.plugins.loader import load_installed_plugins

MAX_RULES_PER_PACK = 512
MAX_PATTERN_LENGTH = 512
MAX_REGEX_LENGTH = 1024

# Engine primitives plus the registry-side vocabulary aliases.
_KIND_ALIASES = {
    "contains": "contains",
    "required-keyword": "contains",
    "not_contains": "not_contains",
    "forbidden-keyword": "not_contains",
    "regex": "regex",
    "regex-block": "regex",
    "line_regex": "line_regex",
    "regex-line": "line_regex",
    "ordered_patterns": "ordered_patterns",
    "ordered-patterns": "ordered_patterns",
    "count": "count",
}

_SEVERITIES = {severity.value for severity in Severity}

# Narrow, documented `when` grammar. Each key is matched against LintContext.
_WHEN_KEYS = frozenset({"target_version", "remote_platform"})


class RulePackError(ValueError):
    """Raised when a lint index or rule file is malformed."""


@dataclass(frozen=True)
class _RawRule:
    id: str
    severity: str
    kind: str
    message: str
    values: tuple[str, ...]
    category: str
    explanation: str
    suggested_fix: str
    documentation_url: str
    when: dict
    min_count: int | None
    max_count: int | None


def _require_str(value, label: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise RulePackError(f"{label} must be a non-empty string")
    return value


def parse_rule(raw: Any, source_label: str) -> CompiledRule:
    if not isinstance(raw, dict):
        raise RulePackError(f"{source_label}: rule must be a JSON object")

    rule_id = _require_str(raw.get("id"), f"{source_label}: rule id")
    severity_raw = raw.get("severity")
    if severity_raw not in _SEVERITIES:
        raise RulePackError(f"{source_label} [{rule_id}]: unsupported severity {severity_raw!r}")

    match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
    kind_raw = match.get("kind") or raw.get("kind")
    kind = _KIND_ALIASES.get(kind_raw)
    if kind is None:
        raise RulePackError(
            f"{source_label} [{rule_id}]: unsupported rule kind {kind_raw!r}"
        )

    message = _require_str(raw.get("message"), f"{source_label} [{rule_id}]: message")

    values: list[str] = []
    if kind == "ordered_patterns":
        patterns = match.get("patterns") or raw.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            raise RulePackError(
                f"{source_label} [{rule_id}]: ordered_patterns needs a non-empty 'patterns' list"
            )
        for pattern in patterns:
            value = _require_str(pattern, f"{source_label} [{rule_id}]: pattern")
            if len(value) > MAX_PATTERN_LENGTH:
                raise RulePackError(
                    f"{source_label} [{rule_id}]: pattern exceeds the length limit"
                )
            values.append(value)
    else:
        value = match.get("value", raw.get("pattern", raw.get("value")))
        value = _require_str(value, f"{source_label} [{rule_id}]: match value")
        if len(value) > MAX_REGEX_LENGTH:
            raise RulePackError(
                f"{source_label} [{rule_id}]: match value exceeds the length limit"
            )
        if kind in ("regex", "line_regex"):
            try:
                re.compile(value)
            except re.error as exc:
                raise RulePackError(
                    f"{source_label} [{rule_id}]: invalid regex ({exc})"
                ) from exc
        values.append(value)

    min_count = max_count = None
    if kind == "count":
        minimum = match.get("min", raw.get("min"))
        maximum = match.get("max", raw.get("max"))
        if isinstance(minimum, int) and not isinstance(minimum, bool):
            min_count = minimum
        if isinstance(maximum, int) and not isinstance(maximum, bool):
            max_count = maximum
        if min_count is None and max_count is None:
            raise RulePackError(
                f"{source_label} [{rule_id}]: count needs a 'min' or 'max'"
            )

    if kind == "ordered_patterns":
        require_all_probe = match.get("require_all", raw.get("require_all"))
        if require_all_probe is not None and not isinstance(require_all_probe, bool):
            raise RulePackError(
                f"{source_label} [{rule_id}]: require_all must be a boolean"
            )

    when_raw = raw.get("when")
    when = when_raw if isinstance(when_raw, dict) else {}
    unknown_when = set(when) - _WHEN_KEYS
    if unknown_when:
        raise RulePackError(
            f"{source_label} [{rule_id}]: unsupported condition keys {sorted(unknown_when)}"
        )
    target = when.get("target_version")
    if target is not None and (
        not isinstance(target, str) or not re.fullmatch(r"\d+(?:\.\d+){0,2}(?:\.\*)?", target)
    ):
        raise RulePackError(
            f"{source_label} [{rule_id}]: invalid when.target_version {target!r}"
        )
    remote_platform = when.get("remote_platform")
    if remote_platform is not None and (
        not isinstance(remote_platform, str) or not remote_platform.strip()
    ):
        raise RulePackError(
            f"{source_label} [{rule_id}]: when.remote_platform must be a non-empty string"
        )

    require_all = match.get("require_all", raw.get("require_all"))
    if require_all is not None and kind != "ordered_patterns":
        raise RulePackError(
            f"{source_label} [{rule_id}]: require_all is only valid for ordered_patterns"
        )

    return CompiledRule(
        id=rule_id,
        severity=Severity(severity_raw),
        kind=kind,
        message=message,
        values=tuple(values),
        category=str(raw.get("category") or ""),
        explanation=str(raw.get("explanation") or ""),
        suggested_fix=str(raw.get("suggested_fix") or ""),
        documentation_url=str(raw.get("documentation_url") or ""),
        when=dict(when),
        min_count=min_count,
        max_count=max_count,
        require_all=True if require_all is None else bool(require_all),
    )


def parse_rule_pack(
    index: dict,
    *,
    plugin_id: str,
    plugin_version: str,
    package_dir: Path | None = None,
) -> RulePack:
    """Build a RulePack from a validated lint index mapping."""
    if not isinstance(index, dict):
        raise RulePackError("lint index must be a JSON object")
    linter_id = index.get("tool") or index.get("linter_id")
    name = index.get("name") or linter_id
    linter_id = _require_str(linter_id, "lint index: tool/linter_id")
    name = _require_str(name, "lint index: name")

    patterns_raw = index.get("file_patterns")
    if patterns_raw is None:
        patterns_raw = []
    if not isinstance(patterns_raw, list) or not all(isinstance(p, str) for p in patterns_raw):
        raise RulePackError("lint index: file_patterns must be a list of strings")

    rules: list[CompiledRule] = []
    rules_refs = index.get("rules")
    if isinstance(rules_refs, list):
        # Summary form: inline rule objects directly under 'rules'.
        for position, raw_rule in enumerate(rules_refs):
            rules.append(parse_rule(raw_rule, f"lint index rule #{position + 1}"))
    elif rules_refs is not None:
        raise RulePackError("lint index: 'rules' must be a list")

    rule_files = index.get("rule_files")
    if isinstance(rule_files, list):
        if package_dir is None:
            raise RulePackError("lint index references rule_files but no package dir is given")
        for reference in rule_files:
            if not isinstance(reference, dict):
                raise RulePackError("lint index: each rule_files entry must be an object")
            rel = reference.get("path")
            rel = _require_str(rel, "lint index: rule_files path")
            if rel.startswith("/") or ".." in rel.split("/") or "\\" in rel:
                raise RulePackError(f"lint index: unsafe rule file path {rel!r}")
            expected_sha = reference.get("sha256")
            path = package_dir / rel
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise RulePackError(f"cannot read rule file '{rel}': {exc}") from exc
            if expected_sha and hashlib.sha256(payload).hexdigest() != expected_sha:
                raise RulePackError(f"rule file '{rel}' failed SHA-256 verification")
            try:
                document = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RulePackError(f"rule file '{rel}' is not valid UTF-8 JSON: {exc}") from exc
            if not isinstance(document, dict):
                raise RulePackError(f"rule file '{rel}' must contain a JSON object")
            file_rules = document.get("rules")
            if not isinstance(file_rules, list):
                raise RulePackError(f"rule file '{rel}' needs a 'rules' list")
            for position, raw_rule in enumerate(file_rules):
                rules.append(parse_rule(raw_rule, f"'{rel}' rule #{position + 1}"))

    if not rules:
        raise RulePackError("lint index provides no rules")
    if len(rules) > MAX_RULES_PER_PACK:
        raise RulePackError("lint index exceeds the maximum number of rules")

    return RulePack(
        linter_id=linter_id,
        name=str(name),
        plugin_id=plugin_id,
        plugin_version=plugin_version,
        file_patterns=tuple(str(p) for p in patterns_raw),
        rules=tuple(rules),
    )


def load_lint_packs(root: str | Path | None = None, app_version: str = __version__) -> list[RulePack]:
    """Load validated rule packs from active, compatible installed plugins."""
    packs: list[RulePack] = []
    result = load_installed_plugins(root=root, app_version=app_version)
    for installed in result.plugins:
        index = installed.lint_index
        if not isinstance(index, dict):
            continue
        try:
            packs.append(
                parse_rule_pack(
                    index,
                    plugin_id=installed.manifest.id,
                    plugin_version=installed.manifest.version,
                    package_dir=installed.directory,
                )
            )
        except (RulePackError, LintError):
            continue  # malformed pack: skip silently, never break the caller
    return packs


