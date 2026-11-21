# Independent integration split audit (transcribed)

- Auditor: read-only subagent `audit_integration_split`.
- Severity: **HIGH — OPEN**. `c26fcac1cea56e37bd2683c73b11a5a5240be984` is one mixed 105-file commit (2,136 insertions / 448 deletions) directly after A/PR67; independent B/D/C branches do not exist.

## Hunk ownership

- `src/hpc_gui/wx_shell_frame.py`: `create_shell_frame().mount_terminal()` and output activation are B; `bind_notebook_native_repaint()` and accelerator lifetime references are D.
- `src/hpc_gui/wx_shell_events.py`: native repaint binding is D.
- `src/hpc_gui/ssh/client.py`: X11 shell construction/delegation, connect metadata, and session stop are C composition; keep out of protocol-only A.
- `src/hpc_gui/ssh/contracts.py`: `SSHConnInfo.x11_trusted` is C's public session/profile contract.
- `tests/test_linux_x11.py`: C; preserve an explicit X11Runner no-display preflight integration assertion during extraction.
- `tests/test_security_hardening_wave.py`: local VcXsrv `-auth`/no-`-ac` policy is C's local display authentication path.
- B owns WebView terminal/lifecycle/diagnostics and related W20/W21/WebView tests. D owns `tests/conftest.py` Qt-before-wx test collection ordering, repaint/accelerator changes, and repaint regressions. Unrelated FTP/plugin/jobs/wave edits in c26 lack an X11 ownership rationale and must be sent to their actual owners.
- C owns profile trust selection through `SSHConnInfo`, X11 shell controller, runner, X-server manager/firewall, and GUI login wiring.

## Dependency blockers

1. Current A head `339b86b...` lacks the `trusted`/fake-cookie behavior and `core/xauthority.py` API expected by c26/C. Update and verify A before constructing C; keep GUI composition in C.
2. `src/hpc_gui/ssh/shell_session.py` imports `X11Unavailable` from the higher-level `ssh/x11_shell.py`; move the exception into a lower-level SSH contract/errors module to preserve dependency direction.
3. B and D can be extracted independently; C depends on A and B. The one-commit mixed history, unrelated edits, exact hunk ownership and missing per-branch test/CI prevent claiming independent PR readiness.

No source edits, commits, GitHub writes, or tests were performed by the auditor.
