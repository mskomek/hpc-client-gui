import pathlib, sys
root=pathlib.Path.home()/'AppData'/'Local'/'Temp'/'hpc-client-gui-r14-debug-20261118'/'repo'
sys.path[:0]=[str(root/'src'),str(root/'tests')]
import pytest
nodes=[
 'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
 'tests/test_wave80_files_outputs_audit_behavior.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked']
raise SystemExit(pytest.main(['-p','no:cacheprovider','-q',*nodes]))
