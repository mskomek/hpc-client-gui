Implement DS-20A only in the supplied clean worktree.

Goal: make config/storage.py save_config write JSON through a same-directory temporary file, flush and fsync it, then replace the destination atomically; failed writes must clean up the temporary file and preserve the previous destination.

In scope: src/truba_gui/config/storage.py and one focused regression test file under tests/.
Forbidden: remote or cluster actions, release/version work, unrelated refactors, changing existing user-facing behavior beyond atomic persistence, and edits outside the two in-scope areas.

Acceptance:
- preserve the existing JSON format and encoding;
- use standard-library APIs and same-directory replacement;
- cover successful replacement and failure preservation/temporary cleanup with a narrow test;
- run the narrow test and report exact files and commands.
