from __future__ import annotations
import contextlib,faulthandler,hashlib,json,os,pathlib,sys,time
import pytest
faulthandler.enable()
root=pathlib.Path(r'C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo');os.chdir(root)
sys.path.insert(0,str(root/'tests'));sys.path.insert(0,str(root/'src'))
tmp=root/'.tmp'/'debug-r14';tmp.mkdir(parents=True,exist_ok=True);os.environ['TMP']=str(tmp);os.environ['TEMP']=str(tmp);os.environ['TMPDIR']=str(tmp);os.environ['PYTHONPATH']=str(root/'tests')+';'+str(root/'src')
name='r14_threeprior_diag';allnodes=(root.parent/'last1000-nodeids.txt').read_text(encoding='utf-8-sig').splitlines();nodes=[allnodes[i] for i in (81,87,111)]+['tests/test_wx_terminal_webview_bridge.py::test_wx_terminal_external_navigation_blocked']
xml=tmp/f'{name}.xml';out=tmp/f'{name}.stdout';err=tmp/f'{name}.stderr';base=tmp/f'basetemp-{name}-{os.getpid()}';cache=tmp/f'cache-{name}'
args=['-vv','--tb=long','--durations=20','-o','faulthandler_timeout=180',f'--basetemp={base}','-o',f'cache_dir={cache}',f'--junitxml={xml}',*nodes]
start=time.monotonic()
with out.open('w',encoding='utf-8') as so,err.open('w',encoding='utf-8') as se:
 with contextlib.redirect_stdout(so),contextlib.redirect_stderr(se):code=int(pytest.main(args))
summary={'group':name,'exit_code':code,'duration_seconds':round(time.monotonic()-start,2),'selected_tests':len(nodes),'junit_sha256':hashlib.sha256(xml.read_bytes()).hexdigest() if xml.exists() else None,'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest(),'stdout_bytes':out.stat().st_size,'stderr_bytes':err.stat().st_size}
(tmp/f'{name}.result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))






