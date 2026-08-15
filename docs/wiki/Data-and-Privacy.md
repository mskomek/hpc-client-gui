# Data and Privacy

> Türkçe: [[Data-and-Privacy-TR]]

The application is client-side. It does not phone home, and nothing leaves your
machine unless you take an action that sends it.

## What is stored locally

Everything lives under `~/.truba_slurm_gui`:

| File | Contents |
|---|---|
| `config.json` | Connection profiles (hostname, username, port, key path) and protected password material |
| `known_hosts` | Host keys you chose to trust and save |
| `app.log` (+ rotations) | The application log, unredacted for local debugging |
| `crash.log` | The crash reporter's record |
| `history.json`, `history.jsonl` | Command and job history |
| `last_batch.json` | The most recent batch submission record |
| `processes.json` | Tracked helper processes |
| `transfer_journal.jsonl` | Transfer state used to resume interrupted transfers |
| `language.json` | The selected interface language |
| `downloads` | Files you downloaded |
| `third_party` | Optional helpers fetched with your approval |

Removing the directory removes all of it. See
[[Upgrading and Uninstalling|Upgrading-and-Uninstalling]].

## What can leave the machine

Exactly three things, all initiated by you:

1. **Your own transfers and commands** — the files you upload or download and
   the commands you run on the cluster.
2. **A diagnostic bundle** you export from the send-logs dialog.
3. **Log text you copy** to the clipboard from that dialog.

Optional X11 helpers (plink, VcXsrv) are downloaded only after you approve the
download.

## What a diagnostic bundle contains

The bundle includes `app.log`, the history files, `last_batch.json`,
`processes.json`, `transfer_journal.jsonl`, the VcXsrv output logs,
`language.json`, and a small `manifest.json` with the generation timestamp.

It **excludes `config.json`** by design, so your saved profiles and encrypted
password material do not travel with it.

## What redaction replaces

Before a text file is written into the bundle it is passed through redaction,
which substitutes:

- your local account name → `<user>`
- every saved profile's remote username → `<user>`
- every saved profile's hostname or IP → `<host>`

The substitution recognizes these values inside paths and URLs, so
`/scratch/yourname/data` becomes `/scratch/<user>/data`. Values shorter than
three characters are left alone, because replacing them would corrupt
unrelated text. Longer names are substituted first so overlapping names do not
leave partial matches behind.

## Limits of redaction, stated plainly

Redaction is best-effort. It only knows about your local account name and the
profiles you have saved. It will not catch:

- a hostname or username that appears in log text but was never saved as a
  profile,
- identifiers inside your own job output or scripts,
- project, allocation, or job identifiers,
- content inside files that could not be read as text and were therefore
  included unchanged.

**Read the bundle before you share it.** It is a ZIP of plain-text files; open
it and look. If it contains something you do not want public, attach it through
a private channel instead — see `SECURITY.md` and
[[Security Model|Security-Model]].

## See also

[[Crash Reports and Send Logs|Crash-Reports-and-Send-Logs]] ·
[[Logs and Diagnostics|Logs-and-Diagnostics]] ·
[[Security Model|Security-Model]]
