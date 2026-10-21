"""Login background connection worker (Wave M01).

Qt ownership of the off-GUI-thread SSH connection worker plus the
GUI-thread prompt bridges it uses (host-key decisions and
keyboard-interactive answers). The connection flow in
``_login_connect`` drives this worker; services are reached through
canonical modules with call-time attribute lookup.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, QObject, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from hpc_gui.config.models import SSHConfig
from hpc_gui.core.i18n import t
from hpc_gui.services import connection_profile_service as _profile_svc
from hpc_gui.services import files_ssh as _files_ssh
from hpc_gui.services import slurm_ssh as _slurm_ssh
from hpc_gui.ssh import client as _ssh_client
from hpc_gui.ssh import jump as _jump

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


class ConnectionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str, object)
    host_key_decision_requested = Signal(object)
    keyboard_interactive_requested = Signal(object)

    def __init__(self, cfg: SSHConfig, shell_size: tuple[int, int], log_cb, shell_output_cb, disconnect_cb=None):
        self._cancelled = False
        self._ssh = None
        super().__init__()
        self._cfg = cfg
        self._shell_size = shell_size
        self._log_cb = log_cb
        self._shell_output_cb = shell_output_cb
        self._disconnect_cb = disconnect_cb

    def _decide_host_key(self, info) -> str:
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

    def _keyboard_interactive(self, title, instructions, prompts):
        request = {
            "title": title or "SSH authentication",
            "instructions": instructions or "",
            "prompts": list(prompts or []),
            "responses": [],
            "done": threading.Event(),
        }
        self.keyboard_interactive_requested.emit(request)
        while not request["done"].wait(0.1):
            if self._cancelled or QCoreApplication.closingDown():
                return []
        return list(request.get("responses") or [])

    def run(self) -> None:
        try:
            auth_methods = _profile_svc.normalize_auth_methods(self._cfg.system_settings)
            conn = _ssh_client.SSHConnInfo(
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
                jump=_jump.jump_info_from_settings(
                    getattr(self._cfg, "jump_host_settings", None)
                ),
                keyboard_interactive_handler=(
                    self._keyboard_interactive
                    if "keyboard-interactive" in auth_methods
                    else None
                ),
            )
            ssh = _ssh_client.SSHClientWrapper(
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
            slurm = _slurm_ssh.SSHSlurmBackend(ssh, self._cfg.system_settings)
            files = _files_ssh.SSHFilesBackend(ssh)
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


def prompt_host_key_decision(widget: LoginWidget, request: object) -> None:
    data = request if isinstance(request, dict) else {}
    done = data.get("done")
    try:
        info = data.get("info")
        if not isinstance(info, _ssh_client.HostKeyInfo):
            return
        role_label = (
            t("connection.host_key_role_jump")
            if getattr(info, "role", "target") == "jump"
            else t("connection.host_key_role_target")
        )
        dialog = QMessageBox(widget)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle(t("connection.host_key_prompt_title"))
        dialog.setText(
            t("connection.host_key_prompt_message").format(
                host=info.hostname,
                key_type=info.key_type,
                fingerprint=info.fingerprint,
                role=role_label,
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


def prompt_keyboard_interactive(widget: LoginWidget, request: object) -> None:
    data = request if isinstance(request, dict) else {}
    done = data.get("done")
    responses: list[str] = []
    try:
        title = str(data.get("title") or "SSH authentication")
        instructions = str(data.get("instructions") or "")
        for prompt, echo in data.get("prompts") or []:
            label = str(prompt or "SSH response")
            if instructions:
                label = f"{instructions}\n\n{label}"
            value, ok = QInputDialog.getText(
                widget,
                title,
                label,
                QLineEdit.EchoMode.Normal if echo else QLineEdit.EchoMode.Password,
            )
            if not ok:
                return
            responses.append(value)
        data["responses"] = responses
    finally:
        if isinstance(done, threading.Event):
            done.set()
