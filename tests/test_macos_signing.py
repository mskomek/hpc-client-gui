from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sign_macos_release as signing


def test_signing_requires_darwin_before_secret_access(monkeypatch, tmp_path):
    monkeypatch.setattr(signing.os.sys, "platform", "win32")
    with mock.patch.object(signing, "_required") as required:
        try:
            signing.sign_and_notarize(tmp_path / "HPC Client GUI.app", tmp_path / "app.dmg", tmp_path / "entitlements.plist", "x86_64")
        except signing.SigningError as exc:
            assert "Darwin" in str(exc)
        else:
            raise AssertionError("signing unexpectedly succeeded")
    required.assert_not_called()


def test_signing_source_has_cleanup_and_no_secret_echo():
    text = Path(signing.__file__).read_text(encoding="utf-8")
    assert "delete-keychain" in text
    assert "MACOS_CERTIFICATE_P12_BASE64" in text
    assert "certificate_password" not in text.split("print(", 1)[-1]
