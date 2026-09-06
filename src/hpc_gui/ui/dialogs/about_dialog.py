"""About dialog – authoritative version, no network required."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.core.paths import is_frozen_exe


def _get_license_text_path() -> Path | None:
    """Return path to LICENSE file if accessible, handling frozen packaging."""
    candidates: list[Path] = []
    # Source checkout
    candidates.append(Path(__file__).resolve().parents[3].parent / "LICENSE")
    candidates.append(Path(__file__).resolve().parents[1] / "LICENSE")
    # Frozen: check for extracted site
    if is_frozen_exe():
        try:
            base = Path(sys.executable).resolve().parent
            candidates.append(base / "LICENSE")
            candidates.append(base / "_internal" / "LICENSE")
            # Try to find via importlib.resources
            try:
                import importlib.resources as resources

                # Attempt to locate via package resources
                for res in resources.files("hpc_gui").rglob("LICENSE*"):
                    candidates.append(Path(str(res)))
            except Exception:
                pass
        except Exception:
            pass
    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.setMinimumWidth(540)
        self.resize(560, 420)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        layout = QVBoxLayout(self)

        title = QLabel("HPC Client GUI")
        title.setStyleSheet("font-weight: 700; font-size: 16px;")
        layout.addWidget(title)

        version_label = QLabel(t("about.version_label").format(version=__version__) if "[about.version_label]" not in t("about.version_label") else f"Version {__version__}")
        # Fallback if key missing
        if version_label.text().startswith("["):
            version_label.setText(f"Version {__version__}")
        version_label.setStyleSheet("color: #333; font-size: 13px;")
        layout.addWidget(version_label)

        desc = QLabel(t("about.description") if t("about.description") != "[about.description]" else "SSH · Slurm · X11 workflow manager for HPC clusters.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        # Repository access – canonical HTTPS
        repo_url = "https://github.com/mskomek/hpc-client-gui"
        self._repo_btn = QPushButton(t("about.project") if t("about.project") != "[about.project]" else "Project Repository")
        self._repo_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(repo_url)))
        layout.addWidget(self._repo_btn)

        # License access – open local file if available, otherwise canonical URL fallback (no source-checkout-only button)
        license_path = _get_license_text_path()
        license_url = "https://github.com/mskomek/hpc-client-gui/blob/main/LICENSE"
        self._license_btn = QPushButton(t("about.license") if t("about.license") != "[about.license]" else "License")
        def open_license():
            if license_path and license_path.is_file():
                # Open via file url if possible, but ensure not source-checkout-only: we always fallback to HTTPS if file not found
                try:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(license_path)))
                    return
                except Exception:
                    pass
            QDesktopServices.openUrl(QUrl(license_url))
        self._license_btn.clicked.connect(open_license)
        layout.addWidget(self._license_btn)

        # Third-party notices
        notices_path = None
        for cand in [Path(__file__).resolve().parents[3].parent / "THIRD_PARTY_NOTICES.md", Path(__file__).resolve().parents[1] / "THIRD_PARTY_NOTICES.md"]:
            if cand.is_file():
                notices_path = cand
                break
        notices_url = "https://github.com/mskomek/hpc-client-gui/blob/main/THIRD_PARTY_NOTICES.md"
        self._notices_btn = QPushButton(t("about.notices") if t("about.notices") != "[about.notices]" else "Third-Party Notices")
        def open_notices():
            if notices_path and notices_path.is_file():
                try:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(notices_path)))
                    return
                except Exception:
                    pass
            QDesktopServices.openUrl(QUrl(notices_url))
        self._notices_btn.clicked.connect(open_notices)
        layout.addWidget(self._notices_btn)

        layout.addStretch(1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton(t("about.close") if t("about.close") != "[about.close]" else t("common.close"))
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        self._close_btn = close_btn
        self._version_label_ref = version_label

    def retranslate_ui(self):
        self.setWindowTitle(t("about.title"))
        # Update version label retains authoritative version
        ver_text = t("about.version_label")
        if ver_text != "[about.version_label]":
            self._version_label_ref.setText(ver_text.format(version=__version__))
        else:
            self._version_label_ref.setText(f"Version {__version__}")
        self._repo_btn.setText(t("about.project") if t("about.project") != "[about.project]" else "Project Repository")
        self._license_btn.setText(t("about.license") if t("about.license") != "[about.license]" else "License")
        self._notices_btn.setText(t("about.notices") if t("about.notices") != "[about.notices]" else "Third-Party Notices")
        self._close_btn.setText(t("about.close") if t("about.close") != "[about.close]" else t("common.close"))
