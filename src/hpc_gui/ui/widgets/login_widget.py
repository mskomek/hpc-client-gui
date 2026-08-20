from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal, Qt, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox, QLabel, QFileDialog,
    QApplication, QListWidget, QSplitter, QMessageBox, QPlainTextEdit,
    QInputDialog, QMenu, QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox
)

from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.config.models import SSHConfig
from hpc_gui.config.storage import (
    load_profiles,
    upsert_profile,
    load_settings,
    update_settings,
    delete_profile,
    coerce_profile_transfer_parallelism,
    coerce_profile_ssh_timeout,
)
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core.history import append_event
from hpc_gui.core.logging import append_log
from hpc_gui.services.slurm_mock import MockSlurmBackend
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.x11_runner import X11Runner
from hpc_gui.ssh.client import (
    HostKeyChangedError,
    HostKeyInfo,
    HostKeyRejectedError,
    SSHClientWrapper,
    SSHConnInfo,
    coerce_keepalive_interval,
)
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.slurm_ssh import SSHSlurmBackend
from hpc_gui.core.crypto_master import encrypt_with_master, decrypt_with_master
from hpc_gui.core.secret_store import (
    is_available as os_secret_store_available,
    protect_secret,
    unprotect_secret,
)
from hpc_gui.ui.widgets.terminal_input import TerminalInput
from hpc_gui.ui.widgets.terminal_widget import TerminalWidget
from hpc_gui.ui.widgets.terminal_header import TerminalHeader
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog

import os
import threading
import shiboken6


FTP_TEST_MODE_ENV = "TRUBA_GUI_FTP_TEST_MODE"
FTP_TEST_HOSTS = {"mock", "mock://ftp", "ftp-mock", "ftp_mock"}


def is_ftp_test_mode_enabled() -> bool:
    return os.environ.get(FTP_TEST_MODE_ENV, "").strip() == "1"


def is_ftp_mock_host(host: str) -> bool:
    return (host or "").strip().lower() in FTP_TEST_HOSTS


class _TerminalConsole(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_handler = None
        self._paste_handler = None

    def set_key_handler(self, handler) -> None:
        self._key_handler = handler

    def set_paste_handler(self, handler) -> None:
        self._paste_handler = handler

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        handler = self._key_handler
        if handler is not None and handler(event):
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            handler = self._paste_handler
            if handler is not None and handler():
                event.accept()
                return
        super().mousePressEvent(event)


class _ConnectionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str, object)
    host_key_decision_requested = Signal(object)

    def __init__(self, cfg: SSHConfig, shell_size: tuple[int, int], log_cb, shell_output_cb, disconnect_cb=None):
        self._cancelled = False
        self._ssh = None
        super().__init__()
        self._cfg = cfg
        self._shell_size = shell_size
        self._log_cb = log_cb
        self._shell_output_cb = shell_output_cb
        self._disconnect_cb = disconnect_cb

    def _decide_host_key(self, info: HostKeyInfo) -> str:
        request = {
            "info": info,
            "decision": "cancel",
            "done": threading.Event(),
        }
        self.host_key_decision_requested.emit(request)
        while not request["done"].wait(0.1):
            if QCoreApplication.closingDown():
                return "cancel"
        return str(request["decision"])

    def run(self) -> None:
        try:
            conn = SSHConnInfo(
                host=self._cfg.host,
                port=self._cfg.port,
                username=self._cfg.username,
                password=self._cfg.password,
                key_path=self._cfg.key_path,
                host_key_policy=self._cfg.host_key_policy,
                x11_forwarding=self._cfg.x11_forwarding,
                timeout=self._cfg.ssh_timeout,
                keepalive_interval_seconds=self._cfg.keepalive_interval_seconds,
                host_key_decision=self._decide_host_key,
            )
            ssh = SSHClientWrapper(
                conn,
                log_cb=self._log_cb,
                shell_output_cb=self._shell_output_cb,
                disconnect_cb=self._disconnect_cb,
            )
            self._ssh = ssh
            ssh.connect(shell_size=self._shell_size)
            if self._cancelled:
                ssh.close()
                return
            transport = ssh.client.get_transport() if ssh.client else None
            if transport is not None:
                authenticated_user = transport.get_username() or ""
                if authenticated_user:
                    self._cfg.username = authenticated_user
            slurm = SSHSlurmBackend(ssh, self._cfg.system_settings)
            files = SSHFilesBackend(ssh)
            self.finished.emit({
                "cfg": self._cfg,
                "ssh": ssh,
                "slurm": slurm,
                "files": files,
            })
        except Exception as exc:
            self.failed.emit(str(exc), exc)

    def cancel(self) -> None:
        self._cancelled = True
        try:
            if self._ssh is not None:
                self._ssh.close()
        except Exception:
            pass


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

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.cb_save_password = QCheckBox(t("login.save_password") if t("login.save_password") != "[login.save_password]" else "Şifreyi kaydet")
        self._profile_system_settings = normalize_system_settings(None)
        self._profile_cli_allowed = False
        self._profile_keepalive = 30
        self._profile_transfer_parallelism = 1
        self._profile_ssh_timeout = None
        self._password_prompt_policy = "when-needed"
        self.key_path = QLineEdit()
        self.btn_browse_key = QPushButton(t("login.browse") if t("login.browse") != "[login.browse]" else "Seç")
        self.btn_browse_key.clicked.connect(self.pick_key)

        self.sp_transfer_parallelism = QSpinBox()
        self.sp_transfer_parallelism.setRange(1, 10)
        self.sp_ssh_timeout = QDoubleSpinBox()
        self.sp_ssh_timeout.setRange(0, 600)
        self.sp_ssh_timeout.setDecimals(1)
        self.sp_ssh_timeout.setSuffix(" s")

        self.cb_x11 = QCheckBox(t("login.x11_enable") if t("login.x11_enable") != "[login.x11_enable]" else "X11 Forwarding")
        self.cb_strict_hostkey = QCheckBox(t("login.strict_host_key"))

        # Simulation / dry-run option removed from UI.
        # (If a legacy profile contains a 'dry_run' field, it is ignored.)

        self.btn_save = QPushButton(t("login.save") if t("login.save") != "[login.save]" else "Kaydet")
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
        self.console = _TerminalConsole(self)
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
        self.btn_run_cmd = QPushButton(t("login.run_command") if t("login.run_command") != "[login.run_command]" else "Çalıştır")
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
        self.form.addRow(t("connection.transfer_parallelism"), self.sp_transfer_parallelism)
        self.form.addRow(t("connection.ssh_timeout"), self.sp_ssh_timeout)
        self.form.addRow(t("login.username"), self.username)
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
        self._console_log_lines: list[str] = []
        self._last_shell_geometry: tuple[int, int] | None = None
        self._connect_thread: QThread | None = None
        self._connect_worker: _ConnectionWorker | None = None
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

        self.refresh_profiles()
        self.btn_connect.setEnabled(False)
        self.cmd_in.set_connected(False)

    def shutdown_external_processes(self) -> None:
        """Called by MainWindow on app exit."""
        if self.terminal_widget is not None:
            self.terminal_widget.detach()
        # Stop a connection attempt before Qt destroys its QThread.
        try:
            worker = self._connect_worker
            thread = self._connect_thread
            if worker is not None:
                worker.cancel()
            if thread is not None:
                thread.quit()
                thread.wait(5000)
        except Exception:
            pass

        try:
            st = load_settings()
        except Exception:
            st = {}

        self._x11_runner.shutdown(
            close_x11_procs=bool(st.get("close_x11_procs_on_exit", True)),
            close_vcxsrv=bool(st.get("close_vcxsrv_on_exit", True)),
        )

        try:
            ssh = self._session.get("ssh") if hasattr(self, "_session") else None
            if ssh is not None:
                ssh.close()
        except Exception:
            pass

        # Wipe connection secrets from in-memory session (best-effort).
        try:
            cfg = self._session.get("cfg") if hasattr(self, "_session") else None
            if cfg is not None:
                try:
                    cfg.password = ""
                except Exception:
                    pass
            ssh = self._session.get("ssh") if hasattr(self, "_session") else None
            if ssh is not None and getattr(ssh, "info", None) is not None:
                try:
                    ssh.info.password = ""
                except Exception:
                    pass
        except Exception:
            pass

        self._master_password_cache = ""

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
        if not self._console_render_timer.isActive():
            self._console_render_timer.start()

    def _render_console_view(self) -> None:
        try:
            lines = list(self._console_log_lines)
            text = "\n".join(lines)
            self.console.blockSignals(True)
            try:
                self.console.setPlainText(text)
                cursor = self.console.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.console.setTextCursor(cursor)
                self.console.ensureCursorVisible()
            finally:
                self.console.blockSignals(False)
        except Exception:
            pass

    def _append_log_line(self, msg: str) -> None:
        text = (msg or "").rstrip("\n")
        self._console_log_lines.extend(text.splitlines() or [""])
        if len(self._console_log_lines) > 2000:
            del self._console_log_lines[:-2000]
        self._schedule_console_render()

    def _append_console_to_widget(self, msg: str) -> None:
        # Guard against "Internal C++ object already deleted" during shutdown.
        try:
            if hasattr(self, "console") and shiboken6.isValid(self.console):
                self._append_log_line(msg)
        except RuntimeError:
            pass
        append_log(msg)

    def _append_ssh_console_to_widget(self, msg: str) -> None:
        try:
            if hasattr(self, "console") and shiboken6.isValid(self.console):
                self._append_log_line(msg)
        except RuntimeError:
            pass

    def _append_shell_output_to_widget(self, msg: str) -> None:
        try:
            if self.terminal_widget is not None:
                return
            if not hasattr(self, "console") or not shiboken6.isValid(self.console):
                return
            self._append_log_line(msg)
            self._schedule_console_render()
        except Exception:
            pass

    def eventFilter(self, obj, event) -> bool:
        try:
            if obj is getattr(self.console, "viewport", lambda: None)():
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                    self._sync_shell_geometry()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _terminal_key_sequence(self, event) -> str | None:
        key = event.key()
        mods = event.modifiers()
        text = event.text() or ""

        if mods & Qt.KeyboardModifier.ControlModifier and text:
            ch = text.upper()[0]
            if "@" <= ch <= "_":
                return chr(ord(ch) - 64)

        special_map = {
            Qt.Key.Key_Return: "\r",
            Qt.Key.Key_Enter: "\r",
            Qt.Key.Key_Tab: "\t",
            Qt.Key.Key_Backtab: "\x1b[Z",
            Qt.Key.Key_Backspace: "\x7f",
            Qt.Key.Key_Escape: "\x1b",
            Qt.Key.Key_Left: "\x1b[D",
            Qt.Key.Key_Right: "\x1b[C",
            Qt.Key.Key_Up: "\x1b[A",
            Qt.Key.Key_Down: "\x1b[B",
            Qt.Key.Key_Home: "\x1b[H",
            Qt.Key.Key_End: "\x1b[F",
            Qt.Key.Key_Delete: "\x1b[3~",
            Qt.Key.Key_PageUp: "\x1b[5~",
            Qt.Key.Key_PageDown: "\x1b[6~",
            Qt.Key.Key_Insert: "\x1b[2~",
        }
        if key in special_map:
            return special_map[key]

        if len(text) == 1 and not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)):
            return text

        return None

    def _forward_console_key_event(self, event) -> bool:
        try:
            ssh = self._session.get("ssh") if hasattr(self, "_session") else None
            if not ssh:
                return False
            seq = self._terminal_key_sequence(event)
            if not seq:
                return False
            if hasattr(ssh, "send_shell_input") and ssh.send_shell_input(seq):
                event.accept()
                return True
        except Exception:
            pass
        return False

    def _paste_console_clipboard(self) -> bool:
        try:
            ssh = self._session.get("ssh") if hasattr(self, "_session") else None
            if not ssh or not hasattr(ssh, "send_shell_input"):
                return False
            text = QApplication.clipboard().text()
            if not text:
                return False
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
            if ssh.send_shell_input(text):
                if self.terminal_widget is not None:
                    self.terminal_widget.focus_terminal()
                else:
                    self.console.setFocus()
                return True
        except Exception:
            pass
        return False

    def _console_shell_geometry(self) -> tuple[int, int]:
        try:
            viewport = self.console.viewport()
            size = viewport.size()
            fm = self.console.fontMetrics()
            char_width = max(1, fm.horizontalAdvance("M"))
            line_height = max(1, fm.lineSpacing())
            width = size.width()
            height = size.height()
            if width < char_width * 4 or height < line_height * 2:
                return (120, 40)
            cols = max(20, width // char_width)
            rows = max(5, height // line_height)
            return (cols, rows)
        except Exception:
            return (120, 40)

    def _sync_shell_geometry(self) -> None:
        try:
            ssh = self._session.get("ssh") if hasattr(self, "_session") else None
            if not ssh or not hasattr(ssh, "resize_shell_pty"):
                return
            cols, rows = self._console_shell_geometry()
            if self._last_shell_geometry == (cols, rows):
                return
            ssh.resize_shell_pty(cols, rows)
            self._last_shell_geometry = (cols, rows)
            self.terminal_dimensions_label.setText(f"{cols}×{rows}")
        except Exception:
            pass

    def _begin_connect_async(self, cfg: SSHConfig, old_ssh) -> bool:
        if self._connect_in_progress:
            return False
        self._connect_in_progress = True
        self._pending_old_ssh = old_ssh
        if self.terminal_widget is not None:
            self.terminal_widget.detach()
        self.btn_connect.setEnabled(False)
        self.btn_add_connection.setEnabled(False)
        self.status_label.setText(t("login.status_connecting"))
        self.cmd_in.set_connected(False)

        thread = QThread(self)
        worker = _ConnectionWorker(
            cfg,
            self._console_shell_geometry(),
            self.append_ssh_console,
            self.append_shell_output,
            self._notify_ssh_disconnected,
        )
        worker.host_key_decision_requested.connect(
            self._prompt_host_key_decision
        )
        self._connect_thread = thread
        self._connect_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_connect_finished)
        worker.failed.connect(self._on_connect_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_connect_thread_finished)
        thread.start()
        return True

    def _prompt_host_key_decision(self, request: object) -> None:
        data = request if isinstance(request, dict) else {}
        done = data.get("done")
        try:
            info = data.get("info")
            if not isinstance(info, HostKeyInfo):
                return
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setWindowTitle(t("connection.host_key_prompt_title"))
            dialog.setText(
                t("connection.host_key_prompt_message").format(
                    host=info.hostname,
                    key_type=info.key_type,
                    fingerprint=info.fingerprint,
                )
            )
            save = dialog.addButton(
                t("connection.host_key_trust_save"),
                QMessageBox.ButtonRole.AcceptRole,
            )
            once = dialog.addButton(
                t("connection.host_key_trust_once"),
                QMessageBox.ButtonRole.ActionRole,
            )
            cancel = dialog.addButton(
                t("common.cancel"), QMessageBox.ButtonRole.RejectRole
            )
            dialog.setDefaultButton(cancel)
            dialog.exec()
            clicked = dialog.clickedButton()
            data["decision"] = "save" if clicked is save else "once" if clicked is once else "cancel"
        finally:
            if isinstance(done, threading.Event):
                done.set()

    def _on_connect_thread_finished(self) -> None:
        self._connect_in_progress = False
        self._connect_thread = None
        self._connect_worker = None
        self._pending_old_ssh = None
        self.btn_add_connection.setEnabled(True)
        self.btn_connect.setEnabled(bool(self._selected_profile_name()))

    def _on_connect_finished(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        ssh = data.get("ssh")
        slurm = data.get("slurm")
        files = data.get("files")
        cfg = data.get("cfg")
        old_ssh = self._pending_old_ssh
        try:
            if old_ssh is not None and old_ssh is not ssh:
                try:
                    old_ssh.close()
                except Exception:
                    pass
            self._session = {
                "connected": True,
                "cfg": cfg,
                "ssh": ssh,
                "slurm": slurm,
                "files": files,
                "profile_name": self.profile_name.text().strip(),
            }
            if self.terminal_widget is not None and ssh is not None:
                self.terminal_widget.attach(ssh)
            if isinstance(cfg, SSHConfig):
                identity = f"{cfg.username}@{cfg.host}" if cfg.username else cfg.host
                self.terminal_identity_label.setText(identity)
            self.status_label.setText(t("login.status_connected") if t("login.status_connected") != "[login.status_connected]" else "Bağlı")
            self.cmd_in.set_connected(True)
            self.append_console("SSH bağlantısı kuruldu.")
            self._sync_shell_geometry()
            try:
                if self.terminal_widget is not None:
                    self.terminal_widget.focus_terminal()
                else:
                    self.console.setFocus()
            except Exception:
                pass
            if isinstance(cfg, SSHConfig):
                append_event({"type": "connect", "host": cfg.host, "user": cfg.username, "dry_run": cfg.dry_run})
            self.session_changed.emit(self._session)
        finally:
            self.btn_add_connection.setEnabled(True)
            self.btn_connect.setEnabled(bool(self._selected_profile_name()))

    def _on_connect_failed(self, message: str, exc: object) -> None:
        if self.terminal_widget is not None:
            self.terminal_widget.detach()
        self.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
        if isinstance(exc, HostKeyChangedError):
            message = t("connection.host_key_changed").format(host=exc.hostname)
        elif isinstance(exc, HostKeyRejectedError):
            message = t("connection.host_key_rejected").format(host=exc.hostname)
        self.status_label.setText(t("login.status_disconnected") if t("login.status_disconnected") != "[login.status_disconnected]" else "Bağlı değil")
        self.cmd_in.set_connected(False)
        self.append_console(t("login.conn_error_prefix").format(err=message))
        if "SSH protocol banner" in message or "banner" in message.lower():
            self.append_console(
                "İpucu: SSH sunucusu banner döndürmeden önce gecikiyor olabilir; VPN/ağ, port ve uzak sshd erişimini kontrol edin."
            )
        elif "key-exchange timed out" in message.lower():
            self.append_console(
                "İpucu: SSH anahtar değişimi zaman aşımına uğradı. VPN/ağ bağlantısını, doğru SSH portunu ve sunucunun erişilebilirliğini kontrol edip tekrar deneyin."
            )
        show_exception(self, title=t("login.conn_error_title"), user_message=message, exc=exc if isinstance(exc, BaseException) else None, area="SSH")
        self.btn_add_connection.setEnabled(True)
        self.btn_connect.setEnabled(bool(self._selected_profile_name()))

    # ---- profiles
    def refresh_profiles(self, select_name: str | None = None) -> None:
        self.profiles_list.clear()
        self.btn_connect.setEnabled(False)
        profiles = load_profiles()
        for p in profiles:
            name = p.get("name", "")
            if name:
                self.profiles_list.addItem(name)
        if select_name:
            items = self.profiles_list.findItems(select_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.profiles_list.setCurrentItem(items[0])

    def on_profile_selected(self) -> None:
        item = self.profiles_list.currentItem()
        if not item:
            self.btn_connect.setEnabled(False)
            return
        name = item.text()
        profiles = load_profiles()
        prof = next((p for p in profiles if p.get("name") == name), None)
        if not prof:
            self.btn_connect.setEnabled(False)
            return
        self._load_profile_into_fields(prof)
        self.btn_connect.setEnabled(True)

    def _ask_master_password(self, *, confirm: bool) -> str | None:
        """Ask user for a master password. Returns None if canceled."""
        if self._master_password_cache:
            return self._master_password_cache

        saved_master = load_settings().get("master_password_dpapi")
        if saved_master:
            try:
                self._master_password_cache = unprotect_secret(str(saved_master))
                return self._master_password_cache
            except Exception:
                update_settings({"master_password_dpapi": ""})

        title = "Şifreleme Parolası"
        prompt = "Kaydedilen şifreleri şifrelemek/çözmek için bir ana parola girin."
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(prompt))
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)
        remember_password = QCheckBox(t("connection.remember_master_password"))
        remember_password.setEnabled(os_secret_store_available())
        layout.addWidget(remember_password)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        password_input.setFocus()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        pw = password_input.text().strip()
        if not pw:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_master_empty"))
            return None
        if confirm:
            pw2, ok2 = QInputDialog.getText(
                self,
                title,
                "Ana parolayı tekrar girin (doğrulama):",
                QLineEdit.EchoMode.Password,
            )
            if not ok2:
                return None
            if pw2 != pw:
                QMessageBox.warning(self, t("login.err_title"), t("login.err_master_mismatch"))
                return None
        self._master_password_cache = pw
        if remember_password.isChecked():
            try:
                update_settings({"master_password_dpapi": protect_secret(pw)})
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    t("login.err_title"),
                    t("connection.master_password_store_failed").format(error=exc),
                )
        return pw

    def _decrypt_saved_password(self, prof: dict) -> str | None:
        """Decrypt a saved password and retry if the cached master password is wrong."""
        token = prof.get("password_enc")
        salt = prof.get("password_salt")
        if not token or not salt:
            return ""

        used_cached_master = bool(self._master_password_cache)
        master = self._ask_master_password(confirm=False)
        if master is None:
            return None

        try:
            return decrypt_with_master(master, token, salt)
        except Exception:
            if used_cached_master:
                self._master_password_cache = ""
                update_settings({"master_password_dpapi": ""})
                master = self._ask_master_password(confirm=False)
                if master is None:
                    return None
                try:
                    return decrypt_with_master(master, token, salt)
                except Exception:
                    pass

        self._master_password_cache = ""
        QMessageBox.critical(self, t("login.err_title"), t("login.err_master_wrong"))
        return None

    def _decrypt_profile_password(
        self,
        prof: dict,
        *,
        allow_prompt: bool,
    ) -> str | None:
        token = prof.get("password_dpapi")
        if token:
            try:
                return unprotect_secret(str(token))
            except Exception:
                QMessageBox.critical(
                    self,
                    t("login.err_title"),
                    t("connection.saved_password_unavailable"),
                )
                return None
        if prof.get("password_enc") and prof.get("password_salt"):
            if not allow_prompt:
                return None
            return self._decrypt_saved_password(prof)
        return ""

    def pick_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("login.ssh_key") if t("login.ssh_key") != "[login.ssh_key]" else "SSH Anahtar Seç")
        if path:
            self.key_path.setText(path)

    def _load_profile_into_fields(self, prof: dict) -> None:
        self.profile_name.setText(prof.get("name", ""))
        self.host.setText(prof.get("host", ""))
        self.port.setText(str(prof.get("port", 22)))
        self.username.setText(prof.get("username", ""))
        self.key_path.setText(prof.get("key_path", ""))
        self.cb_x11.setChecked(bool(prof.get("x11_forwarding", False)))
        self.cb_strict_hostkey.setChecked((prof.get("host_key_policy") or "accept-new") == "strict")
        # legacy field: prof.get("dry_run") ignored

        save_pw = bool(prof.get("save_password", False))
        self.cb_save_password.setChecked(save_pw)
        self._password_prompt_policy = (
            prof.get("password_prompt_policy") or "when-needed"
        )
        self._profile_system_settings = normalize_system_settings(
            prof.get("system")
        )
        self._profile_cli_allowed = bool(prof.get("cli_allowed", False))
        self._profile_keepalive = coerce_keepalive_interval(
            prof.get("keepalive_interval_seconds", 30)
        )
        self._profile_transfer_parallelism = coerce_profile_transfer_parallelism(prof.get("transfer_parallelism", 1))
        self._profile_ssh_timeout = coerce_profile_ssh_timeout(prof.get("ssh_timeout"))
        self.sp_transfer_parallelism.setValue(self._profile_transfer_parallelism)
        self.sp_ssh_timeout.setValue(self._profile_ssh_timeout or 0)
        # Never auto-fill decrypted password.
        # If legacy plain password exists, show it; if encrypted, keep empty.
        if save_pw and isinstance(prof.get("password"), str) and prof.get("password"):
            self.password.setText(prof.get("password", ""))
        else:
            self.password.setText("")

    def _load_profile_by_name(self, name: str) -> dict | None:
        profiles = load_profiles()
        return next((p for p in profiles if p.get("name") == name), None)

    def open_add_connection_dialog(self) -> None:
        dlg = ConnectionDialog(
            self,
            initial_profile=None,
            on_save=self._save_profile_from_dialog,
            on_connect=self._save_and_connect_from_dialog,
        )
        dlg.exec()

    def open_edit_connection_dialog(self, profile_name: str | None = None) -> None:
        name = (profile_name or self._selected_profile_name()).strip()
        if not name:
            return
        initial = self._load_profile_by_name(name)
        if not initial:
            return
        if initial.get("password_dpapi"):
            expected = self._decrypt_profile_password(initial, allow_prompt=False)
            if expected is None:
                return
            entered, ok = QInputDialog.getText(
                self,
                t("connection.edit_auth_title"),
                t("connection.edit_auth_prompt"),
                QLineEdit.EchoMode.Password,
            )
            if not ok:
                return
            if entered != expected:
                QMessageBox.warning(
                    self,
                    t("login.err_title"),
                    t("connection.edit_auth_failed"),
                )
                return
        elif initial.get("password_enc") and initial.get("password_salt"):
            if self._decrypt_profile_password(initial, allow_prompt=True) is None:
                return
        dlg = ConnectionDialog(
            self,
            initial_profile=initial,
            on_save=self._save_profile_from_dialog,
            on_connect=self._save_and_connect_from_dialog,
        )
        dlg.setWindowTitle(t("connection.edit_dialog_title") if t("connection.edit_dialog_title") != "[connection.edit_dialog_title]" else "Edit Connection")
        self._editing_profile_original_name = name
        try:
            dlg.exec()
        finally:
            self._editing_profile_original_name = ""

    def _selected_profile_name(self) -> str:
        item = self.profiles_list.currentItem()
        return item.text().strip() if item else ""

    def show_profile_context_menu(self, pos) -> None:
        item = self.profiles_list.itemAt(pos)
        if not item:
            return
        self.profiles_list.setCurrentItem(item)
        menu = QMenu(self)
        act_connect = menu.addAction(t("login.connect") if t("login.connect") != "[login.connect]" else "Bağlan")
        act_edit = menu.addAction(t("connection.edit_action") if t("connection.edit_action") != "[connection.edit_action]" else "Edit")
        chosen = menu.exec(self.profiles_list.mapToGlobal(pos))
        if chosen == act_connect:
            self.connect_selected_profile()
            return
        if chosen == act_edit:
            self.open_edit_connection_dialog(item.text())

    def _on_profile_double_clicked(self, item) -> None:
        if item is None:
            return
        self.profiles_list.setCurrentItem(item)
        self.connect_selected_profile()

    def _save_profile_from_dialog(self, profile: dict) -> bool:
        self._profile_system_settings = normalize_system_settings(
            profile.get("system")
        )
        self._password_prompt_policy = (
            profile.get("password_prompt_policy") or "when-needed"
        )
        self._load_profile_into_fields(profile)
        return self.save_profile()

    def _save_and_connect_from_dialog(self, profile: dict) -> bool:
        self._load_profile_into_fields(profile)
        if not self.save_profile():
            return False
        return self.connect_clicked()

    def connect_selected_profile(self) -> bool:
        name = self._selected_profile_name()
        if not name:
            return False
        prof = self._load_profile_by_name(name)
        if not prof:
            return False
        self._load_profile_into_fields(prof)
        return self.connect_clicked()

    def save_profile(self) -> bool:
        name = self.profile_name.text().strip()
        if not name:
            username = self.username.text().strip()
            host = self.host.text().strip()
            name = f"{username}@{host}" if username else host
            self.profile_name.setText(name)

        try:
            port = int(self.port.text().strip() or "22")
        except ValueError:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_port_numeric"))
            return False

        prof = {
            "name": name,
            "host": self.host.text().strip(),
            "port": port,
            "username": self.username.text().strip(),
            "key_path": self.key_path.text().strip(),
            "host_key_policy": "strict" if self.cb_strict_hostkey.isChecked() else "accept-new",
            "x11_forwarding": self.cb_x11.isChecked(),
            "cli_allowed": getattr(self, "_profile_cli_allowed", False),
            "keepalive_interval_seconds": self._profile_keepalive,
            "transfer_parallelism": int(self.sp_transfer_parallelism.value()),
            "ssh_timeout": float(self.sp_ssh_timeout.value()) or None,
            # dry_run removed
            "save_password": self.cb_save_password.isChecked(),
            "password_prompt_policy": self._password_prompt_policy,
            "system": normalize_system_settings(self._profile_system_settings),
        }

        # Password storage (encrypted):
        # - Do not store plaintext in config.
        # - When saving with "save password", ask for a master password and encrypt.
        if self.cb_save_password.isChecked():
            plain = self.password.text() or ""
            current = next(
                (p for p in load_profiles() if p.get("name") == name),
                None,
            )
            if (
                self._password_prompt_policy == "edit-only"
                and os_secret_store_available()
            ):
                # Existing profiles may have been encrypted with a master
                # password.  Convert them once to Windows credential
                # protection when the user chooses not to be prompted while
                # connecting, so future double-click connections stay prompt-free.
                if not plain and current and current.get("password_enc"):
                    plain = self._decrypt_profile_password(
                        current,
                        allow_prompt=True,
                    )
                    if plain is None:
                        return False
                try:
                    if plain:
                        prof["password_dpapi"] = protect_secret(plain)
                except Exception as exc:
                    QMessageBox.critical(
                        self,
                        t("login.err_title"),
                        t("connection.password_store_failed").format(
                            error=exc
                        ),
                    )
                    return False
            elif plain:
                master = self._ask_master_password(confirm=True)
                if master is None:
                    return False
                enc = encrypt_with_master(master, plain)
                prof["password_enc"] = enc.token
                prof["password_salt"] = enc.salt
            else:
                # keep existing encrypted password if present (when editing profile)
                if current:
                    for key in ("password_dpapi", "password_enc", "password_salt"):
                        if current.get(key):
                            prof[key] = current.get(key)

            # Always clear legacy plaintext field
            prof["password"] = ""
        else:
            prof["password"] = ""
            prof.pop("password_enc", None)
            prof.pop("password_salt", None)
            prof.pop("password_dpapi", None)

        upsert_profile(prof)
        original_name = getattr(self, "_editing_profile_original_name", "").strip()
        if original_name and original_name != name:
            delete_profile(original_name)
        self.refresh_profiles(select_name=name)
        append_event({"type": "profile_save", "name": name})
        self.append_console(f"Profil kaydedildi: {name}")
        return True

    def update_active_profile_remote_defaults(
        self,
        scratch_dir: str,
        home_dir: str,
    ) -> bool:
        name = str(
            (self._session or {}).get("profile_name")
            or self.profile_name.text()
            or ""
        ).strip()
        if not name:
            return False
        profile = self._load_profile_by_name(name)
        if not profile:
            return False
        system = normalize_system_settings(profile.get("system"))
        if scratch_dir.strip():
            system["scratch_dir"] = scratch_dir.strip()
        if home_dir.strip():
            system["home_dir"] = home_dir.strip()
        profile = dict(profile)
        profile["system"] = system
        upsert_profile(profile)
        self._profile_system_settings = dict(system)
        cfg = (self._session or {}).get("cfg")
        if cfg is not None:
            cfg.system_settings = dict(system)
        self.refresh_profiles(select_name=name)
        self.session_changed.emit(self._session)
        return True

    # ---- connect / command
    def _finish_mock_connection(self, cfg: SSHConfig, old_ssh) -> None:
        if old_ssh is not None:
            try:
                old_ssh.close()
            except Exception:
                pass
        ssh = None
        slurm = MockSlurmBackend()
        files = MockFilesBackend()
        self._session = {
            "connected": True,
            "cfg": cfg,
            "ssh": ssh,
            "slurm": slurm,
            "files": files,
            "profile_name": self.profile_name.text().strip(),
        }
        self.terminal_identity_label.setText(t("login.terminal_mock"))
        self.status_label.setText(t("login.status_mock") if t("login.status_mock") != "[login.status_mock]" else "Mock mod")
        self.cmd_in.set_connected(False)
        self.append_console("Mock bağlantı aktif.")
        append_event({"type": "connect", "host": cfg.host, "user": cfg.username, "dry_run": True})
        self.session_changed.emit(self._session)

    def connect_clicked(self) -> bool:
        try:
            port = int(self.port.text().strip() or "22")
        except ValueError:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_port_numeric"))
            return False

        old_ssh = self._session.get("ssh") if hasattr(self, "_session") else None

        # If password is not typed, resolve the saved secret according to the profile policy.
        password = self.password.text()
        if not password:
            name = (self.profile_name.text() or "").strip()
            if name:
                prof = next((p for p in load_profiles() if p.get("name") == name), None)
                if prof and prof.get("save_password"):
                    password = self._decrypt_profile_password(
                        prof,
                        allow_prompt=True,
                    )
                    if password is None:
                        return False

        use_ftp_mock = is_ftp_test_mode_enabled() and is_ftp_mock_host(self.host.text())
        cfg = SSHConfig(
            host=self.host.text().strip(),
            port=port,
            username=self.username.text().strip(),
            password=password,
            key_path=self.key_path.text().strip(),
            host_key_policy=("strict" if self.cb_strict_hostkey.isChecked() else "accept-new"),
            x11_forwarding=self.cb_x11.isChecked(),
            dry_run=use_ftp_mock,
            keepalive_interval_seconds=self._profile_keepalive,
            transfer_parallelism=coerce_profile_transfer_parallelism(self._profile_transfer_parallelism),
            ssh_timeout=coerce_profile_ssh_timeout(self._profile_ssh_timeout),
            system_settings=normalize_system_settings(
                self._profile_system_settings
            ),
        )

        if not cfg.host:
            QMessageBox.warning(self, t("login.err_title"), t("login.err_host_required"))
            return False

        # X11 preflight: if X11 forwarding is enabled and the user asked for
        # auto dependency management, ensure plink and VcXsrv are available
        # BEFORE connecting.
        app_settings = load_settings()
        if cfg.x11_forwarding and (not cfg.dry_run) and bool(app_settings.get("x11_autodeps", True)):
            if not self._x11_runner.preflight(enabled=True, parent=self, allow_download=True):
                QMessageBox.warning(self, t("login.x11_title"), t("login.err_x11_plink_needed"))
                return False

        target = f"{cfg.username}@{cfg.host}" if cfg.username else cfg.host
        self.append_console(f"Bağlanılıyor: {target}:{cfg.port}")
        try:
            if cfg.dry_run:
                self._finish_mock_connection(cfg, old_ssh)
            else:
                return self._begin_connect_async(cfg, old_ssh)
        except Exception as e:
            self.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
            self.status_label.setText(t("login.status_disconnected") if t("login.status_disconnected") != "[login.status_disconnected]" else "Bağlı değil")
            self.append_console(t("login.conn_error_prefix").format(err=e))
            msg = str(e)
            if "SSH protocol banner" in msg or "banner" in msg.lower():
                self.append_console(
                    "İpucu: SSH sunucusu banner döndürmeden önce gecikiyor olabilir; VPN/ağ, port ve uzak sshd erişimini kontrol edin."
                )
            show_exception(self, title=t("login.conn_error_title"), user_message=str(e), exc=e, area="SSH")
            return False
        return True

    def run_command(self) -> None:
        # Button compatibility: TerminalInput handles history + clear
        if hasattr(self.cmd_in, 'submit_current'):
            self.cmd_in.submit_current()
            return
        cmd = self.cmd_in.text().strip()
        if not cmd:
            return
        self.cmd_in.clear()
        self.run_command_text(cmd)

    def _find_terminal_text(self) -> None:
        if self.terminal_widget is None:
            return
        text, ok = QInputDialog.getText(self, t("login.terminal_find"), t("login.terminal_find"))
        if ok:
            self.terminal_widget.find_text(text)

    def run_command_text(self, cmd: str) -> None:
        cmd = (cmd or '').strip()
        if not cmd:
            return
        ssh = self._session.get("ssh")
        if not ssh or not self._session.get("connected", False):
            if cmd.lower() == "r":
                self._prompt_reconnect()
                return
            self.append_console("SSH bagli degil (Mock modda komut calistirilmaz).")
            return

        info = getattr(ssh, "info", None)
        if self._x11_runner.run_if_x11(info, cmd, parent=self):
            append_event({"type": "x11_cmd", "cmd": cmd})
            return

        # Normal terminal commands go through the live shell session.
        try:
            if hasattr(ssh, "send_shell_text") and ssh.send_shell_text(cmd):
                append_event({"type": "ssh_cmd", "cmd": cmd})
                return
            raise RuntimeError("interactive shell unavailable")
        except Exception as e:
            if self._session.get("connected", False):
                self._handle_ssh_disconnected(str(e) or "SSH bağlantısı kesildi.")
            self.append_console(t("login.cmd_error").format(err=e))

    def _notify_ssh_disconnected(self, reason: str) -> None:
        try:
            self.ssh_disconnected.emit(reason or "SSH bağlantısı kesildi.")
        except Exception:
            pass

    def _handle_ssh_disconnected(self, reason: str) -> None:
        if not self._session.get("connected", False):
            return
        self._session["connected"] = False
        if self.terminal_widget is not None:
            self.terminal_widget.detach()
        self.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
        self.status_label.setText(t("login.status_disconnected") if t("login.status_disconnected") != "[login.status_disconnected]" else "Bağlı değil")
        self.cmd_in.set_connected(False)
        notice = t("login.reconnect_notice").format(reason=reason or "")
        if notice != "[login.reconnect_notice]":
            self.append_console(notice)
        self.session_changed.emit(self._session)
        self._prompt_reconnect()

    def _prompt_reconnect(self) -> None:
        if self._connect_in_progress:
            return
        if self._session.get("connected", False):
            return
        if getattr(self, "_reconnect_prompt_open", False):
            return
        self._reconnect_prompt_open = True
        try:
            ans = QMessageBox.question(
                self,
                t("login.reconnect_prompt_title"),
                t("login.reconnect_prompt_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.append_console(t("login.reconnect_started"))
                self.connect_clicked()
        finally:
            self._reconnect_prompt_open = False

    def retranslate_ui(self):
        """Update user-facing texts when language changes."""
        try:
            self.cb_x11.setText(t("login.x11_enable"))
            self.cb_strict_hostkey.setText(t("login.strict_host_key"))
            # dry-run removed
            self.cb_save_password.setText(t("login.save_password"))
            self.btn_browse_key.setText(t("login.browse"))
            self.btn_save.setText(t("login.save"))
            labels = (
                (self.profile_name, "login.profile_name_label"),
                (self.host, "login.host"),
                (self.port, "login.port"),
                (self.username, "login.username"),
                (self.password, "login.password"),
                (self.key_row_widget, "login.ssh_key"),
            )
            for field, key in labels:
                label = self.form.labelForField(field)
                if label is not None:
                    label.setText(t(key))
            self.console_title_label.setText(t("login.console_title"))
            self.console.setPlaceholderText(t("login.console_placeholder"))
            self.cmd_in.setPlaceholderText(t("login.command_placeholder"))
            self.btn_run_cmd.setText(t("login.run_command"))
            self.terminal_header.retranslate_ui()
            self.btn_add_connection.setText(t("login.add_connection"))
            self.btn_connect.setText(t("login.connect_selected"))
        except Exception:
            pass
