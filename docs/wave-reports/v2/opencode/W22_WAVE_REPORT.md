# W22 — Terminal and connection acceptance replay — Wave Report

```text
Wave: W22
Canonical report: docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
Branch: develop
HEAD: 0f8902a023bac76071527232c2287af96478ed2b
Working tree: dirty; unrelated and stacked changes preserved
Decision: BLOCKED
```

## Authority and scope

Resumed only from `waves/pending/W22.md` and
`opencode/prompts/40_RESUME_WAVE.md`. Read CORE rules, registry rows
`HPC-W05-LIFE-031..065`, the empty W22 TODO set, and all three named sections
of `opencode/sources/WAVE_V2_FINAL_05.md`. No `waves/bak/` material was used.

## Diagnosis and owning remediation cycle

Diagnosis: the previous exact-package failure was not a product write failure.
The packaged diagnostic proved 36 characters crossed the WebView bridge and
SSH transport, but the disposable PTY fixture only framed LF and therefore
never executed the WebView's CR submit. That caused terminal readback and all
dependent package checks to time out.

Remediation: updated the owning disposable SSH/PTY fixture to apply the
standard PTY CR-to-LF line-discipline conversion and added a wire regression
asserting that CR submit produces real shell readback. This is a meaningful
owning repair, not an identical rerun.

## Focused validation and evidence

- `python -m pytest -q tests/test_terminal_pty_wire.py tests/test_ssh_terminal_stream.py`
  -> `7 passed`.
- Focused W20/W21/WebView/package/PTY selection -> `67 passed`.
  Evidence: `build/audit/w22-focused-tests-current.txt`, SHA-256
  `96991E7294D918F235B0FBF56BC352FBDA9ADACB5C3CEE205E4743DBD4B42395`.
- `git diff --check` passed; pre-existing line-ending warnings only.
- Rebuilt the exact onedir artifact and reran the packaged smoke. Artifact
  SHA-256: `ff050baf26fd73f59d46c6a7ed5290913e1669b67cecbbfa13bb29e5c0122876`.
  `build/audit/w22-packaged-smoke-current.json` is `PASS`: all required
  terminal, PTY, round-trip, surface, queue, and clean-shutdown checks pass.

## Remaining blocker and routing

`EXTERNAL` remains `EXTERNAL_BLOCKED`: no authorized real-target connection
matrix or real SSH-shell run is available in this environment. The disposable
loopback package evidence is not substituted for that required evidence.
The package/runtime blocker is closed; `HPC-W05-LIFE-063` and
`HPC-W05-LIFE-064` have current loopback/package evidence, but the external
gate and consequently `HPC-W05-LIFE-065` remain open. No cross-Wave defect was
absorbed; no next Wave was started.

WAVE_PHASE_STATUS: BLOCKED
