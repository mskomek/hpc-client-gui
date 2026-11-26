"""Native catalogue button state, search, localized labels and empty updates."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_catalog_discover_filter_and_update_controls(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
import time
from unittest.mock import patch
import wx
from hpc_gui.core.i18n import load_language, t
from hpc_gui.plugins.state import record_installed_version
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view import build_plugins_panel
from test_plugin_manager_ui_catalog_discovery import grouped, entry, FLUENT, TRUBA, FUTURE
from support.test_plugin_installer_shared import full_install_responses, make_registry_entry, make_fetcher

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
changed = []
frame._wx_rebuild_plugins_menu = lambda: changed.append(True)
registry = grouped()
responses, manifest, manifest_bytes = full_install_responses()
real_entry = make_registry_entry(manifest, manifest_bytes)
registry["plugins"][0] = real_entry
registry["plugins"].append(entry(FUTURE, "Future", "9.9.9", "lint-rules", ">=99.0.0"))
record_installed_version(FLUENT, "0.1.0", root=sys.argv[1])
model = WxPluginManagerModel(root=sys.argv[1], app_version="2.0.0", fetcher=make_fetcher(responses))
model.build_cards_from_registry(registry, "network")
panel = build_plugins_panel(frame, model)
frame.Show()
app.ProcessPendingEvents()
c = panel._wx_plugins_controls
listing = c["listing"]
def select(name):
    row = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == name)
    listing.Select(row)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, listing.GetId())
    event.SetIndex(row)
    event.SetEventObject(listing)
    listing.GetEventHandler().ProcessEvent(event)
    return listing.GetItemText(row, 1)
assert listing.GetItemCount() == 3
assert c["status"].GetLabel() == t("plugins.status_online")
assert t("plugins.incompatible") in select("Future")
assert c["install"].GetLabel() == t("plugins.incompatible") and not c["install"].IsEnabled()
assert t("plugins.capability_cluster_profile") in select("TRUBA")
assert c["install"].GetLabel() == t("plugins.install") and c["install"].IsEnabled()
detail = select("Fluent Tools")
assert t("plugins.update_available") in detail and "0.1.0" in detail and "0.2.0" in detail
assert t("plugins.capability_lint_rules") in detail and "lint-rules" not in detail
assert c["install"].GetLabel() == t("plugins.update") and c["install"].IsEnabled()
c["search"].SetValue("0.1.0")
assert listing.GetItemCount() == 1 and listing.GetItemText(0) == "Fluent Tools"
c["search"].SetValue("")
assert listing.GetItemCount() == 3
record_installed_version(FLUENT, "0.2.0", root=sys.argv[1])
model.reload_installed()
c["view"].SetSelection(2)
event = wx.CommandEvent(wx.EVT_CHOICE.typeId, c["view"].GetId())
event.SetEventObject(c["view"])
c["view"].GetEventHandler().ProcessEvent(event)
assert listing.GetItemCount() == 0 and c["empty_note"].IsShown()
assert c["empty_note"].GetLabel() == t("plugins.no_updates")
c["view"].SetSelection(0)
c["view"].GetEventHandler().ProcessEvent(event)
select("TRUBA")
messages = []
def click_install():
    btn = c["install"]
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
    evt.SetEventObject(btn)
    btn.GetEventHandler().ProcessEvent(evt)
    deadline = time.monotonic() + 8
    while panel._wx_plugins_state["in_flight"] and time.monotonic() < deadline:
        wx.Yield()
        time.sleep(.01)
    assert not panel._wx_plugins_state["in_flight"]
with patch.object(wx, "MessageBox", lambda msg, *a: messages.append(msg) or wx.OK):
    broken = {url: (payload + b" " if url.endswith("/manifest.json") else payload)
              for url, payload in responses.items()}
    model.fetcher = make_fetcher(broken)
    click_install()
    assert not next(c for c in model.cards if c.plugin_id == TRUBA).installed
    assert not changed and len(messages) == 1
    assert messages[-1] == t("plugins.verification_failed").format(name="")
    select("TRUBA")
    assert c["install"].IsEnabled() and c["refresh"].IsEnabled()
    model.fetcher = make_fetcher(responses)
    click_install()
    assert next(c for c in model.cards if c.plugin_id == TRUBA).installed
    assert changed == [True] and len(messages) == 2
    assert "TRUBA" in messages[-1] and "1" in messages[-1]
    update_responses, update_manifest, update_bytes = full_install_responses(version="1.1.0")
    registry["plugins"].append(make_registry_entry(update_manifest, update_bytes))
    model.build_cards_from_registry(registry, "network")
    c["view"].GetEventHandler().ProcessEvent(event)
    select("TRUBA")
    assert c["install"].GetLabel() == t("plugins.update") and c["install"].IsEnabled()
    model.fetcher = make_fetcher(update_responses)
    click_install()
    assert next(c for c in model.cards if c.plugin_id == TRUBA).active_version == "1.1.0"
    assert changed == [True, True] and len(messages) == 3
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), str(root / "tests"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_registry_refresh_lifecycle(tmp_path):
    """Exercise real wx events and delayed registry workers without network I/O."""
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
import time
from threading import Event, Thread, get_ident
from types import SimpleNamespace
from unittest.mock import patch

import wx
from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view import show_plugins
from test_plugin_manager_ui_catalog_discovery import grouped

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
model = WxPluginManagerModel(root=sys.argv[1], app_version="2.0.0")
main_thread = get_ident()
calls = []
workers = []
release = Event()
mode = ["network"]

def worker_thread(*args, **kwargs):
    thread = Thread(*args, **kwargs)
    workers.append(thread)
    return thread

def fetch(**kwargs):
    calls.append((mode[0], get_ident()))
    if not release.wait(8):
        raise RuntimeError("test worker release timed out")
    if mode[0] == "offline":
        raise OSError("no network and no cached registry")
    return SimpleNamespace(registry=grouped(), source=mode[0])

def pump_until(predicate):
    deadline = time.monotonic() + 8
    while not predicate() and time.monotonic() < deadline:
        wx.Yield()
        time.sleep(.01)
    assert predicate()

def click(button):
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)

with patch("hpc_gui._wx_plugins_view_builder.Thread", side_effect=worker_thread), patch(
    "hpc_gui.plugins.registry_client.fetch_registry_with_cache", side_effect=fetch
):
    show_plugins(model=model)
    host = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_plugins_state"))
    state = host._wx_plugins_state
    c = host._wx_plugins_controls
    pump_until(lambda: len(calls) == 1)
    assert state["in_flight"] and not c["refresh"].IsEnabled()
    assert c["status"].GetLabel() == t("plugins.status_loading")
    host.Hide()
    host.Show()
    click(c["refresh"])
    click(c["refresh"])
    assert len(workers) == 1
    release.set()
    pump_until(lambda: not state["in_flight"])
    assert c["status"].GetLabel() == t("plugins.status_online")
    assert c["listing"].GetItemCount() == 2 and c["refresh"].IsEnabled()

    for source in ("cache", "offline"):
        mode[0] = source
        click(c["refresh"])
        pump_until(lambda: not state["in_flight"])
        assert model.registry_source == source
        key = "plugins.status_cached" if source == "cache" else "plugins.status_offline"
        assert c["status"].GetLabel() == t(key)
        assert c["refresh"].IsEnabled()
        assert c["listing"].GetItemCount() == (2 if source == "cache" else 0)
    assert c["empty_note"].IsShown()

    mode[0] = "network"
    release.clear()
    click(c["refresh"])
    pump_until(lambda: len(calls) == 4)
    assert state["in_flight"]
    host.Close()
    pump_until(lambda: state["closed"])
    release.set()
    for worker in workers:
        worker.join(8)
        assert not worker.is_alive()
    wx.Yield()
    app.ProcessPendingEvents()
    assert model.registry_source == "offline" and not model.cards
    assert not state["in_flight"]
    assert [source for source, _ in calls] == ["network", "cache", "offline", "network"]
    assert all(thread_id != main_thread for _, thread_id in calls)

assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), str(root / "tests"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
