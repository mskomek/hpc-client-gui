import pathlib, sys
root=pathlib.Path.home()/'AppData'/'Local'/'Temp'/'hpc-client-gui-r14-debug-20261118'/'repo'
sys.path[:0]=[str(root/'src'),str(root/'tests')]
source=(root/'tests'/'test_wx_terminal_webview_bridge.py').read_text(encoding='utf-8')
source=source.replace('def test_wx_terminal_external_navigation_blocked():','def test_wx_terminal_external_navigation_blocked_closeprobe():',1)
old='    frame.Destroy()\n    wx.Yield()\n\n\n@pytest.mark.gui\n@pytest.mark.regression\n'
new='    panel.close()\n    wx.Yield()\n    frame.Destroy()\n    wx.Yield()\n\n\n@pytest.mark.gui\n@pytest.mark.regression\n'
assert source.count(old)==1, f'unexpected teardown match count: {source.count(old)}'
(root/'tests'/'test_wx_terminal_webview_bridge_closeprobe.py').write_text(source,encoding='utf-8')
import pytest
nodes=[
 'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
 'tests/test_wave80_files_outputs_audit_behavior.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wx_terminal_webview_bridge_closeprobe.py::test_wx_terminal_external_navigation_blocked_closeprobe']
raise SystemExit(pytest.main(['-p','no:cacheprovider','-q',*nodes]))

