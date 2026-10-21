# Test Matrix

## Local evidence

| Check | Command / source | Result | Exit |
|---|---|---:|---:|
| Architecture gate unit tests | `D:\Projeler\hpc-client-gui\.venv\Scripts\python.exe -m pytest tests/test_source_architecture_gate.py -q` | 5 passed | 0 |
| Architecture gate Ruff | `python -m ruff check scripts/check_source_architecture.py tests/test_source_architecture_gate.py` | passed | 0 |
| Architecture gate syntax | `python -m py_compile scripts/check_source_architecture.py tests/test_source_architecture_gate.py` | passed | 0 |
| Changed-source architecture gate | shared Agent Core + project gate, base `f61919bad12be5f328cb9db3fee3c8de8563fa5b` | PASS; 52 untouched baseline files remain over limit; no new errors | 0 |
| Starting full architecture inventory | shared Agent Core `--scope project` at starting SHA | FAIL as expected for baseline debt: 52 over limit | 1 |
| Full architecture on WAVE 00 working tree | shared Agent Core `project` + project dependency/API/cycle gate | FAIL as expected: 52 over limit, 2 inherited symbol imports, 8 inherited cycles, 0 API errors | 1 |
| Wave 01 Jobs persistence/history | five focused Jobs service suites at `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` | 45 passed, 0 failed, 0 skipped | 0 |
| Wave 01 Ruff | Ruff over all 11 changed Python files | passed | 0 |
| Wave 01 compileall | six Jobs service modules | passed | 0 |
| Wave 01 changed-source architecture gate | base `179fb47dfc94765cbec5d9eb058ba0d0f6247232`, 782 Python files | PASS; no new LOC/import/API/cycle errors; 52 existing over-limit files remain | 0 |
| Wave 01 full project architecture | `--mode full` at `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` | FAIL expected: 52 LOC violations, 2 unresolved imports, 8 cycles, 0 API errors | 1 |
| GitHub Actions | not run | NOT RUN | — |

The first `py -m pytest` attempt used the global Python 3.14 installation, which has no pytest module; the WAVE 00 suite was rerun with the project `.venv` and passed 5/5. During Wave 01 source selection, one exploratory suite invocation had 44 passes and one failure because a later Jobs Wave 02 test rewrite patched an extracted module not yet present. That test-only rewrite was excluded from Wave 01; the final WAVE 01 suites passed 45/45 with the existing test retained and provenance assertions added. This diagnostic failure is source incompatibility, not an unresolved product failure.

## Pending suites

Focused suites will be added as waves land. Local and GitHub Actions results remain separate. Unrun suites must remain `NOT RUN`; skipped tests and environmental blockers are recorded individually and never counted as PASS.
