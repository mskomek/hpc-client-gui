# Wave 25 — Licensing Transition for v1.2.0

Status: waiting
Owner: Codex
Priority: P0
Execution: sequential, one prompt invocation
DeepSeek model: opencode-go/deepseek-v4-flash
Timeouts: analyze 20m, implement 30m, review 20m

## Goal

Prepare the next release, v1.2.0, for the PolyForm Noncommercial License
1.0.0, with a separate commercial licensing path. Free personal, academic,
educational, public-research, and other permitted non-commercial use must stay
easy. Commercial embedding, incorporation, OEM/bundling, redistribution as a
commercial product, and proprietary commercial derivatives require a separate
commercial license from the copyright holder.

Use this copyright holder text everywhere new or updated project copyright
metadata is required:

`Copyright © 2026 Mehmed Sinan KÖMEK`

Do not retain an alternate short username as the project copyright author.

## Historical boundary

Previous releases were distributed under the MIT License. Starting with
v1.2.0, the new licensing model applies only to the new release and subsequent
releases where legally applicable. Do not claim that the transition revokes
MIT rights already granted for previously distributed copies. Preserve all
tags, commits, branches, and Git history.

## Evidence

- Current project license is MIT in `LICENSE`.
- Current application/package version is 1.1.21; v1.2.0 is the proposed
  licensing boundary.
- README has a minimal license/contributions section and already states that
  the project is not an official TRUBA product.
- Both project `pyproject.toml` files lack explicit license metadata.
- Windows PyInstaller packaging does not currently include the project license
  documents in the released application bundle.
- Visible Git history has one apparent human contributor represented by more
  than one commit identity; ownership should be confirmed before release.
- Direct dependencies retain their own licenses and notices; packaging must
  preserve those obligations.

## Packets

### DS-25A — Licensing and ownership implementation audit (Audit)

- Reconfirm every license, copyright, author, SPDX, README, metadata,
  packaging, workflow, release-note, source-header, dependency, and vendored
  source reference.
- Reconfirm contributor identity evidence without reading secrets or rewriting
  history.
- Map exact files that must change for v1.2.0 and identify any unresolved
  ownership or dependency-license blocker.

Allowed: read-only repository, local Git, package metadata, and existing
release configuration. Forbidden: edits, commits, pushes, release creation,
release deletion, asset deletion, credential access, and real cluster actions.

### DS-25B — License and documentation transition (Medium)

- Replace the project license for v1.2.0 onward with the unmodified,
  publicly documented PolyForm Noncommercial License 1.0.0 text.
- Add `COMMERCIAL_LICENSE.md` without inventing prices, contractual terms, or
  affiliation with TRUBA, TÜBİTAK, ANSYS, or any other organization.
- Add a plain-language README Licensing section separating permitted free use
  from COMMERCIAL LICENSE REQUIRED use.
- State the historical MIT boundary exactly and keep the independent-project
  statement.
- Update applicable project metadata, source headers, documentation, badges,
  and release documentation to use only
  `Mehmed Sinan KÖMEK` as the project copyright author.

Allowed: license/docs/metadata/release files and narrowly required packaging
definitions. Forbidden: application behavior changes, dependency-license
changes, Git-history rewrites, release/tag/asset operations, and new custom
license wording when the established license text covers the case.

### DS-25C — Versioned packaging and release notes (Small)

- Bump all authoritative version references to v1.2.0 consistently.
- Ensure `LICENSE`, `COMMERCIAL_LICENSE.md`, and required third-party notices
  are included in source and Windows distribution packages.
- Add a clearly visible `Licensing Change` section to the v1.2.0 changelog.
- Keep old release packages and tags untouched.

Allowed: version metadata, changelog, release scripts/workflow, and packaging
specifications. Forbidden: publishing a release, deleting assets, or changing
application functionality.

### DS-25D — Verification and stale-reference review (Small)

- Run the existing tests, compile/import checks, configured lint/static checks,
  packaging checks, and application startup smoke check.
- Search the entire repository for stale MIT/license/copyright/SPDX/OSI
  references and classify intentional historical references separately.
- Verify dependency licenses were not changed and new license files are in
  distribution artifacts.
- Run `git diff --check` and inspect `git status --short`.
- Produce an explicit list of old GitHub releases/assets that could be removed
  later; perform no destructive GitHub action.

Allowed: local/offline checks and read-only GitHub release inspection.
Forbidden: weakening tests, live SSH/Slurm/transfer operations, publishing,
deleting, or rewriting history.

## Exit Gate

v1.2.0 documentation, metadata, source headers, release notes, and packages
consistently identify PolyForm Noncommercial 1.0.0 and
`Mehmed Sinan KÖMEK`; historical MIT rights are described accurately; third-
party notices remain intact; tests and packaging checks pass; and no GitHub
release, tag, asset, branch, commit, or history was deleted or rewritten.

## Blockers requiring user/legal decision

- Copyright ownership cannot be confirmed for every contributor.
- A dependency or bundled binary imposes an obligation not satisfied by the
  planned package notices.
- The requested free-use boundary would require custom exceptions not supplied
  by the established license.

## Deferred

Commercial pricing, contract terms, legal enforcement strategy, old-release
asset deletion, tag deletion, branch deletion, commit rewriting, and any push,
release publication, or deployment require separate explicit approval.

## Completion Notes

- Completed at:
- Packet verdicts:
- Files changed:
- Tests and exit codes:
- Old releases/assets retained:
- Remaining uncertainty:

## On Completion

Codex reports the complete local diff and verification results. Stop before
commit, push, release publication, or destructive GitHub actions.
