"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""

import tempfile
from pathlib import Path

import pytest

# Shared imports
from hpc_gui.config import storage

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")


def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Ensure clean config
    storage.save_config({"profiles": [], "settings": {}})
    return tmp
