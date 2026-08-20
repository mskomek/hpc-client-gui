# Publishing this wiki

Operational note for maintainers. This file is **not** mirrored to the wiki.

## One-time setup

The GitHub wiki does not exist as a git repository until it is enabled and its
first page is created:

1. Repository → **Settings** → **Features** → enable **Wikis**.
2. Open the **Wiki** tab and create the first page (any content — the sync
   overwrites it).

Until then `hpc-client-gui.wiki.git` returns "Repository not found" and
`scripts/sync_wiki.py` stops with an explanatory message.

## Convention

Wiki pages are **generated** from `docs/wiki/` and reviewed like code. Do not
edit pages on github.com — the next sync overwrites them. `Home.md`, the
sidebar, and the footer all state this so readers who arrive on the wiki know
where to send a correction.

## Syncing

```bash
python scripts/sync_wiki.py              # dry run: prints the plan, writes nothing
python scripts/sync_wiki.py --publish    # applies the plan and pushes
```

The script:

- refuses to run when `scripts/check_wiki.py` reports any problem;
- refuses to mirror anything matching an excluded path or credential pattern
  (`waves/`, `.agent-runs/`, `.env`, key material, `known_hosts`, and similar);
- excludes `docs/wiki/README.md` and this file from the mirror;
- prints an exact add/update/delete plan before doing anything;
- **defaults to dry run**. Publication requires `--publish` and an inspected
  plan.

It stores no credentials; pushing uses whatever git credential helper the
machine already has.

## After publishing

Spot-check on github.com that `Home`, `_Sidebar`, one deep English page, one
deep Turkish page, and one image all render.

## Not automated

CI does not publish the wiki. `check_wiki.py` gates the source in the `docs`
job, but mirroring stays a deliberate, manual step.
