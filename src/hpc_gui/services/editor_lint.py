"""Toolkit-independent editor lint pipeline and diagnostic navigation."""
from __future__ import annotations

from pathlib import Path

from hpc_gui.core.i18n import t


class EditorLintPipeline:
    def collect(self, path: str, text: str, *, plugin_id=None):
        issues = self._collect_lint_issues(path, text)
        if plugin_id is None:
            diagnostics = self._run_plugin_lint(path, text) + self._run_v2_tool_lint(path, text)
        else:
            diagnostics = self._run_plugin_lint(path, text, plugin_id=plugin_id)
            diagnostics += self._run_v2_tool_lint(path, text, plugin_id=plugin_id)
        return issues, diagnostics + self._run_cross_checks(text)

    def _run_cross_checks(self, text: str) -> list:
        """Static Slurm/Fluent resource-consistency checks on the same text."""
        from hpc_gui.lint.job_context import (
            cross_diagnostics,
            parse_fluent_launch,
            parse_slurm_context,
        )

        try:
            context = parse_slurm_context(text)
            launch = parse_fluent_launch(text)
            return cross_diagnostics(context, launch)
        except Exception:  # never break the editor on parse surprises
            return []
    def _run_plugin_lint(self, path: str, text: str, plugin_id: str | None = None) -> list:
        """Run installed declarative lint packs matching the file name."""
        from hpc_gui.lint.engine import lint_text
        from hpc_gui.lint.rulepack import load_lint_packs

        diagnostics = []
        try:
            packs = load_lint_packs()
        except Exception:
            return diagnostics
        if plugin_id is not None:
            packs = [pack for pack in packs if pack.plugin_id == plugin_id]
        matched = [pack for pack in packs if pack.matches(path)]
        for pack in matched:
            try:
                diagnostics.extend(lint_text(text, file_name=path, rule_pack=pack))
            except Exception:  # never break the editor
                continue
        return diagnostics
    def _run_v2_tool_lint(self, path: str, text: str, plugin_id: str | None = None) -> list:
        """Run Plugin API v2 linter tools for the file suffix (additive)."""
        import logging

        try:
            from hpc_gui.lint.models import Diagnostic, Severity
            from hpc_gui.plugins.linter_tools import tools_supporting_suffix
        except Exception:
            return []
        suffix = Path(path).suffix.lower()
        if not suffix:
            return []
        try:
            tools = tools_supporting_suffix(suffix)
        except Exception:
            logging.getLogger(__name__).warning(
                "v2 lint tool lookup failed for %s", path, exc_info=True
            )
            return []
        if plugin_id is not None:
            tools = [tool for tool in tools if tool.plugin_id == plugin_id]
        if not tools:
            return []
        # Collect from every supporting tool; per-tool failures are contained.
        raw_diags: list[tuple] = []  # (tool, diag)
        for tool in tools:
            try:
                from hpc_gui.plugins.linter_tools import lint_text_with_tool_for

                run = lint_text_with_tool_for(tool, text, file_name=path)
            except Exception:
                logging.getLogger(__name__).warning(
                    "v2 lint failed for %s via %s", path, tool.plugin_id, exc_info=True
                )
                continue
            # lint_text_with_tool_for returns a FileResult (editor path);
            # be tolerant if a future wrapper returns a LintRunResult or list.
            diags: list = []
            if hasattr(run, "diagnostics"):
                diags = list(getattr(run, "diagnostics") or [])
            elif hasattr(run, "files"):
                for fr in getattr(run, "files") or []:
                    diags.extend(getattr(fr, "diagnostics", []) or [])
            elif isinstance(run, list):
                diags = run
            for diag in diags:
                raw_diags.append((tool, diag))
        if not raw_diags:
            return []
        # Deduplicate by (rule_id, line, column, message); sort by position.
        seen: set[tuple] = set()
        deduped: list[tuple] = []
        for tool, diag in raw_diags:
            key = (
                getattr(diag, "code", getattr(diag, "rule_id", "V2")),
                getattr(diag, "line", None),
                getattr(diag, "column", None),
                getattr(diag, "message", str(diag)),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append((tool, diag))
        deduped.sort(
            key=lambda item: (
                getattr(item[1], "line", None) or 9999,
                getattr(item[1], "column", None) or 0,
                getattr(item[1], "code", getattr(item[1], "rule_id", "")),
            )
        )
        # When multiple tools contribute, prefix the message with the plugin id
        # so the result list stays attributable without changing the model shape.
        multi = len({t.plugin_id for t, _ in deduped}) > 1
        converted: list = []
        for tool, diag in deduped:
            try:
                severity_value = getattr(diag.severity, "value", str(diag.severity))
                severity = Severity(severity_value)
            except ValueError:
                severity = Severity.INFO
            raw_message = getattr(diag, "message", str(diag))
            message = f"[{tool.plugin_id}] {raw_message}" if multi else raw_message
            converted.append(
                Diagnostic(
                    rule_id=getattr(diag, "code", getattr(diag, "rule_id", "V2")),
                    severity=severity,
                    message=message,
                    line=getattr(diag, "line", None),
                    column=getattr(diag, "column", None),
                    end_line=getattr(diag, "end_line", getattr(diag, "endLine", None)),
                    end_column=getattr(diag, "end_column", getattr(diag, "endColumn", None)),
                    explanation=getattr(diag, "explanation", "") or "",
                    suggested_fix=getattr(diag, "suggested_fix", getattr(diag, "suggestedFix", "")) or "",
                    documentation_url=getattr(diag, "source_url", getattr(diag, "documentation_url", "")) or "",
                    plugin_id=getattr(tool, "plugin_id", ""),
                    plugin_version=getattr(tool, "version", ""),
                )
            )
        return converted
    @staticmethod
    def _lint_result_entries(issues: list[str], diagnostics: list) -> tuple[list[str], list[int]]:
        """Build display labels and 0-based navigation lines (-1 = no target)."""
        labels: list[str] = []
        positions: list[int] = []
        for issue in issues:
            labels.append(f"- {issue}")
            positions.append(-1)
        for diagnostic in sorted(diagnostics, key=lambda d: (d.line or 0, d.column or 0)):
            location = f"{diagnostic.line}:{diagnostic.column}" if diagnostic.line else "-"
            severity = (
                diagnostic.severity.value
                if hasattr(diagnostic.severity, "value")
                else str(diagnostic.severity)
            )
            labels.append(f"[{location}] {severity}: {diagnostic.message} ({diagnostic.rule_id})")
            positions.append(diagnostic.line - 1 if diagnostic.line and diagnostic.line > 0 else -1)
        return labels, positions
    def _collect_lint_issues(self, path: str, text: str) -> list[str]:
        issues: list[str] = []
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            return issues
        stripped = text.lstrip()
        if not stripped.startswith("#!"):
            issues.append(t("editor.validation_missing_shebang"))
        if "#SBATCH" not in text:
            issues.append(t("editor.validation_missing_sbatch"))
        if "USERNAME" in text or "<partition>" in text:
            issues.append(t("editor.validation_placeholders"))
        if "--time=" not in text and "\n#SBATCH -t " not in text:
            issues.append(t("editor.validation_missing_time"))
        if "--output=" not in text and "\n#SBATCH -o " not in text:
            issues.append(t("editor.validation_missing_output"))
        return issues
    def _diagnose_submit_output(self, details: str) -> str:
        msg = (details or "").lower()
        if "invalid account" in msg:
            return t("editor.submit_hint_account")
        if "invalid qos" in msg or "qos" in msg and "invalid" in msg:
            return t("editor.submit_hint_qos")
        if "time limit" in msg or "walltime" in msg or "qosmaxwalldurationperjoblimit" in msg:
            return t("editor.submit_hint_time")
        if "more processors requested than permitted" in msg or "assocmaxcpuperjoblimit" in msg:
            return t("editor.submit_hint_cpu")
        if "gres" in msg and ("invalid" in msg or "requested node configuration is not available" in msg):
            return t("editor.submit_hint_gpu")
        return t("editor.submit_failed_hint")
