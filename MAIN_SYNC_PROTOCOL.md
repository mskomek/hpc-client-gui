# Main Sync Protocol

`main` and the development line (`codex/develop`) are reconciled with a real
Git merge, not path copying. The historical root-path copy procedure is
superseded; its exclusion rules survive as the published-tree boundary below.

## Reconciliation flow (develop → main)

1. Fetch tags and confirm `origin/main`; back up both branches
   (`codex/develop-backup-<date>`, `main-backup-<short>`).
2. Trial-merge `main` into `codex/develop` in a throwaway worktree with
   `--no-commit` to inventory conflicts, then abort.
3. Perform the merge on `codex/develop`, resolving semantically:
   - packaging/release infrastructure follows `main`;
   - application code/tests follow the validated development line;
   - workflows, metadata, and docs combine both.
4. Run full gates: compileall, i18n gate, Ruff, release-surface check, and the
   complete offline test suite.
5. Move local `main` to the merged result (`git branch -f main codex/develop`),
   verify gates on `main`, then return to `codex/development` work.

## Published-tree boundary (Always excluded)

Before treating a tree as `main`, the following stay **untracked**
(`git rm -r --cached`); local copies remain on disk:

- `.agent-runs/`, `tools/`, `devtools/` (except `performance_probe.py`,
  which tests load), `waves/`
- `AGENTS.md` and `CLAUDE.md`: these two are **never synced to `main` and
  never pushed**; they exist only as local working copies
- internal process documents under root `docs/` (delegation reports, wave
  plans/audits, publication kit)

Public user documentation under `docs/` (wiki, assets, CLI docs,
verification/validation guides) remains tracked.

Never add these paths to `.gitignore` exceptions or re-track them for `main`.

## Release gate

For a release: update version + changelog first, run the release checks, commit
on the development line, re-run the reconciliation above so `main` contains it,
and only then push.

## Push boundary

- GitHub (`origin`) carries exactly one branch: `main`. Never push anything
  else; delete stray remote branches if one appears.
- Pushing is a separate, explicitly approved action — never part of an
  implementation wave or reconciliation session.
