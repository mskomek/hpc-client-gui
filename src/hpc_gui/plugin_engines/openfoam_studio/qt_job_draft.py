"""Qt job-draft flow: open a case first, then review Allrun plus wrapper.

The dialog previews the application-generated Allrun and the matching
wrapper that references it only by SHA-256. Saving is create-only: an
existing Allrun or wrapper is preserved, and the wrapper save stays
disabled until the on-disk Allrun matches the reviewed digest.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .job_draft import (
    DEFAULT_JOB_NAME,
    DEFAULT_MODULE,
    DEFAULT_TIME,
    JobSpec,
    build_draft_bundle,
    validate_job_spec,
)
from .job_draft_store import DEFAULT_JOB_FILENAME, allrun_matches, create_local_job, create_remote_job
from .qt_actions import _session_files


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def ensure_case_for_draft(page) -> bool:
    """Guide the user to open a case before any draft preview."""
    if page.workspace is not None:
        return True
    page.status.setText("No case open — choose Open Case or Open Snapshot first")
    try:
        page.case_manager_actions._open_case()
    except Exception as exc:
        page._show_error(f"Could not open case: {exc}")
    return False


def _read_spec(dialog: QDialog) -> JobSpec:
    return validate_job_spec(
        job_name=dialog._job_name.text().strip() or DEFAULT_JOB_NAME,
        nodes=int(dialog._nodes.value()),
        ntasks=int(dialog._ntasks.value()),
        time=dialog._time.text().strip() or DEFAULT_TIME,
        partition=dialog._partition.text().strip(),
        module=dialog._module.text().strip() or DEFAULT_MODULE,
    )


def _refresh_previews(page, dialog) -> object | None:
    try:
        spec = _read_spec(dialog)
    except Exception as exc:
        dialog._status.setText(f"Invalid job inputs: {exc}")
        return None
    if page.workspace is None:
        dialog._status.setText("No case open")
        return None
    if page.workspace.read_only:
        dialog._status.setText("Case is a read-only snapshot; drafts cannot be created")
        return None
    if page.workspace.modified_paths():
        dialog._status.setText("Unsaved edits: review the Diff tab and save before drafting")
        return None
    try:
        bundle = build_draft_bundle(
            page.documents, page.command_catalog, page.workflow_plan.steps, spec
        )
    except Exception as exc:
        dialog._status.setText(f"Cannot build draft: {exc}")
        return None
    dialog._allrun_view.setPlainText(bundle.allrun_text)
    dialog._slurm_view.setPlainText(bundle.slurm_text)
    dialog._status.setText(f"Solver {bundle.solver}; Allrun SHA-256 {bundle.allrun_sha256[:12]}… (review only)")
    trusted = allrun_matches(page.workspace, bundle.allrun_sha256)
    dialog._save_button.setEnabled(bool(trusted))
    if not trusted:
        dialog._status.setText(dialog._status.text() + "; create the generated Allrun first")
    dialog._bundle = bundle
    return bundle


def _create_allrun(page, dialog) -> None:
    from .qt_review import store_reviewed_allrun

    if not store_reviewed_allrun(page):
        _refresh_previews(page, dialog)
        return
    _refresh_previews(page, dialog)


def _save_wrapper(page, dialog) -> None:
    bundle = getattr(dialog, "_bundle", None) or _refresh_previews(page, dialog)
    if bundle is None:
        return
    workspace = page.workspace
    if workspace is None or workspace.read_only:
        page._show_error("Draft save needs a writable open case")
        return
    if not allrun_matches(workspace, bundle.allrun_sha256):
        dialog._status.setText("Save blocked: on-disk Allrun does not match the reviewed draft")
        dialog._save_button.setEnabled(False)
        return
    try:
        if workspace.remote:
            files = _session_files(page.session_state)
            if files is None:
                page._show_error("Remote session is unavailable; reconnect before saving")
                return
            path = create_remote_job(workspace.root, files, bundle.slurm_text, filename=DEFAULT_JOB_FILENAME)
        else:
            path = create_local_job(workspace.root, bundle.slurm_text, filename=DEFAULT_JOB_FILENAME)
    except FileExistsError as exc:
        dialog._status.setText(f"Wrapper preserved (already exists): {exc}")
        return
    except Exception as exc:
        page._show_error(f"Could not save job wrapper: {exc}")
        return
    dialog._status.setText(f"Job wrapper created: {path} (review only, nothing submitted)")
    dialog._save_button.setEnabled(False)


def open_job_draft(page) -> bool:
    """Prompt for a case when needed, then show the reviewable job draft."""
    if not ensure_case_for_draft(page):
        return False
    dialog = QDialog(page)
    dialog.setWindowTitle("Job Draft (review only — nothing is submitted)")
    dialog.resize(860, 640)
    layout = QVBoxLayout(dialog)
    form = QFormLayout()
    dialog._job_name = QLineEdit(DEFAULT_JOB_NAME)
    dialog._nodes = QSpinBox()
    dialog._nodes.setRange(1, 100000)
    dialog._nodes.setValue(1)
    dialog._ntasks = QSpinBox()
    dialog._ntasks.setRange(1, 100000)
    dialog._ntasks.setValue(1)
    dialog._time = QLineEdit(DEFAULT_TIME)
    dialog._partition = QLineEdit()
    dialog._module = QLineEdit(DEFAULT_MODULE)
    form.addRow("Job name", dialog._job_name)
    form.addRow("Nodes", dialog._nodes)
    form.addRow("Tasks", dialog._ntasks)
    form.addRow("Walltime", dialog._time)
    form.addRow("Partition", dialog._partition)
    form.addRow("Module", dialog._module)
    layout.addLayout(form)
    dialog._status = QLabel("Review the generated scripts before saving")
    layout.addWidget(dialog._status)
    layout.addWidget(QLabel("Generated Allrun (review)"))
    dialog._allrun_view = QTextEdit()
    dialog._allrun_view.setReadOnly(True)
    layout.addWidget(dialog._allrun_view)
    layout.addWidget(QLabel("Generated Slurm wrapper (review)"))
    dialog._slurm_view = QTextEdit()
    dialog._slurm_view.setReadOnly(True)
    layout.addWidget(dialog._slurm_view)
    buttons = QHBoxLayout()
    refresh_button = QPushButton("Refresh Preview")
    create_button = QPushButton("Create Allrun (create-only)")
    dialog._save_button = QPushButton("Save Job Wrapper (create-only)")
    dialog._save_button.setEnabled(False)
    close_button = QPushButton("Close")
    for button in (refresh_button, create_button, dialog._save_button, close_button):
        buttons.addWidget(button)
    layout.addLayout(buttons)
    dialog._bundle = None
    refresh_button.clicked.connect(lambda _checked=False: _refresh_previews(page, dialog))
    create_button.clicked.connect(lambda _checked=False: _create_allrun(page, dialog))
    dialog._save_button.clicked.connect(lambda _checked=False: _save_wrapper(page, dialog))
    close_button.clicked.connect(dialog.reject)
    _refresh_previews(page, dialog)
    return dialog.exec() == QDialog.Accepted
