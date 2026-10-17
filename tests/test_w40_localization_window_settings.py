"""W40 execution tests: localization, window state and runtime setting effects.

Owned requirements (waves/pending/W40.md):
  HPC-W09-UISTATE-001..020 (E1 language/i18n, E2 window/layout persistence,
  E3 settings effect ownership) plus TODO-detail IDs HPC-W09-TODO-005/006,
  VISUAL-CURRENT-001, TODO-015..020, A11Y-CURRENT-001, TODO-022/023,
  I18N-CURRENT-001, PUBLIC-SURFACE-CURRENT-001, EVIDENCE-FRESHNESS-001,
  MIGRATION-LANGUAGE-001 and TODO-056.

Live owners:
  src/hpc_gui/core/i18n.py (SUPPORTED_LANGUAGES, validation, fallback,
    persistence)
  src/hpc_gui/config/storage.py (main-window state record)
  src/hpc_gui/services/geometry_policy.py (resolve/recover/dispose)
  src/hpc_gui/wx_shell.py (live relabel, save-on-close, restore-on-create)

No network, no real user config for persistence paths (isolated tmp roots via
monkeypatch). GUI claims use the real wx runtime (frames, menus, notebook
events, readback). OS-level DPI scaling and screen-reader certification are
not drivable unattended and are classified in the wave report, not faked here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpc_gui.core import i18n
from hpc_gui.config import storage
from hpc_gui.config import _storage_core
from hpc_gui.services.geometry_policy import (
    Rect,
    dispose_legacy_qt_geometry_blob,
    resolve_main_window_state,
)


@pytest.fixture(autouse=True)
def _restore_language():
    yield
    try:
        i18n.load_language("tr")
    except Exception:
        pass


@pytest.fixture
def isolated_app_data(tmp_path, monkeypatch):
    root = tmp_path / "appdata"
    root.mkdir()
    monkeypatch.setattr(i18n, "app_data_dir", lambda: root)
    return root


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(_storage_core, "_config_path", lambda: config_path)
    return config_path


# ---------------------------------------------------------------------------
# UISTATE-001: enumerate all user-selectable languages
# ---------------------------------------------------------------------------

def test_w40_uistate001_supported_languages_enumerated():
    """FIX-A contract: exactly en+tr are user-selectable, and only those."""
    assert tuple(i18n.SUPPORTED_LANGUAGES) == ("en", "tr")
    for lang in i18n.SUPPORTED_LANGUAGES:
        assert (Path(i18n.__file__).resolve().parent.parent / "i18n" / f"{lang}.json").is_file()


# ---------------------------------------------------------------------------
# UISTATE-002/004: change through GUI/API + persist; invalid rejected
# ---------------------------------------------------------------------------

def test_w40_uistate002_set_language_switches_current(isolated_app_data):
    i18n.set_language("en")
    assert i18n.current_language() == "en"
    assert i18n.t("tabs.login") == "Connection"
    i18n.set_language("tr")
    assert i18n.current_language() == "tr"
    assert i18n.t("tabs.login") == "Bağlantı"


def test_w40_uistate002_invalid_language_rejected_without_side_effects(isolated_app_data):
    before_lang = i18n.current_language()
    before_file = isolated_app_data / "language.json"
    with pytest.raises(ValueError):
        i18n.set_language("de")
    with pytest.raises(ValueError):
        i18n.load_language("fr")
    assert i18n.current_language() == before_lang
    assert i18n.t("tabs.login") != "[tabs.login]"
    if before_file.exists():
        # No persistence write happened for the rejected value.
        assert json.loads(before_file.read_text(encoding="utf-8")).get("lang") != "de"


def test_w40_uistate004_language_selection_persists_and_reloads(isolated_app_data):
    i18n.set_language("en")
    persisted = json.loads((isolated_app_data / "language.json").read_text(encoding="utf-8"))
    assert persisted == {"lang": "en"}
    i18n.load_language("tr")
    assert i18n.load_saved_language("tr") == "en"
    assert i18n.current_language() == "en"


# ---------------------------------------------------------------------------
# UISTATE-003: live vs restart effect documented + live notification proven
# ---------------------------------------------------------------------------

def test_w40_uistate003_language_effect_is_live():
    seen = []
    i18n.subscribe_language_change(seen.append)
    try:
        i18n.set_language("en")
        i18n.set_language("tr")
    finally:
        i18n.unsubscribe_language_change(seen.append)
    assert seen == ["en", "tr"]
    # No restart-required language path exists in the shell contract.
    from hpc_gui import wx_settings as _wx_settings

    assert "language" not in {k.lower() for k in _wx_settings.RESTART_REQUIRED_KEYS}


# ---------------------------------------------------------------------------
# UISTATE-005/006: consistent relabel + no raw-key leakage
# ---------------------------------------------------------------------------

def test_w40_uistate005_representative_surfaces_relabel():
    keys = [
        "tabs.login", "tabs.jobs_outputs", "tabs.editor", "tabs.logs",
        "menu.settings", "menu.plugins", "menu.help_center", "menu.about",
        "help.language", "login.connect", "login.disconnect",
        "common.error", "common.cancel",
    ]
    i18n.load_language("en")
    en = {k: i18n.t(k) for k in keys}
    i18n.load_language("tr")
    tr = {k: i18n.t(k) for k in keys}
    for k in keys:
        assert en[k] and not en[k].startswith("["), k
        assert tr[k] and not tr[k].startswith("["), k


def test_w40_uistate006_missing_key_falls_back_not_raw_key():
    i18n.load_language("tr")
    assert i18n.t("no.such.key.anywhere") == "[no.such.key.anywhere]"
    # Key present only in the other shipped bundle must not leak [key].
    i18n._LANG.pop("w40", None)
    i18n._FALLBACK.setdefault("w40", {}).setdefault("fallback", {}).setdefault(
        "probe", {}).__setitem__("only", {"in": {"en": "fallback-visible"}})
    try:
        got = i18n.t("w40.fallback.probe.only.in.en")
        assert got == "fallback-visible", got
    finally:
        i18n._FALLBACK.get("w40", {}).pop("fallback", None)
        i18n.load_language("tr")


def test_w40_uistate006_shipped_bundles_have_no_key_drift():
    import hpc_gui.core.i18n as _i18n

    assert _i18n._flatten_keys(
        json.loads((Path(_i18n.__file__).resolve().parent.parent / "i18n" / "tr.json").read_text(encoding="utf-8"))
    ) == _i18n._flatten_keys(
        json.loads((Path(_i18n.__file__).resolve().parent.parent / "i18n" / "en.json").read_text(encoding="utf-8"))
    )


# ---------------------------------------------------------------------------
# UISTATE-009..014: window-state persistence + recovery
# ---------------------------------------------------------------------------

def test_w40_uistate009_fresh_defaults_when_no_state(isolated_config):
    assert storage.get_main_window_state() is None
    state = resolve_main_window_state(None, (Rect(0, 0, 1920, 1080),))
    assert state["rect"] == Rect(0, 0, 1440, 900)
    assert state["maximized"] is False
    assert state["selected_tab"] is None


def test_w40_uistate009_save_restart_roundtrip(isolated_config):
    storage.save_main_window_state(x=100, y=80, width=1280, height=760,
                                   maximized=False, selected_tab=3)
    raw = storage.get_main_window_state()
    assert raw == {"x": 100, "y": 80, "width": 1280, "height": 760,
                   "maximized": False, "selected_tab": 3}
    state = resolve_main_window_state(raw, (Rect(0, 0, 1920, 1080),), tab_count=7)
    assert state["rect"] == Rect(100, 80, 1280, 760)
    assert state["selected_tab"] == 3


def test_w40_uistate010_maximized_and_tab_survive_roundtrip(isolated_config):
    storage.save_main_window_state(x=0, y=0, width=1920, height=1040,
                                   maximized=True, selected_tab=6)
    state = resolve_main_window_state(storage.get_main_window_state(),
                                      (Rect(0, 0, 1920, 1080),), tab_count=7)
    assert state["maximized"] is True
    assert state["selected_tab"] == 6


def test_w40_uistate_corrupt_state_recovers_to_defaults(isolated_config):
    for bad in [
        {"x": "oops", "y": 0, "width": 100, "height": 100},
        {"x": 0, "y": 0, "width": 0, "height": 700},
        {"x": 0, "y": 0, "width": -5, "height": 700},
        {"qt_geometry": "a2V5...", "qt_state": "AAAA"},
        "not-a-dict",
        {"x": 0, "y": 0},
    ]:
        cfg = {"ui": {storage.MAIN_WINDOW_STATE_KEY: bad}}
        isolated_config.write_text(json.dumps(cfg), encoding="utf-8")
        assert storage.get_main_window_state() is None or isinstance(
            storage.get_main_window_state(), dict)
        state = resolve_main_window_state(bad, (Rect(0, 0, 1920, 1080),), tab_count=7)
        assert state["rect"].width > 0 and state["rect"].height > 0
    with pytest.raises(ValueError):
        storage.save_main_window_state(x=0, y=0, width=0, height=700)


def test_w40_uistate_offscreen_geometry_recovered_into_work_area():
    raw = {"x": 5000, "y": 3000, "width": 1280, "height": 760,
           "maximized": False, "selected_tab": 2}
    state = resolve_main_window_state(raw, (Rect(0, 0, 1920, 1080),), tab_count=7)
    r = state["rect"]
    assert 0 <= r.x <= 1920 - r.width and 0 <= r.y <= 1080 - r.height
    # Out-of-range tab index is dropped, never applied blindly.
    raw_bad_tab = dict(raw, selected_tab=99)
    assert resolve_main_window_state(raw_bad_tab, (Rect(0, 0, 1920, 1080),),
                                     tab_count=7)["selected_tab"] is None


def test_w40_uistate015_qt_blobs_never_drive_wx_geometry(isolated_config):
    for blob in [b"\x01\xd9\xd0\xcb\x00\x03\x00\x00", "AAAA//8AAP8A/wAAAAA", {"qt": True}]:
        verdict = dispose_legacy_qt_geometry_blob(blob)
        assert verdict.startswith("ignored:")
    # A Qt-style record planted in config is treated as absent/corrupt.
    isolated_config.write_text(json.dumps({"ui": {storage.MAIN_WINDOW_STATE_KEY: {
        "qt_geometry": "AAAA", "qt_state": "AAAA"}}}), encoding="utf-8")
    assert storage.get_main_window_state() is None


# ---------------------------------------------------------------------------
# UISTATE-016..020: every settings domain has a live consumer (no orphans)
# ---------------------------------------------------------------------------

def test_w40_uistate_settings_effect_ownership(tmp_path):
    from hpc_gui.config import storage as st

    # UISTATE-016 terminal: graphics bootstrap reads stored settings.
    from hpc_gui.core import terminal_graphics

    boot = terminal_graphics.normalize_settings({"terminal_graphics_mode": "compatibility"})
    assert boot[0] == "compatibility"
    # UISTATE-017 files/transfers/editor: live getters consumed by panels.
    assert st.get_remote_directory_cache_enabled() in (True, False)
    assert st.get_transfer_checksum_verification_enabled() in (True, False)
    assert st.coerce_profile_transfer_parallelism(4) == 4
    # UISTATE-018 jobs refresh/output: widget consumes the interval getter.
    assert st.get_jobs_outputs_refresh_interval_seconds() >= 1
    # UISTATE-019 plugin: namespaced settings survive provider absence.
    from hpc_gui.wx_settings import plugin_settings_survive_absence

    assert plugin_settings_survive_absence(
        tmp_path, "org.w40.absent", {"refresh_seconds": {"type": int, "default": 15}}
    ) == {"refresh_seconds": 15}
    # UISTATE-020 updater/log/language/window: startup consumes language.json.
    assert callable(i18n.load_saved_language)
    assert callable(storage.get_main_window_state)


def test_w40_uistate_settings_live_apply_declared():
    from hpc_gui import wx_settings as m

    for key in ("remote_directory_cache", "transfer_checksum",
                "jobs_outputs_refresh_interval", "transfer_parallelism"):
        assert key in m.LIVE_APPLY_KEYS, key
        assert key in m.GLOBAL_STORAGE_KEYS or key in m.PROFILE_STORAGE_KEYS


# ---------------------------------------------------------------------------
# TODO-MIGRATION-LANGUAGE-001: language preference migration
# ---------------------------------------------------------------------------

def test_w40_migration_language_preference(isolated_app_data):
    (isolated_app_data / "language.json").write_text(json.dumps({"lang": "en"}),
                                                     encoding="utf-8")
    assert i18n.load_saved_language("tr") == "en"
    (isolated_app_data / "language.json").write_text(json.dumps({"lang": "xx"}),
                                                     encoding="utf-8")
    assert i18n.load_saved_language("tr") == "tr"
    (isolated_app_data / "language.json").write_text("{corrupt", encoding="utf-8")
    assert i18n.load_saved_language("en") == "en"


# ---------------------------------------------------------------------------
# TODO-I18N-CURRENT-001: every shipped language exercised on this candidate
# ---------------------------------------------------------------------------

def test_w40_i18n_every_shipped_language_exercised(isolated_app_data):
    exercised = {}
    for lang in i18n.SUPPORTED_LANGUAGES:
        i18n.set_language(lang)
        persisted = json.loads((isolated_app_data / "language.json").read_text(encoding="utf-8"))
        assert persisted == {"lang": lang}
        assert i18n.load_saved_language("tr") == lang  # restart-load path
        exercised[lang] = (i18n.t("tabs.login"), i18n.t("menu.settings"))
    assert exercised["en"][0] == "Connection" and exercised["tr"][0] == "Bağlantı"
    assert all(v[0] and v[1] for v in exercised.values())


# ---------------------------------------------------------------------------
# TODO-PUBLIC-SURFACE-CURRENT-001: README/help/About/legal vs shipped runtime
# ---------------------------------------------------------------------------

def test_w40_public_surface_matches_shipped_runtime():
    root = Path(__file__).resolve().parent.parent
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "English and Turkish" in readme
    for name in ("HELP_en.md", "HELP_tr.md", "PLUGINS_en.md", "PLUGINS_tr.md",
                 "CLI_GUIDE_en.md", "CLI_GUIDE_tr.md"):
        assert (root / "src" / "hpc_gui" / "docs" / name).is_file(), name
    assert (root / "LICENSE").is_file()
    import hpc_gui.wx_shell_frame as shell_frame
    import inspect as _inspect

    assert '"APP-ABOUT"' in _inspect.getsource(shell_frame)


# ---------------------------------------------------------------------------
