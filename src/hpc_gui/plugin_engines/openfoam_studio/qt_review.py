"""Validate and Allrun-draft review for the Qt Case Studio page.

Validation runs only through the installed API 3 OpenFOAM linter's
verified-byte path (``linter_tools.load_tool_for_plugin`` over the exact
linter identity; empty pins fail closed). Allrun text renders only from
the approved host command catalog and workflow plan and is stored only
through the create-only store: an existing Allrun is preserved and
reported, never overwritten. Draft review never submits jobs.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout

_LINTER_ID = "org.hpcclient.openfoamlint"


def _resolve_linter_tool():
    """Return the verified linter tool for the exact linter identity, or None."""
    try:
        from hpc_gui.plugins.linter_tools import load_tool_for_plugin
        from hpc_gui.plugins.loader import load_installed_plugins
    except Exception:
        return None
    try:
        result = load_installed_plugins()
    except Exception:
        return None
    installed = next(
        (
            plugin
            for plugin in result.plugins
            if getattr(getattr(plugin, "manifest", None), "id", None) == _LINTER_ID
            and getattr(plugin.manifest, "plugin_api", None) == 3
        ),
        None,
    )
    if installed is None:
        return None
    try:
        tool = load_tool_for_plugin(installed)
    except Exception:
        return None
    if getattr(tool, "plugin_id", None) != _LINTER_ID:
        return None
    return tool


def validate_case(page) -> bool:
    """Lint the open case through verified linter bytes (read-only)."""
    workspace = page.workspace
    if workspace is None:
        page.status.setText("No case open")
        return False
    tool = _resolve_linter_tool()
    if tool is None:
        page.validation.setPlainText("Linter unavailable: install the OpenFOAM linter.")
        page.bottom.setCurrentWidget(page.validation)
        page.status.setText("Validation unavailable: no verified linter engine")
        return False
    try:
        module = sys.modules.get(getattr(tool, "module_name", ""))
        lint_files = getattr(module, "lint_files", None) if module is not None else None
        if not callable(lint_files):
            raise RuntimeError("verified linter engine has no case lint entrypoint")
        contents = {name: document.to_bytes() for name, document in workspace.documents.items()}
        root = None if workspace.remote else workspace.root
        result = lint_files(contents, root=root, case_context=True)
    except Exception as exc:
        page._show_error(f"Validation failed: {exc}")
        return False
    page.validation.setPlainText(result.to_markdown())
    page.bottom.setCurrentWidget(page.validation)
    page.status.setText(f"Validation complete: {len(result.diagnostics)} finding(s)")
    return True


def build_allrun_script(page) -> str:
    """Render the draft Allrun from catalog + plan; raises on any violation."""
    from .run_script import render_allrun

    workspace = page.workspace
    if workspace is None:
        raise ValueError("no case is open")
    if workspace.read_only:
        raise PermissionError("case workspace is a read-only snapshot")
    if workspace.modified_paths():
        raise ValueError("save all dictionaries before generating Allrun")
    control = page.documents.get("system/controlDict")
    solver = control.parsed.value("application") if control else None
    solver = str(solver or "").strip().strip("\"'")
    return render_allrun(solver, page.workflow_plan.steps, page.command_catalog["commands"])


def open_draft_review(page) -> bool:
    """Show the reviewable Allrun draft; creation stays create-only, never submit."""
    try:
        script = build_allrun_script(page)
    except Exception as exc:
        page._show_error(f"Could not create Allrun: {exc}")
        return False
    dialog = QDialog(page)
    dialog.setWindowTitle("Job Draft (review only — nothing is submitted)")
    dialog.resize(720, 520)
    layout = QVBoxLayout(dialog)
    viewer = QTextEdit()
    viewer.setReadOnly(True)
    viewer.setPlainText(script)
    layout.addWidget(viewer)
    create_button = QPushButton("Create Allrun (create-only)")
    close_button = QPushButton("Close")
    layout.addWidget(create_button)
    layout.addWidget(close_button)
    outcome: list = []
    create_button.clicked.connect(lambda _checked=False: outcome.append(True) or dialog.accept())
    close_button.clicked.connect(dialog.reject)
    if dialog.exec() != QDialog.Accepted:
        return False
    return store_reviewed_allrun(page)


def store_reviewed_allrun(page) -> bool:
    """Persist a reviewed draft; an existing Allrun is preserved, never replaced."""
    workspace = page.workspace
    if workspace is None:
        page.status.setText("No case open")
        return False
    try:
        script = build_allrun_script(page)
    except Exception as exc:
        page._show_error(f"Could not create Allrun: {exc}")
        return False
    page.status.setText("Generating OpenFOAM Allrun ...")
    try:
        path = workspace.create_allrun(script)
    except FileExistsError as exc:
        page.status.setText(f"Allrun preserved (already exists): {exc}")
        return False
    except Exception as exc:
        page._show_error(f"Could not create Allrun: {exc}")
        return False
    page.status.setText(f"Allrun created: {path}")
    return True
