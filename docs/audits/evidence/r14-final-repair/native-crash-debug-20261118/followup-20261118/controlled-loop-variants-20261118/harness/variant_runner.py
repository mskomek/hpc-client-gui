import os
import pathlib
import sys
import time

root = pathlib.Path(r'C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo')
os.chdir(root)
sys.path[:0] = [str(root / 'src'), str(root / 'tests')]
variant = sys.argv[1]
import wx_terminal_webview_support as support

if variant == 'yield':
    def wait_with_yield(panel, timeout=6):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(panel, '_ready', False):
                return True
            try:
                wx = __import__('wx')
                wx.Yield()
            except Exception:
                pass
            time.sleep(0.05)
        return bool(getattr(panel, '_ready', False))
    support._wait_for_ready = wait_with_yield
elif variant != 'nested-loop':
    raise SystemExit(f'unknown variant: {variant}')

import pytest
raise SystemExit(pytest.main([
    '-p', 'no:cacheprovider',
    '-q',
    'tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked',
]))
