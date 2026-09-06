"""Additional hardening tests for menu/plugin task."""

from __future__ import annotations

import json
import pathlib


def test_template_api_filtering(tmp_path):
    """load_job_templates() vs filtered by plugin_id."""
    from hpc_gui.plugins.job_templates import load_job_templates

    # Setup two plugins each with a template
    from hpc_gui.plugins.storage import write_active_versions
    import hashlib

    def install_fake(plugin_id, version, template_id):
        pkg = tmp_path / "packages" / plugin_id / version
        pkg.mkdir(parents=True, exist_ok=True)
        # Minimal template index and content
        content = f"#!/bin/bash\n#SBATCH --time=01:00:00\n# {template_id}\n"
        content_path = "template.tpl"
        (pkg / content_path).write_text(content, encoding="utf-8", newline="\n")
        sha = hashlib.sha256(content.encode()).hexdigest()
        index = {
            "schema_version": 1,
            "name": "Test",
            "templates": [
                {
                    "id": template_id,
                    "name": template_id,
                    "scheduler": "slurm",
                    "content_path": content_path,
                    "file_name": f"{template_id}.slurm.tpl",
                    "sha256": sha,
                }
            ],
        }
        (pkg / "index.json").write_text(json.dumps(index), encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "plugin_api": 1,
            "id": plugin_id,
            "name": plugin_id,
            "version": version,
            "publisher": "Test",
            "license": "MIT",
            "description": "desc",
            "requires_app": ">=1.5.8",
            "capabilities": ["job-template"],
            "entrypoints": {"job_templates": ["index.json"]},
            "files": [
                {"path": "index.json", "sha256": hashlib.sha256(json.dumps(index).encode()).hexdigest(), "size": len(json.dumps(index).encode()), "role": "template-index"},
                {"path": content_path, "sha256": sha, "size": len(content.encode()), "role": "template-content"},
            ],
        }
        # Fix file hashes/sizes after writing
        for entry in manifest["files"]:
            p = pkg / entry["path"]
            entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            entry["size"] = p.stat().st_size
        (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    # Install two plugins
    install_fake("org.test.plugina", "1.0.0", "tpl-a")
    install_fake("org.test.pluginb", "1.0.0", "tpl-b")
    write_active_versions({"org.test.plugina": "1.0.0", "org.test.pluginb": "1.0.0"}, root=tmp_path)

    all_templates = load_job_templates(root=tmp_path)
    assert len(all_templates) == 2
    assert {t.id for t in all_templates} == {"tpl-a", "tpl-b"}

    a_only = load_job_templates(root=tmp_path, plugin_id="org.test.plugina")
    assert len(a_only) == 1
    assert a_only[0].id == "tpl-a"
    assert a_only[0].plugin_id == "org.test.plugina"

    b_only = load_job_templates(root=tmp_path, plugin_id="org.test.pluginb")
    assert len(b_only) == 1
    assert b_only[0].id == "tpl-b"

    zero = load_job_templates(root=tmp_path, plugin_id="org.test.nonexistent")
    assert zero == []


def test_plugin_template_action_uses_explicit_api():
    """plugin menu action must call explicit filtered flow with owning plugin ID."""
    from unittest.mock import MagicMock
    from hpc_gui.plugins.models import InstalledPlugin, PluginManifest, PluginFile
    from hpc_gui.services.plugin_menu_actions import dispatch_plugin_menu_action
    from hpc_gui.services.plugin_menu_host import PluginMenuHost

    mf = PluginManifest(
        schema_version=1, plugin_api=1, id="org.test.plugina", name="A", version="1.0.0",
        publisher="x", license="MIT", description="d", requires_app=">=1.5.8",
        capabilities=("job-template",), entrypoints={}, files=(PluginFile(path="a.json", sha256="0"*64, size=1, role="documentation"),)
    )
    plugin = InstalledPlugin(manifest=mf, directory=pathlib.Path("/tmp"))

    # Fake host that records plugin_id
    class FakeHost:
        def __init__(self):
            self.called_with = None
        def run_editor_lint(self, plugin_id: str) -> bool:
            return True
        def open_plugin_templates(self, plugin_id: str) -> bool:
            self.called_with = plugin_id
            return True
        def open_trusted_tool(self, plugin):
            return True

    host = FakeHost()
    # Dispatch via host – should pass owning plugin's ID, not arbitrary
    dispatch_plugin_menu_action("editor.new_from_plugin_templates", plugin, host)
    assert host.called_with == "org.test.plugina"

    # Plugin B
    mf_b = PluginManifest(
        schema_version=1, plugin_api=1, id="org.test.pluginb", name="B", version="1.0.0",
        publisher="x", license="MIT", description="d", requires_app=">=1.5.8",
        capabilities=("job-template",), entrypoints={}, files=(PluginFile(path="a.json", sha256="0"*64, size=1, role="documentation"),)
    )
    plugin_b = InstalledPlugin(manifest=mf_b, directory=pathlib.Path("/tmp"))
    host2 = FakeHost()
    dispatch_plugin_menu_action("editor.new_from_plugin_templates", plugin_b, host2)
    assert host2.called_with == "org.test.pluginb"


def test_host_adapter_import_boundary():
    """Shared dispatcher must not import PySide6."""
    import pathlib
    shared = pathlib.Path("src/hpc_gui/services/plugin_menu_actions.py").read_text(encoding="utf-8")
    assert "PySide6" not in shared
    assert "QDialog" not in shared
    assert "QVBoxLayout" not in shared

    # Qt host must handle trusted tool, wx host must not open Qt dialog
    from hpc_gui.services.plugin_menu_host import PluginMenuHost

    # Check Qt host exists and imports Qt only there
    qt_host_src = pathlib.Path("src/hpc_gui/ui/plugin_menu_qt_host.py").read_text(encoding="utf-8")
    assert "QDialog" in qt_host_src
    assert "load_tool_for_plugin" in qt_host_src

    wx_host_src = pathlib.Path("src/hpc_gui/services/wx_plugin_menu_host.py").read_text(encoding="utf-8")
    assert "QDialog" not in wx_host_src
    assert "PySide6" not in wx_host_src


def test_condition_validation_strict():
    """Unknown key, wrong bool type, unknown capability, wrong capability type must be rejected."""
    from hpc_gui.plugins.ui_contributions import validate_ui_contributions_dict, _parse_plugins_menu

    # Unknown key
    ui_unknown = {"plugins_menu": {"label": "Root", "items": [
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current", "when": {"unknown_condition": True}}
    ]}}
    errors = validate_ui_contributions_dict(ui_unknown)
    assert any("unknown" in e.lower() for e in errors)
    contrib, errs = _parse_plugins_menu(ui_unknown["plugins_menu"], "org.test", "1.0.0")
    # Strict parsing should skip the invalid item
    assert len(contrib.items) == 0

    # Wrong bool type
    ui_wrong_bool = {"plugins_menu": {"label": "Root", "items": [
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current", "when": {"connected": "yes"}}
    ]}}
    errors2 = validate_ui_contributions_dict(ui_wrong_bool)
    assert errors2
    contrib2, _ = _parse_plugins_menu(ui_wrong_bool["plugins_menu"], "org.test", "1.0.0")
    assert len(contrib2.items) == 0

    # Unknown capability
    ui_unknown_cap = {"plugins_menu": {"label": "Root", "items": [
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current", "when": {"capability_available": "totally-unknown"}}
    ]}}
    errors3 = validate_ui_contributions_dict(ui_unknown_cap)
    assert errors3
    contrib3, _ = _parse_plugins_menu(ui_unknown_cap["plugins_menu"], "org.test", "1.0.0")
    assert len(contrib3.items) == 0

    # Wrong capability type
    ui_wrong_cap_type = {"plugins_menu": {"label": "Root", "items": [
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current", "when": {"capability_available": 123}}
    ]}}
    errors4 = validate_ui_contributions_dict(ui_wrong_cap_type)
    assert errors4
    contrib4, _ = _parse_plugins_menu(ui_wrong_cap_type["plugins_menu"], "org.test", "1.0.0")
    assert len(contrib4.items) == 0

    # Valid should pass
    ui_valid = {"plugins_menu": {"label": "Root", "items": [
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current", "when": {"connected": True, "capability_available": "lint-rules"}}
    ]}}
    errors5 = validate_ui_contributions_dict(ui_valid)
    assert errors5 == []
    contrib5, errs5 = _parse_plugins_menu(ui_valid["plugins_menu"], "org.test", "1.0.0")
    assert errs5 == []
    assert len(contrib5.items) == 1


def test_localized_sort():
    """Plugin roots sorted by localized display label, not plugin ID."""
    from hpc_gui.plugins.ui_contributions import _parse_plugins_menu, get_display_label, MenuContext
    from hpc_gui.plugins.models import InstalledPlugin, PluginManifest, PluginFile

    def mk(pid, label, labels=None):
        mf = PluginManifest(
            schema_version=1, plugin_api=1, id=pid, name=label, version="1.0.0",
            publisher="x", license="MIT", description="d", requires_app=">=1.5.8",
            capabilities=("lint-rules",), entrypoints={}, files=(PluginFile(path="a.json", sha256="0"*64, size=1, role="documentation"),),
            ui_contributions={"plugins_menu": {"label": label, "labels": labels or {}, "items": [{"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current"}]}}
        )
        contrib, _ = _parse_plugins_menu(mf.ui_contributions["plugins_menu"], pid, "1.0.0")
        return InstalledPlugin(manifest=mf, directory=pathlib.Path("/tmp"), plugin_menu_contribution=contrib)

    # IDs deliberately not alphabetical: z, a, m but labels Beta, Alpha, Gamma -> expected Alpha, Beta, Gamma
    p_z = mk("org.z", "Beta")
    p_a = mk("org.a", "Alpha")
    p_m = mk("org.m", "Gamma")
    contribs = [p_z.plugin_menu_contribution, p_a.plugin_menu_contribution, p_m.plugin_menu_contribution]
    # Simulate sorting as done in main_window: by localized label
    ctx_en = MenuContext(language="en")
    sorted_contribs = sorted(contribs, key=lambda c: (get_display_label(c.label, c.labels, ctx_en.language).casefold(), c.label.casefold(), c.plugin_id.casefold()))
    assert [c.plugin_id for c in sorted_contribs] == ["org.a", "org.z", "org.m"]
    # Also test Turkish localized labels can change ordering
    p_tr_z = mk("org.z", "Beta", {"tr": "Alfa"})
    p_tr_a = mk("org.a", "Alpha", {"tr": "Beta"})
    p_tr_m = mk("org.m", "Gamma", {"tr": "Gamma"})
    contribs_tr = [p_tr_z.plugin_menu_contribution, p_tr_a.plugin_menu_contribution, p_tr_m.plugin_menu_contribution]
    ctx_tr = MenuContext(language="tr")
    sorted_tr = sorted(contribs_tr, key=lambda c: (get_display_label(c.label, c.labels, ctx_tr.language).casefold(), c.label.casefold(), c.plugin_id.casefold()))
    # In TR, org.z label "Alfa" should come before org.a "Beta"
    assert [c.plugin_id for c in sorted_tr] == ["org.z", "org.a", "org.m"]

    # Ensure internal item order preserved (plugin-defined items order authoritative)
    from hpc_gui.plugins.ui_contributions import _parse_plugins_menu as pm
    ui_ordered = {"label": "Root", "items": [
        {"kind": "action", "id": "b", "label": "B", "action": "editor.lint_current"},
        {"kind": "action", "id": "a", "label": "A", "action": "editor.lint_current"},
    ]}
    contrib_ordered, _ = pm(ui_ordered, "org.test", "1.0.0")
    assert [i.id for i in contrib_ordered.items] == ["b", "a"]


def test_plugin_isolation_real(tmp_path):
    """One valid + one malformed plugin: valid still contributes, bad does not crash."""
    from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions, _parse_plugins_menu
    from hpc_gui.plugins.models import InstalledPlugin, PluginManifest, PluginFile
    import json, hashlib
    from pathlib import Path
    from hpc_gui.plugins.storage import write_active_versions

    # Valid plugin - use job-template with proper files
    valid_ui = {"plugins_menu": {"label": "Valid", "items": [{"kind": "action", "id": "good", "label": "Good", "action": "editor.lint_current"}]}}
    # Create minimal template files for valid plugin
    valid_content = "#!/bin/bash\n#SBATCH --time=01:00:00\n# valid\n"
    valid_sha = hashlib.sha256(valid_content.encode()).hexdigest()
    valid_index = {"schema_version": 1, "name": "Valid", "templates": [{"id": "t1", "name": "T1", "scheduler": "slurm", "content_path": "template.tpl", "file_name": "t1.slurm", "sha256": valid_sha}]}
    valid_mf = {
        "schema_version": 1, "plugin_api": 1, "id": "org.test.valid", "name": "Valid", "version": "1.0.0",
        "publisher": "Test", "license": "MIT", "description": "d", "requires_app": ">=1.5.8",
        "capabilities": ["job-template"], "entrypoints": {"job_templates": ["index.json"]},
        "files": [
            {"path": "index.json", "sha256": hashlib.sha256(json.dumps(valid_index).encode()).hexdigest(), "size": len(json.dumps(valid_index).encode()), "role": "template-index"},
            {"path": "template.tpl", "sha256": valid_sha, "size": len(valid_content.encode()), "role": "template-content"},
        ],
        "ui_contributions": valid_ui,
    }
    pkg_valid = tmp_path / "packages" / "org.test.valid" / "1.0.0"
    pkg_valid.mkdir(parents=True, exist_ok=True)
    (pkg_valid / "template.tpl").write_text(valid_content, encoding="utf-8", newline="\n")
    (pkg_valid / "index.json").write_text(json.dumps(valid_index), encoding="utf-8")
    for entry in valid_mf["files"]:
        p = pkg_valid / entry["path"]
        entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        entry["size"] = p.stat().st_size
    (pkg_valid / "manifest.json").write_text(json.dumps(valid_mf), encoding="utf-8")

    # Malformed plugin: unknown condition (strictly invalid)
    bad_ui = {"plugins_menu": {"label": "Bad", "items": [{"kind": "action", "id": "bad", "label": "Bad", "action": "editor.lint_current", "when": {"unknown_condition": True}}]}}
    bad_content = "#!/bin/bash\n#SBATCH --time=01:00:00\n# bad\n"
    bad_sha = hashlib.sha256(bad_content.encode()).hexdigest()
    bad_index = {"schema_version": 1, "name": "Bad", "templates": [{"id": "t2", "name": "T2", "scheduler": "slurm", "content_path": "template.tpl", "file_name": "t2.slurm", "sha256": bad_sha}]}
    bad_mf = {
        "schema_version": 1, "plugin_api": 1, "id": "org.test.bad", "name": "Bad", "version": "1.0.0",
        "publisher": "Test", "license": "MIT", "description": "d", "requires_app": ">=1.5.8",
        "capabilities": ["job-template"], "entrypoints": {"job_templates": ["index.json"]},
        "files": [
            {"path": "index.json", "sha256": hashlib.sha256(json.dumps(bad_index).encode()).hexdigest(), "size": len(json.dumps(bad_index).encode()), "role": "template-index"},
            {"path": "template.tpl", "sha256": bad_sha, "size": len(bad_content.encode()), "role": "template-content"},
        ],
        "ui_contributions": bad_ui,
    }
    pkg_bad = tmp_path / "packages" / "org.test.bad" / "1.0.0"
    pkg_bad.mkdir(parents=True, exist_ok=True)
    (pkg_bad / "template.tpl").write_text(bad_content, encoding="utf-8", newline="\n")
    (pkg_bad / "index.json").write_text(json.dumps(bad_index), encoding="utf-8")
    for entry in bad_mf["files"]:
        p = pkg_bad / entry["path"]
        entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        entry["size"] = p.stat().st_size
    (pkg_bad / "manifest.json").write_text(json.dumps(bad_mf), encoding="utf-8")

    write_active_versions({"org.test.valid": "1.0.0", "org.test.bad": "1.0.0"}, root=tmp_path)

    from hpc_gui.plugins.loader import load_installed_plugins
    result = load_installed_plugins(root=tmp_path)
    # Both manifests are valid per validator? No, bad_ui has unknown condition which makes validator fail, so bad plugin should be considered corrupt and not loaded?
    # However, our validator now is strict, so bad plugin's manifest will be rejected entirely.
    # For isolation test, we want valid plugin to still load even if bad is malformed.
    # So we expect valid plugin present, bad plugin in problems, but no crash.
    assert any(p.manifest.id == "org.test.valid" for p in result.plugins)
    # And that valid's contribution is still collectible
    from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions
    contribs = collect_plugin_menu_contributions(result.plugins)
    assert len(contribs) == 1
    assert contribs[0].plugin_id == "org.test.valid"


def test_menu_qt_smoke_offscreen():
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        import pytest
        pytest.skip(f"PySide6 unavailable: {e}")
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.main_window import MainWindow
    load_language("en")
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        menubar = w.menuBar()
        titles = [menubar.actions()[i].text() for i in range(len(menubar.actions()))]
        assert "Menu" in titles
        assert "Plugins" in titles
        assert "Help" in titles
        corner = menubar.cornerWidget()
        assert corner is not None
        layout = corner.layout()
        assert layout.count() == 2
        first = layout.itemAt(0).widget()
        second = layout.itemAt(1).widget()
        assert first is w._lang_btn
        assert second is w._version_label
        assert w._version_label.text().startswith("v")
        plugins_texts = [a.text() for a in w._plugins_menu.actions() if not a.isSeparator()]
        assert any("Browse" in t for t in plugins_texts)
        assert any("Manage" in t for t in plugins_texts)
        assert any("Check for Plugin Updates" in t for t in plugins_texts)
        assert any("Request a Plugin" in t for t in plugins_texts)
        assert w._lang_btn is not None
        assert w._version_label is not None
    finally:
        w.deleteLater()


def test_wx_dispatch_uses_host():
    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    assert "WxPluginMenuHost" in src
    assert "dispatch_plugin_menu_action(action, plugin, host)" in src
    # Legacy fallback must not be used in production wx path
    assert "dispatch_plugin_menu_action(action, plugin, editor_widget=editor_widget, host_window=frame)" not in src


def test_wx_submenu_disable_hide():
    src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    # disable must actually disable children, not just pass
    assert "for mi in sub_menu.GetMenuItems():" in src
    assert "mi.Enable(False)" in src
    # hide must continue (skip) – check that hide still does continue
    assert 'if not show and item.unavailable == "hide":' in src


def test_dynamic_separators_qt_and_wx():
    import pathlib
    qt_src = pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    wx_src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    # Both must have has_any logic and setVisible/Enable
    assert "has_any = len(self._plugins_dynamic_actions) > 0" in qt_src
    assert "setVisible(has_any)" in qt_src
    assert "has_any = len(_wx_plugin_dynamic_items) > 0" in wx_src
    assert "sep_plugins_top.Enable" in wx_src


def test_qt_separator_visibility_offscreen():
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        import pytest
        pytest.skip(f"PySide6 unavailable: {e}")
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.main_window import MainWindow
    load_language("en")
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        # No dynamic roots initially (no plugins with contributions) -> exactly one separator
        w._plugin_contributions = []
        w._plugins_dynamic_actions = []
        # Ensure separators exist
        assert w._plugins_dynamic_separator_top is not None
        assert w._plugins_dynamic_before is not None
        # Rebuild with no visible roots
        w._rebuild_plugins_menu_dynamic()
        # After rebuild, top separator should be hidden (only one visible)
        assert w._plugins_dynamic_separator_top.isVisible() is False
        assert w._plugins_dynamic_before.isVisible() is True
        # Now simulate one visible root
        from hpc_gui.plugins.ui_contributions import PluginMenuContribution, PluginMenuAction
        from hpc_gui.plugins.models import PluginManifest, PluginFile
        mf = PluginManifest(schema_version=1, plugin_api=1, id="org.test.fake", name="Fake", version="1.0.0", publisher="x", license="MIT", description="d", requires_app=">=1.5.8", capabilities=("lint-rules",), entrypoints={}, files=(PluginFile(path="a.json", sha256="0"*64, size=1, role="documentation"),))
        contrib = PluginMenuContribution(plugin_id="org.test.fake", plugin_version="1.0.0", label="Fake", labels={}, items=(PluginMenuAction(id="a", label="A", labels={}, action="editor.lint_current", when={}, unavailable="disable"),))
        w._plugin_contributions = [contrib]
        w._rebuild_plugins_menu_dynamic()
        assert w._plugins_dynamic_separator_top.isVisible() is True
        assert w._plugins_dynamic_before.isVisible() is True
        # All hidden by context: create a contribution where item is hidden
        from hpc_gui.plugins.ui_contributions import PluginMenuAction as PMA
        hidden_contrib = PluginMenuContribution(plugin_id="org.test.hidden", plugin_version="1.0.0", label="Hidden", labels={}, items=(PMA(id="a", label="A", labels={}, action="editor.lint_current", when={"connected": True}, unavailable="hide"),))
        w._plugin_contributions = [hidden_contrib]
        # Need to set context to disconnected so item is hidden
        w._session = {"connected": False}
        w._rebuild_plugins_menu_dynamic()
        # No visible dynamic actions, so top separator hidden
        assert len(w._plugins_dynamic_actions) == 0
        assert w._plugins_dynamic_separator_top.isVisible() is False
    finally:
        w.deleteLater()
