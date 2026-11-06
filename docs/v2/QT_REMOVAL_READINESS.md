# Qt Removal Readiness

Qt removal is a hard, evidence-backed gate. It is `GO` only when every
mandatory P0 parity row is `COVERED`, production AST import/dependency and
packaging scans are empty, the authoritative default runtime is `wx`, and
both packaged wx smoke and manual parity results are `PASS` for Windows,
Linux, and macOS. Every evidence file must be schema-valid and contain the
full SHA of the current `HEAD`.

Run:

```text
python scripts/qt_removal_gate.py
```

Exit code `0` means `GO`; any non-zero exit means `NO-GO`. Use `--output` to
write the versioned JSON report without dirtying the tree by default.

The following are not evidence: a test plan, a Markdown file existing on
disk, an import-only smoke test, a failed/empty evidence file, or a PASS from
only one platform. Packaged evidence and manual evidence are separate
requirements, and Windows PASS never implies Linux or macOS PASS.

The report's Qt inventory is generated from the same AST import records used
for the decision; counts are not fixed invariants. Current readiness remains
`NO-GO` until the actual wx migration and platform evidence are complete.

## Reproducibility policy

Source, dependency, and packaging inventories are generated only from
Git-tracked authoritative files. Ignored and untracked local files do not
affect the removal gate. Gate-relevant tracked changes relative to `HEAD`
cause `NO-GO`, including source code, parity documents, dependency manifests,
production `.spec` files, and `scripts/qt_removal_gate.py`; this keeps evidence
tied to the committed revision.

A tracked production Python file or packaging spec that cannot be read or
parsed is a hard `NO-GO`. The gate never silently skips an unreadable or
unparseable tracked file.

`Qt dependency records` counts occurrences across authoritative dependency
files. `Qt dependency unique packages` counts unique normalized package names.
`Qt packaging blocker references` counts active Qt references, while `Qt
packaging blocker files` counts the unique spec files containing them.

Evidence rules are strict: a test plan is not test evidence, file existence is
not `PASS`, import smoke is not packaged GUI smoke, Windows `PASS` is not
Linux/macOS `PASS`, and evidence from another SHA is not current evidence.

## 2026-11-06 legacy split

Qt code moved to `legacy/qt/` (untracked, ignored via `.gitignore`) at base `3d74ee3c`. The archive preserves `src/hpc_gui/ui/`, `src/hpc_gui/app.py`, Qt plugin pages, `services/x11_runner.py`, `services/terminal_bridge.py`, Qt-only tests and `scripts/capture_current_gui_qt.py` / `scripts/generate_qt_lgpl_sources.py` (see `legacy/qt/README.md`). Packaged and manual platform evidence (Windows/Linux/macOS `wx-packaged-smoke` and `wx-manual-parity`) is still required by the gate; Qt removal readiness remains `NO-GO` until that evidence is supplied.
