Review the bounded DS-20A diff in the sibling worktree D:/Projeler/TrubaGUI-worktrees/wave20-ds20a.

Scope: that worktree's src/truba_gui/config/storage.py and tests/test_config_storage_atomic.py.
Goal: atomic same-directory config replacement with flush/fsync, cleanup on failure, and preservation of the previous file.
Forbidden: remote or cluster actions, release/version work, unrelated refactors, and edits.

Check correctness, resource cleanup, platform behavior, test quality, and scope. Do not edit files. Report concrete findings with severity and file/symbol references, or state no findings.
