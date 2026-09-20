# W18 Audit Report

```text
Wave: W18
Audit cycle: 1
Decision: PASS
Auditor: GPT-5.6 Luna (openai/gpt-5.6-luna), reasoning medium
Date: 2026-09-20
```

## Authority and dependency

Fresh-context audit re-read `opencode/protocol/CORE_EXECUTION_RULES.md`, the
sole executable `waves/pending/W18.md`, all 16 mandatory W18 registry/index
rows, the zero-row W18 TODO ownership result, and Workstreams 0.1 and 0.2 of
`opencode/sources/WAVE_V2_FINAL_05.md`. `waves/bak/` was not used. W17
predecessor truth is `W17_AUDIT_REPORT.md` cycle 3, Decision PASS, with no later
REOPEN/BLOCKED evidence found.

## Identity and working tree

- Branch: `develop`
- HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
- `origin/develop`: same SHA
- Plugin: `develop`, `f0abb7e7037e66ab451d463c699fecf4e00c89eb`
- Working tree is dirty with preserved unrelated W01/W15/W17 and other
  changes; no reset, clean, destructive operation, or push was performed.
- `git diff --check` exited 0. This audit writes only this canonical audit
  report.

## Re-verification

The canonical W18 report, GUI evidence, and external matrix were read in full.
The GUI log records 14/14 passed and exit 0, including wrong-password,
missing-key, changed-key, unknown-host YES/NO/CANCEL, cancellation-safe state,
and no-secret-echo cases. The external log records E1-E8 PASS, cleanup PASS,
and no secret values. Its real hpclab identity/healthy-before-and-after claim
is consistent with the recorded matrix; no package claim is required by W18.

Live source review confirmed:

- password, configured key/certificate, agent/home-key discovery, and
  provider-gated keyboard-interactive paths remain wired through the shared SSH
  transport;
- `accept-new` prompts and persists only on save, `once` does not persist,
  reject raises, and strict mode uses Paramiko `RejectPolicy`;
- `BadHostKeyException` becomes a hard `HostKeyChangedError`;
- `HostKeyRequest.key_type` is populated from the offered transport key and is
  rendered with host, fingerprint, and role;
- wx failures use the shared classifier and cancellation is deferred after the
  controller repaint, avoiding a false success/ambiguous failure state;
- no secret is included in `SSHConnInfo` repr or the reviewed evidence, and
  the evidence/test scan found no actual password, token, or key material.

The W18 test file has meaningful assertions, no skip/xfail, and mocks only
transport/dialog boundaries as documented. The fresh focused rerun passed:

```text
python -m pytest tests/test_w18_auth_hostkey.py -v -p no:randomly
14 passed in 0.53s

python -m pytest tests/test_w18_auth_hostkey.py tests/test_ssh_credential_flow.py tests/test_optional_ssh_credentials.py tests/test_connection_controller.py -q
48 passed, 9 subtests passed in 1.46s
```

The canonical report's before-evidence and fault-injection sensitivity claims
were checked against its recorded FIX-W18-001/FIX-W18-002 traces; the live
post-fix tests are green. The implementation diff is limited to the reported
wx mapping/cancel and host-key type plumbing (plus the reported controller
support), with W17-owned pre-existing hunks retained. No silent host-key
mismatch acceptance, test weakening, fabricated PASS, or in-scope unresolved
finding was identified. The W19-owned mid-connect-cancel and worker-thread
modal observations are correctly routed out of W18.

## Verdict

**PASS.** All 16 mandatory W18 requirements have live implementation traces,
current GUI and real external evidence, clean focused verification, and no
owned blocking defect. W19 must not be started automatically; its dependency
checks remain required when explicitly planned.
