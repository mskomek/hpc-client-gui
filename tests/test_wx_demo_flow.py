"""Exercise the actual developer demo in a fresh native wx process."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_wx_demo_uses_real_workspace_with_mock_backends(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["HPC_GUI_CONFIG_ROOT"] = str(tmp_path / "outside-demo")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "create_demo_gif.py"), "--verify-flow"],
        cwd=root, env=env, capture_output=True, text=True, timeout=70,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wx-demo-flow=PASS splash,profile,connected,selected,uploading,uploaded,edited,jobs,outputs" in result.stdout
    assert not (tmp_path / "outside-demo").exists()
