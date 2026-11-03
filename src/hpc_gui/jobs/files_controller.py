"""Selected-job remote Files view and navigation actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.job_paths import resolve_job_directory


@dataclass
class JobFilesBindings:
    wx: Any
    model: Any
    state: dict[str, Any]
    browser: Any
    directory_model: Any
    no_selection_panel: Any
    header: Any
    browser_sizer: Any
    job_header: Any
    workdir_label: Any
    open_main_files: Callable | None


class JobFilesController:
    """Resolve job paths and keep the shared browser bound to one selection."""

    def __init__(self, bindings: JobFilesBindings) -> None:
        self.bindings = bindings

    def directory(self, context) -> str:
        return resolve_job_directory(context).path

    def update_header(self, context=None) -> None:
        bindings = self.bindings
        context = context or bindings.model.selected_job_store.context
        if not context.job_id:
            bindings.job_header.SetLabel("")
            bindings.workdir_label.SetLabel("")
            return
        resolved = resolve_job_directory(context)
        qualifier = "" if resolved.verified or not resolved.path else f" · fallback: {resolved.source}"
        bindings.job_header.SetLabel(
            f"{t('jobs_outputs.job_label')} {context.job_id}"
            + (f" · {context.name}" if context.name else "")
        )
        bindings.workdir_label.SetLabel(
            f"{t('jobs_outputs.workdir')}: {resolved.path or '—'}{qualifier}"
        )

    def show_selected_state(self, show: bool) -> None:
        bindings = self.bindings
        if show:
            bindings.no_selection_panel.Hide()
            bindings.header.Show()
            bindings.browser.Show()
        else:
            bindings.header.Hide()
            bindings.browser.Hide()
            bindings.no_selection_panel.Show()
        bindings.browser_sizer.Layout()

    def open_main_files(self, _event=None) -> None:
        bindings = self.bindings
        context = bindings.model.selected_job_store.context
        directory = self.directory(context)
        if not context.job_id or not directory:
            bindings.wx.MessageBox(
                t("jobs_outputs.directory_unavailable"), t("jobs_outputs.workdir"),
                bindings.wx.OK | bindings.wx.ICON_INFORMATION,
            )
            return
        try:
            result = bindings.open_main_files(directory) if callable(bindings.open_main_files) else False
            if result is False:
                raise RuntimeError(t("jobs_outputs.main_files_unavailable"))
        except Exception as error:
            bindings.wx.MessageBox(str(error), t("jobs_outputs.workdir"), bindings.wx.OK | bindings.wx.ICON_ERROR)

    def reset_browser(self) -> None:
        bindings = self.bindings
        reset = getattr(bindings.browser, "_wx_remote_reset", None)
        if callable(reset):
            reset()
            return
        try:
            bindings.directory_model.invalidate()
            bindings.browser._wx_remote_controls["listing"].DeleteAllItems()
        except Exception:
            pass

    def navigate_to_workdir(self, _event=None) -> None:
        bindings = self.bindings
        context = bindings.model.selected_job_store.context
        self.update_header(context)
        if not context.job_id:
            self.show_selected_state(False)
            return
        workdir = self.directory(context)
        if not workdir:
            self.reset_browser()
            self.show_selected_state(True)
            return
        self.show_selected_state(True)
        try:
            bindings.browser._wx_remote_controls["navigate"](workdir)
            bindings.browser._wx_remote_controls["load"]()
        except Exception as error:
            bindings.wx.MessageBox(str(error), t("jobs_outputs.workdir"), bindings.wx.OK | bindings.wx.ICON_ERROR)