import json
import os
import pathlib
import subprocess
import sys
import textwrap
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_terminal_webview import _is_webview_available
def _run(code, timeout=15):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=timeout, env=env,
    )
def _wrap(code):
    return textwrap.dedent(code)

__all__ = [
    'json',
    'os',
    'pathlib',
    'subprocess',
    'sys',
    'textwrap',
    'pytest',
    'wx',
    '_is_webview_available',
    '_run',
    '_wrap',
]
