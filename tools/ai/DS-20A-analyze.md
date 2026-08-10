Analyze DS-20A only. Goal: map the smallest safe implementation for atomic config writes.

In scope: src/truba_gui/config/storage.py and existing focused tests under tests/.
Forbidden: remote or cluster actions, release/version work, unrelated refactors, and edits to the primary worktree.

Acceptance: identify existing test conventions, the exact save_config failure/preservation cases to cover, and any path/temporary-file edge cases. Do not edit files. Report concrete file and symbol names.
