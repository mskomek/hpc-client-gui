from __future__ import annotations

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from truba_gui.config.storage import (
    clear_file_association,
    get_cli_default_profile,
    get_cli_external_access_enabled,
    get_file_associations,
    get_follow_window_open_minimized_enabled,
    get_ftp_transfer_type,
    get_jobs_outputs_refresh_interval_seconds,
    get_lssrv_auto_refresh_enabled,
    get_live_tracking_warning_interval_seconds,
    get_pause_live_follow_when_minimized_enabled,
    get_sacct_auto_refresh_enabled,
    get_sbatch_follow_mode,
    get_squeue_auto_refresh_enabled,
    get_transfer_checksum_verification_enabled,
    get_transfer_parallelism,
    get_upload_preflight_confirmation_enabled,
    load_profiles,
    load_settings,
    set_file_association,
    update_settings,
)
from truba_gui.core.i18n import t
from truba_gui.services.transfer_speed_test import run_transfer_speed_test
from truba_gui.ui.async_call import AsyncCall
from truba_gui.config.system_profile import (
    format_remote_path,
    normalize_system_settings,
    truba_default_remote_paths,
)


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        session=None,
        update_remote_defaults=None,
        clear_remote_directory_cache=None,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(t("settings.dialog_title"))

        st = load_settings()
        self._session = session
        self._update_remote_defaults = update_remote_defaults
        self._clear_remote_directory_cache = clear_remote_directory_cache

        self.cb_x11_autodeps = QCheckBox(t("login.x11_autodeps_label"))
        self.cb_x11_autodeps.setToolTip(t("login.x11_autodeps_tip"))
        self.cb_x11_autodeps.setChecked(bool(st.get("x11_autodeps", True)))

        self.cb_close_vcxsrv_on_exit = QCheckBox(t("login.close_vcxsrv_label"))
        self.cb_close_vcxsrv_on_exit.setToolTip(t("login.close_vcxsrv_tip"))
        self.cb_close_vcxsrv_on_exit.setChecked(bool(st.get("close_vcxsrv_on_exit", True)))

        self.cb_close_x11_procs_on_exit = QCheckBox(t("login.close_x11_procs_label"))
        self.cb_close_x11_procs_on_exit.setToolTip(t("login.close_x11_procs_tip"))
        self.cb_close_x11_procs_on_exit.setChecked(bool(st.get("close_x11_procs_on_exit", True)))

        self.sp_jobs_outputs_refresh_interval = QSpinBox()
        self.sp_jobs_outputs_refresh_interval.setRange(1, 3600)
        self.sp_jobs_outputs_refresh_interval.setSingleStep(1)
        self.sp_jobs_outputs_refresh_interval.setValue(get_jobs_outputs_refresh_interval_seconds())
        self.sp_jobs_outputs_refresh_interval.setToolTip(t("settings.jobs_outputs_refresh_interval_tip"))

        self.sp_live_tracking_warning_interval = QSpinBox()
        self.sp_live_tracking_warning_interval.setRange(0, 3600)
        self.sp_live_tracking_warning_interval.setValue(get_live_tracking_warning_interval_seconds())
        self.sp_live_tracking_warning_interval.setSuffix(" s")
        self.sp_live_tracking_warning_interval.setToolTip(t("settings.live_tracking_warning_interval_tip"))

        self.cb_pause_live_follow_when_minimized = QCheckBox(
            t("settings.pause_live_follow_when_minimized_label")
        )
        self.cb_pause_live_follow_when_minimized.setChecked(
            get_pause_live_follow_when_minimized_enabled()
        )
        self.cb_pause_live_follow_when_minimized.setToolTip(
            t("settings.pause_live_follow_when_minimized_tip")
        )

        self.cb_follow_window_open_minimized = QCheckBox(
            t("settings.follow_window_open_minimized_label")
        )
        self.cb_follow_window_open_minimized.setChecked(
            get_follow_window_open_minimized_enabled()
        )
        self.cb_follow_window_open_minimized.setToolTip(
            t("settings.follow_window_open_minimized_tip")
        )

        self.cb_squeue_auto_refresh = QCheckBox(t("settings.squeue_auto_refresh_label"))
        self.cb_squeue_auto_refresh.setChecked(get_squeue_auto_refresh_enabled())
        self.cb_squeue_auto_refresh.setToolTip(t("settings.squeue_auto_refresh_tip"))

        self.cb_sacct_auto_refresh = QCheckBox(t("settings.sacct_auto_refresh_label"))
        self.cb_sacct_auto_refresh.setChecked(get_sacct_auto_refresh_enabled())
        self.cb_sacct_auto_refresh.setToolTip(t("settings.sacct_auto_refresh_tip"))

        self.cb_lssrv_auto_refresh = QCheckBox(t("settings.lssrv_auto_refresh_label"))
        self.cb_lssrv_auto_refresh.setChecked(get_lssrv_auto_refresh_enabled())
        self.cb_lssrv_auto_refresh.setToolTip(t("settings.lssrv_auto_refresh_tip"))

        self.cb_sbatch_follow_mode = QComboBox()
        for mode, label_key, tip_key in (
            ("none", "settings.sbatch_follow_mode_none", "settings.sbatch_follow_mode_none_tip"),
            ("outputs_tab", "settings.sbatch_follow_mode_outputs_tab", "settings.sbatch_follow_mode_outputs_tab_tip"),
            ("new_tabs_split", "settings.sbatch_follow_mode_tabs", "settings.sbatch_follow_mode_tabs_tip"),
            ("new_window_combined", "settings.sbatch_follow_mode_window_combined", "settings.sbatch_follow_mode_window_combined_tip"),
            ("new_windows_split", "settings.sbatch_follow_mode_windows_split", "settings.sbatch_follow_mode_windows_split_tip"),
        ):
            self.cb_sbatch_follow_mode.addItem(t(label_key), mode)
            self.cb_sbatch_follow_mode.setItemData(
                self.cb_sbatch_follow_mode.count() - 1,
                t(tip_key),
                Qt.ItemDataRole.ToolTipRole,
            )
        follow_mode_index = self.cb_sbatch_follow_mode.findData(get_sbatch_follow_mode())
        self.cb_sbatch_follow_mode.setCurrentIndex(max(0, follow_mode_index))
        self.cb_sbatch_follow_mode.setToolTip(t("settings.sbatch_follow_mode_tip"))

        self.sp_transfer_parallelism = QSpinBox()
        self.sp_transfer_parallelism.setRange(1, 10)
        self.sp_transfer_parallelism.setSingleStep(1)
        self.sp_transfer_parallelism.setValue(get_transfer_parallelism())
        self.sp_transfer_parallelism.setToolTip(t("settings.transfer_parallelism_tip"))

        self.cb_remote_directory_cache = QCheckBox(
            _tr(
                "settings.remote_directory_cache_label",
                "Cache remote directory listings",
            )
        )
        self.cb_remote_directory_cache.setChecked(
            bool(st.get("remote_directory_cache_enabled", True))
        )
        self.cb_remote_directory_cache.setToolTip(
            _tr(
                "settings.remote_directory_cache_tip",
                "Reuse recently visited remote folders until they are changed or refreshed.",
            )
        )
        self.btn_clear_remote_directory_cache = QPushButton(
            _tr("settings.remote_directory_cache_clear", "Clear remote directory cache")
        )
        self.btn_clear_remote_directory_cache.clicked.connect(
            self._clear_remote_directory_cache_clicked
        )

        self.cb_upload_preflight_confirmation = QCheckBox(
            _tr(
                "settings.upload_preflight_confirmation_label",
                "Show upload plan confirmation",
            )
        )
        self.cb_upload_preflight_confirmation.setChecked(
            get_upload_preflight_confirmation_enabled()
        )

        self.cb_transfer_checksum_verification = QCheckBox(
            _tr(
                "settings.transfer_checksum_verification_label",
                "Verify transfers with SHA-256 after completion",
            )
        )
        self.cb_transfer_checksum_verification.setChecked(
            get_transfer_checksum_verification_enabled()
        )
        self.cb_transfer_checksum_verification.setToolTip(
            _tr(
                "settings.transfer_checksum_verification_tip",
                "Compare the source and destination SHA-256 values before marking a transfer successful.",
            )
        )
        self.cb_transfer_speed_test_size = QComboBox()
        for size_mib in (8, 32, 100):
            self.cb_transfer_speed_test_size.addItem(f"{size_mib} MiB", size_mib)
        self.cb_transfer_speed_test_size.setToolTip(_tr("settings.transfer_speed_test_size_tip", "Choose the temporary test file size."))
        self.btn_transfer_speed_test = QPushButton(_tr("settings.transfer_speed_test", "Run remote transfer speed test"))
        self.btn_transfer_speed_test.setEnabled(bool(session and session.get("connected") and session.get("files")))
        self.btn_transfer_speed_test.setToolTip(_tr("settings.transfer_speed_test_tip", "Uploads and downloads a temporary 8 MiB file, verifies it, then removes it."))
        self.btn_transfer_speed_test.clicked.connect(self._run_transfer_speed_test)

        self.cb_ftp_transfer_type = QComboBox()
        self.cb_ftp_transfer_type.addItem(t("ftp.mode_auto"), "auto")
        self.cb_ftp_transfer_type.addItem(t("ftp.mode_binary"), "binary")
        self.cb_ftp_transfer_type.addItem(t("ftp.mode_ascii"), "ascii")
        transfer_type_index = self.cb_ftp_transfer_type.findData(get_ftp_transfer_type())
        self.cb_ftp_transfer_type.setCurrentIndex(max(0, transfer_type_index))
        self.cb_ftp_transfer_type.setToolTip(t("settings.ftp_transfer_type_tip"))
        self._file_associations = get_file_associations()

        self.cb_cli_external_access = QCheckBox(t("settings.cli_external_access_label"))
        self.cb_cli_external_access.setChecked(get_cli_external_access_enabled())
        self.cb_cli_external_access.setToolTip(t("settings.cli_external_access_tip"))

        self.cb_cli_default_profile = QComboBox()
        self.cb_cli_default_profile.addItem(t("settings.cli_default_profile_none"), "")
        for profile in load_profiles():
            name = str(profile.get("name") or "").strip()
            if name:
                self.cb_cli_default_profile.addItem(name, name)
        default_index = self.cb_cli_default_profile.findData(get_cli_default_profile())
        self.cb_cli_default_profile.setCurrentIndex(max(0, default_index))
        self.cb_cli_default_profile.setToolTip(t("settings.cli_default_profile_tip"))

        connection_group = QGroupBox(t("settings.connection_section"))
        connection_form = QFormLayout(connection_group)
        connection_form.addRow(self.cb_x11_autodeps)
        connection_form.addRow(self.cb_close_vcxsrv_on_exit)
        connection_form.addRow(self.cb_close_x11_procs_on_exit)
        connection_form.addRow(self.cb_cli_external_access)
        connection_form.addRow(
            t("settings.cli_default_profile_label"),
            self.cb_cli_default_profile,
        )

        jobs_group = QGroupBox(t("settings.jobs_outputs_section"))
        jobs_form = QFormLayout(jobs_group)
        jobs_form.addRow(
            t("settings.jobs_outputs_refresh_interval_label"),
            self.sp_jobs_outputs_refresh_interval,
        )
        jobs_form.addRow(t("settings.live_tracking_warning_interval_label"), self.sp_live_tracking_warning_interval)
        jobs_form.addRow(self.cb_pause_live_follow_when_minimized)
        jobs_form.addRow(self.cb_follow_window_open_minimized)
        jobs_form.addRow(self.cb_squeue_auto_refresh)
        jobs_form.addRow(self.cb_sacct_auto_refresh)
        jobs_form.addRow(self.cb_lssrv_auto_refresh)
        jobs_form.addRow(
            t("settings.sbatch_follow_mode_label"),
            self.cb_sbatch_follow_mode,
        )

        ftp_group = QGroupBox(t("settings.ftp_section"))
        ftp_form = QFormLayout(ftp_group)
        cfg = (session or {}).get("cfg") if session else None
        system = normalize_system_settings(
            getattr(cfg, "system_settings", None) if cfg else None
        )
        self.ftp_scratch_dir = QLineEdit(system["scratch_dir"])
        self.ftp_home_dir = QLineEdit(system["home_dir"])
        self._saved_remote_defaults = (
            system["scratch_dir"].strip(),
            system["home_dir"].strip(),
        )
        profile_available = bool(
            session
            and session.get("connected")
            and session.get("profile_name")
            and update_remote_defaults
        )
        self.ftp_scratch_dir.setEnabled(profile_available)
        self.ftp_home_dir.setEnabled(profile_available)
        ftp_form.addRow(t("settings.ftp_scratch_default"), self.ftp_scratch_dir)
        ftp_form.addRow(t("settings.ftp_home_default"), self.ftp_home_dir)
        ftp_form.addRow(
            t("settings.ftp_transfer_type_label"),
            self.cb_ftp_transfer_type,
        )
        ftp_form.addRow(
            t("settings.transfer_parallelism_label"),
            self.sp_transfer_parallelism,
        )
        ftp_form.addRow(self.cb_upload_preflight_confirmation)
        ftp_form.addRow(self.cb_transfer_checksum_verification)
        ftp_form.addRow(t("settings.transfer_speed_test_size_label"), self.cb_transfer_speed_test_size)
        ftp_form.addRow(self.btn_transfer_speed_test)
        ftp_form.addRow(self.cb_remote_directory_cache)
        ftp_form.addRow(self.btn_clear_remote_directory_cache)
        self.btn_ftp_reset_defaults = QPushButton(
            t("settings.ftp_reset_defaults")
        )
        self.btn_ftp_reset_defaults.setEnabled(profile_available)
        self.btn_ftp_reset_defaults.clicked.connect(self._reset_ftp_defaults)
        ftp_form.addRow(self.btn_ftp_reset_defaults)

        associations_group = QGroupBox(t("settings.file_associations_section"))
        associations_layout = QVBoxLayout(associations_group)
        self.file_associations_list = QListWidget()
        associations_layout.addWidget(self.file_associations_list)
        association_buttons = QHBoxLayout()
        self.btn_change_file_association = QPushButton(
            t("settings.file_association_change")
        )
        self.btn_clear_file_association = QPushButton(
            t("settings.file_association_clear")
        )
        self.btn_change_file_association.clicked.connect(
            self._change_selected_file_association
        )
        self.btn_clear_file_association.clicked.connect(
            self._clear_selected_file_association
        )
        association_buttons.addWidget(self.btn_change_file_association)
        association_buttons.addWidget(self.btn_clear_file_association)
        associations_layout.addLayout(association_buttons)
        self._refresh_file_association_list()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close
        )
        self.btn_apply = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.btn_close = self.buttons.button(QDialogButtonBox.StandardButton.Close)
        self.btn_apply.setText(_tr("settings.apply", "Apply"))
        self.btn_close.setText(_tr("common.close", "Close"))
        self.btn_apply.clicked.connect(self._apply_settings)
        self.btn_close.clicked.connect(self.reject)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(connection_group)
        content_layout.addWidget(jobs_group)
        content_layout.addWidget(ftp_group)
        content_layout.addWidget(associations_group)
        content_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.addWidget(scroll, 1)
        root.addWidget(self.buttons, 0)
        self.resize(720, min(760, max(520, self.sizeHint().height())))

    def _apply_settings(self) -> None:
        update_settings(
            {
                "x11_autodeps": self.cb_x11_autodeps.isChecked(),
                "close_vcxsrv_on_exit": self.cb_close_vcxsrv_on_exit.isChecked(),
                "close_x11_procs_on_exit": self.cb_close_x11_procs_on_exit.isChecked(),
                "cli_external_access_enabled": self.cb_cli_external_access.isChecked(),
                "cli_default_profile": str(self.cb_cli_default_profile.currentData() or ""),
                "jobs_outputs_refresh_interval_seconds": int(self.sp_jobs_outputs_refresh_interval.value()),
                "live_tracking_warning_interval_seconds": int(self.sp_live_tracking_warning_interval.value()),
                "pause_live_follow_when_minimized_enabled": (
                    self.cb_pause_live_follow_when_minimized.isChecked()
                ),
                "follow_window_open_minimized_enabled": (
                    self.cb_follow_window_open_minimized.isChecked()
                ),
                "squeue_auto_refresh_enabled": self.cb_squeue_auto_refresh.isChecked(),
                "sacct_auto_refresh_enabled": self.cb_sacct_auto_refresh.isChecked(),
                "lssrv_auto_refresh_enabled": self.cb_lssrv_auto_refresh.isChecked(),
                "sbatch_follow_mode": str(
                    self.cb_sbatch_follow_mode.currentData() or "outputs_tab"
                ),
                "transfer_parallelism": int(self.sp_transfer_parallelism.value()),
                "upload_preflight_confirmation_enabled": (
                    self.cb_upload_preflight_confirmation.isChecked()
                ),
                "transfer_checksum_verification_enabled": (
                    self.cb_transfer_checksum_verification.isChecked()
                ),
                "ftp_transfer_type": str(
                    self.cb_ftp_transfer_type.currentData() or "auto"
                ),
                "remote_directory_cache_enabled": self.cb_remote_directory_cache.isChecked(),
            }
        )
        if not self.cb_remote_directory_cache.isChecked():
            self._clear_remote_directory_cache_clicked()
        remote_defaults = (
            self.ftp_scratch_dir.text().strip(),
            self.ftp_home_dir.text().strip(),
        )
        if (
            self._update_remote_defaults is not None
            and self.ftp_scratch_dir.isEnabled()
            and remote_defaults != self._saved_remote_defaults
        ):
            self._update_remote_defaults(*remote_defaults)
            self._saved_remote_defaults = remote_defaults

    def _run_transfer_speed_test(self) -> None:
        session = self._session
        files = session.get("files") if session else None
        if not session or not session.get("connected") or not files:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        cfg = session.get("cfg")
        system = normalize_system_settings(getattr(cfg, "system_settings", None))
        remote_dir = format_remote_path(system["scratch_dir"], getattr(cfg, "username", "user"))
        self.btn_transfer_speed_test.setEnabled(False)
        worker = AsyncCall(("speed-test", id(self)), lambda: run_transfer_speed_test(files, remote_dir=remote_dir, size_mib=int(self.cb_transfer_speed_test_size.currentData() or 8)))
        self._speed_test_worker = worker
        def finished(_token, result) -> None:
            self._speed_test_worker = None
            self.btn_transfer_speed_test.setEnabled(True)
            QMessageBox.information(self, _tr("settings.transfer_speed_test", "Remote transfer speed test"), _tr("settings.transfer_speed_test_result", "Size: {size} MiB\\nUpload: {upload} MiB/s\\nDownload: {download} MiB/s").format(size=f"{result['size_mib']:.0f}", upload=f"{result['upload_mib_s']:.2f}", download=f"{result['download_mib_s']:.2f}"))
        def failed(_token, error) -> None:
            self._speed_test_worker = None
            self.btn_transfer_speed_test.setEnabled(True)
            QMessageBox.warning(self, _tr("common.error", "Error"), str(error))
        worker.signals.finished.connect(finished)
        worker.signals.failed.connect(failed)
        QThreadPool.globalInstance().start(worker)

    def _clear_remote_directory_cache_clicked(self) -> None:
        if self._clear_remote_directory_cache is not None:
            self._clear_remote_directory_cache()

    def _reset_ftp_defaults(self) -> None:
        defaults = truba_default_remote_paths()
        self.ftp_scratch_dir.setText(defaults["scratch_dir"])
        self.ftp_home_dir.setText(defaults["home_dir"])

    def _refresh_file_association_list(self) -> None:
        self.file_associations_list.clear()
        for extension, program in sorted(self._file_associations.items()):
            self.file_associations_list.addItem(f"{extension} -> {program}")
        empty = not self._file_associations
        self.btn_change_file_association.setEnabled(not empty)
        self.btn_clear_file_association.setEnabled(not empty)

    def _selected_file_association_extension(self) -> str:
        item = self.file_associations_list.currentItem()
        if item is None:
            return ""
        return item.text().split(" -> ", 1)[0].strip()

    def _change_selected_file_association(self) -> None:
        extension = self._selected_file_association_extension()
        if not extension:
            QMessageBox.information(
                self,
                t("common.info"),
                t("settings.file_association_none_selected"),
            )
            return
        program, _ = QFileDialog.getOpenFileName(
            self,
            t("files.open_with_select_program"),
            self._file_associations.get(extension, ""),
            t("files.open_with_program_filter"),
        )
        if not program:
            return
        self._file_associations = set_file_association(extension, program)
        self._refresh_file_association_list()

    def _clear_selected_file_association(self) -> None:
        extension = self._selected_file_association_extension()
        if not extension:
            QMessageBox.information(
                self,
                t("common.info"),
                t("settings.file_association_none_selected"),
            )
            return
        self._file_associations = clear_file_association(extension)
        self._refresh_file_association_list()
