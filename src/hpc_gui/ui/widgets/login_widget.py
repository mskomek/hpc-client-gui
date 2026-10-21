"""Login widget facade (Wave M01).

Thin Qt composition owner for the connection/profile/terminal surface.
Behavior lives in cohesive helpers: ``_login_ftp_mode`` (Qt-free
mock-mode detection), ``_login_terminal`` (console/key/geometry),
``_login_secrets`` (master password and saved secrets),
``_login_profiles`` (profile list/form/dialogs),
``_login_connect`` (SSH connection lifecycle) and
``_login_profile_store`` (profile persistence). This module keeps widget
construction, Qt signals and the public/private API surface
(``LoginWidget``, FTP helpers, and the methods tests and ``MainWindow``
rely on) with identical behavior.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox, QLabel,
    QListWidget, QSplitter, QPlainTextEdit,
    QSpinBox, QDoubleSpinBox
)
from PySide6.QtWidgets import QDialog as QDialog, QInputDialog as QInputDialog, QMessageBox as QMessageBox

from hpc_gui.core.i18n import t
from hpc_gui.config.models import SSHConfig
from hpc_gui.config.file_manager_profile import (
    normalize_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import (
    normalize_jump_host_settings,
)
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.services.connection_controller import ConnectionController
from hpc_gui.services.x11_runner import X11Runner
from hpc_gui.ui.widgets.terminal_input import TerminalInput
from hpc_gui.ui.widgets.terminal_widget import TerminalWidget
from hpc_gui.ui.widgets.terminal_header import TerminalHeader
from hpc_gui.ui.widgets import _login_connect as _connect
from hpc_gui.ui.widgets import _login_profiles as _profiles
from hpc_gui.ui.widgets import _login_profile_store as _store
from hpc_gui.ui.widgets import _login_retranslate as _retranslate
from hpc_gui.ui.widgets import _login_secrets as _secrets
from hpc_gui.ui.widgets import _login_terminal as _terminal
from hpc_gui.ui.widgets._login_ftp_mode import (
    FTP_TEST_HOSTS,
    FTP_TEST_MODE_ENV,
    is_ftp_mock_host,
    is_ftp_test_mode_enabled,
)
from hpc_gui.ui.widgets._login_connection_worker import ConnectionWorker as _ConnectionWorker
from hpc_gui.ui.widgets._login_compat import (
    LEGACY_EXPORTS as _LEGACY_EXPORTS,
    install_legacy_login_exports,
    resolve_legacy_export as __getattr__,  # noqa: F401 — module lazy API hook
)

__all__ = [
    "FTP_TEST_HOSTS",
    "FTP_TEST_MODE_ENV",
    "LoginWidget",
    "_ConnectionWorker",
    "QDialog",
    "QInputDialog",
    "QMessageBox",
    "is_ftp_mock_host",
    "is_ftp_test_mode_enabled",
    *_LEGACY_EXPORTS,
]


class LoginWidget(QWidget):
    """
    Sol: Profil listesi
    Sağ: Bağlantı formu + Kaydet + Konsol + SSH terminal komutu çalıştırma
    """
    session_changed = Signal(object)
    console_message = Signal(str)
    ssh_console_message = Signal(str)
    shell_output_message = Signal(str)
    ssh_disconnected = Signal(str)

    def __init__(self):
        super().__init__()
        self._x11_runner = X11Runner(log_cb=self.append_console, parent=self)

        # ---- Left: profiles
        self.profiles_list = QListWidget()
        self.profiles_list.itemSelectionChanged.connect(self.on_profile_selected)
        self.profiles_list.itemDoubleClicked.connect(self._on_profile_double_clicked)
        self.profiles_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.profiles_list.customContextMenuRequested.connect(self.show_profile_context_menu)

        # ---- Right: form
        self.profile_name = QLineEdit()
        self.host = QLineEdit()
        self.port = QLineEdit("22")
        self.username = QLineEdit()
        self.project = QLineEdit()
        self.account = QLineEdit()
        self.project_label = QLabel(t("connection.project"))
        self.account_label = QLabel(t("connection.account"))

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.cb_save_password = QCheckBox(t("login.save_password"))
        self._profile_system_settings = normalize_system_settings(None)
        self._profile_file_manager_settings = normalize_file_manager_settings(None)
        self._profile_file_manager_raw: dict = {}
        self._profile_jump_host_raw: dict = {}
        self._profile_jump_host_settings = normalize_jump_host_settings(None)
        self._profile_cli_allowed = False
        self._profile_keepalive = 30
        self._profile_transfer_parallelism = 1
        self._profile_ssh_timeout = None
        self._password_prompt_policy = "when-needed"
        self.key_path = QLineEdit()
        self.btn_browse_key = QPushButton(t("login.browse"))
        self.btn_browse_key.clicked.connect(self.pick_key)

        self.sp_transfer_parallelism = QSpinBox()
        self.sp_transfer_parallelism.setRange(1, 10)
        self.sp_ssh_timeout = QDoubleSpinBox()
        self.sp_ssh_timeout.setRange(0, 600)
        self.sp_ssh_timeout.setDecimals(1)
        self.sp_ssh_timeout.setSuffix(" s")

        self.cb_x11 = QCheckBox(t("login.x11_enable"))
        self._profile_host_key_policy = "accept-new"
        self.cb_strict_hostkey = QCheckBox(t("login.strict_host_key"))
        # Legacy visible checkbox kept only as a mirror of the canonical
        # host-key policy state below; the Add/Edit Connection dialog combo
        # is the primary user-facing control.
        self.cb_strict_hostkey.toggled.connect(self._on_strict_hostkey_toggled)

        # Simulation / dry-run option removed from UI.
        # (If a legacy profile contains a 'dry_run' field, it is ignored.)

        self.btn_save = QPushButton(t("login.save"))
        self.btn_save.clicked.connect(self.save_profile)

        self.btn_add_connection = QPushButton(t("login.add_connection"))
        self.btn_add_connection.clicked.connect(self.open_add_connection_dialog)

        self.btn_connect = QPushButton(t("login.connect_selected"))
        self.btn_connect.clicked.connect(self.connect_selected_profile)

        self.terminal_header = TerminalHeader(self)
        self.status_label = self.terminal_header.status_label
        self.terminal_identity_label = self.terminal_header.identity_label
        self.terminal_dimensions_label = self.terminal_header.dimensions_label

        # ---- Console
        self.console = _terminal.TerminalConsole(self)
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.console.setStyleSheet(
            "QPlainTextEdit { background-color: #111111; color: #e8e8e8; "
            "border: 1px solid #555; selection-background-color: #264f78; }"
        )
        self.console.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        ph = t("login.console_placeholder")
        self.console.setPlaceholderText(ph)
        self.console.viewport().installEventFilter(self)
        self.console.set_key_handler(self._forward_console_key_event)
        self.console.set_paste_handler(self._paste_console_clipboard)

        # ---- SSH terminal line
        self.cmd_in = TerminalInput()
        self.cmd_in.setStyleSheet(
            "QLineEdit { background-color: #111111; color: #e8e8e8; "
            "border: 1px solid #555; padding: 4px; "
            "selection-background-color: #264f78; }"
        )
        self.cmd_in.setPlaceholderText(t("login.command_placeholder"))
        self.btn_run_cmd = QPushButton(t("login.run_command"))
        self.btn_run_cmd.clicked.connect(self.cmd_in.submit_current)
        self.cmd_in.command_submitted.connect(self.run_command_text)
        self.cmd_in.reconnect_requested.connect(self._prompt_reconnect)

        cmd_row = QHBoxLayout()
        cmd_row.addWidget(self.cmd_in)
        cmd_row.addWidget(self.btn_run_cmd)
        self.quick_command_row = QWidget()
        self.quick_command_row.setLayout(cmd_row)
        self.quick_command_row.setVisible(False)

        self.btn_terminal_find = self.terminal_header.find_button
        self.btn_terminal_clear = self.terminal_header.clear_button
        self.btn_terminal_font_down = self.terminal_header.font_down_button
        self.btn_terminal_font_up = self.terminal_header.font_up_button

        self.terminal_widget: TerminalWidget | None = None
        self._terminal_init_error: str | None = None
        try:
            self.terminal_widget = TerminalWidget(self)
        except RuntimeError as exc:
            self._terminal_init_error = str(exc)
        else:
            self.console.hide()

        self.form = QFormLayout()
        self.form.addRow(t("login.profile_name_label"), self.profile_name)
        self.form.addRow(t("login.host"), self.host)
        self.form.addRow(t("login.port"), self.port)
        self.form.addRow(t("connection.max_simultaneous_transfers"), self.sp_transfer_parallelism)
        self.form.addRow(t("connection.ssh_timeout_override"), self.sp_ssh_timeout)
        self.form.addRow(t("login.username"), self.username)
        self.form.addRow(self.project_label, self.project)
        self.form.addRow(self.account_label, self.account)
        self.form.addRow(t("login.password"), self.password)
        self.form.addRow("", self.cb_save_password)

        key_row = QHBoxLayout()
        key_row.addWidget(self.key_path)
        key_row.addWidget(self.btn_browse_key)
        self.key_row_widget = QWidget()
        self.key_row_widget.setLayout(key_row)
        self.form.addRow(t("login.ssh_key"), self.key_row_widget)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_connect)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setSpacing(8)
        action_row = QHBoxLayout()
        action_row.addWidget(self.btn_add_connection)
        action_row.addWidget(self.btn_connect)
        action_row.addStretch(1)
        right_lay.addLayout(action_row)
        self.terminal_header.find_requested.connect(self._find_terminal_text)
        self.terminal_header.clear_requested.connect(lambda: self.terminal_widget and self.terminal_widget.clear())
        self.terminal_header.font_delta_requested.connect(
            lambda delta: self.terminal_widget and self.terminal_widget.change_font_size(delta)
        )
        right_lay.addWidget(self.terminal_header)
        self.console_title_label = QLabel(t("login.console_title"))
        self.console_title_label.setVisible(False)
        right_lay.addWidget(self.terminal_widget or self.console, 1)
        right_lay.addWidget(self.quick_command_row)

        splitter = QSplitter()
        splitter.addWidget(self.profiles_list)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([220, 780])

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        self._session = {"connected": False, "cfg": SSHConfig(), "ssh": None, "slurm": None, "files": None}
        self._connection_controller = ConnectionController()
        self._console_log_lines: list[str] = []
        self._last_shell_geometry: tuple[int, int] | None = None
        self._connect_thread = None
        self._connect_worker = None
        self._connect_in_progress = False
        self._pending_old_ssh = None
        self._reconnect_prompt_open = False
        self._master_password_cache = ""
        self._console_render_timer = QTimer(self)
        self._console_render_timer.setSingleShot(True)
        self._console_render_timer.setInterval(50)
        self._console_render_timer.timeout.connect(self._render_console_view)
        self.console_message.connect(self._append_console_to_widget)
        self.ssh_console_message.connect(self._append_ssh_console_to_widget)
        self.shell_output_message.connect(self._append_shell_output_to_widget)
        self.ssh_disconnected.connect(self._handle_ssh_disconnected)
        if self.terminal_widget is not None:
            self.terminal_widget.failed.connect(lambda msg: self.append_console(f"[terminal: {msg}]"))
            self.terminal_widget.bridge.error.connect(lambda msg: self.append_console(f"[terminal: {msg}]"))
        elif self._terminal_init_error:
            self.append_console(f"[terminal unavailable: {self._terminal_init_error}]")

        _profiles.refresh_profiles(self)
        self.btn_connect.setEnabled(False)
        self.cmd_in.set_connected(False)

    def _on_strict_hostkey_toggled(self, checked: bool) -> None:
        self._profile_host_key_policy = "strict" if checked else "accept-new"

    def shutdown_external_processes(self) -> None:
        """Called by MainWindow on app exit."""
        _connect.shutdown_external_processes(self)

    # ---- public helpers
    def append_console(self, msg: str) -> None:
        # Route writes through a Qt signal so background SSH reader threads
        # and QProcess callbacks stay on the GUI thread.
        try:
            self.console_message.emit(msg)
        except RuntimeError:
            pass

    def append_shell_output(self, msg: str) -> None:
        if self.terminal_widget is not None:
            self.terminal_widget.bridge.receive_output(msg)
        try:
            self.shell_output_message.emit(msg)
        except RuntimeError:
            pass

    def append_ssh_console(self, msg: str) -> None:
        try:
            self.ssh_console_message.emit(msg)
        except RuntimeError:
            pass

    def _schedule_console_render(self) -> None:
        _terminal.schedule_console_render(self)

    def _render_console_view(self) -> None:
        _terminal.render_console_view(self)

    def _append_log_line(self, msg: str) -> None:
        _terminal.append_log_line(self, msg)

    def _append_console_to_widget(self, msg: str) -> None:
        _terminal.append_console_to_widget(self, msg)

    def _append_ssh_console_to_widget(self, msg: str) -> None:
        _terminal.append_ssh_console_to_widget(self, msg)

    def _append_shell_output_to_widget(self, msg: str) -> None:
        _terminal.append_shell_output_to_widget(self, msg)

    def eventFilter(self, obj, event) -> bool:
        _terminal.handle_console_viewport_event(self, obj, event)
        return super().eventFilter(obj, event)

    def _terminal_key_sequence(self, event) -> str | None:
        return _terminal.terminal_key_sequence(event)

    def _forward_console_key_event(self, event) -> bool:
        return _terminal.forward_console_key_event(self, event)

    def _paste_console_clipboard(self) -> bool:
        return _terminal.paste_console_clipboard(self)

    def _console_shell_geometry(self) -> tuple[int, int]:
        return _terminal.console_shell_geometry(self)

    def _sync_shell_geometry(self) -> None:
        _terminal.sync_shell_geometry(self)

    def _find_terminal_text(self) -> None:
        _terminal.find_terminal_text(self)

    # ---- connection
    def _begin_connect_async(self, cfg: SSHConfig, old_ssh) -> bool:
        return _connect.begin_connect_async(self, cfg, old_ssh)

    def _on_connect_thread_finished(self) -> None:
        _connect.connect_thread_finished(self)

    def _on_connect_finished(self, payload: object) -> None:
        _connect.connect_finished(self, payload)

    def _on_connect_failed(self, message: str, exc: object) -> None:
        _connect.connect_failed(self, message, exc)

    def _prompt_host_key_decision(self, request: object) -> None:
        from hpc_gui.ui.widgets import _login_connection_worker as _worker

        _worker.prompt_host_key_decision(self, request)

    def _prompt_keyboard_interactive(self, request: object) -> None:
        from hpc_gui.ui.widgets import _login_connection_worker as _worker

        _worker.prompt_keyboard_interactive(self, request)

    def connect_clicked(self, transient_password: str = "") -> bool:
        return _connect.connect_clicked(self, transient_password=transient_password)

    def run_command(self) -> None:
        _connect.run_command(self)

    def run_command_text(self, cmd: str) -> None:
        _connect.run_command_text(self, cmd)

    def _notify_ssh_disconnected(self, reason: str) -> None:
        _connect.notify_ssh_disconnected(self, reason)

    def _handle_ssh_disconnected(self, reason: str) -> None:
        _connect.handle_ssh_disconnected(self, reason)

    def _prompt_reconnect(self) -> None:
        _connect.prompt_reconnect(self)

    # ---- profiles
    def refresh_profiles(self, select_name: str | None = None) -> None:
        _profiles.refresh_profiles(self, select_name=select_name)

    def on_profile_selected(self) -> None:
        _profiles.on_profile_selected(self)

    def _ask_master_password(self, *, confirm: bool) -> str | None:
        """Ask user for a master password. Returns None if canceled."""
        return _secrets.ask_master_password(self, confirm=confirm)

    def _decrypt_saved_password(self, prof: dict) -> str | None:
        """Decrypt a saved password and retry if the cached master password is wrong."""
        return _secrets.decrypt_saved_password(self, prof)

    def _decrypt_profile_password(
        self,
        prof: dict,
        *,
        allow_prompt: bool,
    ) -> str | None:
        return _secrets.decrypt_profile_password(self, prof, allow_prompt=allow_prompt)

    def _should_prompt_for_password(self, prof: dict | None) -> bool:
        return _secrets.should_prompt_for_password(self, prof)

    def pick_key(self) -> None:
        _profiles.pick_key_file(self)

    def _load_profile_into_fields(self, prof: dict) -> None:
        _profiles.load_profile_into_fields(self, prof)

    def _load_profile_by_name(self, name: str) -> dict | None:
        return _profiles.load_profile_by_name(self, name)

    def _update_provider_requirement_labels(self) -> None:
        _profiles.update_provider_requirement_labels(self)

    def open_add_connection_dialog(self) -> None:
        _profiles.open_add_connection_dialog(self)

    def open_edit_connection_dialog(self, profile_name: str | None = None) -> None:
        _profiles.open_edit_connection_dialog(self, profile_name)

    def _selected_profile_name(self) -> str:
        return _profiles.selected_profile_name(self)

    def show_profile_context_menu(self, pos) -> None:
        _profiles.show_profile_context_menu(self, pos)

    def duplicate_selected_profile(self, profile_name: str | None = None) -> None:
        _profiles.duplicate_selected_profile(self, profile_name)

    def _on_profile_double_clicked(self, item) -> None:
        _profiles.on_profile_double_clicked(self, item)

    def _save_profile_from_dialog(self, profile: dict) -> bool:
        return _profiles.save_profile_from_dialog(self, profile)

    def _save_and_connect_from_dialog(self, profile: dict) -> bool:
        return _profiles.save_and_connect_from_dialog(self, profile)

    def connect_selected_profile(self) -> bool:
        return _profiles.connect_selected_profile(self)

    def save_profile(self) -> bool:
        return _store.save_profile(self)

    def update_active_profile_remote_defaults(
        self,
        scratch_dir: str,
        home_dir: str,
    ) -> bool:
        return _store.update_active_profile_remote_defaults(self, scratch_dir, home_dir)

    def retranslate_ui(self):
        """Update user-facing texts when language changes."""
        _retranslate.retranslate_ui(self)


install_legacy_login_exports(__name__)
