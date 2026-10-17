import tempfile
from pathlib import Path
from unittest import mock
import pytest
from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.services.profile_duplicate import duplicate_profile
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.plugins.models import validate_storage_area
from hpc_gui.ssh.client import HostKeyInfo
from hpc_gui.wx_connection import WxConnectionModel, ssh_info_from_profile
from hpc_gui.config.system_profile import builtin_system_template_groups
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.config.system_profile import normalize_system_settings
from hpc_gui.config.file_manager_profile import normalize_file_manager_settings
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings
wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")
def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Ensure clean config
    storage.save_config({"profiles": [], "settings": {}})
    return tmp

__all__ = [
    'tempfile',
    'Path',
    'mock',
    'pytest',
    'storage',
    'load_profiles',
    'duplicate_profile',
    'quota_gate',
    'validate_storage_area',
    'HostKeyInfo',
    'WxConnectionModel',
    'ssh_info_from_profile',
    'builtin_system_template_groups',
    'installed_cluster_template_groups',
    'normalize_system_settings',
    'normalize_file_manager_settings',
    'normalize_jump_host_settings',
    'wx',
    '_isolated_storage',
]
