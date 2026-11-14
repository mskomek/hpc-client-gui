"""Wave 71.5 — wx Connection micro-hardening.

Covers: begin_connect/Thread.start failure recovery, connect_selected bool
contract proofs, Remember=true settings persistence, Test Cluster
Remember=true, Save & Connect contract fixes.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from pathlib import Path

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage


def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp


def _make_profile(name="p", master=None, secret="s3cret"):
    """Create profile; if master given, encrypt with it."""
    if master:
        from hpc_gui.core.crypto_master import encrypt_with_master
        enc = encrypt_with_master(master, secret)
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
            "save_password": True, "password_enc": enc.token, "password_salt": enc.salt,
        })
    else:
        storage.upsert_profile({
            "name": name, "host": "h.example", "port": 22, "username": "user",
        })
