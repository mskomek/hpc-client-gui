# Wave 17 — Transfer Integrity and Streaming

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Make large-file mode handling and completion semantics safe without changing
the existing transfer API or adding file chunking.

## Evidence

- `services/transfer_mode.py` materializes the whole source for ASCII upload.
- Download validation uses `Path.read_bytes()[:8192]`, which reads the whole
  destination before slicing.
- `.dat` is currently classified as text in Auto mode.
- Transfers write directly to the final destination, so a partial file can look
  complete.

## Packets

### DS-17A — Bounded mode detection and streaming ASCII conversion (Medium)

- Keep Auto, Binary, and explicit ASCII semantics.
- Remove whole-file reads from classification and ASCII conversion.
- Treat `.dat` as Binary in Auto mode unless explicit ASCII is requested.
- Reject detected binary content in explicit ASCII mode.
- Add focused tests for large-file spies, line endings, UTF-8 errors, and `.dat`.

Allowed: `src/truba_gui/services/transfer_mode.py` and narrow transfer tests.
Forbidden: new dependencies, chunking, GUI changes, live operations.

### DS-17B — Atomic partial-file completion (Medium)

- Download to `<destination>.part`, then replace the final path only after
  successful validation and completion.
- Upload through a temporary remote name where the existing backend supports a
  safe rename, retaining the current fallback behavior when it does not.
- Preserve cancellation, retry, conflict, resume, and progress semantics.
- Test that failed transfers leave the final path untouched.

Allowed: existing transfer services/backends and focused tests.
Forbidden: persistence changes, new transfer abstractions, live operations.

### DS-17C — Safer optional verification (Small)

- Preserve SHA-256 verification but make the verification choice explicit and
  optional at the existing call boundary.
- Do not add a second full read when size-only verification is selected.
- Keep resume decisions loss-averse; do not infer identity from size alone when
  the current flow has no trustworthy source metadata.

Allowed: existing transfer service and focused tests only.
Forbidden: a new settings system or a mandatory checksum pass.

## Exit gate

Large files are not materialized solely for classification, incomplete files do
not appear finalized, Auto mode is conservative for `.dat`, and existing fake
transfer tests remain green.

## Deferred

File splitting, FileZilla benchmark infrastructure, and a new transfer protocol
remain out of scope until measurements prove they are needed.

## Validation

`$env:PYTHONPATH = "src"; python -m pytest tests/test_local_transfer_gate.py tests/test_ftp_widget.py -q`,
`python scripts/check_i18n.py`, `git diff --check`, and `git status --short`.
