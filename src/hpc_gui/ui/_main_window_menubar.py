"""Main-window menubar and language ownership (Wave M01).

Mixin owning legacy flag/version icons, the Menu construction, the
language switch and full UI retranslations. Plugin management is owned
exclusively by the active native wx shell.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMenu, QSizePolicy, QToolButton, QWidget,
)

from hpc_gui import __version__
from hpc_gui.core.i18n import set_language, t


class _MainWindowMenubarMixin:
    def _flag_icon(self, country_code: str) -> QIcon:
        """Return a small flag icon from packaged SVGs (stable on Windows)."""
        cc = (country_code or "").strip().lower()
        if cc == "en":
            cc = "gb"
        # Load SVG from: hpc_gui/assets/flags/{cc}.svg
        try:
            from pathlib import Path
            base = Path(__file__).resolve().parent.parent  # ui -> hpc_gui
            svg_path = base / "assets" / "flags" / f"{cc}.svg"
            if svg_path.exists():
                renderer = QSvgRenderer(str(svg_path))
                pm = QPixmap(18, 12)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                return QIcon(pm)
        except Exception:
            pass

        # Fallback: simple colored badge (no text, no emoji)
        pm = QPixmap(18, 12)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QColor("#444" if cc != "tr" else "#E30A17"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pm.rect().adjusted(0, 0, -1, -1), 2, 2)
        painter.end()
        return QIcon(pm)

    def _init_language_menu(self):
        """Legacy menu with compact language + version."""
        menubar = self.menuBar()
        # --- Language menu (compact, directly accessible) ---
        self._lang_menu = QMenu(self)
        self._act_tr = QAction(self)
        self._act_en = QAction(self)
        self._act_tr.setCheckable(True)
        self._act_en.setCheckable(True)
        self._act_tr.setIcon(self._flag_icon("TR"))
        self._act_en.setIcon(self._flag_icon("GB"))
        self._act_tr.triggered.connect(lambda: self._switch_language("tr"))
        self._act_en.triggered.connect(lambda: self._switch_language("en"))
        self._lang_menu.addAction(self._act_tr)
        self._lang_menu.addAction(self._act_en)

        self._lang_btn = QToolButton(self)
        self._lang_btn.setPopupMode(QToolButton.InstantPopup)
        self._lang_btn.setMenu(self._lang_menu)
        self._lang_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._lang_btn.setIconSize(QSize(20, 14))
        # Compact selector – no wide minimum that crowds the header
        self._lang_btn.setStyleSheet(
            "QToolButton { padding: 4px 8px; text-align: left; }"
            "QToolButton::menu-indicator { subcontrol-position: right center; }"
        )

        self._version_label = QLabel(f"v{__version__}")
        self._version_label.setStyleSheet(
            "QLabel { color: #555; padding: 0 8px; font-weight: 600; }"
        )

        # --- Menu ---
        self._menu_menu = menubar.addMenu(t("menu.menu"))
        # Command Palette only if a REAL implementation exists – omit the fake Help wiring
        # No visible Command Palette entry when none exists; Help stays on F1.
        self._menu_menu.addSeparator()
        self._act_exit = QAction(t("menu.exit"), self)
        self._act_exit.triggered.connect(self.close)
        self._menu_menu.addAction(self._act_exit)

        # --- Compact upper-right utilities: language + plain version text ---
        lang_container = QWidget(self)
        lang_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout = QHBoxLayout(lang_container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.addWidget(self._lang_btn)
        layout.addWidget(self._version_label)
        menubar.setCornerWidget(lang_container, Qt.TopRightCorner)

    def _asset_svg_icon(self, rel_path: str, w: int = 18, h: int = 18) -> QIcon:
        """Render an SVG asset into a QIcon (stable across platforms)."""
        try:
            from pathlib import Path
            base = Path(__file__).resolve().parent.parent  # ui -> hpc_gui
            svg_path = base / rel_path
            if svg_path.exists():
                renderer = QSvgRenderer(str(svg_path))
                pm = QPixmap(w, h)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                return QIcon(pm)
        except Exception:
            pass
        return QIcon()

    def _switch_language(self, lang: str):
        set_language(lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        # Window + tabs
        self.setWindowTitle(t("app.title"))
        if hasattr(self, "tabs"):
            self.tabs.setTabText(self.tabs.indexOf(self.login), t("tabs.login"))
            self.tabs.setTabText(self.tabs.indexOf(self.jobs_outputs), t("tabs.jobs_outputs"))
            self.tabs.setTabText(self.tabs.indexOf(self.directories), t("tabs.directories"))
            self.tabs.setTabText(
                self.tabs.indexOf(self.ftp),
                t("tabs.ftp") if t("tabs.ftp") != "[tabs.ftp]" else "FTP",
            )
            self.tabs.setTabText(self.tabs.indexOf(self.editor), t("tabs.editor"))
            self.tabs.setTabText(self.tabs.indexOf(self.logs), t("tabs.logs"))

        # Menus
        if hasattr(self, "_menu_menu"):
            self._menu_menu.setTitle(t("menu.menu"))
        if hasattr(self, "_act_exit"):
            self._act_exit.setText(t("menu.exit"))
        # Language menu labels / selected language display
        if hasattr(self, "_act_tr"):
            self._act_tr.setText(t("language.turkish"))
        if hasattr(self, "_act_en"):
            self._act_en.setText(t("language.english"))
        # Button shows currently selected language (with flag) and is compact
        if hasattr(self, "_lang_btn"):
            cur = getattr(self, "_current_lang", None)
            if cur is None:
                from hpc_gui.core.i18n import current_language as _cur_lang
                cur = _cur_lang()
            if cur == "tr":
                self._lang_btn.setIcon(self._flag_icon("TR"))
                self._lang_btn.setText(t("language.turkish"))
                if hasattr(self, "_act_tr"):
                    self._act_tr.setChecked(True)
                if hasattr(self, "_act_en"):
                    self._act_en.setChecked(False)
            else:
                self._lang_btn.setIcon(self._flag_icon("GB"))
                self._lang_btn.setText(t("language.english"))
                if hasattr(self, "_act_tr"):
                    self._act_tr.setChecked(False)
                if hasattr(self, "_act_en"):
                    self._act_en.setChecked(True)
            self._lang_btn.setToolTip(t("language.menu_title"))
        # Ask children to retranslate if they support it
        for w in (
            getattr(self, "login", None),
            getattr(self, "jobs_outputs", None),
            getattr(self, "directories", None),
            getattr(self, "ftp", None),
            getattr(self, "editor", None),
            getattr(self, "logs", None),
        ):
            if w is not None and hasattr(w, "retranslate_ui"):
                try:
                    w.retranslate_ui()
                except Exception:
                    pass
