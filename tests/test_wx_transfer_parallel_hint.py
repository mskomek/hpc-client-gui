"""Native wx transfer limit labels, isolated from other native GUI tests."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
@pytest.mark.regression
@pytest.mark.parametrize("embedded", [True, False])
@pytest.mark.parametrize("configured,effective", [(4, 1), (4, 4)])
def test_transfer_parallel_hint(embedded, configured, effective):
    script = """
import sys
import wx
from hpc_gui.core.i18n import load_language, t
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_transfer_workspace import build_transfers_panel, create_transfer_progress

embedded = sys.argv[1] == 'True'
configured, effective = map(int, sys.argv[2:])
load_language('en')
app = wx.App(False)
frame = wx.Frame(None)
controller = TransferSessionController([], lambda item, progress: None,
                                       parallel_limit=effective)
controller.configured_parallel_limit = configured
# No worker or pending transfer is required for the limit label.
controller.start()
assert controller.engine.wait(5)
host = None
try:
    if embedded:
        host = build_transfers_panel(frame, controller)
    else:
        host = create_transfer_progress(frame, controller)
    assert host is not None
    label = host._wx_transfer_controls['parallel_hint'].GetLabel()
    assert str(configured) in label and str(effective) in label, label
    if configured != effective:
        assert t('transfer.parallel_reduced_backend') in label, label
    else:
        assert label.count(str(configured)) >= 2, label
        assert t('transfer.parallel_reduced_server') not in label, label
        assert t('transfer.parallel_reduced_backend') not in label, label
finally:
    if host is not None:
        host._wx_transfer_close(None)
        if embedded:
            host.Destroy()
    frame.Destroy()
    app.ProcessPendingEvents()
"""
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), env.get("PYTHONPATH", "")]
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(embedded), str(configured), str(effective)],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
