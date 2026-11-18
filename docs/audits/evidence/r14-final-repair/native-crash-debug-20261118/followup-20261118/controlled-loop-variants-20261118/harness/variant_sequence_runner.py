import os
import pathlib
import sys
import time

root = pathlib.Path(r'C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo')
os.chdir(root)
sys.path[:0] = [str(root / 'src'), str(root / 'tests')]
variant = sys.argv[1]
import wx_terminal_webview_support as support

if variant.startswith('yield'):
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
elif not variant.startswith('nested'):
    raise SystemExit(f'unknown variant: {variant}')

import pytest
nodes = [
    'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
    'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
    'tests/test_wave80_files_outputs_audit_behavior.py::TestWave80Audit::test_files_follow_menu_has_following_check',
    'tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked',
]
if variant.endswith('-seq'):
    selected = nodes
else:
    selected = [nodes[-1]]
raise SystemExit(pytest.main(['-p', 'no:cacheprovider', '-q', *selected]))
