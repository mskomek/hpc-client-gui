# S3 Product Repair Audit

Verdict: **KEEP**

## Scope reviewed

Reviewed the frozen common repair in `src/hpc_gui/wx_shell_smoke_session.py`, `src/hpc_gui/wx_shell_fresh_smoke.py`, and `src/hpc_gui/wx_shell_connections.py`, plus the W19 connection completion path in `src/hpc_gui/wx_connection.py`. No native GUI tests were run and no timing changes were made.

## Findings

- **Worker-safe transport creation:** `_create_packaged_smoke_session` now only reads environment/configuration, creates the SSH wrapper and service backends, and connects the SSH transport. It does not read or mutate wx widgets/session state or call the shell callback graph. During creation the output subscriber list is empty, so the shell output callback has no widget callback to invoke.
- **No wx side effects remain on the worker path:** the fresh-user flow passes this creator as the connection panel's `connect` callback. `ConnectSelected` runs that callback on its worker, then `wx_connection.py` posts `done` with `wx.CallAfter`. The connection controller's `finish`, `on_connected`, shell status update, panel rebinding, and terminal SSH binding therefore run in the GUI completion callback.
- **Attach once:** the fresh-user flow supplies exactly one `on_connected` callback, which invokes `_attach_packaged_smoke_session`. The W19 completion path invokes `on_connected` once after a successful controller finish. The compatibility composition helper also attaches once for direct GUI-thread callers; no production fresh-user call site uses that composition now.
- **Cleanup once:** cleanup registration now occurs in the shared shell `on_connected` callback, once per successful attach, with `worker_safe=True`. The previous extra `lifecycle.register_cleanup(ssh.close)` in the packaged smoke helper is gone. Stale or canceled connection attempts are closed by the controller completion path before `on_connected`, so they are not registered as active-session cleanup.
- **Stale generation and reconnect/disconnect:** the existing connection attempt tag check still rejects superseded completion and closes its returned session. Cancellation similarly closes before attach. Successful attach uses the existing shell callback to set session and increment generation; disconnect continues to clear session and increment generation. No generation or disconnect policy was changed by the patch.
- **Status import:** importing `_update_shell_status_text` from `wx_shell_window_support` in `wx_shell_connections.py` resolves the callback's dependency at module scope. This is the intended utility and does not alter connection policy.
- **Product scope:** only the fresh-user smoke connection seam changes from a combined connect-and-attach callback to separate transport creation and GUI-thread attachment. The normal product connection callback path is unchanged.

## W19 lifecycle assessment

The repair makes the shell's existing attach/rebind work execute on the GUI thread. That can make a shell terminal's existing `set_ssh`/WebView interactions occur in their intended thread and may make W19 exercise the real GUI lifecycle more consistently. This is not evidence of a product lifecycle regression: it is the expected correction of thread affinity. It does, however, make the suspected broad-interpreter test partition/lifecycle contamination plausible and strengthens the case for evaluating W19 process isolation independently. No timing or product lifecycle workaround is justified by the evidence reviewed here.

## Decision

Keep the common repair unchanged. I found no certain correctness defect requiring a follow-up patch. Validate W19 partitioning and native ownership in the supervisor's serialized gates.
