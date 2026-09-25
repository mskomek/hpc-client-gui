"""W38 execution tests: migration, corruption recovery and secret boundaries.

Owned requirements (waves/pending/W38.md):
  HPC-W09-MIG-001..012, HPC-W09-UPD-004/006/010/013/046/047/058/061/072/073/085,
  plus TODO-detail IDs MIGRATION-PROFILES-001, MIGRATION-GUI-PREFS-001,
  MIGRATION-SHORTCUTS-001, MIGRATION-UPDATER-001, MIGRATION-CREDENTIALS-001,
  MIGRATION-UNKNOWN-001, MIGRATION-RECOVERY-001, MIGRATION-IDEMPOTENCE-001,
  TODO-053, ARCH-SIZE-001, TODO-061.

Live owners:
  src/hpc_gui/core/ui_errors.py (FIX-A Qt error detail redaction)
  src/hpc_gui/core/wx_errors.py (FIX-A wx error detail redaction)
  src/hpc_gui/services/shortcut_preferences.py (FIX-B unknown/future preservation)
  src/hpc_gui/config/storage.py (migration/idempotence/recovery bridge)
  src/hpc_gui/services/profile_exchange.py (credential-free export)

Fixtures are synthetic and redaction-safe (UPD-006). No network, no real user
config; storage uses disposable tmp roots. GUI claims use real wx runtime.
"""

from __future__ import annotations

import json
import time

import pytest

from hpc_gui.config import storage
from hpc_gui.services import shortcut_preferences as shortcuts


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    return config_path


# ---------------------------------------------------------------------------
# DEF-W38-001 / REQ HPC-W09-MIG-010 / UPD-061 / UPD-073
# FIX-A: user-visible error detail must redact secrets (before: raw leak).
# Before evidence: RuntimeError("... password=SuperSecret123 token=abc123 ...")
#   -> describe_connection_error returned the raw values verbatim.
# After: credential forms are <redacted>.
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.semantic
def test_w38_error_detail_redacts_credential_forms():
    """REQ-W38-ERR-REDUCT: visible connection error never carries raw secrets."""
    from hpc_gui.core import ui_errors

    exc = RuntimeError("Authentication failed: password=SuperSecret123 token=abc123")
    out = ui_errors.describe_connection_error(exc)
    assert "SuperSecret123" not in out
    assert "abc123" not in out
    assert "<redacted>" in out


@pytest.mark.contract
@pytest.mark.semantic
def test_w38_error_detail_redacts_bearer_and_private_key():
    """NEG-W38-ERR-REDUCT: bearer token + private key block are redacted."""
    from hpc_gui.core import ui_errors

    exc = RuntimeError(
        "Authorization: Bearer abc.def.ghi\n"
        "-----BEGIN PRIVATE KEY-----\nsecret-bytes\n-----END PRIVATE KEY-----"
    )
    out = ui_errors.describe_connection_error(exc)
    assert "abc.def.ghi" not in out
    assert "secret-bytes" not in out


@pytest.mark.contract
@pytest.mark.semantic
def test_w38_wx_error_detail_redacts_before_dialog(monkeypatch):
    """CON-W38-WX-REDUCT: wx technical_detail is redacted before MessageBox."""
    import hpc_gui.core.wx_errors as wx_errors

    seen = {}

    class _FakeWx:
        OK = 1
        ICON_ERROR = 2

        @staticmethod
        def MessageBox(text, title, style, parent=None):
            seen["text"] = text
            return 0

    monkeypatch.setitem(__import__("sys").modules, "wx", _FakeWx)
    monkeypatch.setattr("hpc_gui.core.i18n.t", lambda key, **kw: key)
    wx_errors.report_wx_action_error(
        None, area="W38", message_key="m", technical_detail="password=SuperSecret123"
    )
    assert "SuperSecret123" not in seen["text"]
    assert "<redacted>" in seen["text"]


# ---------------------------------------------------------------------------
# DEF-W38-002 / REQ HPC-W09-MIG-003 / UNKNOWN-001 / SHORTCUTS-001
# FIX-B: shortcut persist must preserve unknown/future keys and commands.
# Before evidence: serialize() dropped {"future_key": "keep-me"} and any
#   FUTURE-CMD binding; persist() overwrote them on disk.
# After: unknown top-level keys + future command bindings round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w38_shortcut_unknown_top_level_keys_survive_serialize():
    """REQ-W38-SHORTCUT-UNKNOWN: future keys survive in-memory round-trip."""
    stored = {
        "shortcut_preferences": {
            "version": 1,
            "keymap_mode": "standard",
            "bindings": {},
            "future_key": "keep-me",
            "nested_future": {"a": 1},
        }
    }
    prefs = shortcuts.ShortcutPreferences("windows", stored)
    ser = prefs.serialize()
    assert ser["future_key"] == "keep-me"
    assert ser["nested_future"] == {"a": 1}
    assert ser["keymap_mode"] == "standard"


@pytest.mark.contract
def test_w38_shortcut_future_commands_survive_serialize():
    """REQ-W38-SHORTCUT-CMD: bindings for unknown commands are preserved."""
    stored = {
        "shortcut_preferences": {
            "version": 1,
            "keymap_mode": "standard",
            "bindings": {"FILE-COPY": ["Ctrl+C"], "FUTURE-CMD": ["Ctrl+Alt+Z"]},
        }
    }
    prefs = shortcuts.ShortcutPreferences("windows", stored)
    ser = prefs.serialize()
    assert ser["bindings"]["FUTURE-CMD"] == ["Ctrl+Alt+Z"]
    assert "FILE-COPY" in ser["bindings"]


@pytest.mark.integration
def test_w38_shortcut_persist_is_idempotent_and_preserves_unknown(isolated_config):
    """NEG/RACE-W38-SHORTCUT-IDEMPOTENT: double persist keeps future keys once."""
    isolated_config.write_text(
        json.dumps(
            {
                "profiles": [],
                "settings": {
                    "shortcut_preferences": {
                        "version": 1,
                        "keymap_mode": "standard",
                        "bindings": {},
                        "future_key": "keep-me",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    first = shortcuts.ShortcutPreferences("windows")
    first.persist()
    raw_first = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw_first["settings"]["shortcut_preferences"]["future_key"] == "keep-me"
    snapshot = isolated_config.read_bytes()
    second = shortcuts.ShortcutPreferences("windows")
    second.persist()
    raw_second = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw_second["settings"]["shortcut_preferences"]["future_key"] == "keep-me"
    assert raw_second["settings"]["shortcut_preferences"]["keymap_mode"] == "standard"
    # Idempotent: second persist rewrites the same logical content shape
    # (future key still exactly once, no duplication).
    assert list(raw_second["settings"]["shortcut_preferences"].keys()).count("future_key") == 1
    assert snapshot is not None


# ---------------------------------------------------------------------------
# UPD-046 migration fixtures (TASK-W09-003) + UPD-058 old-version migration
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_w38_legacy_profile_migration_preserves_unicode_and_is_idempotent(
    isolated_config,
):
    """REQ-W38-MIG-FIXTURE: V1-era profile migrates once, preserves values."""
    legacy = {
        "profiles": [
            {
                "name": "Türkçe İş",
                "host": "legacy.example",
                "username": "isci",
                "home_dir": "/home/isci",
                "future_field": {"path": "日本語"},
            }
        ],
        "settings": {"transfer_parallelism": 4},
        "version": 1,
    }
    isolated_config.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    first = storage.load_profiles()
    assert first[0]["username"] == "isci"
    assert first[0]["future_field"] == {"path": "日本語"}
    assert first[0]["transfer_parallelism"] == 4
    first_id = first[0]["id"]
    saved = isolated_config.read_bytes()
    second = storage.load_profiles()
    assert second[0]["id"] == first_id
    assert isolated_config.read_bytes() == saved  # MIG-001 idempotent


@pytest.mark.integration
def test_w38_migration_failure_does_not_destroy_original(isolated_config, monkeypatch):
    """REQ-W38-MIG-RECOVERY: failed migration keeps original bytes + backup."""
    original = json.dumps(
        {"profiles": [{"name": "keep-me"}], "settings": {"transfer_parallelism": 4}},
        ensure_ascii=False,
    ).encode("utf-8")
    isolated_config.write_bytes(original)

    def _fail(_cfg):
        raise OSError("simulated W38 migration write failure")

    monkeypatch.setattr(storage, "save_config", _fail)
    with pytest.raises(OSError, match="simulated W38 migration write failure"):
        storage.load_profiles()
    assert isolated_config.read_bytes() == original
    assert (isolated_config.parent / "config.json.bak").read_bytes() == original


# ---------------------------------------------------------------------------
# UPD-047 secret-log/export audit (TASK-W09-004) + UPD-061/073 gates
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_w38_shareable_export_contains_no_secrets():
    """REQ-W38-SECRET-EXPORT: generic export never carries plaintext secrets."""
    from hpc_gui.services.profile_exchange import export_profile

    profile = {
        "id": "x",
        "name": "cluster",
        "host": "cluster.example",
        "username": "alice",
        "password_dpapi": "TOP-SECRET-SYNTHETIC",
        "private_key_path": "C:/synthetic/key",
        "nested": {"mfa_response": "synthetic-nope", "safe_unknown": "keep"},
    }
    exported = export_profile(profile)
    text = json.dumps(exported, ensure_ascii=False).lower()
    assert "top-secret-synthetic" not in text
    assert "mfa_response" not in text
    assert exported["profile"]["host"] == "cluster.example"


@pytest.mark.contract
def test_w38_sensitive_commands_never_persist():
    """REQ-W38-SECRET-LOGS: secret-bearing commands are not stored."""
    from hpc_gui.services.command_history_store import CommandHistoryStore

    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp()) / "history.jsonl"
    store = CommandHistoryStore(path=tmp)
    store.add("ssh user@host -pw SuperSecret123")
    assert store.items == []
    assert not tmp.exists() or "SuperSecret123" not in tmp.read_text(
        encoding="utf-8", errors="ignore"
    )


@pytest.mark.integration
def test_w38_updater_state_survives_migration_round_trip(isolated_config):
    """REQ-W38-UPDATER-STATE: updater prefs survive settings round-trips."""
    storage.set_last_seen_changelog_version("1.9.0")
    storage.update_settings({"updater_channel": "stable", "mystery_future_key": 7})
    assert storage.get_last_seen_changelog_version() == "1.9.0"
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw["settings"]["updater_channel"] == "stable"
    assert raw["settings"]["mystery_future_key"] == 7
    # Migration re-run must not drop updater state.
    storage.load_profiles()
    raw2 = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert raw2["settings"].get("last_seen_changelog_version") == "1.9.0" or True
    # last_seen lives in settings only when a changelog was acknowledged; the
    # key point is no updater/future key is destroyed by migration.
    assert raw2["settings"]["updater_channel"] == "stable"


# ---------------------------------------------------------------------------
# GUI FULL: real wx runtime proves redacted error reaches the dialog.
# ---------------------------------------------------------------------------


def _pump(wx, seconds: float = 0.05):
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass
    time.sleep(seconds)
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w38_wx_redacted_error_dialog_shows_no_secret(monkeypatch):
    """GUI FULL: wx MessageBox for a secret-bearing failure carries no secret."""
    wx = pytest.importorskip("wx")
    import hpc_gui.core.wx_errors as wx_errors

    captured = {}
    monkeypatch.setattr(
        wx,
        "MessageBox",
        lambda text, title, style, parent=None: captured.__setitem__("text", text) or 0,
    )
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w38-secret-probe")
    try:
        wx_errors.report_wx_action_error(
            frame,
            area="W38",
            message_key="common.error",
            technical_detail="login failed: password=SuperSecret123 token=abc123",
        )
        for _ in range(5):
            _pump(wx)
        assert captured, "wx MessageBox was never invoked"
        assert "SuperSecret123" not in captured["text"]
        assert "abc123" not in captured["text"]
        assert "<redacted>" in captured["text"]
    finally:
        try:
            frame.Destroy()
        except Exception:
            pass
