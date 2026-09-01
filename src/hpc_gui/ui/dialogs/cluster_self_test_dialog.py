from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from hpc_gui.core.i18n import t
from hpc_gui.services.cluster_self_test import ClusterSelfTestResult, run_cluster_self_test
from hpc_gui.services.provider_capabilities import build_provider_capability_view, observed_from_self_test
from hpc_gui.ssh.client import SSHConnInfo
from hpc_gui.ssh.jump import jump_info_from_settings
from hpc_gui.ui.async_call import AsyncCall

_COLORS = {"PASS": "#188038", "FAIL": "#c5221f", "WARNING": "#b06000"}


def format_self_test_result(result: ClusterSelfTestResult) -> str:
    """Return safe, host/user-free text suitable for issue reports."""
    lines = [f"status: {result.status}"]
    for section in result.sections:
        lines.append(f"[{section.id}]")
        for item in section.items:
            detail = f" — {item.detail}" if item.detail else ""
            lines.append(f"{item.id}: {item.status}{detail}")
    return "\n".join(lines)


class ClusterSelfTestDialog(QDialog):
    def __init__(self, parent, profile: Mapping[str, Any]) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("cluster_self_test.title"))
        self.resize(680, 520)
        self._profile = dict(profile)
        self._closed = False
        self._worker: AsyncCall | None = None
        self._result: ClusterSelfTestResult | None = None

        self.summary = QLabel(t("cluster_self_test.ready"), self)
        self.summary.setWordWrap(True)
        self.results = QListWidget(self)
        self.results.setAlternatingRowColors(True)
        self.results.setAccessibleName(t("cluster_self_test.results"))
        self.btn_again = QPushButton(t("cluster_self_test.run_again"), self)
        self.btn_copy = QPushButton(t("cluster_self_test.copy"), self)
        self.btn_close = QPushButton(t("common.close"), self)
        self.btn_again.clicked.connect(self.run_test)
        self.btn_copy.clicked.connect(self.copy_result)
        self.btn_close.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.btn_again)
        buttons.addWidget(self.btn_copy)
        buttons.addWidget(self.btn_close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.results, 1)
        layout.addLayout(buttons)
        self.run_test()

    def _info(self) -> SSHConnInfo:
        return SSHConnInfo(
            host=str(self._profile.get("host") or "").strip(),
            port=int(self._profile.get("port") or 22),
            username=str(self._profile.get("username") or "").strip(),
            password=str(self._profile.get("password") or ""),
            key_path=str(self._profile.get("key_path") or "").strip(),
            host_key_policy=str(self._profile.get("host_key_policy") or "accept-new"),
            x11_forwarding=bool(self._profile.get("x11_forwarding", False)),
            timeout=self._profile.get("ssh_timeout"),
            jump=jump_info_from_settings(self._profile.get("jump_host")),
        )

    def run_test(self) -> None:
        if self._worker is not None:
            return
        self._closed = False
        self.summary.setText(t("cluster_self_test.running"))
        self.results.clear()
        self.btn_again.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self._worker = AsyncCall(
            self,
            lambda: run_cluster_self_test(
                self._info(),
                provider=self._profile.get("provider_template"),
                project=str(self._profile.get("project") or ""),
                account=str(self._profile.get("account") or ""),
            ),
        )
        self._worker.signals.finished.connect(self._finished)
        self._worker.signals.failed.connect(self._failed)
        QThreadPool.globalInstance().start(self._worker)

    def _finished(self, _token: object, result: object) -> None:
        self._worker = None
        if self._closed or not isinstance(result, ClusterSelfTestResult):
            return
        self._result = result
        self.summary.setText(t("cluster_self_test.summary").format(status=result.status))
        view = build_provider_capability_view(
            self._profile.get("provider_template"),
            observed_from_self_test(result),
            project=str(self._profile.get("project") or ""),
            account=str(self._profile.get("account") or ""),
        )
        self.results.addItem(QListWidgetItem(t("cluster_self_test.declared_header").format(provider=view.provider)))
        self.results.addItem(QListWidgetItem(t("cluster_self_test.observed_header")))
        for capability in view.capabilities:
            self.results.addItem(QListWidgetItem(
                f"  {capability.id}: {capability.declared} / {capability.observed}"
            ))
        for section in result.sections:
            header = QListWidgetItem(section.id)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            self.results.addItem(header)
            for item in section.items:
                row = QListWidgetItem(f"  {item.id}: {item.status} — {item.detail}")
                if item.status in _COLORS:
                    row.setForeground(QColor(_COLORS[item.status]))
                self.results.addItem(row)
        self.btn_again.setEnabled(True)
        self.btn_copy.setEnabled(True)
        self.results.setFocus()

    def _failed(self, _token: object, _error: object) -> None:
        self._worker = None
        if self._closed:
            return
        self.summary.setText(t("cluster_self_test.failed"))
        self.btn_again.setEnabled(True)

    def copy_result(self) -> None:
        if self._result is not None:
            QApplication.clipboard().setText(format_self_test_result(self._result))

    def reject(self) -> None:
        self._closed = True
        super().reject()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._closed = True
        super().closeEvent(event)
