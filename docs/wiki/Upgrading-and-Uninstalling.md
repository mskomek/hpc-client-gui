# Upgrading and Uninstalling

> Türkçe: [[Upgrading-and-Uninstalling-TR]]

## Where your data lives

Everything the application stores locally is under `~/.truba_slurm_gui`
(`C:\Users\<you>\.truba_slurm_gui` on Windows). The directory name is legacy
and is deliberately retained so existing installations keep working.

Typical contents:

| Entry | What it holds |
|---|---|
| `config.json` | Application configuration and connection profiles |
| `language.json` | The selected interface language |
| `known_hosts` | Host keys you chose to trust and save |
| `app.log`, `app.log.1`, … | The rotating application log |
| `crash.log` | The crash reporter's record |
| `history.json`, `history.jsonl` | Command and job history |
| `processes.json` | Tracked helper processes |
| `downloads` | Downloaded files |
| `third_party` | Optional helpers fetched with your approval |

Upgrades keep this directory; it is not versioned per release.

## Upgrading

**Windows portable ZIP** — download the new ZIP, extract it to a new folder,
and run `hpc-client-gui.exe` from there. Delete the old folder once you are
satisfied. Your profiles and settings are untouched because they live outside
the application folder.

**Linux AppImage** — download the new AppImage, verify its `.sha256`, make it
executable, and replace the old file.

**Linux `.deb`** — install the newer package over the old one:

```bash
sudo apt install ./hpc-client-gui_1.2.6_amd64.deb
```

**From source** — pull the new revision and reinstall in the same virtual
environment:

```bash
pip install -e .[test]
```

## Downgrading

Downgrading is done the same way as upgrading: run the older artifact. Because
configuration is shared across versions, an older build may not understand
settings written by a newer one. If an older version misbehaves after a
downgrade, move `~/.truba_slurm_gui/config.json` aside and let the application
recreate it.

## Uninstalling

1. Remove the application:
   - Windows portable ZIP: delete the extracted folder.
   - Linux AppImage: delete the AppImage file.
   - Linux `.deb`: `sudo apt remove hpc-client-gui`.
   - From source: delete the virtual environment and the checkout.
2. Optionally remove your data by deleting `~/.truba_slurm_gui`.

Deleting that directory removes your saved profiles, trusted host keys, logs,
and history. Copy anything you want to keep first.

## See also

[[Installation on Windows|Installation-Windows]] ·
[[Installation on Linux|Installation-Linux]] ·
[[Data and Privacy|Data-and-Privacy]]
