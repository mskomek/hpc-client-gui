"""Version selector wiring for manifest-pinned Case Studio catalogs."""

from __future__ import annotations

from .command_catalog import load_command_catalog
from .workflow import WorkflowPlan


class ReleaseSelectionController:
    """Switch release catalogs without dropping incompatible workflow steps."""

    def __init__(self, page):
        self.page = page

    def bind(self):
        selector = self.page.version
        if hasattr(selector, "currentTextChanged"):
            selector.currentTextChanged.connect(self._qt_changed)
        else:
            selector.Bind(self.page.wx.EVT_CHOICE, self._wx_changed)

    def _qt_changed(self, release: str):
        self._switch(str(release))

    def _wx_changed(self, event):
        self._switch(self.page.version.GetStringSelection())
        event.Skip()

    def _switch(self, release: str):
        page = self.page
        previous = page.target_release
        if release == previous:
            return
        try:
            catalog = load_command_catalog(page.plugin, release)
            plan = WorkflowPlan(catalog["commands"])
            for step in page.workflow_plan.steps:
                plan.add(step)
        except (ValueError, OSError) as exc:
            self._restore(previous)
            self._set_status(str(exc))
            return

        page.target_release = release
        page.command_catalog = catalog
        page.workflow_plan = plan
        if hasattr(page, "workflow"):
            page.workflow.plan = plan
            page.workflow.commands = list(catalog["commands"])
            page.workflow.visible_commands = list(page.workflow.commands)
            page.workflow.release = release
            page.workflow._show_commands()
            page.workflow._refresh_flow()
        else:
            page._show_commands()
            page._refresh_flow()
        if release == "v1912":
            self._set_status(
                "v1912 limited profile: blockMesh, checkMesh and simpleFoam; "
                "no TRUBA module is verified."
            )
        else:
            self._set_status("OpenFOAM.com / ESI v2312 selected.")

    def _restore(self, release: str):
        selector = self.page.version
        if hasattr(selector, "setCurrentText"):
            selector.blockSignals(True)
            selector.setCurrentText(release)
            selector.blockSignals(False)
        else:
            selector.SetStringSelection(release)

    def _set_status(self, message: str):
        status = self.page.status
        if hasattr(status, "setText"):
            status.setText(message)
        else:
            status.SetLabel(message)
