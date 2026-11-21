# Windows11-New GUI stress receipt

- Environment: Kole Windows11-New, interactive `home` console session 1.
- Task Scheduler task: `CodexX11V45Win11NewGUIAcceptance`; interactive-only, run as `home`; Last Result 0.
- Source base: `0ea4a5953228fe79ce7ce7c07c0b7ed04a03b2b8`.
- Source overlay manifest SHA-256: `71d21fd1445452156ad717422a482d84ddda4b9723e21c332efa9e3cd26f4c13`.
- Runtime: Python 3.14, pytest 9.2.0, wxPython 4.3.2, PySide6 6.12.0.
- Ordered predecessor GUI regression: ten independent pytest subprocesses, 10/10 pass, process exit codes 0.
- `tests/test_wx_terminal_webview_bridge.py`: 12/12 pass, process exit 0.
- JUnit, stdout/stderr, Task Scheduler receipt, source manifest and executed command script are retained with SHA-256 checksums.

This is native Windows GUI regression evidence for the recorded tests. It does not identify the earlier intermittent wx/WebView native crash root cause and does not cover an authenticated SSH X11 connection, trusted/untrusted policy, xclock, or packaged executable shutdown acceptance.
