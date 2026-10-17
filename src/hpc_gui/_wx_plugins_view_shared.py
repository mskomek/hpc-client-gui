"""wx plugins view backed by WxPluginManagerModel (W35 backend-driven GUI)."""
from __future__ import annotations
from threading import Thread
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_host import make_host
from hpc_gui.wx_plugins import WxPluginManagerModel
_VIEW_IDS = ("discover", "installed", "updates")
def _view_label(view: str) -> str:
    mapping = {
        "discover": t("plugins.tab_discover"),
        "installed": t("plugins.tab_installed"),
        "updates": t("plugins.tab_updates"),
    }
    label = mapping.get(view, view)
    return label if label and not label.startswith("[plugins.") else view
def _status_label_for_source(source: str) -> str:
    if source == "network":
        text = t("plugins.status_online")
        return text if text != "[plugins.status_online]" else "Online"
    if source == "cache":
        text = t("plugins.status_cached")
        return text if text != "[plugins.status_cached]" else "Cached"
    text = t("plugins.status_offline")
    return text if text != "[plugins.status_offline]" else "Offline"
def _loading_label() -> str:
    text = t("plugins.status_loading")
    return text if text != "[plugins.status_loading]" else "Loading..."

def _refresh_plugin_labels(
    *,
    state,
    host,
    title,
    search,
    effect_note,
    view_choice,
    btn_refresh,
    btn_disable,
    btn_remove,
    btn_close,
    list_ctrl,
    current_view,
    update_buttons,
) -> None:
    if state["closed"]:
        return
    try:
        host.set_host_title(t("plugins.dialog_title"))
        title.SetLabel(t("plugins.dialog_title"))
        try:
            search.SetHint(t("plugins.search_placeholder"))
        except Exception:
            pass
        effect_note.SetLabel(t("plugins.lifecycle_effect_note"))
        try:
            effect_note.Wrap(760)
        except Exception:
            pass
        current = current_view()
        try:
            view_choice.Set([_view_label(view) for view in _VIEW_IDS])
            view_choice.SetSelection(_VIEW_IDS.index(current))
        except Exception:
            pass
        btn_refresh.SetLabel(t("plugins.refresh"))
        btn_disable.SetLabel(t("plugins.disable"))
        btn_remove.SetLabel(t("plugins.remove"))
        btn_close.SetLabel(t("common.close"))
        list_ctrl.SetColumnWidth(0, 200)
        update_buttons()
    except Exception:
        pass


__all__ = [
    "Thread",
    "WxPluginManagerModel",
    "make_host",
    "subscribe_language_change",
    "t",
    "unsubscribe_language_change",
    "_VIEW_IDS",
    "_view_label",
    "_status_label_for_source",
    "_loading_label",
    "_refresh_plugin_labels",
]
