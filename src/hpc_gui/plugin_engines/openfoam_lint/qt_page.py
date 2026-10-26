"""Qt Linter page for bounded local and authenticated SFTP validation."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from threading import Event

from PySide6.QtCore import QFileSystemWatcher, Qt, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from hpc_gui.core.i18n import t

from .lint_worker import LintTask


def _remote_files(session_state):
    session = session_state.get("session") if isinstance(session_state, dict) else None
    if isinstance(session, dict):
        return session.get("files")
    return getattr(session, "files", None)


def _local_finding_path(raw: str, roots: tuple[str, ...]) -> str:
    candidate = Path(raw)
    if candidate.is_absolute():
        return str(candidate)
    for value in roots:
        root = Path(value)
        if root.is_dir():
            child = root / Path(*PurePosixPath(raw).parts)
            if child.is_file():
                return str(child)
    return raw


def create_qt_page(parent=None, *, initial_paths=(), session_state=None, host_window=None):
    """Create a visible, read-only lint UI with cancellation and stale tracking."""
    from PySide6.QtWidgets import QHeaderView, QAbstractItemView

    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    status = QLabel(t("openfoam.static_only"))
    paths = QListWidget()
    for path in initial_paths:
        paths.addItem(str(path))
    remote_files = _remote_files(session_state)
    remote_context = (
        isinstance(session_state, dict) and session_state.get("remote") is True
    )
    remote_mode = remote_files is not None or remote_context

    add_file = QPushButton(t("openfoam.add_file"))
    add_case = QPushButton(t("openfoam.add_case"))
    run = QPushButton(t("openfoam.validate"))
    cancel = QPushButton(t("openfoam.cancel"))
    cancel.setEnabled(False)
    actions = QHBoxLayout()
    for control in (add_file, add_case, run, cancel):
        actions.addWidget(control)
    layout.addWidget(status)
    layout.addLayout(actions)
    layout.addWidget(paths)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels([
        t("openfoam.severity"), t("openfoam.rule"), t("openfoam.file"),
        t("openfoam.line"), t("openfoam.finding"),
    ])
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    table.itemDoubleClicked.connect(lambda item: open_finding(item.row()))
    layout.addWidget(table)

    watcher = QFileSystemWatcher(widget)
    worker_pool = QThreadPool.globalInstance()
    task_state = {
        "token": 0, "task": None, "cancel_event": None,
        "stale": False, "has_result": False,
    }
    host = host_window

    def mark_stale(_path=None):
        if task_state["task"] is not None or task_state["has_result"]:
            task_state["stale"] = True
            status.setText(t("openfoam.results_stale"))

    watcher.fileChanged.connect(mark_stale)
    watcher.directoryChanged.connect(mark_stale)

    def set_watch_paths(local_paths, result_paths=()):
        existing = watcher.files() + watcher.directories()
        if existing:
            watcher.removePaths(existing)
        candidates = set()
        for raw in (*local_paths, *result_paths):
            try:
                path = Path(raw)
                if path.exists() and not path.is_symlink():
                    candidates.add(str(path))
                    if path.is_file():
                        candidates.add(str(path.parent))
            except OSError:
                continue
        if candidates:
            watcher.addPaths(sorted(candidates))

    def add_paths(selected):
        existing = {paths.item(index).text() for index in range(paths.count())}
        for item in selected:
            value = str(item)
            if value not in existing:
                paths.addItem(value)
                existing.add(value)

    def choose_files():
        selected, _filter = QFileDialog.getOpenFileNames(
            widget, t("openfoam.add_file"), "", t("openfoam.dictionary_filter")
        )
        add_paths(selected)

    def choose_case():
        selected = QFileDialog.getExistingDirectory(widget, t("openfoam.add_case"))
        if selected:
            add_paths([selected])

    def set_busy(busy: bool):
        task_state["task"] = task_state["task"] if busy else None
        add_file.setEnabled(not busy and not remote_mode)
        add_case.setEnabled(not busy and not remote_mode)
        run.setEnabled(not busy)
        cancel.setEnabled(busy)

    def show_result(result):
        table.setRowCount(0)
        roots = tuple(paths.item(index).text() for index in range(paths.count()))
        for diagnostic in result.diagnostics:
            path = diagnostic.path
            if not path.startswith("/") and not Path(path).is_absolute():
                path = _local_finding_path(path, roots)
            row = table.rowCount()
            table.insertRow(row)
            values = (
                diagnostic.severity, diagnostic.rule_id, path,
                str(diagnostic.line), diagnostic.message,
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, (path, diagnostic.line))
                table.setItem(row, column, cell)
        status.setText(t("openfoam.lint_summary").format(
            files=len(result.files_checked), errors=result.errors, warnings=result.warnings
        ))
        if not result.diagnostics:
            status.setText(t("openfoam.no_findings"))
        task_state["stale"] = False
        task_state["has_result"] = True
        if not remote_mode:
            set_watch_paths(roots, result.files_checked)

    def completed(token, result):
        if token != task_state["token"]:
            return
        set_busy(False)
        if task_state["stale"]:
            show_result(result)
            task_state["stale"] = True
            status.setText(t("openfoam.results_stale"))
            return
        show_result(result)

    def failed(token, message):
        if token != task_state["token"]:
            return
        set_busy(False)
        status.setText(t("openfoam.lint_failed").format(error=message))

    def cancelled(token):
        if token != task_state["token"]:
            return
        set_busy(False)
        status.setText(t("openfoam.cancelled"))

    def validate():
        selected = tuple(paths.item(index).text() for index in range(paths.count()))
        if not selected:
            status.setText(t("openfoam.select_path"))
            return
        if remote_mode:
            if remote_files is None:
                status.setText(t("openfoam.remote_session_missing"))
                return
            for path in selected:
                remote = PurePosixPath(path)
                if not remote.is_absolute() or ".." in remote.parts or "\\" in path or "\x00" in path:
                    status.setText(t("openfoam.remote_path_invalid"))
                    return
        else:
            for path in selected:
                if Path(path).is_absolute() is False:
                    status.setText(t("openfoam.local_path_required"))
                    return
        task_state["token"] += 1
        task_state["stale"] = False
        task_state["has_result"] = False
        event = Event()
        task_state["cancel_event"] = event
        task = LintTask(
            task_state["token"], selected,
            remote_files=remote_files if remote_mode else None,
            cancel_event=event,
        )
        task_state["task"] = task
        task.signals.finished.connect(completed)
        task.signals.failed.connect(failed)
        task.signals.cancelled.connect(cancelled)
        if not remote_mode:
            set_watch_paths(selected)
        table.setRowCount(0)
        status.setText(t("openfoam.lint_running"))
        set_busy(True)
        worker_pool.start(task)

    def request_cancel():
        event = task_state["cancel_event"]
        if event is not None:
            event.set()
            cancel.setEnabled(False)
            status.setText(t("openfoam.cancel_requested"))

    def open_finding(row: int):
        cell = table.item(row, 0)
        if cell is None or host is None:
            return
        payload = cell.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, tuple) or len(payload) != 2:
            return
        path, line = payload
        try:
            if path.startswith("/"):
                if remote_files is None:
                    return
                from .remote_case import read_remote_dictionary_text

                content = read_remote_dictionary_text(path, remote_files)
                host.open_in_editor(path, content)
            else:
                host.open_local_in_editor(path)
            editor = getattr(host, "editor", None)
            if editor is not None:
                editor.go_to_line(int(line))
        except Exception as exc:
            status.setText(t("openfoam.lint_failed").format(error=f"{type(exc).__name__}: {exc}"))

    add_file.clicked.connect(choose_files)
    add_case.clicked.connect(choose_case)
    run.clicked.connect(validate)
    cancel.clicked.connect(request_cancel)
    add_file.setEnabled(not remote_mode)
    add_case.setEnabled(not remote_mode)
    if remote_context and remote_files is None:
        status.setText(t("openfoam.remote_session_missing"))
        run.setEnabled(False)
    elif remote_mode:
        status.setText(t("openfoam.remote_selection"))
    if initial_paths:
        validate()
    return widget
