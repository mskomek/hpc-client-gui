## v1.1.12
- Startup: added a branded splash screen and ensured the application icon is used
  consistently for the window and taskbar.
- CLI: added commands for diagnostics, connection profiles, and file operations,
  while preserving normal GUI startup when no command is supplied.
- FTP: added configurable transfer mode, encoding, timeout, passive-mode, and
  keep-alive settings; transfer errors now provide clearer guidance for
  ASCII-mode files that are not valid UTF-8 text.
- Transfers: added queue and connection controls in the Directories view, along
  with safer cancellation, cleanup, and status reporting for SSH and FTP work.
- Jobs & outputs: added detachable output views, adjustable refresh/follow
  behavior, and improved scroll handling for live output.
- Release quality: expanded FTP stress coverage and added build/startup smoke
  checks before release artifacts are packaged.
