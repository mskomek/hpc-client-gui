# V2 candidate build environment (verified facts, 2026-09-25)

Facts for W56/W57 candidate builds on this Windows host. They correct two observations recorded in
`docs/wave-reports/v2/opencode/W56_WAVE_REPORT.md`.

## Interpreter: use the project venv, not `python` on PATH

- `pyproject.toml` pins `requires-python = "==3.14.*"`.
- `python` on PATH is `D:\Python\Python312\python.exe` (3.12.4) and is **not** the build interpreter.
- The project venv is on the pin: `.venv\Scripts\python.exe --version` → `Python 3.14.0`;
  `.venv\Scripts\python.exe -m PyInstaller --version` → `6.22.2`.
- A system 3.14.0 also exists at `%LOCALAPPDATA%\Programs\Python\Python314\python.exe` for a fresh clean venv
  (`uv venv -p 3.14` resolves it), e.g. to install `requirements-release.lock` into an isolated build venv.

So an on-pin Windows candidate can be built here; building with 3.12 would be off-pin and is not required.

## Program concurrency

The current `/ac-wave-opencode-parallel` run records `parallel_serial_fallback` ("no project-declared managed
parallel task graph") in its `events.ndjson`: the controller dispatches one Wave phase at a time and no sibling
Wave is executing while W56 runs. Whether that satisfies the LOCAL_REAL lease rule is governed by
`.opencode/protocol/LOCAL_REAL_HPC_LAB.md`; this note only records the concurrency fact.
