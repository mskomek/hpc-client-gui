import os
import pathlib
import sys
import time

root = pathlib.Path(r'C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo')
os.chdir(root)
sys.path[:0] = [str(root / 'src'), str(root / 'tests')]
variant = sys.argv[1]
import wx_terminal_webview_support as support
if not variant.startswith('nested-'):
    raise SystemExit(f'unknown variant: {variant}')

nodes = {
    'a': 'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
    'b': 'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
    'c': 'tests/test_wave80_files_outputs_audit_behavior.py::TestWave80Audit::test_files_follow_menu_has_following_check',
    'ab': [
        'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
        'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
    ],
}
selection = nodes.get(variant[7:])
if selection is None:
    raise SystemExit(f'unknown diagnostic group: {variant}')
if isinstance(selection, str):
    selection = [selection]
selection = [*selection, 'tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked']
import pytest
raise SystemExit(pytest.main(['-p', 'no:cacheprovider', '-q', *selection]))
