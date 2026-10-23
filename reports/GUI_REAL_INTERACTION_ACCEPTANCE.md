# GUI Real Interaction Acceptance

Date: 2026-10-23

## Result

Status: PARTIAL / NOT_RUN for the requested operating-system-level drag-and-drop and cross-session layout workflows.

Current-source Journal Studio model, parser, and large-file regression coverage passed. The 10,000+ line performance test passed 6/6; the current implementation pauses visual block materialization after 10,000 lines while preserving source text. This is automated test evidence, not Explorer/File Manager drag-and-drop acceptance.

The following real GUI interactions were not evidenced on the current source commit:

- Explorer drag-and-drop of one or several .jou files, wrong-target drop, cancel, and unsaved-document prompts.
- Command Library to Visual Flow drag-and-drop.
- Persist panel size, selected tab, source view, scroll position, and layout across a new process.
- Plugin disable/update with an open document.
- Disk-full, abrupt shutdown, corrupt Scheme, and live SFTP disconnect in the GUI.

The full app pytest process also encountered a wxWidgets native class-unregistration access violation during a separate broad run. The focused editor-flow test passed in isolation. The failure is recorded in the regression report and was not hidden or converted to a pass.

No current-source interactive GUI result should be inferred from historical Windows11 frozen-GUI evidence.
