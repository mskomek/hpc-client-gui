"""Rule severity / enable-disable / suppress-with-reason policy (W65 LINT-013, G38).

Studio-independent: imports only the lint engine, never the Studio plugin.
Suppression requires a reason string and an anchor; bare wildcards are
rejected so findings cannot be silently waived.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LintPolicy:
    disabled: set[str] = field(default_factory=set)
    severity_overrides: dict[str, str] = field(default_factory=dict)
    suppressions: list[dict] = field(default_factory=list)

    def disable(self, rule_id: str) -> None:
        self.disabled.add(_require_rule(rule_id))

    def enable(self, rule_id: str) -> None:
        self.disabled.discard(_require_rule(rule_id))

    def set_severity(self, rule_id: str, severity: str) -> None:
        _require_rule(rule_id)
        if severity not in ("error", "warning", "info"):
            raise ValueError(f"severity '{severity}' must be error|warning|info")
        self.severity_overrides[rule_id] = severity

    def suppress(self, rule_id: str, *, path: str, line: int, reason: str) -> None:
        _require_rule(rule_id)
        if not path or not reason.strip():
            raise ValueError("suppression requires a file anchor and a non-empty reason")
        if line < 1:
            raise ValueError("suppression line must be >= 1")
        self.suppressions.append({"rule": rule_id, "path": path,
                                  "line": line, "reason": reason.strip()})

    def suppressed(self, rule_id: str, path: str, line: int) -> str | None:
        for entry in self.suppressions:
            if (entry["rule"], entry["path"], entry["line"]) == (rule_id, path, line):
                return entry["reason"]
        return None

    def apply(self, diagnostics: list) -> list:
        """Filter + re-severity diagnostics. Suppressed items are dropped
        with their reason retained in the returned ``(diag, reason)`` map via
        ``diag.fix_preview`` suffix? No: returns kept diags; use
        :meth:`suppressed` for audit of dropped items."""
        kept = []
        for diag in diagnostics:
            rule = diag.rule if hasattr(diag, "rule") else diag["rule"]
            path = diag.file if hasattr(diag, "file") else diag["file"]
            line = diag.line if hasattr(diag, "line") else diag["line"]
            if rule in self.disabled:
                continue
            if self.suppressed(rule, path, line) is not None:
                continue
            sev = self.severity_overrides.get(rule)
            if sev is not None:
                if hasattr(diag, "severity"):
                    import dataclasses
                    diag = dataclasses.replace(diag, severity=sev)
                else:
                    diag = dict(diag, severity=sev)
            kept.append(diag)
        return kept


def _require_rule(rule_id: str) -> str:
    from hpc_gui.plugins.openfoam_lint.api import rule_catalog
    known = {entry["id"] for entry in rule_catalog()}
    if rule_id not in known:
        raise ValueError(f"unknown rule '{rule_id}' (no silent policy for unlisted rules)")
    return rule_id
