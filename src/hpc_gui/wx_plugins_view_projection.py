"""Render plugin-manager cards and their lifecycle button states in wx."""

from __future__ import annotations

from hpc_gui.core.i18n import t


VIEW_IDS = ("discover", "installed", "updates")


def view_label(view: str) -> str:
    label = t(f"plugins.tab_{view}")
    return label if label and not label.startswith("[plugins.") else view


def status_label_for_source(source: str) -> str:
    key = {
        "network": "plugins.status_online",
        "cache": "plugins.status_cached",
    }.get(source, "plugins.status_offline")
    label = t(key)
    if label and not label.startswith("[plugins."):
        return label
    return {"network": "Online", "cache": "Cached"}.get(source, "Offline")


def loading_label() -> str:
    label = t("plugins.status_loading")
    return label if label and not label.startswith("[plugins.") else "Loading..."


class PluginListProjection:
    """Keep the wx list and action enablement in sync with manager state."""

    def __init__(
        self,
        model,
        view_choice,
        search,
        list_ctrl,
        state,
        install_button,
        disable_button,
        remove_button,
        rollback_button,
    ):
        self.model = model
        self.view_choice = view_choice
        self.search = search
        self.list_ctrl = list_ctrl
        self.state = state
        self.install_button = install_button
        self.disable_button = disable_button
        self.remove_button = remove_button
        self.rollback_button = rollback_button
        self.visible = []

    def current_view(self) -> str:
        try:
            selected = self.view_choice.GetSelection()
        except Exception:
            selected = 0
        if 0 <= selected < len(VIEW_IDS):
            return VIEW_IDS[selected]
        return self.state["view"]

    def selected_card(self):
        index = self.list_ctrl.GetFirstSelected()
        if index == -1 or index >= len(self.visible):
            return None
        return self.visible[index]

    def refresh(self) -> None:
        selected = self.selected_card()
        selected_id = selected.plugin_id if selected is not None else None
        self.visible[:] = []
        try:
            needle = self.search.GetValue()
        except Exception:
            needle = ""
        view = self.current_view()
        self.state["view"] = view
        try:
            cards = self.model.filtered_cards(view, needle)
        except Exception:
            cards = tuple(self.model.cards)
        self.visible.extend(cards)
        self.list_ctrl.DeleteAllItems()
        for card in self.visible:
            index = self.list_ctrl.InsertItem(
                self.list_ctrl.GetItemCount(), card.name or card.plugin_id
            )
            if card.plugin_id == selected_id:
                self.list_ctrl.Select(index)
            state_bits = ["installed" if card.installed else "available"]
            state_bits.append("enabled" if card.enabled else "disabled")
            if not card.compatible:
                state_bits.append("incompatible")
            if card.update_available:
                state_bits.append("update-available")
            detail = f"{card.version} {' / '.join(state_bits)}"
            if card.active_version and card.active_version != card.version:
                detail += f" (active {card.active_version})"
            self.list_ctrl.SetItem(index, 1, detail)
        self.update_buttons()

    def update_buttons(self) -> None:
        card = self.selected_card()
        if card is None:
            self.install_button.Enable(False)
            self.install_button.SetLabel(t("plugins.install"))
            self.disable_button.Enable(False)
            self.remove_button.Enable(False)
            self.rollback_button.Enable(False)
            return

        if not card.compatible:
            self.install_button.Enable(False)
            self.install_button.SetLabel(t("plugins.incompatible"))
        elif card.update_available:
            self.install_button.Enable(not self.state["in_flight"])
            self.install_button.SetLabel(t("plugins.update"))
        elif card.installed:
            self.install_button.Enable(False)
            self.install_button.SetLabel(t("plugins.installed_badge"))
        else:
            self.install_button.Enable(not self.state["in_flight"])
            self.install_button.SetLabel(t("plugins.install"))

        installed = bool(card.installed)
        can_act = not self.state["in_flight"]
        self.disable_button.Enable(installed and can_act)
        self.disable_button.SetLabel(
            t("plugins.enable") if not card.enabled else t("plugins.disable")
        )
        self.remove_button.Enable(installed and can_act)
        try:
            can_rollback = bool(self.model.rollback_versions(card.plugin_id))
        except Exception:
            can_rollback = False
        self.rollback_button.Enable(installed and can_rollback and can_act)


__all__ = ["PluginListProjection", "VIEW_IDS", "loading_label", "status_label_for_source", "view_label"]
