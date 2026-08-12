# Wave 20 — Config, Version, and Release Consistency

Status: waiting
Owner: Codex
Priority: P1
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Prevent torn settings and mismatched release metadata with the smallest
possible number of authoritative sources.

## Evidence

- `config/storage.py:save_config()` writes directly to `config.json`.
- `src/truba_gui/__init__.py`, `src/truba_gui/pyproject.toml`, and changelog
  headings currently expose different version values.
- The release workflow already accepts a version and packages under the
  canonical versioned directory.

## Packets

### DS-20A — Atomic config writes (Small)

- Write the serialized config to a same-directory temporary file, flush and
  fsync it, then use `os.replace()`.
- Clean up failed temporary writes without deleting the previous config.
- Add a narrow test for replacement and failure preservation.

### DS-20B — Single version source (Small)

- Choose one repository-owned version source after inspecting packaging and
  release consumers; derive or validate the other views from it.
- Correct the currently inconsistent values without rewriting historical notes.
- Add a source-tree consistency check.

### DS-20C — Release consistency gate (Medium)

- Verify tag/input version, package version, `__version__`, changelog section,
  release folder, and required help files before publishing.
- Keep the existing release output layout and block mismatches early.

Allowed: `config/storage.py`, packaging metadata, release scripts/workflow,
focused tests, and release docs/checklist. Forbidden: credentials, deployment,
publication, or loose release artifacts.

## Exit gate

Interrupted config writes preserve the last valid file, version values agree,
and release packaging refuses inconsistent metadata before publication.
