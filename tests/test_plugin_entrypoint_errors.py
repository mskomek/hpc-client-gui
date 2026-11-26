"""Plugin Manager shell dispatch and diagnostic contracts without GUI toolkit startup."""
import logging
import re
import sys
from types import SimpleNamespace

import pytest

from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_shell_dispatch import _dispatch


@pytest.mark.unit
@pytest.mark.parametrize(("command", "tab"), [
    ("PLUGIN-BROWSE", "discover"),
    ("PLUGIN-MANAGE", "installed"),
    ("PLUGIN-UPDATES", "updates"),
])
def test_plugin_dispatch_selects_initial_tab(monkeypatch, command, tab):
    calls = []
    parent = object()
    monkeypatch.setattr("hpc_gui.wx_plugins_view.show_plugins", lambda **kwargs: calls.append(kwargs))
    _dispatch(command, parent)
    assert calls == [{"parent": parent, "initial_tab": tab}]


@pytest.mark.unit
def test_open_plugins_surfaces_failure_and_logs_diagnostic(monkeypatch, caplog):
    load_language("en")
    messages = []
    parent = object()
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(
        OK=1, ICON_ERROR=2, MessageBox=lambda *args: messages.append(args),
    ))
    def boom(**kwargs):
        raise RuntimeError("plugin manager exploded")

    monkeypatch.setattr("hpc_gui.wx_plugins_view.show_plugins", boom)
    with caplog.at_level(logging.ERROR, logger="hpc_gui.wx_shell"):
        _dispatch("PLUGIN-BROWSE", parent)

    assert len(messages) == 1
    message, title, _, owner = messages[0]
    assert t("plugins.open_failed") in message
    assert title == t("common.error") and owner is parent
    match = re.search(r"PLUGIN-[0-9A-F]{6}", message)
    assert match
    assert any(match.group(0) in record.getMessage() and record.exc_info
               and "plugin manager exploded" in str(record.exc_info[1])
               for record in caplog.records)


@pytest.mark.unit
def test_plugin_request_browser_failure_is_reported(monkeypatch):
    from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
    opened, errors = [], []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or False)
    monkeypatch.setattr("hpc_gui.wx_shell_dispatch.report_wx_action_error",
                        lambda *args, **kwargs: errors.append(kwargs))
    _dispatch("PLUGIN-REQUEST")
    assert opened == [PLUGIN_REQUEST_URL]
    assert len(errors) == 1
    assert errors[0]["message_key"] == "plugins.request_plugin_failed"
