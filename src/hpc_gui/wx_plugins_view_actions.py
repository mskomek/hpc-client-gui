"""Run plugin lifecycle actions from the wx manager without blocking its UI."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.wx_plugins_view_projection import loading_label, status_label_for_source


class PluginLifecycleActions:
    def __init__(self, wx, host, model, state, projection, status, install_button):
        self.wx = wx
        self.host = host
        self.model = model
        self.state = state
        self.projection = projection
        self.status = status
        self.install_button = install_button

    def _selected(self):
        return self.projection.selected_card()

    def _refresh_model_cards(self) -> None:
        refresh = getattr(self.model, "refresh_installed_state", None)
        if callable(refresh):
            refresh()

    def _begin(self) -> int:
        self.state["in_flight"] = True
        self.state["gen"] += 1
        return self.state["gen"]

    def _finish(self, generation: int) -> bool:
        self.state["in_flight"] = False
        return not self.state["closed"] and generation == self.state["gen"]

    def _run_async(self, operation, done) -> None:
        generation = self._begin()

        def worker():
            try:
                operation()
                self.wx.CallAfter(done, generation, None)
            except Exception as exc:
                self.wx.CallAfter(done, generation, exc)

        Thread(target=worker, daemon=True).start()

    def install(self, _event=None) -> None:
        card = self._selected()
        if not card or self.state["closed"] or self.state["in_flight"]:
            return
        if not card.compatible:
            self.wx.MessageBox(
                t("plugins.incompatible"),
                t("plugins.dialog_title"),
                self.wx.OK | self.wx.ICON_ERROR,
                self.host,
            )
            return
        self.install_button.Enable(False)
        self.status.SetLabel(loading_label())
        plugin_id = card.plugin_id

        def operation():
            entry = self.model.registry_entry_for(plugin_id)
            payload = dict(entry) if entry is not None else {
                "id": card.plugin_id,
                "version": card.version,
                "name": card.name,
            }
            if self.model.install is not None:
                outcome = self.model.install_or_update(payload)
            else:
                outcome = self.model.default_installer(payload)
            if outcome is None:
                raise RuntimeError("plugin installer produced no backend action")

        def done(generation, error):
            if not self._finish(generation):
                return
            self.install_button.Enable(True)
            if error is not None:
                self.status.SetLabel(status_label_for_source(self.model.registry_source))
                self.wx.MessageBox(
                    str(error), t("plugins.dialog_title"), self.wx.OK | self.wx.ICON_ERROR, self.host
                )
            else:
                try:
                    from hpc_gui.plugins.loader import load_installed_plugins

                    load_installed_plugins(root=self.model.root, app_version=self.model.app_version)
                except Exception:
                    pass
                self._refresh_model_cards()
                self.status.SetLabel(status_label_for_source(self.model.registry_source))
                name = card.name or card.plugin_id
                success = t("plugins.install_generic")
                try:
                    success = success.format(name=name)
                except Exception:
                    success = f"Installed {name}"
                self.wx.MessageBox(
                    success,
                    t("plugins.dialog_title"),
                    self.wx.OK | self.wx.ICON_INFORMATION,
                    self.host,
                )
                try:
                    from hpc_gui.plugins.storage import read_active_versions

                    read_active_versions(self.model.root)
                except Exception:
                    pass
            self.projection.refresh()

        self._run_async(operation, done)

    def toggle(self, _event=None) -> None:
        card = self._selected()
        if not card or not card.installed or self.state["closed"] or self.state["in_flight"]:
            return
        target_enabled = not card.enabled

        def operation():
            self.model.set_enabled(card.plugin_id, target_enabled)

        self._run_async(operation, self._simple_done)

    def remove(self, _event=None) -> None:
        card = self._selected()
        if not card or not card.installed or self.state["closed"] or self.state["in_flight"]:
            return
        confirm = t("plugins.remove_confirm_text")
        try:
            confirm = confirm.format(name=card.name or card.plugin_id)
        except Exception:
            confirm = f"Remove {card.name or card.plugin_id}?"
        answer = self.wx.MessageBox(
            confirm,
            t("plugins.remove_confirm_title"),
            self.wx.YES_NO | self.wx.ICON_WARNING | self.wx.NO_DEFAULT,
            self.host,
        )
        if answer != self.wx.YES:
            return

        def operation():
            self.model.remove(card.plugin_id)

        self._run_async(operation, self._simple_done)

    def rollback(self, _event=None) -> None:
        card = self._selected()
        if not card or not card.installed or self.state["closed"] or self.state["in_flight"]:
            return
        versions = self.model.rollback_versions(card.plugin_id)
        if not versions:
            return
        chooser = self.wx.SingleChoiceDialog(
            self.host,
            t("plugins.switch_version_label"),
            t("plugins.dialog_title"),
            list(versions),
        )
        try:
            if chooser.ShowModal() != self.wx.ID_OK:
                return
            target = chooser.GetStringSelection()
        finally:
            chooser.Destroy()
        current = card.active_version or card.version
        confirm = t("plugins.version_rollback_confirm_text")
        try:
            confirm = confirm.format(
                name=card.name or card.plugin_id, current=current, version=target
            )
        except Exception:
            confirm = f"Roll {card.name or card.plugin_id} back from {current} to {target}?"
        answer = self.wx.MessageBox(
            confirm,
            t("plugins.version_switch_confirm_title"),
            self.wx.YES_NO | self.wx.ICON_QUESTION | self.wx.NO_DEFAULT,
            self.host,
        )
        if answer != self.wx.YES:
            return

        def operation():
            self.model.rollback(card.plugin_id, target)

        def done(generation, error):
            if not self._finish(generation):
                return
            self.status.SetLabel(status_label_for_source(self.model.registry_source))
            if error is not None:
                self.wx.MessageBox(
                    str(error), t("common.error"), self.wx.OK | self.wx.ICON_ERROR, self.host
                )
            else:
                self._refresh_model_cards()
                success = t("plugins.version_switch_success")
                try:
                    success = success.format(name=card.name or card.plugin_id, version=target)
                except Exception:
                    success = f"{card.name or card.plugin_id} now uses {target}."
                self.wx.MessageBox(
                    success,
                    t("plugins.version_switch_confirm_title"),
                    self.wx.OK | self.wx.ICON_INFORMATION,
                    self.host,
                )
            self.projection.refresh()

        self.status.SetLabel(loading_label())
        self._run_async(operation, done)

    def _simple_done(self, generation, error) -> None:
        if not self._finish(generation):
            return
        if error is not None:
            self.wx.MessageBox(
                str(error), t("common.error"), self.wx.OK | self.wx.ICON_ERROR, self.host
            )
        else:
            self._refresh_model_cards()
        self.projection.refresh()


__all__ = ["PluginLifecycleActions"]
