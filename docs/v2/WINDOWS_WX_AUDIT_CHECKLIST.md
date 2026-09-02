# Windows wx UX and Packaging Audit

Automated checks cover importability, the shared geometry matrix, file URL
payload construction, and Ctrl+C terminal interrupt semantics. On this machine
the wx smoke uses wxPython 4.3.1 under Python 3.12.

Before a packaged release, manually verify on Windows:

- 1366×768 at 100%, 150%, and 200%; mixed 100%/150% monitor move and monitor removal;
- keyboard focus after resize; menu accelerators; Explorer file URL clipboard and drag/drop;
- terminal Ctrl+C interrupt versus Ctrl+Shift+C copy, resize PTY dimensions, clear/find;
- optional VcXsrv/plink absence and cleanup; updater signature verification/cancel;
- packaged ANSYS allowlist install, open-tool disclosure, lint, and broken-tool isolation;
- taskbar/tray availability and graceful shutdown while connection, transfer, job follow,
  ANSYS, and updater operations are active.

The wx shell remains optional and makes no Qt parity claim. Qt WebEngine GPU
settings are legacy-only and are not passed to wx. No credentials, remote
paths, or diagnostic content are included in geometry or audit output.
