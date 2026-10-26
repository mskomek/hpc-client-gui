"""wx command-library interactions for the Visual Flow."""
from __future__ import annotations

from hpc_gui.core.i18n import t

from .workflow import WorkflowPlan


class WxCommandWorkflow:
    def __init__(
        self,
        wx,
        commands,
        plan: WorkflowPlan,
        *,
        command_list,
        command_details,
        command_filter,
        add_button,
        flow,
        remove_button,
        move_up_button,
        move_down_button,
        status,
    ):
        self.wx = wx
        self.plan = plan
        self.commands = list(commands)
        self.visible_commands = list(self.commands)
        self.command_list = command_list
        self.command_details = command_details
        self.command_filter = command_filter
        self.add_button = add_button
        self.flow = flow
        self.remove_button = remove_button
        self.move_up_button = move_up_button
        self.move_down_button = move_down_button
        self.status = status
        self._drag_origin = None
        self._drop_target = self._make_drop_target()
        self.flow.SetDropTarget(self._drop_target)
        self.command_list.Bind(wx.EVT_LISTBOX, self._command_selected)
        self.command_list.Bind(wx.EVT_LEFT_DOWN, self._drag_started)
        self.command_list.Bind(wx.EVT_LEFT_UP, self._drag_ended)
        self.command_list.Bind(wx.EVT_MOTION, self._drag_motion)
        self.add_button.Bind(wx.EVT_BUTTON, self._add_selected)
        self.remove_button.Bind(wx.EVT_BUTTON, self._remove_selected)
        self.move_up_button.Bind(wx.EVT_BUTTON, self._move_up)
        self.move_down_button.Bind(wx.EVT_BUTTON, self._move_down)
        self.command_filter.Bind(wx.EVT_TEXT, self._filter)
        self._show_commands()
        self._refresh_flow()

    def _make_drop_target(self):
        controller = self

        class FlowDropTarget(self.wx.TextDropTarget):
            def OnDropText(self, x, y, text):
                return controller.add_dropped(str(text), x, y)

        return FlowDropTarget()

    def _show_commands(self):
        self.visible_commands = list(self.commands)
        self.command_list.Set([self._command_label(item) for item in self.visible_commands])

    @staticmethod
    def _command_label(item):
        return f"{item['name']} — {item['category']}"

    def _filter(self, _event):
        needle = self.command_filter.GetValue().strip().casefold()
        self.visible_commands = [
            item for item in self.commands
            if needle in str(item["name"]).casefold()
            or needle in str(item["category"]).casefold()
            or needle in str(item["verification_status"]).casefold()
        ]
        self.command_list.Set([self._command_label(item) for item in self.visible_commands])

    def _selected_command(self):
        index = self.command_list.GetSelection()
        if 0 <= index < len(self.visible_commands):
            return self.visible_commands[index]
        return None

    def _command_selected(self, event):
        command = self._selected_command()
        if command is not None:
            self.command_details.SetValue(
                f"{command['name']}\n{command['category']}\nOpenFOAM.com / ESI v2312\n"
                f"Status: {command['verification_status']}\nSource: {command['source']}\n"
                f"{t('openfoam.no_parameters_verified')}\n{t('openfoam.commands_draft_only')}"
            )
        event.Skip()

    def _add_selected(self, _event):
        command = self._selected_command()
        if command is not None:
            self._add(str(command["name"]))

    def add_dropped(self, name: str, x: int, y: int) -> bool:
        index = self.flow.HitTest(self.wx.Point(x, y))
        if index < 0:
            index = len(self.plan.steps)
        return self._add(name, index=index)

    def _add(self, name: str, *, index=None):
        try:
            inserted = self.plan.add(name, index=index)
        except (IndexError, ValueError):
            self.status.SetLabel(t("openfoam.invalid_workflow_command"))
            return False
        self._refresh_flow(selected=inserted)
        self.status.SetLabel(t("openfoam.workflow_added").format(name=name))
        return True

    def _remove_selected(self, _event):
        index = self.flow.GetSelection()
        try:
            name = self.plan.remove(index)
        except IndexError:
            return
        self._refresh_flow(selected=min(index, len(self.plan.steps) - 1))
        self.status.SetLabel(t("openfoam.workflow_removed").format(name=name))

    def _move_up(self, _event):
        self._move(-1)

    def _move_down(self, _event):
        self._move(1)

    def _move(self, offset):
        index = self.flow.GetSelection()
        try:
            target = self.plan.move(index, offset)
        except (IndexError, ValueError):
            return
        if target is not None:
            self._refresh_flow(selected=target)

    def _refresh_flow(self, *, selected=None):
        self.flow.Set(list(self.plan.labels()))
        if selected is not None and 0 <= selected < len(self.plan.steps):
            self.flow.SetSelection(selected)

    def _drag_started(self, event):
        position = event.GetPosition()
        index = self.command_list.HitTest(position)
        self._drag_origin = position if index >= 0 else None
        if index >= 0:
            self.command_list.SetSelection(index)
        event.Skip()

    def _drag_ended(self, event):
        self._drag_origin = None
        event.Skip()

    def _drag_motion(self, event):
        origin = self._drag_origin
        if origin is None or not event.Dragging() or not event.LeftIsDown():
            event.Skip()
            return
        position = event.GetPosition()
        if abs(position.x - origin.x) + abs(position.y - origin.y) < 6:
            event.Skip()
            return
        index = self.command_list.HitTest(origin)
        if index < 0 or index >= len(self.visible_commands):
            self._drag_origin = None
            return
        self.command_list.SetSelection(index)
        command = self.visible_commands[index]
        source = self.wx.DropSource(self.command_list)
        source.SetData(self.wx.TextDataObject(str(command["name"])))
        source.DoDragDrop(self.wx.Drag_CopyOnly)
        self._drag_origin = None
