@echo off
setlocal EnableDelayedExpansion
set ROOT=C:\Users\msi\.tmp\hpc-client-gui\x11-final-develop-20261121
set SRC=%ROOT%\source-v44
set OUT=%ROOT%\baba-predecessor-v44-x10
set PY=%ROOT%\venv\Scripts\python.exe
set PYTHONPATH=%SRC%\src;%SRC%\tests
set QT_QPA_PLATFORM=offscreen
set RC=0
if not exist "%OUT%" mkdir "%OUT%"
cd /d "%SRC%"
echo source_manifest_sha256=4ee50b32de11ad58dff9af6b840b563030bc5f2200f76eb343ce323c9675c76a > "%OUT%\run.meta"
echo source_base=0ea4a5953228fe79ce7ce7c07c0b7ed04a03b2b8>> "%OUT%\run.meta"
echo started_local=%DATE% %TIME%>> "%OUT%\run.meta"
echo python=3.14.10 pytest=9.1.1 wx=4.3.1 Qt=6.12.0 platform=Windows11-on-baba-Session2>> "%OUT%\run.meta"
echo command=predecessor GUI subprocess regression repeated ten times>> "%OUT%\run.meta"
for %%I in (1 2 3 4 5 6 7 8 9 10) do (
  set PYTEST_ADDOPTS=--basetemp=%OUT%\pytest-temp-%%I
  echo ===== ITERATION %%I =====>> "%OUT%\stdout.txt"
  "%PY%" -m pytest -q tests\test_wx_file003_final_stress.py::test_editor_wx_lifecycle_predecessor_preserves_context_menu_runtime --junitxml="%OUT%\run-%%I.xml" >> "%OUT%\stdout.txt" 2>> "%OUT%\stderr.txt"
  set RC=!ERRORLEVEL!
  echo exit_%%I=!RC!>> "%OUT%\exit-codes.txt"
  if not "!RC!"=="0" goto finished
)
:finished
echo ended_local=%DATE% %TIME%>> "%OUT%\run.meta"
exit /b !RC!
