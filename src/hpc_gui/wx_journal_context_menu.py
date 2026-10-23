"""Inject context actions only while the Journal Studio plugin is active."""

from __future__ import annotations

from pathlib import PurePosixPath

from hpc_gui.core.i18n import t


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
JOURNAL_SUFFIXES = frozenset({".jou", ".scm"})


def _active_plugin():
    try:
        from hpc_gui.plugins.loader import load_installed_plugins

        return next((item for item in load_installed_plugins().plugins if item.manifest.id == PLUGIN_ID), None)
    except Exception:
        return None


def append_context_actions(
    wx,
    menu,
    listing,
    *,
    frame,
    session_state,
    path: str,
    is_dir: bool,
    remote: bool,
    run_text_action=None,
    text_action_args=(),
):
    plugin = _active_plugin()
    if plugin is None:
        return False

    def bind(target_menu, label, callback):
        item = target_menu.Append(wx.ID_ANY, label)
        listing.Bind(wx.EVT_MENU, lambda _event: callback(), item)

    from hpc_gui.wx_journal_studio import (
        dispatch_journal_studio_action,
        open_journal_from_context,
    )

    if is_dir:
        new_menu = wx.Menu()
        bind(
            new_menu,
            t("journal_studio.context_new"),
            lambda: dispatch_journal_studio_action(frame, session_state, plugin, "open")
            and session_state["_journal_studio_controller"].new_journal(initial_path=path, remote=remote),
        )
        menu.AppendSubMenu(new_menu, t("dirs.new"))
        return True

    if PurePosixPath(path).suffix.casefold() not in JOURNAL_SUFFIXES:
        return False

    studio_menu = wx.Menu()
    bind(
        studio_menu,
        t("journal_studio.context_open_with"),
        lambda: open_journal_from_context(frame, session_state, plugin, path, remote=remote),
    )
    if callable(run_text_action):
        bind(studio_menu, t("journal_studio.context_open_text"), lambda: run_text_action(*text_action_args))
    bind(
        studio_menu,
        t("journal_studio.validate"),
        lambda: open_journal_from_context(frame, session_state, plugin, path, remote=remote, validate=True),
    )
    bind(
        studio_menu,
        t("journal_studio.context_select_version"),
        lambda: dispatch_journal_studio_action(frame, session_state, plugin, "settings"),
    )
    menu.AppendSubMenu(studio_menu, t("journal_studio.title"))
    return True
