"""W43 — restart-safe install, exact-package validation, signing policy.

Owned requirements: HPC-W09-UPD-039..043, 053..055, 068, 069, 079..081,
086..088, HPC-W09-PKGUPD-001..002, HPC-W09-TODO-058.

Mock boundaries (legitimate only): synthetic UpdateRelease fixtures,
tmp-dir archives, stubbed ``_request`` for the safe test channel,
``wx.MessageBox``/``CallAfter`` inline where a live dialog is driven, and
the dialog's ``unsaved_probe``/``confirm_fn`` hooks (the seam under test).
No product behavior under test is replaced: verification still runs the
real ``verify_artifact``/``verify_signed_metadata`` path and install still
runs the real ``_start_install`` guard.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.services import app_updater, update_restart_policy as policy
from hpc_gui.services.update_restart_policy import (
    count_unsaved,
    deferral_message,
    handoff_payload,
    restart_mode,
    should_defer_install,
    verify_post_update_version,
    windows_signing_policy,
)
from hpc_gui.services.update_verification import (
    UpdateVerificationError,
    verify_artifact,
)

wx = pytest.importorskip("wx")


@pytest.fixture(autouse=True)
def _clean_providers():
    policy.clear_unsaved_providers()
    yield
    policy.clear_unsaved_providers()


def _doc(dirty: bool):
    return SimpleNamespace(dirty=dirty)


# --- UPD-039..043 / UPD-053 restart semantics (unit) ------------------------


def test_restart_is_user_confirmed_not_automatic():
    assert restart_mode() == "user-confirmed"


def test_clean_state_does_not_defer():
    assert count_unsaved([_doc(False), _doc(False)]) == 0
    assert should_defer_install([_doc(False)]) is False
    assert should_defer_install([]) is False
    assert should_defer_install(None) is False


def test_dirty_state_defers_install():
    docs = [_doc(False), _doc(True), _doc(True)]
    assert count_unsaved(docs) == 2
    assert should_defer_install(docs) is True


def test_deferral_message_names_count_and_later():
    text = deferral_message(2)
    assert "2" in text
    assert "Later" in text
    assert "never install silently" in text


def test_post_update_version_confirmed_by_exact_equality():
    assert verify_post_update_version("1.9.0", "1.9.0") is True
    assert verify_post_update_version("1.9.0 ", "1.9.0") is True
    assert verify_post_update_version("1.8.0", "1.9.0") is False
    assert verify_post_update_version("", "1.9.0") is False


def test_provider_registry_aggregates_counts():
    policy.register_unsaved_provider(lambda: 2)
    policy.register_unsaved_provider(lambda: 0)
    assert policy.get_unsaved_count() == 2


# --- UPD-068 runtime: dialog defers with dirty editor, installs when clean -


def _ready_dialog(monkeypatch, *, unsaved: int, confirm: bool | None):
    from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_READY_TO_INSTALL

    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    app = wx.App.Get() or wx.App(False)
    parent = wx.Frame(None, title="w43-parent")
    release = app_updater.UpdateRelease(
        version="1.9.0",
        tag="v1.9.0",
        zip_name="hpc-client-gui_windows_onedir.zip",
        zip_url="https://example.invalid/x.zip",
        sha_name="x.sha256",
        sha_url="https://example.invalid/x.sha256",
        html_url="https://example.invalid",
        install_strategy="windows-portable",
        body="notes",
        size=10,
    )
    dlg = WxUpdateDialog(parent, release)
    dlg._build_for_state(STATE_READY_TO_INSTALL)
    dlg._zip_path = Path("C:/fake/update.zip")
    dlg._artifact_verified = True
    dlg.unsaved_probe = lambda: unsaved
    calls = {}

    def _confirm(count):
        calls["count"] = count
        return bool(confirm)

    dlg.confirm_fn = _confirm
    return app, parent, dlg, calls


def test_ready_install_defers_when_dirty_and_user_declines(monkeypatch):
    app, parent, dlg, calls = _ready_dialog(monkeypatch, unsaved=2, confirm=False)
    try:
        dlg._start_install()
        assert dlg._install_deferred_due_to_unsaved is True
        assert calls["count"] == 2
        # Still in READY with the verified artifact retained (safe shutdown
        # can retry after saving); nothing was installed or discarded.
        from hpc_gui.wx_updater_view import STATE_READY_TO_INSTALL

        assert dlg.state == STATE_READY_TO_INSTALL
        assert dlg._zip_path is not None
        assert dlg._artifact_verified is True
    finally:
        dlg.Destroy()
        parent.Destroy()


def test_ready_install_proceeds_when_dirty_but_user_confirms(monkeypatch):
    import hpc_gui.wx_updater_view as view

    app, parent, dlg, calls = _ready_dialog(monkeypatch, unsaved=1, confirm=True)
    splashes = {"n": 0}

    class _Splash:
        def Show(self):
            splashes["n"] += 1

        def Destroy(self):
            pass

    monkeypatch.setattr(view, "show_installing_splash", lambda *a, **k: _Splash())

    import threading

    class _InlineThread:
        def __init__(self, target=None, daemon=None, **kwargs):
            self._target = target

        def start(self):
            # Do not run the installer worker (would call launch_update_installer);
            # the guard decision is what this test pins: confirmation recorded
            # and the dialog closed for install instead of deferred.
            splashes["started"] = True

    monkeypatch.setattr(threading, "Thread", _InlineThread)
    try:
        dlg._start_install()
        assert dlg._install_deferred_due_to_unsaved is False
        assert dlg._install_confirmed_with_unsaved == 1
        assert splashes["n"] == 1
    finally:
        dlg.Destroy()
        parent.Destroy()


def test_ready_install_with_clean_state_needs_no_confirm(monkeypatch):
    import hpc_gui.wx_updater_view as view

    app, parent, dlg, calls = _ready_dialog(monkeypatch, unsaved=0, confirm=None)
    splashes = {"n": 0}

    class _Splash:
        def Show(self):
            splashes["n"] += 1

        def Destroy(self):
            pass

    monkeypatch.setattr(view, "show_installing_splash", lambda *a, **k: _Splash())

    import threading

    class _InlineThread:
        def __init__(self, target=None, daemon=None, **kwargs):
            self._target = target

        def start(self):
            pass

    monkeypatch.setattr(threading, "Thread", _InlineThread)

    def _fail_confirm(_count):
        raise AssertionError("no confirm prompt expected when clean")

    dlg.confirm_fn = _fail_confirm
    try:
        dlg._start_install()
        assert dlg._install_deferred_due_to_unsaved is False
        assert "count" not in calls
        assert splashes["n"] == 1
    finally:
        dlg.Destroy()
        parent.Destroy()


def test_ready_dialog_states_restart_requirement(monkeypatch):
    from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_READY_TO_INSTALL

    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    app = wx.App.Get() or wx.App(False)
    parent = wx.Frame(None, title="w43-label")
    release = app_updater.UpdateRelease(
        version="1.9.0",
        tag="v1.9.0",
        zip_name="a.zip",
        zip_url="https://example.invalid",
        sha_name="a.sha",
        sha_url="https://example.invalid",
        html_url="https://example.invalid",
        body="n",
        size=5,
    )
    dlg = WxUpdateDialog(parent, release)
    try:
        dlg._build_for_state(STATE_READY_TO_INSTALL)
        labels = []

        def _collect(win):
            try:
                children = win.GetChildren()
            except Exception:
                return
            for child in children:
                try:
                    labels.append(child.GetLabel())
                except Exception:
                    pass
                _collect(child)

        _collect(dlg.panel)
        from hpc_gui.core.i18n import t as _t

        _expected = _t("updates.restart_required")
        if _expected == "[updates.restart_required]":
            _expected = "The application must restart to install the update."
        _norm = lambda s: str(s or "").strip().casefold()
        assert any(
            _norm(text) == _norm(_expected)
            or "restart" in _norm(text)
            or "yeniden ba" in _norm(text)
            for text in labels
        )
    finally:
        dlg.Destroy()
        parent.Destroy()


# --- PKGUPD-001 exact artifact / PKGUPD-002 same production path ------------


def test_exact_artifact_sha256_bound(tmp_path: Path):
    payload = b"w43-exact-package-bytes"
    package = tmp_path / "hpc-client-gui_windows_onedir.zip"
    package.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    artifact = {
        "platform": "windows",
        "architecture": "x86_64",
        "file": "hpc-client-gui_windows_onedir.zip",
        "url": "https://github.com/x/y.zip",
        "kind": "windows-portable",
        "size": len(payload),
        "sha256": digest,
    }
    verify_artifact(package, artifact)  # exact artifact passes
    package.write_bytes(payload + b"!")
    with pytest.raises(UpdateVerificationError):
        verify_artifact(package, artifact)  # any byte change invalidates


def test_safe_test_channel_uses_production_verification_path(monkeypatch, tmp_path: Path):
    """A mock endpoint still exercises download_and_verify_release fully."""
    payload = b"w43-channel-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    artifact = {
        "platform": "windows",
        "architecture": "x86_64",
        "file": "hpc-client-gui_windows_onedir.zip",
        "url": "https://github.com/x/y.zip",
        "kind": "windows-portable",
        "size": len(payload),
        "sha256": digest,
    }
    release = app_updater.UpdateRelease(
        version="9.9.9",
        tag="v9.9.9",
        zip_name="hpc-client-gui_windows_onedir.zip",
        zip_url="https://github.com/x/y.zip",
        sha_name="y.sha256",
        sha_url="https://github.com/x/y.sha256",
        html_url="https://example.invalid",
        install_strategy="windows-portable",
        body="",
        size=len(payload),
        signed_artifact=artifact,
    )

    class _Response:
        headers = {"Content-Length": str(len(payload))}

        def __init__(self):
            self._chunks = [payload]
            self._url = "https://github.com/x/y.zip"

        def read(self, _size):
            return self._chunks.pop(0) if self._chunks else b""

        def geturl(self):
            return self._url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(app_updater, "_request", lambda *_a, **_k: _Response())
    monkeypatch.setattr(app_updater, "app_data_dir", lambda: tmp_path)
    result = app_updater.download_and_verify_release(release)
    assert result.exists()
    assert hashlib.sha256(result.read_bytes()).hexdigest() == digest


def test_installer_refuses_unverified_exact_artifact(tmp_path: Path, monkeypatch):
    package = tmp_path / "update.zip"
    package.write_bytes(b"unverified")
    monkeypatch.setattr(app_updater, "is_frozen_exe", lambda: True)
    with pytest.raises(RuntimeError, match="authenticated verification"):
        app_updater.launch_update_installer(package, "1.9.0", "windows-portable")


# --- UPD-087 rollback preserves known-good path ------------------------------


def test_windows_script_preserves_known_good_and_rolls_back():
    script = app_updater.build_update_script(
        zip_path=Path("C:/updates/v1.9.0/pkg.zip"),
        install_dir=Path("C:/app"),
        current_exe=Path("C:/app/hpc-client-gui.exe"),
        new_version="1.9.0",
        process_id=1234,
    )
    assert "_internal.backup" in script
    assert "hpc-client-gui.exe.backup" in script
    assert "Rollback" in script or "rollback" in script.lower()
    assert "update-install.log" in script


# --- TODO-058 Authenticode policy / UPD-088 handoff ---------------------------


def test_windows_signing_policy_is_unsigned_with_documented_wording():
    pol = windows_signing_policy()
    assert pol["status"] == "unsigned"
    assert pol["authenticode_enabled"] is False
    doc = Path(pol["policy_doc"])
    assert doc.exists()
    text = doc.read_text(encoding="utf-8", errors="replace")
    assert "Authenticode signing is **not enabled yet**" in text
    # No product code may claim a signed Windows build.
    import pathlib

    hits = []
    for path in pathlib.Path("src/hpc_gui").rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="replace")
        lowered = content.lower()
        if "windows" in lowered and "signed" in lowered and "unsigned" not in lowered:
            if "authenticode" in lowered or "signed-notarized" in lowered:
                hits.append(str(path))
    assert hits == []


def test_handoff_payload_carries_required_fields():
    payload = handoff_payload(
        settings_schema_version="7",
        migration_coverage=["v6->v7 theme keys", "updater verification fixtures"],
        verification_evidence="tests/test_w43_restart_package_policy.py 17 passed",
        packaging_requirements="exact ZIP + SHA-256 + signed UPDATE_METADATA.json; unsigned Windows per VERIFYING_RELEASES §5",
    )
    assert payload["settings_schema_version"] == "7"
    assert len(payload["migration_coverage"]) == 2
    assert "SHA-256" in payload["packaging_requirements"]
