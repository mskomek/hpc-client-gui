# GUI-TERM-002 Execution Evidence

Environment: Windows, Python 3.12.4 (`D:\Python\Python312\python.exe`), wxPython 4.3.1 msw (Phoenix), branch `develop`, tested commit `4818c944b752c47dac8ed68c18fb9fe6cfe076b4` plus the working-tree change recorded by the final commit.

Commands executed:

```text
python -m pytest -q tests/test_wx_term002.py --cache-clear
python -m pytest -q tests/test_wx_terminal.py tests/test_wx_local_files.py tests/test_wx_remote_files.py tests/test_wx_shell.py tests/test_wx_term002.py --cache-clear
python -m ruff check src tests
git diff --check
```

Results:

- `test_wx_term002.py`: 2 passed, 0 failed, 0 skipped, 1.40s.
- Related wx regression selection: 19 passed, 0 failed, 0 skipped, 2.46s.
- Ruff: passed. Diff check: passed.

Evidence: a real wx local-file frame action runs a shell script in the terminal using `bash --` and shell-safe quoting; a real wx editor Run button reaches the same production terminal dispatch. The editor and file-view flows use the existing i18n-backed production labels and SSH adapter.

Scope limitation: the real-wx GUI execution evidence was measured on Windows only. The complete wx suite has one pre-existing Windows clipboard-environment failure in `test_wx_remote_copy_path_preserves_multiple_selected_paths`; the isolated test remains unrelated to TERM-002 and the focused TERM tests pass.
