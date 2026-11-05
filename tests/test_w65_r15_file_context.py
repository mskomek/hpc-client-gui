"""W65 r15: trusted OpenFOAM actions in local and remote wx File menus."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from test_w65_r14_openfoam_dispatch import (
    ENGINE_REL,
    ENGINE_SRC,
    STUDIO_ENGINE_REL,
    STUDIO_ENGINE_SRC,
    TEMPLATES_REL,
    TEMPLATES_SRC,
    _installed,
    _linter_manifest,
    _pins_for,
    _studio_manifest,
    _wx_frame_context,
    _write_package,
)


def test_plugin_discovery_ignores_malformed_loader_entries(monkeypatch):
    import hpc_gui.plugins.loader as loader
    from hpc_gui.services.file_context_actions import installed_openfoam_file_context_plugins

    valid = SimpleNamespace(manifest=SimpleNamespace(id="org.hpcclient.openfoamlint"))
    monkeypatch.setattr(
        loader,
        "load_installed_plugins",
        lambda: SimpleNamespace(plugins=(None, SimpleNamespace(manifest=None), valid)),
    )
    assert installed_openfoam_file_context_plugins() == (valid,)


def test_local_file_context_menu_dispatches_selected_dictionary_to_pinned_linter(
    tmp_path: Path, monkeypatch,
):
    import hpc_gui.plugins.loader as loader
    import hpc_gui.plugins.trusted_api3 as t3
    from hpc_gui.plugins.loader import PluginLoadResult
    from hpc_gui.services.file_context_actions import context_selection, wx_file_context_host
    from hpc_gui.wx_local_files_interactions import (
        _openfoam_plugins,
        local_menu_actions,
        run_openfoam_file_context_action,
    )

    manifest, _ = _linter_manifest()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, json.dumps(manifest).encode()))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    monkeypatch.setattr(loader, "load_installed_plugins", lambda: PluginLoadResult([installed]))
    dictionary = tmp_path / "case" / "system" / "controlDict"
    dictionary.parent.mkdir(parents=True)
    dictionary.write_text("application simpleFoam;\n", encoding="utf-8")
    selection = context_selection(str(dictionary), False, (str(dictionary),), (False,))
    editor, frames = _wx_frame_context(monkeypatch)
    view = SimpleNamespace(host=editor, _wx_openfoam_session_state={})
    assert _openfoam_plugins(view) == (installed,)
    wx_host, session_state = wx_file_context_host(view, selection)

    assert "of.validate" in local_menu_actions(
        selection, [installed], host=wx_host, session_state=session_state
    )
    assert run_openfoam_file_context_action(
        "of.validate", selection, [installed], host=wx_host,
        session_state=session_state,
    ) == (True, "")
    assert len(frames) == 1 and frames[0].visible


def test_remote_file_context_requires_live_session_and_dispatches_pinned_linter(
    tmp_path: Path, monkeypatch,
):
    import hpc_gui.plugins.loader as loader
    import hpc_gui.plugins.trusted_api3 as t3
    from hpc_gui.plugins.loader import PluginLoadResult
    from hpc_gui.services.file_context_actions import context_selection, wx_file_context_host
    from hpc_gui.wx_remote_files_interactions import (
        _openfoam_plugins,
        remote_menu_actions,
        run_openfoam_file_context_action,
    )

    manifest, _ = _linter_manifest()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, json.dumps(manifest).encode()))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    monkeypatch.setattr(loader, "load_installed_plugins", lambda: PluginLoadResult([installed]))
    path = "/case/system/controlDict"
    selection = context_selection(path, False, (path,), (False,))
    editor, frames = _wx_frame_context(monkeypatch)
    disconnected = {"session": {"connection_id": "test-session"}}
    editor._wx_openfoam_session_state = disconnected
    view = SimpleNamespace(host=editor)
    assert _openfoam_plugins(view) == (installed,)
    wx_host, session_state = wx_file_context_host(view, selection, remote=True)
    assert "of.validate" not in remote_menu_actions(
        selection, [installed], host=wx_host, session_state=session_state
    )

    connected = {"session": {"connection_id": "test-session", "files": object()}}
    editor._wx_openfoam_session_state = connected
    wx_host, session_state = wx_file_context_host(view, selection, remote=True)
    assert "of.validate" in remote_menu_actions(
        selection, [installed], host=wx_host, session_state=session_state
    )
    assert run_openfoam_file_context_action(
        "of.validate", selection, [installed], host=wx_host,
        session_state=session_state,
    ) == (True, "")
    assert len(frames) == 1 and frames[0].visible


def test_studio_file_context_routes_to_real_wx_action(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3
    from hpc_gui.services.file_context_actions import context_selection, wx_file_context_host
    from hpc_gui.wx_local_files_interactions import (
        local_menu_actions,
        run_openfoam_file_context_action,
    )

    manifest = _studio_manifest()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, json.dumps(manifest).encode()))
    package = _write_package(tmp_path, manifest, {
        STUDIO_ENGINE_REL: STUDIO_ENGINE_SRC, TEMPLATES_REL: TEMPLATES_SRC,
    })
    installed = _installed(manifest, package)
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    selection = context_selection(str(case), True, (str(case),), (True,))
    editor, frames = _wx_frame_context(monkeypatch)
    view = SimpleNamespace(host=editor, _wx_openfoam_session_state={})
    wx_host, session_state = wx_file_context_host(view, selection)
    actions = local_menu_actions(selection, [installed], host=wx_host, session_state=session_state)
    assert ("of.newCase", "of.openStudio", "of.createJob") == tuple(
        action for action in actions if action.startswith("of.")
    )
    assert run_openfoam_file_context_action(
        "of.openStudio", selection, [installed], host=wx_host,
        session_state=session_state,
    ) == (True, "")
    page = frames[0].sizer.children[0][0]
    assert frames[0].visible and page.action is None
    assert page.initial_path == str(case) and page.remote is False


def test_remote_target_validation_rejects_malformed_or_unbounded_paths():
    from hpc_gui.services.openfoam_file_dispatch import supports_remote_target

    assert supports_remote_target("/case/system/controlDict", is_directory=False)
    assert supports_remote_target("/case", is_directory=True)
    for path in (
        "/", "//case/system/controlDict", "/case/../controlDict",
        "/case//controlDict", "/case/./controlDict", r"\case\system\controlDict",
        "/case/\x00/controlDict", "/case/\n/controlDict", "/" + "a" * 4096,
    ):
        assert not supports_remote_target(path, is_directory=True), path


def test_remote_studio_context_actions_share_canonical_path_validation(monkeypatch):
    import hpc_gui.services.file_context_actions as actions
    import hpc_gui.services.plugin_menu_actions as menu_actions

    plugin = SimpleNamespace(
        manifest=SimpleNamespace(id="org.hpcclient.openfoamcasestudio")
    )
    host = SimpleNamespace()
    session_state = {"session": {"files": object()}}
    monkeypatch.setattr(menu_actions, "can_execute_action", lambda *_args, **_kwargs: (True, ""))

    for path in ("//server/case", "/case/../tmp", "/case//tmp", "/case/./tmp", r"\case"):
        selection = actions.context_selection(path, True, (path,), (True,))
        assert actions.openfoam_file_context_actions(
            selection, plugin, remote=True, host=host, session_state=session_state
        ) == (), path

    selection = actions.context_selection("/case/system", True, ("/case/system",), (True,))
    assert actions.openfoam_file_context_actions(
        selection, plugin, remote=True, host=host, session_state=session_state
    ) == ("of.newCase", "of.openStudio", "of.createJob")


def test_local_right_click_binds_and_runs_the_verified_linter_action(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.loader as loader
    import hpc_gui.plugins.trusted_api3 as t3
    import hpc_gui.wx_local_files_interactions as local_view
    from hpc_gui.plugins.loader import PluginLoadResult
    from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS

    manifest, _ = _linter_manifest()
    monkeypatch.setattr(
        t3, "APPROVED_API3_PINS",
        _pins_for(manifest, json.dumps(manifest).encode()),
    )
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    monkeypatch.setattr(loader, "load_installed_plugins", lambda: PluginLoadResult([installed]))
    monkeypatch.setattr(local_view, "t", lambda key: key)
    dictionary = tmp_path / "case" / "system" / "controlDict"
    dictionary.parent.mkdir(parents=True)
    dictionary.write_text("application simpleFoam;\n", encoding="utf-8")
    editor, frames = _wx_frame_context(monkeypatch)
    editor._wx_openfoam_session_state = {}
    wx = sys.modules["wx"]

    class Menu:
        def __init__(self):
            self.items = []

        def Append(self, _identifier, label):
            item = SimpleNamespace(label=label)
            self.items.append(item)
            return item

        def Destroy(self):
            self.destroyed = True

    wx.Menu = Menu
    wx.ID_ANY = 1
    wx.EVT_MENU = object()
    wx.DefaultPosition = object()
    wx.OK = 1
    wx.ICON_WARNING = 2
    wx.MessageBox = lambda *_args, **_kwargs: None

    class Listing:
        def __init__(self):
            self.callbacks = {}
            self.menu = None

        def IsSelected(self, _index):
            return True

        def HitTest(self, _position):
            return 0, 0

        def ScreenToClient(self, position):
            return position

        def GetItemCount(self):
            return 1

        def Select(self, *_args):
            pass

        def Bind(self, _event_type, callback, item):
            self.callbacks[item.label] = callback

        def PopupMenu(self, menu):
            self.menu = menu
            self.callbacks["openfoam.validate"](None)

    listing = Listing()
    entry = SimpleNamespace(path=dictionary, is_dir=False)
    tab = {"path": dictionary.parent, "entries": [entry], "listing": listing}
    view = SimpleNamespace(
        active_tab_state=lambda: tab,
        create_tab=lambda *_args: None,
        host=editor,
        labels=FILE_CONTEXT_LABEL_KEYS,
        model=SimpleNamespace(),
        navigate=lambda *_args: None,
        notebook=SimpleNamespace(),
        open_editor=None,
        path_ctrl=SimpleNamespace(),
        refresh=lambda: None,
        run_action=lambda *_args: None,
        state={},
        tab_label=str,
        upload=True,
        wx=wx,
    )
    local_view.install_interactions(view)
    view.context_menu(SimpleNamespace(GetPosition=lambda: SimpleNamespace(x=4, y=4)))

    assert any(item.label == "openfoam.validate" for item in listing.menu.items)
    assert len(frames) == 1 and frames[0].visible
