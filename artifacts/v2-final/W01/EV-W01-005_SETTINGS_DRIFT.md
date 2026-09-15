# EV-W01-005 — Settings Drift List

**Pinned SHA:** `afd4fb1d6ed3d0bbd87b9b6db6115eb159f63a87`
**Generated:** 2026-09-15

---

## Settings Drift Classification

### Orphan Settings (persisted but unused by current UI)

| Setting Key | Storage Location | Drift Evidence | Recommendation |
|---|---|---|---|
| `transfer_parallelism` (global) | `config.json > settings` | Legacy global key; per-profile value is now authoritative via `coerce_profile_transfer_parallelism()` | MIGRATE-OR-DEPRECATE: Remove global key or add migration to profile scope |
| `focus_jobs_outputs_after_submission_enabled` | `config.json > settings` | Read-only migration source in `get_sbatch_follow_mode()`; no UI reads it | DEPRECATE: Already migrated to `sbatch_follow_mode` |

### Ghost Controls (visible but not meaningfully wired)

| Control | File:Line | Drift Evidence | Resolution |
|---|---|---|---|
| Quick Tour menu item | `wx_shell.py:131` (BEFORE fix) | Menu item created but dispatched to `pass` | FIXED by FIX-W01-001: removed |

### Hidden Capabilities (implemented but not exposed in UI)

| Capability | Location | Notes |
|---|---|---|
| `transfer_completion_action` | `config/storage.py` | Valid values: none, notification, attention, play_sound, close_once, run_command, close, reboot_once, shutdown_once, suspend_once. No direct UI control. | 
| `last_seen_changelog_version` | `config/storage.py` | Controls startup changelog display. No direct UI control. |
| `master_password_dpapi` | `config/storage.py` | Encrypted credential storage. Auto-managed, no UI. |

### UI Preferences Drift

| Setting | Location | Notes |
|---|---|---|
| `ui.show_welcome` | `config.json > ui` | Welcome dialog on startup. Wired in `app.py`. |
| `ui.show_tour` | `config.json > ui` | Quick tour display. Wired in `quick_tour.py` (Qt only). wx Quick Tour removed by FIX-W01-001. |

---

## WxSettingsModel Key Mapping

The wx settings model uses simplified key names that map to underlying storage keys:

| WxSettingsModel Key | Underlying Storage Key | Section |
|---|---|---|
| `remote_directory_cache` | `remote_directory_cache_enabled` | GLOBAL_KEYS |
| `transfer_checksum` | `transfer_checksum_verification_enabled` | GLOBAL_KEYS |
| `jobs_outputs_refresh_interval` | `jobs_outputs_refresh_interval_seconds` | GLOBAL_KEYS |
| `shortcut_preferences` | `shortcut_preferences` | GLOBAL_KEYS |
| `transfer_parallelism` | `transfer_parallelism` (per-profile) | PROFILE_KEYS |
| `ssh_timeout` | `ssh_timeout` (per-profile) | PROFILE_KEYS |
| `keepalive_interval_seconds` | `keepalive_interval_seconds` (per-profile) | PROFILE_KEYS |
| `x11_enabled` | `x11_enabled` (per-profile) | PROFILE_KEYS |

### Legacy Ignored Keys (never loaded by wx)

| Key | Notes |
|---|---|
| `terminal_graphics_auto_compatibility` | Qt-era setting, no wx equivalent |
| `qt_webengine_gpu` | Qt-era setting, no wx equivalent |
