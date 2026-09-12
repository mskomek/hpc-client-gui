# Packet K: Reporting and E2E ownership

This review separates composed user workflows, report/evidence validation,
release metadata generation, and real artifact execution. Marker changes are
classification only; no tests were removed or renamed.

| File / owner | Classification | Evidence boundary |
| --- | --- | --- |
| `tests/test_plugin_e2e.py::test_full_clean_user_lifecycle` | `e2e`, `acceptance` | One temporary app-data lifecycle crosses injected registry fetch, plugin installation and storage, template loading, lint execution, version activation, and failed-update rollback. It does not claim GUI or live-cluster coverage. |
| `tests/test_gui_audit_screenshots.py` | `reporting` | Validates screenshot manifest fields, file presence, PNG bytes, hashes, duplicate rules, and required pairs. It does not capture or compare a live GUI. The manifest/HEAD mismatch still skips the current-commit assertion as historical evidence. |
| `tests/test_reproducibility_bundle.py` | `reporting` | Validates a locally generated ZIP report, schema, optional environment contents, and redaction. It does not test a packaged runtime. |
| `tests/test_capability_report.py::CapabilityReportTests` | `reporting` | Exercises serialized capability status/summary reporting, not the underlying external capabilities. |
| `tests/test_release_manifest.py` | `release` | Generates release metadata from temporary fixture files and checks inventory, platform/format labels, hashes, and secret-free output. No real release artifact is validated. |
| `tests/test_wave79_audit.py` | `contract` for parser/schema/provider compatibility; `unit` for parser-error formatting and `RawCommandResult`; per-node `contract`/`unit` for the mixed Wave 78 class | Parser input/output shapes and profile compatibility are contracts. Error formatting and raw-result value behavior are isolated units. |
| `tests/test_wave79_provider_contract.py` | `contract` for registries, parser formats, schema, provider declarations, and backward compatibility; `unit` for error formatting and raw-result values; `integration` for the production Jobs callback wiring | The callback owner traverses the declared adapter into the production callback with a fake backend, so it crosses real production components but not a cluster. |
| `tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages` | `runtime_smoke`, `artifact_dependent`, `packaging` | Calls the real packaged-artifact runner, which executes the discovered artifact and reads its runtime-owned report. It is not a report-only unit test. No artifact exists in the runner's three discovery locations in this worktree, so this node would fail for missing evidence. |

The packaged-smoke test was deliberately not executed. With no discovered
artifact, the runner would return failure and write to its default
`build/audit/wx-packaged-smoke-windows.json`, overwriting the existing
artifact-owned Windows report. The existing report remains `FAIL`; GUI-TERM-001
remains `PARTIAL`. This review creates no new packaged-runtime evidence.

The screenshot tests validate existing report contents only. Their success,
including any historical-evidence skip, does not count as runtime GUI evidence.
Likewise, the reproducibility and capability-report tests do not grant runtime
coverage. The plugin lifecycle is the only reviewed true composed E2E owner.

No nodes were added, removed, or renamed in Packet K. The marker changes are
checked against collected pytest markers and the Packet C ratchet.
