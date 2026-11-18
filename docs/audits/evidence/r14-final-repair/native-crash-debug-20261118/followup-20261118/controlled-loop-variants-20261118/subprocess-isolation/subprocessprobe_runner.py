import pathlib, sys
root=pathlib.Path.home()/'AppData'/'Local'/'Temp'/'hpc-client-gui-r14-debug-20261118'/'repo'
sys.path[:0]=[str(root/'src'),str(root/'tests')]
probe='''import os, pathlib, subprocess, sys
import pytest
ROOT=pathlib.Path(__file__).parents[1]
@pytest.mark.wx
def test_external_navigation_native_isolation_probe():
    env=os.environ.copy()
    env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests'),env.get('PYTHONPATH','')])
    result=subprocess.run([sys.executable,'-X','faulthandler','-m','pytest','-p','no:cacheprovider','-q','tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked'],cwd=ROOT,capture_output=True,text=True,timeout=20,env=env)
    assert result.returncode==0, f'isolated child failed: stdout={result.stdout!r} stderr={result.stderr!r}'
'''
(root/'tests'/'test_wx_terminal_external_navigation_subprocessprobe.py').write_text(probe,encoding='utf-8')
import pytest
nodes=[
 'tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wave80_files_outputs.py::TestRegression::test_wave78_tabs_still_work',
 'tests/test_wave80_files_outputs_audit_behavior.py::TestWave80Audit::test_files_follow_menu_has_following_check',
 'tests/test_wx_terminal_external_navigation_subprocessprobe.py::test_external_navigation_native_isolation_probe']
raise SystemExit(pytest.main(['-p','no:cacheprovider','-q',*nodes]))

