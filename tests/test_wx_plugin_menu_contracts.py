"""Native wx plugin-menu and separator contract tests."""

from __future__ import annotations

import pathlib
import pytest

wx = pytest.importorskip("wx")

@pytest.mark.audit
@pytest.mark.wx
def test_wx_submenu_disable_hide():
    src = pathlib.Path("src/hpc_gui/wx_shell_plugins.py").read_text(encoding="utf-8")
    # disable must actually disable children, not just pass
    assert "for mi in sub_menu.GetMenuItems():" in src
    assert "mi.Enable(False)" in src
    # hide must continue (skip) – check that hide still does continue
    assert 'if not show and item.unavailable == "hide":' in src

@pytest.mark.audit
@pytest.mark.wx
@pytest.mark.qt
def test_dynamic_separators_qt_and_wx():
    import pathlib
    qt_src = pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    wx_src = pathlib.Path("src/hpc_gui/wx_shell_plugins.py").read_text(encoding="utf-8")
    # Qt must have has_any logic and setVisible
    assert "has_any = len(self._plugins_dynamic_actions) > 0" in qt_src
    assert "setVisible(has_any)" in qt_src
    # Wx must use InsertSeparator/Remove, not Enable(False) for separator visibility
    assert "has_any = len(_wx_plugin_dynamic_items) > 0" in wx_src
    assert "InsertSeparator" in wx_src
    assert "Remove(sep_plugins_top" in wx_src
    assert "sep_plugins_top.Enable(False)" not in wx_src or "sep_plugins_top.Enable(False)" not in wx_src.split("has_any = len(_wx_plugin_dynamic_items)")[1].split("except")[0]

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.semantic
@pytest.mark.regression
def test_wx_separator_lifecycle_offscreen():
    import subprocess
    import sys
    import tempfile
    import textwrap
    import os

    # Run real wx lifecycle in isolated subprocess to avoid Qt/wx App conflicts
    script = textwrap.dedent("""
        import sys
        sys.path.insert(0, "src")
        try:
            import wx
        except ImportError as e:
            print(f"SKIP wx unavailable: {e}")
            sys.exit(0)
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        from hpc_gui.wx_shell import create_shell_frame
        from hpc_gui.plugins.models import PluginManifest, PluginFile, InstalledPlugin

        def _make_fake_plugin(plugin_id, label, item_label, when, unavailable="hide"):
            items = [{"kind": "action", "id": "lint", "label": item_label, "action": "editor.lint_current", "when": when, "unavailable": unavailable}]
            mf = PluginManifest(
                schema_version=1, plugin_api=1, id=plugin_id, name=label, version="1.0.0",
                publisher="x", license="MIT", description="d", requires_app=">=1.5.8",
                capabilities=("lint-rules",), entrypoints={}, files=(PluginFile(path="a.json", sha256="0"*64, size=1, role="documentation"),),
                ui_contributions={"plugins_menu": {"label": label, "items": items}},
            )
            return InstalledPlugin(manifest=mf, directory=Path("/tmp"))

        fake_plugin = _make_fake_plugin("org.test.fake", "FakeRoot", "Lint", {"connected": True})

        def _snapshot(menu):
            out=[]
            for it in menu.GetMenuItems():
                if it.IsSeparator():
                    out.append(("separator", None))
                elif it.GetSubMenu() is not None:
                    out.append(("submenu", it.GetItemLabelText()))
                else:
                    out.append(("action", it.GetItemLabelText()))
            return out
        def _count_seps(menu):
            return sum(1 for it in menu.GetMenuItems() if it.IsSeparator())
        def _count_submenus(menu):
            return sum(1 for it in menu.GetMenuItems() if it.GetSubMenu() is not None)

        session_state = {"session": None, "generation": 0}
        frame, _lifecycle, _ss = create_shell_frame(session_state=session_state)
        plugins_menu = frame._wx_shell_plugins_menu
        try:
            # 1. 0 visible roots
            with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=[])):
                session_state["session"] = None
                frame._wx_rebuild_plugins_menu()
                snap1 = _snapshot(plugins_menu)
                assert _count_seps(plugins_menu) == 1, f"step1 expected 1 separator, got {snap1}"
                assert _count_submenus(plugins_menu) == 0, f"step1 expected 0 submenus, got {snap1}"
                assert len(plugins_menu.GetMenuItems()) == 5
                assert "request" in plugins_menu.GetMenuItems()[-1].GetItemLabelText().lower()
                print("STEP1 OK", snap1)

            # 2. 1 visible root
            with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=[fake_plugin])):
                session_state["session"] = {"connected": True}
                frame._wx_rebuild_plugins_menu()
                snap2 = _snapshot(plugins_menu)
                assert _count_seps(plugins_menu) == 2, f"step2 expected 2 separators, got {snap2}"
                assert _count_submenus(plugins_menu) == 1, f"step2 expected 1 submenu, got {snap2}"
                items = list(plugins_menu.GetMenuItems())
                assert len(items) == 7, f"step2 expected 7 items, got {snap2}"
                assert items[3].IsSeparator(), f"step2 idx3 sep {snap2}"
                assert items[4].GetSubMenu() is not None, f"step2 idx4 submenu {snap2}"
                assert items[4].GetItemLabelText() == "FakeRoot", f"step2 label {snap2}"
                assert items[5].IsSeparator(), f"step2 idx5 sep {snap2}"
                assert "request" in items[6].GetItemLabelText().lower(), f"step2 request {snap2}"
                assert snap2 == [("action", items[0].GetItemLabelText()), ("action", items[1].GetItemLabelText()), ("action", items[2].GetItemLabelText()), ("separator", None), ("submenu", "FakeRoot"), ("separator", None), ("action", items[6].GetItemLabelText())]
                print("STEP2 OK", snap2)

            # 3. rebuild again unchanged
            with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=[fake_plugin])):
                session_state["session"] = {"connected": True}
                frame._wx_rebuild_plugins_menu()
                snap3 = _snapshot(plugins_menu)
                assert _count_seps(plugins_menu) == 2, f"step3 2 seps {snap3}"
                assert _count_submenus(plugins_menu) == 1, f"step3 1 submenu {snap3}"
                assert snap3 == snap2, f"step3 != step2 {snap3} vs {snap2}"
                assert len(plugins_menu.GetMenuItems()) == 7
                print("STEP3 OK", snap3)

            # 4. all hidden
            print("STEP4 BEGIN", flush=True)
            with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=[fake_plugin])):
                session_state["session"] = {"connected": False}
                print("STEP4 CALL", flush=True)
                frame._wx_rebuild_plugins_menu()
                print("STEP4 RETURN", flush=True)
                snap4 = _snapshot(plugins_menu)
                assert _count_seps(plugins_menu) == 1, f"step4 1 sep {snap4}"
                assert _count_submenus(plugins_menu) == 0, f"step4 0 submenu {snap4}"
                assert len(plugins_menu.GetMenuItems()) == 5
                assert snap4[3] == ("separator", None)
                assert "request" in snap4[4][1].lower()
                print("STEP4 OK", snap4)

            # 5. visible again
            with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=[fake_plugin])):
                session_state["session"] = {"connected": True}
                frame._wx_rebuild_plugins_menu()
                snap5 = _snapshot(plugins_menu)
                assert _count_seps(plugins_menu) == 2, f"step5 2 seps {snap5}"
                assert _count_submenus(plugins_menu) == 1, f"step5 1 submenu {snap5}"
                assert snap5 == snap2, f"step5 != step2 {snap5} vs {snap2}"
                items5 = list(plugins_menu.GetMenuItems())
                assert items5[4].GetSubMenu() is not None and items5[4].GetItemLabelText() == "FakeRoot"
                print("STEP5 OK", snap5)

            # 6. Unicode roots, hide/disable conditions, order and repeated lifecycle.
            hide_plugin = _make_fake_plugin(
                "org.test.hide", "Çalışma Araçları", "İş_日本語", {"connected": True}, "hide"
            )
            disable_plugin = _make_fake_plugin(
                "org.test.disable", "日本語ツール", "Çalışma araçları", {"connected": True}, "disable"
            )
            visible_plugins = [hide_plugin, disable_plugin]
            expected_roots = sorted(
                [hide_plugin.manifest.name, disable_plugin.manifest.name],
                key=str.casefold,
            )
            for cycle in range(25):
                session_state["session"] = {"connected": True}
                with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=visible_plugins)):
                    frame._wx_rebuild_plugins_menu()
                menu_items = list(plugins_menu.GetMenuItems())
                roots = [item for item in menu_items if item.GetSubMenu() is not None]
                root_labels = [item.GetItemLabelText() for item in roots]
                assert root_labels == expected_roots, f"cycle {cycle}: roots {root_labels}"
                assert len(root_labels) == len(set(root_labels))
                assert _count_seps(plugins_menu) == 2
                actions = {
                    item.GetItemLabelText(): list(item.GetSubMenu().GetMenuItems())
                    for item in roots
                }
                assert actions["Çalışma Araçları"][0].GetItemLabelText() == "İş_日本語"
                assert actions["日本語ツール"][0].GetItemLabelText() == "Çalışma araçları"
                assert all(items[0].IsEnabled() for items in actions.values())

                session_state["session"] = {"connected": False}
                with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=SimpleNamespace(plugins=visible_plugins)):
                    frame._wx_rebuild_plugins_menu()
                menu_items = list(plugins_menu.GetMenuItems())
                roots = [item for item in menu_items if item.GetSubMenu() is not None]
                assert [item.GetItemLabelText() for item in roots] == ["日本語ツール"]
                assert _count_seps(plugins_menu) == 2
                disabled_action = roots[0].GetSubMenu().GetMenuItems()[0]
                assert disabled_action.GetItemLabelText() == "Çalışma araçları"
                assert not disabled_action.IsEnabled()
            print("STEP6 OK 25 cycles; Unicode labels and hide/disable conditions")

            print("ALL_STEPS_PASSED", flush=True)
        finally:
            import wx
            app = wx.GetApp()
            frame.Close()
            app.ProcessPendingEvents()
            wx.Yield()
            app.ProcessPendingEvents()
            assert not wx.GetTopLevelWindows(), "wx top-level windows remain after frame teardown"
            app.Destroy()
            print("TEARDOWN_OK", flush=True)
            import os, sys
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)
        sys.exit(0)
    """)

    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "wx_lifecycle_check.py"
        p.write_text(script, encoding="utf-8")
        # Use minimal env to avoid Qt/pytest pollution
        keep = ["PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "TEMP", "TMP", "PYTHONPATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"]
        env = {k: os.environ[k] for k in keep if k in os.environ}
        # Ensure src is found via cwd, not PYTHONPATH, but keep PYTHONPATH if set
        env["PYTHONPATH"] = env.get("PYTHONPATH", "")
        try:
            result = subprocess.run(
                [sys.executable, "-u", str(p)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(pathlib.Path.cwd()),
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            pytest.fail(f"wx lifecycle subprocess timed out; stdout={stdout!r}; stderr={stderr!r}")
        out = result.stdout + result.stderr
        if "SKIP wx unavailable:" in out:
            pytest.skip("wxPython is not installed in the child process")
        # Duplicate handler warnings do not substitute for completed lifecycle assertions.
        if "ALL_STEPS_PASSED" in out:
            assert result.returncode == 0
            assert "STEP1 OK" in out and "STEP2 OK" in out and "STEP3 OK" in out and "STEP4 OK" in out and "STEP5 OK" in out
            assert "STEP6 OK 25 cycles" in out and "TEARDOWN_OK" in out
            assert "UnregisterClass" not in out and "open windows" not in out
            return
        if result.returncode != 0:
            pytest.fail(f"wx lifecycle subprocess failed (code {result.returncode}):\\n{out}")
        assert "ALL_STEPS_PASSED" in result.stdout, f"wx lifecycle did not complete: {out}"
