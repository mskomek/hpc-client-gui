@echo off
setlocal EnableDelayedExpansion
set ROOT=C:\Users\home\.tmp\hpc-client-gui\x11-final-develop-20261121
set SRC=%ROOT%\source-v45
set OUT=%ROOT%\win11new-v45-gui-acceptance
set PY=%ROOT%\venv\Scripts\python.exe
set PYTHONPATH=%SRC%\src;%SRC%\tests
set QT_QPA_PLATFORM=offscreen
set TEMP=%SRC%\.tmp\win11new-v45
set TMP=%TEMP%
set FINAL_RC=0
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%TEMP%" mkdir "%TEMP%"
cd /d "%SRC%"
echo source_manifest_sha256=71d21fd1445452156ad717422a482d84ddda4b9723e21c332efa9e3cd26f4c13 > "%OUT%\run.meta"
echo source_base=0ea4a5953228fe79ce7ce7c07c0b7ed04a03b2b8>> "%OUT%\run.meta"
echo started_local=%DATE% %TIME%>> "%OUT%\run.meta"
echo python=3.14 pytest=9.2.0 wx=4.3.2 Qt=6.12.0 platform=Kole-Windows11-New-Session1>> "%OUT%\run.meta"
echo predecessor=10 independent pytest subprocesses>> "%OUT%\run.meta"
echo webview_bridge=tests\test_wx_terminal_webview_bridge.py>> "%OUT%\run.meta"
for %%I in (1 2 3 4 5 6 7 8 9 10) do (
  set PYTEST_ADDOPTS=--basetemp=%TEMP%\pred-%%I
  echo ===== PREDECESSOR ITERATION %%I =====>> "%OUT%\stdout.txt"
  "%PY%" -m pytest -q tests\test_wx_file003_final_stress.py::test_editor_wx_lifecycle_predecessor_preserves_context_menu_runtime --junitxml="%OUT%\predecessor-%%I.xml" >> "%OUT%\stdout.txt" 2>> "%OUT%\stderr.txt"
  set RC=!ERRORLEVEL!
  echo predecessor_%%I=!RC!>> "%OUT%\exit-codes.txt"
  if not "!RC!"=="0" if "!FINAL_RC!"=="0" set FINAL_RC=!RC!
)
set PYTEST_ADDOPTS=--basetemp=%TEMP%\webview-bridge
echo ===== WEBVIEW BRIDGE =====>> "%OUT%\stdout.txt"
"%PY%" -m pytest -q tests\test_wx_terminal_webview_bridge.py --junitxml="%OUT%\webview-bridge.xml" >> "%OUT%\stdout.txt" 2>> "%OUT%\stderr.txt"
set RC=!ERRORLEVEL!
echo webview_bridge=!RC!>> "%OUT%\exit-codes.txt"
if not "!RC!"=="0" if "!FINAL_RC!"=="0" set FINAL_RC=!RC!
echo ended_local=%DATE% %TIME%>> "%OUT%\run.meta"
exit /b !FINAL_RC!
