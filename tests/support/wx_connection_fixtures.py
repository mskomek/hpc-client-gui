"""Shared isolated storage and wx teardown fixtures for connection tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def isolated_storage(monkeypatch):
    """Point profile, plugin, and application storage at one temporary home."""
    from hpc_gui.config import storage

    temporary = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(temporary.name))
    try:
        import hpc_gui.core.paths as paths
        import hpc_gui.config.storage as config_storage
        import hpc_gui.plugins.storage as plugin_storage

        data_dir = Path(temporary.name) / ".truba_slurm_gui"
        data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths, "app_data_dir", lambda: data_dir)
        monkeypatch.setattr(config_storage, "app_data_dir", lambda: data_dir)
        monkeypatch.setattr(plugin_storage, "app_data_dir", lambda: data_dir)
        monkeypatch.setattr(plugin_storage, "plugins_root", lambda override=None: data_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return temporary


def seed_master_dpapi_cache(monkeypatch, master_password):
    """Model a successfully decrypted Windows DPAPI cache on every platform."""
    import hpc_gui.config.storage as config_storage

    token = f"dpapi-{master_password}"

    def unprotect(value):
        if value == token:
            return master_password
        raise ValueError("decrypt failed")

    monkeypatch.setattr(config_storage, "load_settings", lambda: {"master_password_dpapi": token})
    monkeypatch.setattr("hpc_gui.core.secret_store.is_available", lambda: True)
    monkeypatch.setattr("hpc_gui.core.secret_store.unprotect_secret", unprotect)
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.unprotect_secret", unprotect)


@pytest.fixture(autouse=True)
def clean_wx_after():
    """Restore language and destroy all test-owned top-level wx windows."""
    from hpc_gui.core.i18n import current_language, set_language

    try:
        import wx
    except ImportError:
        yield
        return
    language = current_language()
    set_language("en")
    yield
    try:
        set_language(language)
    finally:
        app = wx.GetApp()
        if app is not None:
            for window in list(wx.GetTopLevelWindows()):
                try:
                    window.Destroy()
                except Exception:
                    pass
            for _ in range(5):
                try:
                    wx.Yield()
                except Exception:
                    break
