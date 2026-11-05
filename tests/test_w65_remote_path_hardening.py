"""W65 local/SFTP path-link rejection tests."""

from __future__ import annotations

import stat
from types import SimpleNamespace

import pytest

from hpc_gui.plugin_engines.openfoam_lint.api import lint_paths
from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path


def test_lint_paths_rejects_symlinked_parent(tmp_path):
    target = tmp_path / "real" / "system" / "controlDict"
    target.parent.mkdir(parents=True)
    target.write_text("application simpleFoam;\n", encoding="utf-8")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target.parents[1], target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    result = lint_paths([alias / "system" / "controlDict"])
    assert any(item.rule_id == "OF-CASE-006" for item in result.diagnostics)


def test_lint_paths_rejects_symlinked_case_root(tmp_path):
    target = tmp_path / "real-case"
    (target / "system").mkdir(parents=True)
    (target / "system" / "controlDict").write_text(
        "application simpleFoam;\n", encoding="utf-8"
    )
    alias = tmp_path / "case-link"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    result = lint_paths([alias])
    assert any(item.rule_id == "OF-CASE-006" for item in result.diagnostics)


def test_remote_symlinked_parent_rejected_before_download():
    class _Files:
        downloaded = False

        def lstat_entry(self, path):
            if path == "/case/link":
                return SimpleNamespace(mode=stat.S_IFLNK | 0o777, size=0)
            if path == "/case/link/system/controlDict":
                return SimpleNamespace(mode=stat.S_IFREG | 0o644, size=24)
            return SimpleNamespace(mode=stat.S_IFDIR | 0o755, size=0)

        stat_entry = lstat_entry

        def is_dir(self, _path):
            return False

        def stat(self, _path):
            return 24, 0

        def exists(self, _path):
            return True

        def listdir_entries(self, _path):
            return []

        def download(self, _remote, _local):
            self.downloaded = True

    files = _Files()
    with pytest.raises(ValueError, match="symbolic|link"):
        lint_remote_path("/case/link/system/controlDict", files)
    assert not files.downloaded
