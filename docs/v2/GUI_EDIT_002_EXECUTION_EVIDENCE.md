# GUI-EDIT-002 Execution Evidence

Environment: Windows, Python 3.12.4 (`D:\Python\Python312\python.exe`), wxPython 4.3.1 msw (Phoenix), branch `develop`, tested working tree based on `87a860d28fe4dc7dd21d02a309c7bec7e739e6aa`.

Commands executed:

```text
python -m pytest -q tests/test_wx_editor.py tests/test_wx_editor_window_parity.py tests/test_wx_editor_cross_view_actions.py tests/test_wx_remote_editor_flow.py --cache-clear
python -m pytest -q tests/test_wx_term002.py tests/test_wx_terminal.py --cache-clear
python -m ruff check src tests
python -m compileall -q src tests
git diff --check
```

Results:

- Editor integration selection: 49 passed, 0 failed, 0 skipped, 18.39s.
- Shell/editor integration selection: 4 passed, 0 failed, 0 skipped, 1.56s.
- Full expanded wx suite: 347 passed, 1 failed, 0 skipped, 359.42s; the sole failure is the unrelated Windows clipboard test `test_wx_remote_copy_path_preserves_multiple_selected_paths`.
- Ruff: passed.
- Compileall: passed.
- Diff check: passed.

Real wx evidence covers local and remote save-then-submit, save-then-run, primary editor reuse, standalone new editor windows, dirty-document replacement, asynchronous remote loading, stale-result rejection, reconnect/session-safe backend selection, and shell-builder integration.

Scope limitation: the real-wx GUI evidence was measured on Windows only. The complete wx suite has one unrelated Windows clipboard-environment failure in `test_wx_remote_copy_path_preserves_multiple_selected_paths`.
