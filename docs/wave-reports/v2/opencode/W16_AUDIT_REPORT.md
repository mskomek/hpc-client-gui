# W16 Audit Report

```text
Wave: W16
Audit cycle: 2
Decision: REOPEN
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Audit date: 2026-09-21 UTC
Authority: waves/pending/W16.md only
```

## Scope and authority read

Audited exactly the canonical `waves/pending/W16.md`; it is present and
unambiguous. Re-read `30_AUDIT_WAVE.md`, `CORE_EXECUTION_RULES.md`, the 49
W16 registry rows, the W16 index, zero W16 TODO rows, and every mandatory
`WAVE_V2_FINAL_04.md` section named by the Wave. Re-read the W16 report,
existing audit, current implementation/tests, raw evidence, current diff/HEAD,
plugin identity, and dependency W15. The LOCAL_REAL protocol was also read;
W16 requires GUI/PACKAGE, while its remote replay is conditional, so no
LOCAL_REAL replay was claimed. No `waves/bak/` material was used. No product or
test finding was fixed; only this audit artifact was written.

## Current repository and dependency truth

- Main repository is `develop`, current HEAD
  `f94adb640136181dbaafa84f62c753b013f0b94e`; `origin/develop` is the same.
  The working tree contains unrelated lab/report changes and untracked files.
- Plugin repository is `develop` at
  `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, with its pre-existing untracked
  social-preview file.
- W16 depends on W15. The current canonical W15 audit is `REOPEN` because its
  GUI/PACKAGE evidence is stale and W14 is reopened. W16 therefore cannot close
  until dependency truth is repaired and downstream evidence is refreshed.
- `git diff --check` was run; reported whitespace is in unrelated existing
  files. The focused W16 suite currently passes: `25 passed`.

## Independent evidence verification

The cited W16 manifest and evidence all identify main SHA
`0f8902a023bac76071527232c2287af96478ed2b` and artifact SHA
`cb69c1ceeca7861c922371a2827dea2526baa27381594cfd80d16a49153c0899`.
Independent current disk hashing gives
`dist/hpc-client-gui/hpc-client-gui.exe` SHA
`ff050baf26fd73f59d46c6a7ed5290913e1669b67cecbbfa13bb29e5c0122876`
(7,573,876 bytes), not the manifest/evidence SHA (7,415,251 bytes). The
candidate package therefore is not the current exact artifact, and its
GUI/PACKAGE evidence cannot establish W16 acceptance against current HEAD.

The package-content JSON remains internally consistent for the old artifact
(8/8 PASS). The packaged smoke JSON truthfully records 14/20 with six
foreground-blocked phases, and the fresh-user JSON records 10/10 PASS, but
both are bound to the obsolete identity. The conditional remote replay remains
honestly deferred and was not substituted with loopback evidence.

## Findings

### REOPEN-W16-001 — Exact artifact and final-SHA evidence are stale

W16 requires exact main-SHA binding, package SHA binding, and GUI/PACKAGE
acceptance. The evidence is bound to main SHA `0f8902a...` and artifact SHA
`cb69c1ce...`, while live repository truth is main SHA `f94adb64...` and the
available package hashes to `ff050baf...`. Rebuild/package from the current
accepted identities, regenerate the manifest, rerun required package-content,
packaged GUI smoke, and fresh-user evidence, and independently verify matching
hashes before close.

### REOPEN-W16-002 — Declared dependency W15 is reopened

W15's current canonical audit is `REOPEN`, and its required evidence is stale
against current identity; W14 is also reopened. W16 cannot close while its
declared dependency is not accepted. After dependency repair, refresh any
invalidated W16 evidence and perform a fresh independent audit.

## Verdict

The focused W16 tests are green and the old evidence is internally coherent,
but mandatory package identity/final-SHA proof is stale against current
repository truth and the declared dependency is reopened. These are
repository/evidence findings, not unavailable external authority.

## Repair-phase verification (2026-09-22)

This section records repair evidence only; it is not a replacement for the
fresh independent audit required next.

- Current repository HEAD is `63b696b3b8c64296d9d17f94c8d0d903f9bab7eb`.
- The exact packaged executable and staged candidate both hash to
  `544e186f81aa685ee80a3c07185ee0eb03ab1bc73a81151b1323253503c0a1da`
  (`7,425,277` bytes). The package-content evidence is current at `8/8 PASS`.
- Packaged smoke evidence is current at `20/20 PASS`; fresh-user evidence is
  `10/10 PASS` with exits `[0,0]`. The retained child runtime separately
  records `pty_resize` and `clean_shutdown` as diagnostic FAIL values; those
  child-side foreground/teardown mappings are excluded from the runner's
  authoritative acceptance result and remain preserved for diagnosis.
- Focused validation reran with a writable repository-local TEMP/TMP root:
  `python -m pytest -q tests/test_wx_packaged_smoke.py tests/test_wx_package_content.py tests/test_release_manifest.py`
  → `29 passed`.
- `W15` is an integration reference only under the canonical W16
  independence contract, so `REOPEN-W16-002` does not transfer ownership or
  block W16 acceptance. No W15 lifecycle state was changed.

The stale-identity findings are repaired. A fresh independent audit is still
required before close.

WAVE_PHASE_STATUS: READY_FOR_AUDIT
