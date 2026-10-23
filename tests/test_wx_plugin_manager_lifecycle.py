from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from threading import Event
import time

import pytest

from hpc_gui.core.i18n import t


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"


def _entry(package: Path, version: str) -> dict:
    manifest_bytes = (package / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    return {
        "id": manifest["id"],
        "name": manifest["name"],
        "version": version,
        "plugin_api": manifest["plugin_api"],
        "type": "application-tools",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": manifest["requires_app"],
        "manifest_path": f"plugins/ansys-journal-studio/{version}/manifest.json",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "official": False,
        "capabilities": manifest["capabilities"],
        "keywords": ["ANSYS", "Fluent", "journal"],
    }


def _wait_idle(wx, state: dict) -> None:
    deadline = time.monotonic() + 10.0
    while state["in_flight"] and time.monotonic() < deadline:
        wx.YieldIfNeeded()
        time.sleep(0.01)
    wx.YieldIfNeeded()
    assert state["in_flight"] is False


def _click(wx, button, state: dict) -> None:
    assert button.IsEnabled()
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    button.GetEventHandler().ProcessEvent(event)
    _wait_idle(wx, state)


def _select_first(wx, controls: dict) -> None:
    listing = controls["listing"]
    assert listing.GetItemCount() == 1
    listing.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
    wx.YieldIfNeeded()


def _set_view(wx, controls: dict, index: int) -> None:
    view = controls["view"]
    view.SetSelection(index)
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, view.GetId())
    view.GetEventHandler().ProcessEvent(event)
    wx.YieldIfNeeded()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.integration
def test_wx_plugin_manager_drives_real_install_update_toggle_rollback_remove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package_value = os.environ.get("HPC_JOURNAL_STUDIO_PACKAGE")
    if not package_value:
        pytest.skip("acceptance run must supply HPC_JOURNAL_STUDIO_PACKAGE")
    source = Path(package_value).resolve()
    assert (source / "manifest.json").is_file()

    packages = {}
    for version in ("0.1.0", "0.1.1"):
        target = tmp_path / f"source-{version}"
        shutil.copytree(source, target)
        manifest_path = target / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = version
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        packages[version] = target

    entries = {version: _entry(path, version) for version, path in packages.items()}

    def fetcher(url: str, max_bytes: int) -> bytes:
        for version, package in packages.items():
            marker = f"plugins/ansys-journal-studio/{version}/"
            if marker not in url:
                continue
            relative = url.split(marker, 1)[1].split("?", 1)[0]
            payload = (package / relative).read_bytes()
            if len(payload) > max_bytes:
                raise ValueError("payload exceeds requested limit")
            return payload
        raise AssertionError(f"unexpected package URL: {url}")

    wx = pytest.importorskip("wx")
    from hpc_gui.plugins.state import read_installed_state
    from hpc_gui.plugins.storage import read_active_versions, read_disabled_ids
    from hpc_gui.wx_plugins import WxPluginManagerModel
    from hpc_gui.wx_plugins_view import build_plugins_panel

    answers = []

    class VersionChoice:
        def __init__(self, _parent, _message, _caption, versions):
            self.versions = versions

        def ShowModal(self):
            return wx.ID_OK

        def GetStringSelection(self):
            return "0.1.0" if "0.1.0" in self.versions else self.versions[0]

        def Destroy(self):
            pass

    def message_box(_message, _caption, style, *_args, **_kwargs):
        if style & wx.YES_NO:
            answers.append("confirmed")
            return wx.YES
        return wx.OK

    monkeypatch.setattr(wx, "SingleChoiceDialog", VersionChoice)
    monkeypatch.setattr(wx, "MessageBox", message_box)

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="journal-studio-real-manager-lifecycle")
    model = WxPluginManagerModel(root=tmp_path, fetcher=fetcher, app_version="1.5.9")
    registry_v1 = {"plugins": [entries["0.1.0"]]}
    registry_v2 = {"plugins": [entries["0.1.1"]]}
    model.build_cards_from_registry(registry_v1, "cache", root=tmp_path)
    try:
        panel = build_plugins_panel(
            frame, model=model, root=tmp_path, initial_tab="discover"
        )
        controls = panel._wx_plugins_controls
        state = panel._wx_plugins_state

        _select_first(wx, controls)
        assert controls["listing"].GetItemText(0, 0) == "ANSYS Journal Studio"
        assert controls["listing"].GetColumnWidth(0) > 0
        assert controls["listing"].GetColumnWidth(1) > 0
        _click(wx, controls["install"], state)
        assert read_active_versions(tmp_path)[PLUGIN_ID] == "0.1.0"

        _set_view(wx, controls, 1)
        _select_first(wx, controls)
        _click(wx, controls["disable"], state)
        assert PLUGIN_ID in read_disabled_ids(tmp_path)
        assert "disabled" in controls["listing"].GetItemText(0, 1)
        assert controls["listing"].GetFirstSelected() == 0
        assert controls["disable"].GetLabel() == t("plugins.enable")
        assert controls["disable"].IsEnabled()

        _set_view(wx, controls, 1)
        _select_first(wx, controls)
        _click(wx, controls["disable"], state)
        assert PLUGIN_ID not in read_disabled_ids(tmp_path)
        assert "enabled" in controls["listing"].GetItemText(0, 1)
        assert controls["listing"].GetFirstSelected() == 0
        assert controls["disable"].GetLabel() == t("plugins.disable")
        assert controls["disable"].IsEnabled()

        model.build_cards_from_registry(registry_v2, "cache", root=tmp_path)
        _set_view(wx, controls, 2)
        _select_first(wx, controls)
        _click(wx, controls["install"], state)
        assert read_active_versions(tmp_path)[PLUGIN_ID] == "0.1.1"
        assert {v for v in read_installed_state(tmp_path)[PLUGIN_ID]["versions"]} == {
            "0.1.0",
            "0.1.1",
        }

        _set_view(wx, controls, 1)
        _select_first(wx, controls)
        _click(wx, controls["rollback"], state)
        assert read_active_versions(tmp_path)[PLUGIN_ID] == "0.1.0"
        assert "active 0.1.0" in controls["listing"].GetItemText(0, 1)

        _set_view(wx, controls, 1)
        _select_first(wx, controls)
        _click(wx, controls["remove"], state)
        assert answers == ["confirmed", "confirmed"]
        assert PLUGIN_ID not in read_active_versions(tmp_path)
        assert PLUGIN_ID not in read_installed_state(tmp_path)
        assert controls["listing"].GetItemCount() == 0
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.integration
def test_wx_plugin_manager_shows_installed_rows_before_registry_refresh(
    tmp_path: Path,
) -> None:
    wx = pytest.importorskip("wx")
    from hpc_gui.plugins.storage import write_active_versions
    from hpc_gui.wx_plugins import WxPluginManagerModel
    from hpc_gui.wx_plugins_view import build_plugins_panel

    started = Event()
    release = Event()

    def blocked_fetcher(_url: str, _max_bytes: int) -> bytes:
        started.set()
        release.wait(timeout=5)
        raise OSError("offline registry probe")

    write_active_versions({PLUGIN_ID: "0.1.1"}, root=tmp_path)
    model = WxPluginManagerModel(root=tmp_path, fetcher=blocked_fetcher)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="journal-studio-manager-bootstrap")
    try:
        panel = build_plugins_panel(
            frame, model=model, root=tmp_path, initial_tab="installed"
        )
        controls = panel._wx_plugins_controls
        state = panel._wx_plugins_state
        listing = controls["listing"]
        assert listing.GetItemCount() == 1
        assert listing.GetItemText(0, 0) == PLUGIN_ID
        assert listing.GetColumnWidth(0) > 0
        assert listing.GetColumnWidth(1) > 0

        deadline = time.monotonic() + 5
        while not started.is_set() and time.monotonic() < deadline:
            wx.YieldIfNeeded()
            time.sleep(0.01)
        assert started.is_set(), "initial registry refresh did not start"
        assert state["in_flight"] is True
    finally:
        release.set()
        if "state" in locals() and state["in_flight"]:
            _wait_idle(wx, state)
        frame.Destroy()
        app.ProcessPendingEvents()

    assert model.registry_source == "offline"
    assert model.filtered_cards("installed")[0].plugin_id == PLUGIN_ID
