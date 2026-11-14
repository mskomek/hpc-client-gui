"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from pathlib import Path

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

from hpc_gui.config import storage


def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    # Patch both Path.home and the app_data_dir helpers so config and plugins
    # use the same isolated temp dir regardless of which helper a module
    # imported. Without this, conftest's tmp_path for plugins and our
    # Path.home temp would diverge and load_profiles would look in the wrong
    # place when tests are run as part of a large suite.
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Also patch the core and config helpers directly
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        # plugins uses its own helper but conftest already patches it to tmp_path;
        # we override to use the same fake_dir for consistency when tests run
        # as part of the large suite.
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp
