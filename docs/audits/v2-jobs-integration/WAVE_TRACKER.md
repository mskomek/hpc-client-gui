# Wave Tracker

| Wave | Scope | Status | Start SHA | End SHA | Local tests | Merge target |
|---|---|---|---|---|---|---|
| 00 | Repository and architecture foundation | WAVE_COMPLETE | `f61919bad12be5f328cb9db3fee3c8de8563fa5b` | `718fbd01296793b513526adabedd3e48deea2d4a` | 5 focused tests, Ruff, py_compile, changed-source gate pass; global baseline scan has 52 LOC violations | isolated integration |
| 01 | Jobs persistence and history | WAVE_COMPLETE | `179fb47dfc94765cbec5d9eb058ba0d0f6247232` | `c1d8e66f5b5b4a06abcf79511c48bf97017df0cf` | 45 focused tests passed; Ruff, compileall, changed-source gate passed; full global scan remains baseline-failing at 52 files | isolated integration |
| 02 | Jobs workspace and wx UI | WAVE_COMPLETE | `7c3ee2260aac03eea2e6aebf7d9f3e7a39ee55e3` | `d12a752c1557b2cff7ea5a21bbf2d391c13b5fa3` | 95 focused tests plus 64 extended GUI tests passed; post-fix stress 10/10; architecture gate, Ruff and compileall passed; 51 global LOC violations remain | isolated integration |
| 03 | Release runner and test scopes | WAVE_COMPLETE | `49ce32cc85d9a926542597b33f70dec259e7e2e1` | `4ed2075c072b0cd38ca05249a9670aa96dfc3af1` | 13 focused tests passed; Ruff, compileall, evidence SHA and wheel build passed; changed-source gate passed; full architecture remains baseline-failing at 51 files | isolated integration |
| 04 | Config storage | WAVE_COMPLETE | `66f07565e19947b8140c5f7798fa32c2b3e36890` | `71ef960bb486cc821e1a79f969e5b58913841715` | 384 passed, 0 failed, 1 POSIX-only skip; Ruff, compileall, facade API and changed-source gate passed | isolated integration |
| 05 | Connection and SSH | NOT STARTED | — | — | — | isolated integration |
| 06 | CLI modularization | NOT STARTED | — | — | — | isolated integration |
| 07 | Plugin system | NOT STARTED | — | — | — | isolated integration |
| 08 | Qt Jobs Outputs | NOT STARTED | — | — | — | isolated integration |
| 09 | Splash, updater and dialogs | NOT STARTED | — | — | — | isolated integration |
| 10 | Files / FTP modularization | NOT STARTED | — | — | — | isolated integration |
| 11 | Remaining large modules | NOT STARTED | — | — | — | isolated integration |
| 12 | Final acceptance | NOT STARTED | — | — | — | isolated integration |
