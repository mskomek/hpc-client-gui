"""Login SSH connection flow (Wave M01).

Qt ownership of the login widget's connection lifecycle: the background
connection worker, host-key/keyboard-interactive prompts, connect result
handling, mock connections, command dispatch and reconnect handling.
Service access goes through canonical modules with call-time attribute
lookup so tests can patch the canonical homes. The facade keeps thin
delegating methods for signal wiring and the tested API surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from hpc_gui.config import storage as _storage
from hpc_gui.config.models import SSHConfig
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.core import history as _history
from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import describe_connection_error, show_exception
from hpc_gui.services import files_mock as _files_mock
from hpc_gui.services import slurm_mock as _slurm_mock
from hpc_gui.ssh import client as _ssh_client
from hpc_gui.ui.widgets import _login_terminal as _terminal
from hpc_gui.ui.widgets._login_ftp_mode import (
    is_ftp_mock_host,
    is_ftp_test_mode_enabled,
)

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


from hpc_gui.ui.widgets._login_connection_worker import (
    ConnectionWorker,
    prompt_host_key_decision,
    prompt_keyboard_interactive,
)


def begin_connect_async(widget: LoginWidget, cfg: SSHConfig, old_ssh) -> bool:
    if widget._connect_in_progress:
        return False
    widget._connect_in_progress = True
    widget._connection_controller.begin_connect()
    widget._pending_old_ssh = old_ssh
    if widget.terminal_widget is not None:
        widget.terminal_widget.detach()
    widget.btn_connect.setEnabled(False)
    widget.btn_add_connection.setEnabled(False)
    widget.status_label.setText(t("login.status_connecting"))
    widget.cmd_in.set_connected(False)

    thread = QThread(widget)
    worker = ConnectionWorker(
        cfg,
        _terminal.console_shell_geometry(widget),
        widget.append_ssh_console,
        widget.append_shell_output,
        widget._notify_ssh_disconnected,
    )
    worker.host_key_decision_requested.connect(
        lambda request: prompt_host_key_decision(widget, request)
    )
    worker.keyboard_interactive_requested.connect(
        lambda request: prompt_keyboard_interactive(widget, request)
    )
    widget._connect_thread = thread
    widget._connect_worker = worker
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(lambda payload: connect_finished(widget, payload))
    worker.failed.connect(lambda message, exc: connect_failed(widget, message, exc))
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(lambda: connect_thread_finished(widget))
    thread.start()
    return True


def connect_thread_finished(widget: LoginWidget) -> None:
    from hpc_gui.ui.widgets import _login_profiles as _profiles

    widget._connect_in_progress = False
    widget._connect_thread = None
    widget._connect_worker = None
    widget._pending_old_ssh = None
    widget.btn_add_connection.setEnabled(True)
    widget.btn_connect.setEnabled(bool(_profiles.selected_profile_name(widget)))


def connect_finished(widget: LoginWidget, payload: object) -> None:
    from hpc_gui.ui.widgets import _login_profiles as _profiles

    data = payload if isinstance(payload, dict) else {}
    ssh = data.get("ssh")
    slurm = data.get("slurm")
    files = data.get("files")
    cfg = data.get("cfg")
    old_ssh = widget._pending_old_ssh
    try:
        if old_ssh is not None and old_ssh is not ssh:
            try:
                old_ssh.close()
            except Exception:
                pass
        widget._session = {
            "connected": True,
            "cfg": cfg,
            "ssh": ssh,
            "slurm": slurm,
            "files": files,
            "profile_name": widget.profile_name.text().strip(),
        }
        widget._connection_controller.finish(widget._session)
        if widget.terminal_widget is not None and ssh is not None:
            widget.terminal_widget.attach(ssh)
        if isinstance(cfg, SSHConfig):
            identity = f"{cfg.username}@{cfg.host}" if cfg.username else cfg.host
            widget.terminal_identity_label.setText(identity)
        widget.status_label.setText(t("login.status_connected"))
        widget.cmd_in.set_connected(True)
        widget.append_console(t("login.ssh_connected"))
        _terminal.sync_shell_geometry(widget)
        try:
            if widget.terminal_widget is not None:
                widget.terminal_widget.focus_terminal()
            else:
                widget.console.setFocus()
        except Exception:
            pass
        if isinstance(cfg, SSHConfig):
            _history.append_event({"type": "connect", "host": cfg.host, "user": cfg.username, "dry_run": cfg.dry_run})
        widget.session_changed.emit(widget._session)
    finally:
        widget.btn_add_connection.setEnabled(True)
        widget.btn_connect.setEnabled(bool(_profiles.selected_profile_name(widget)))


def connect_failed(widget: LoginWidget, message: str, exc: object) -> None:
    from hpc_gui.ui.widgets import _login_profiles as _profiles

    widget._connection_controller.fail()
    if widget.terminal_widget is not None:
        widget.terminal_widget.detach()
    widget.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
    if isinstance(exc, _ssh_client.HostKeyChangedError):
        message = t("connection.host_key_changed").format(host=exc.hostname)
    elif isinstance(exc, _ssh_client.HostKeyRejectedError):
        message = t("connection.host_key_rejected").format(host=exc.hostname)
    elif isinstance(exc, BaseException):
        message = describe_connection_error(exc, message)
    widget.status_label.setText(t("login.status_disconnected"))
    widget.cmd_in.set_connected(False)
    widget.append_console(t("login.conn_error_prefix").format(err=message))
    show_exception(widget, title=t("login.conn_error_title"), user_message=message, exc=exc if isinstance(exc, BaseException) else None, area="SSH")
    widget.btn_add_connection.setEnabled(True)
    widget.btn_connect.setEnabled(bool(_profiles.selected_profile_name(widget)))


def finish_mock_connection(widget: LoginWidget, cfg: SSHConfig, old_ssh) -> None:
    if old_ssh is not None:
        try:
            old_ssh.close()
        except Exception:
            pass
    ssh = None
    slurm = _slurm_mock.MockSlurmBackend()
    files = _files_mock.MockFilesBackend()
    widget._session = {
        "connected": True,
        "cfg": cfg,
        "ssh": ssh,
        "slurm": slurm,
        "files": files,
        "profile_name": widget.profile_name.text().strip(),
    }
    widget.terminal_identity_label.setText(t("login.terminal_mock"))
    widget.status_label.setText(t("login.status_mock"))
    widget.cmd_in.set_connected(False)
    widget.append_console(t("login.mock_connected"))
    _history.append_event({"type": "connect", "host": cfg.host, "user": cfg.username, "dry_run": True})
    widget.session_changed.emit(widget._session)


def connect_clicked(widget: LoginWidget, transient_password: str = "") -> bool:
    from hpc_gui.config.file_manager_profile import normalize_file_manager_settings
    from hpc_gui.config.jump_host_profile import normalize_jump_host_settings
    from hpc_gui.config.storage import (
        coerce_profile_ssh_timeout,
        coerce_profile_transfer_parallelism,
    )

    try:
        port = int(widget.port.text().strip() or "22")
    except ValueError:
        QMessageBox.warning(widget, t("login.err_title"), t("login.err_port_numeric"))
        return False

    old_ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None

    provider = widget._profile_system_settings.get("provider_template") or {}
    requirements = provider.get("requirements", {}) if isinstance(provider, dict) else {}
    for key, field, label in (("project", widget.project, widget.project_label), ("account", widget.account, widget.account_label)):
        rule = requirements.get(key) if isinstance(requirements, dict) else None
        if isinstance(rule, dict) and rule.get("required") and not field.text().strip():
            QMessageBox.warning(
                widget,
                t("login.err_title"),
                t("connection.required_field").format(
                    field=label.text().rstrip(" *")
                ),
            )
            field.setFocus()
            return False

    # Resolve the credential for this attempt.  The typed field wins, then
    # the transient credential passed by Save & Connect, then a securely
    # saved secret, then a prompt.  Cancelling the prompt aborts before any
    # SSH connection is attempted.
    use_ftp_mock = is_ftp_test_mode_enabled() and is_ftp_mock_host(widget.host.text())
    password = widget.password.text() or str(transient_password or "")
    name = (widget.profile_name.text() or "").strip()
    from hpc_gui.ui.widgets import _login_profiles as _profiles

    prof = _profiles.load_profile_by_name(widget, name)
    if not password and prof and prof.get("save_password"):
        password = widget._decrypt_profile_password(
            prof,
            allow_prompt=True,
        )
        if password is None:
            return False
    if not password and not use_ftp_mock and widget._should_prompt_for_password(prof):
        entered, ok = QInputDialog.getText(
            widget,
            t("connection.password_prompt_title"),
            t("connection.password_prompt_message"),
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            widget.append_console(t("connection.auth_cancelled"))
            return False
        password = entered or ""

    cfg = SSHConfig(
        host=widget.host.text().strip(),
        port=port,
        username=widget.username.text().strip(),
        project=widget.project.text().strip(),
        account=widget.account.text().strip(),
        provider_template=dict(widget._profile_system_settings.get("provider_template") or {}),
        password=password,
        key_path=widget.key_path.text().strip(),
        host_key_policy=widget._profile_host_key_policy,
        x11_forwarding=widget.cb_x11.isChecked(),
        dry_run=use_ftp_mock,
        keepalive_interval_seconds=widget._profile_keepalive,
        transfer_parallelism=coerce_profile_transfer_parallelism(widget._profile_transfer_parallelism),
        ssh_timeout=coerce_profile_ssh_timeout(widget._profile_ssh_timeout),
        system_settings=normalize_system_settings(
            widget._profile_system_settings
        ),
        file_manager_settings=dict(
            normalize_file_manager_settings(
                getattr(widget, "_profile_file_manager_settings", None)
            )
        ),
        jump_host_settings=dict(
            normalize_jump_host_settings(
                getattr(widget, "_profile_jump_host_settings", None)
            )
        ),
    )

    if not cfg.host:
        QMessageBox.warning(widget, t("login.err_title"), t("login.err_host_required"))
        return False

    # X11 preflight: if X11 forwarding is enabled and the user asked for
    # auto dependency management, ensure plink and VcXsrv are available
    # BEFORE connecting.
    app_settings = _storage.load_settings()
    if cfg.x11_forwarding and (not cfg.dry_run) and bool(app_settings.get("x11_autodeps", True)):
        if not widget._x11_runner.preflight(enabled=True, parent=widget, allow_download=True):
            QMessageBox.warning(widget, t("login.x11_title"), t("login.err_x11_plink_needed"))
            return False

    target = f"{cfg.username}@{cfg.host}" if cfg.username else cfg.host
    widget.append_console(t("login.connecting_to").format(target=target, port=cfg.port))
    try:
        if cfg.dry_run:
            finish_mock_connection(widget, cfg, old_ssh)
        else:
            return widget._begin_connect_async(cfg, old_ssh)
    except Exception as e:
        widget.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
        widget.status_label.setText(t("login.status_disconnected"))
        msg = str(e)
        message = describe_connection_error(e, msg)
        widget.append_console(t("login.conn_error_prefix").format(err=message))
        if "SSH protocol banner" in msg or "banner" in msg.lower():
            widget.append_console(
                t("login.ssh_banner_hint")
            )
        show_exception(widget, title=t("login.conn_error_title"), user_message=message, exc=e, area="SSH")
        return False
    return True


def run_command(widget: LoginWidget) -> None:
    # Button compatibility: TerminalInput handles history + clear
    if hasattr(widget.cmd_in, 'submit_current'):
        widget.cmd_in.submit_current()
        return
    cmd = widget.cmd_in.text().strip()
    if not cmd:
        return
    widget.cmd_in.clear()
    run_command_text(widget, cmd)


def run_command_text(widget: LoginWidget, cmd: str) -> None:
    cmd = (cmd or '').strip()
    if not cmd:
        return
    ssh = widget._session.get("ssh")
    if not ssh or not widget._session.get("connected", False):
        if cmd.lower() == "r":
            prompt_reconnect(widget)
            return
        widget.append_console(t("login.ssh_not_connected_mock"))
        return

    info = getattr(ssh, "info", None)
    if widget._x11_runner.run_if_x11(info, cmd, parent=widget):
        _history.append_event({"type": "x11_cmd", "cmd": cmd})
        return

    # Normal terminal commands go through the live shell session.
    try:
        if hasattr(ssh, "send_shell_text") and ssh.send_shell_text(cmd):
            _history.append_event({"type": "ssh_cmd", "cmd": cmd})
            return
        raise RuntimeError("interactive shell unavailable")
    except Exception as e:
        if widget._session.get("connected", False):
            handle_ssh_disconnected(widget, str(e) or "SSH bağlantısı kesildi.")
        widget.append_console(t("login.cmd_error").format(err=e))


def notify_ssh_disconnected(widget: LoginWidget, reason: str) -> None:
    try:
        widget.ssh_disconnected.emit(reason or "SSH bağlantısı kesildi.")
    except Exception:
        pass


def handle_ssh_disconnected(widget: LoginWidget, reason: str) -> None:
    if not widget._session.get("connected", False):
        return
    widget._session["connected"] = False
    widget._connection_controller.finish_disconnect()
    if widget.terminal_widget is not None:
        widget.terminal_widget.detach()
    widget.terminal_identity_label.setText(t("login.terminal_protocol_ssh"))
    widget.status_label.setText(t("login.status_disconnected"))
    widget.cmd_in.set_connected(False)
    notice = t("login.reconnect_notice").format(reason=reason or "")
    if notice != "[login.reconnect_notice]":
        widget.append_console(notice)
    widget.session_changed.emit(widget._session)
    prompt_reconnect(widget)


def prompt_reconnect(widget: LoginWidget) -> None:
    if widget._connect_in_progress:
        return
    if widget._session.get("connected", False):
        return
    if getattr(widget, "_reconnect_prompt_open", False):
        return
    widget._reconnect_prompt_open = True
    try:
        ans = QMessageBox.question(
            widget,
            t("login.reconnect_prompt_title"),
            t("login.reconnect_prompt_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ans == QMessageBox.StandardButton.Yes:
            widget.append_console(t("login.reconnect_started"))
            widget.connect_clicked()
    finally:
        widget._reconnect_prompt_open = False


def shutdown_external_processes(widget: LoginWidget) -> None:
    """Called by MainWindow on app exit."""
    if widget.terminal_widget is not None:
        widget.terminal_widget.detach()
    # Stop a connection attempt before Qt destroys its QThread.
    try:
        worker = widget._connect_worker
        thread = widget._connect_thread
        widget._connection_controller.cancel_connect()
        if worker is not None:
            worker.cancel()
        if thread is not None:
            thread.quit()
            thread.wait(5000)
    except Exception:
        pass

    try:
        st = _storage.load_settings()
    except Exception:
        st = {}

    widget._x11_runner.shutdown(
        close_x11_procs=bool(st.get("close_x11_procs_on_exit", True)),
        close_vcxsrv=bool(st.get("close_vcxsrv_on_exit", True)),
    )

    try:
        ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None
        if ssh is not None:
            ssh.close()
    except Exception:
        pass

    # Wipe connection secrets from in-memory session (best-effort).
    try:
        cfg = widget._session.get("cfg") if hasattr(widget, "_session") else None
        if cfg is not None:
            try:
                cfg.password = ""
            except Exception:
                pass
        ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None
        if ssh is not None and getattr(ssh, "info", None) is not None:
            try:
                ssh.info.password = ""
            except Exception:
                pass
    except Exception:
        pass

    widget._master_password_cache = ""
