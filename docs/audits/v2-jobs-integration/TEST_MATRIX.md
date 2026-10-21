# Test Matrix

## Local evidence

| Check | Command / source | Result | Exit |
|---|---|---:|---:|
| Architecture gate unit tests | `D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe -m pytest tests/test_source_architecture_gate.py -q` | 4 passed | 0 |
| Python syntax | `py -m py_compile scripts/check_source_architecture.py tests/test_source_architecture_gate.py` | passed | 0 |
| Changed-source architecture gate | shared Agent Core + project gate, base `f61919bad12be5f328cb9db3fee3c8de8563fa5b` | PASS; 52 untouched baseline files remain over limit; no new errors | 0 |
| Starting full architecture inventory | shared Agent Core `--scope project` at starting SHA | FAIL as expected for baseline debt: 52 over limit | 1 |
| Full architecture on WAVE 00 working tree | shared Agent Core `project` + project dependency/API/cycle gate | FAIL as expected: 52 over limit, 2 inherited symbol imports, 8 inherited cycles, 0 API errors | 1 |
| GitHub Actions | not run | NOT RUN | — |

The first `py -m pytest` attempt used the global Python 3.14 installation, which has no pytest module. The test was rerun with the project `.venv` and passed 4/4; the failed launch is an environment setup attempt, not a test failure.

## Pending suites

Focused suites will be added as waves land. Local and GitHub Actions results remain separate. Unrun suites must remain `NOT RUN`; skipped tests and environmental blockers are recorded individually and never counted as PASS.
