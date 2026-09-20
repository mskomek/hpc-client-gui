# W15 Audit Report

```text
Wave: W15
Decision: PASS
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Date: 2026-09-19
```

## Scope and authority

Fresh-context audit performed against `CORE_EXECUTION_RULES.md`, canonical
`waves/pending/W15.md`, all 14 W15 registry rows, W15 index rows and zero TODO
rows, Workstream C0 and Workstream E, live main/plugin truth, W14 predecessor
PASS, the canonical W15 report, and current evidence. No `waves/bak/` material
was used. Only this audit report was written; product and implementation
report files were not changed.

## Identity and hygiene

- Main `develop`: `0f8902a023bac76071527232c2287af96478ed2b`; `origin/develop`
  matches. Plugin `develop`: `f0abb7e7037e66ab451d463c699fecf4e00c89eb`;
  plugin origin matches. W14 predecessor report is `PASS`.
- Main tree remains dirty with the inventoried W01-W15/unrelated changes and
  W15 evidence/helpers; no reset, clean, or destructive operation was used.
  Plugin has only pre-existing untracked `.github/social-preview.jpg`.
- Main `git diff --check` exits 0 (only pre-existing CRLF warnings); no
  W15-scope secrets, weakened assertions, added skips, or xfails found.

## Verification

- `python -m pytest tests/test_w15_fresh_user_startup.py -q` → **11 passed**.
- Current artifact exists at the cited path and independently hashes to
  `d2aab99d998a1dd0d912098f319f9bbf6c227ba0b4b82c9db9303bcf6c863cfd`, size
  `7,414,472` bytes, matching `build/audit/w15-fresh-user-windows.json`.
  `build/hpc-client-gui/PYZ-00.toc` contains `hpc_gui.core.paths` and
  `hpc_gui.wx_shell`.
- Canonical evidence is `build/audit/w15-fresh-user-windows.json`:
  `result=PASS`, all 10 checks PASS, exit codes `[0,0]`, both runtime payloads
  PASS, generated `2026-09-19T20:20:48.374368+00:00`, isolated root,
  outside-repo workdir, frozen execution, and `isolated_from_src=true`.
  GUI and PACKAGE claims are therefore bound to one exact available SHA.
- Superseded evidence was re-read and is not current acceptance evidence:
  `a2a0f079...` solo/r2 PASS files are explicitly superseded with unavailable
  bytes; sibling `cc4fd240...` has runtime FAIL and exits `[1,1]`; `bd7fbbf8...`
  is honest FAIL with `[1,0]` and `NameError`. The current report removes all
  corroboration claims and cites only `d2aab99d...`.
- External evidence is **N/A**: W15 requires GUI and PACKAGE; the acceptance
  uses a documented loopback fixture, not an external cluster. Manual-only
  capabilities are listed in the evidence and are not misrepresented.

## Prior findings

- `REOPEN-W15-001` is truthfully closed: a new solo executable was rebuilt,
  accepted, retained, and hash-verified at the cited path.
- `REOPEN-W15-002` is truthfully closed: failed sibling evidence is labeled
  superseded pre-fix failure and is excluded from acceptance/corroboration.

No new blocking finding remains. W15 meets its 14 owned requirements and the
GUI/PACKAGE evidence gates. **PASS — ready for close; no downstream Wave was
started.**
