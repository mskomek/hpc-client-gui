# Wiki source

This directory is the **source of truth** for the GitHub Wiki of
[`mskomek/hpc-client-gui`](https://github.com/mskomek/hpc-client-gui).

- Pages are reviewed like code and mirrored to `hpc-client-gui.wiki.git` by
  `scripts/sync_wiki.py`.
- **Do not edit pages on github.com.** Wiki-side edits are overwritten by the
  next sync.
- GitHub wiki pages are flat: the filename is the page title. Use
  `Page-Name.md` for English and `Page-Name-TR.md` for the Turkish mirror.
  `Home.md`, `_Sidebar.md`, and `_Footer.md` are reserved names.
- Product behavior is canonical in `src/hpc_gui/docs/` and `README.md`. A wiki
  page may summarize and cross-link that content; it may not introduce a
  behavioral claim no canonical doc, source file, or observed command output
  supports.
- `scripts/check_wiki.py` enforces link resolution, EN/TR parity, sidebar
  completeness, and forbidden terms in CI.
