from __future__ import annotations

import sys
import base64
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

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


@pytest.mark.release
@pytest.mark.regression
def test_signing_cleans_keychain_without_echoing_secrets(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(signing.os.sys, "platform", "darwin")
    monkeypatch.setattr(signing.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(signing.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("MACOS_SIGNING_IDENTITY", raising=False)
    app = tmp_path / "HPC Client GUI.app"
    app.mkdir()
    dmg = tmp_path / "app.dmg"
    dmg.write_bytes(b"test")
    secret = "TEST_SIGNING_PASSWORD_MUST_NOT_BE_PRINTED"
    values = {
        "MACOS_CERTIFICATE_P12_BASE64": base64.b64encode(b"certificate").decode("ascii"),
        "MACOS_CERTIFICATE_PASSWORD": secret,
        "APPLE_TEAM_ID": "team",
        "APPLE_NOTARY_KEY_ID": "key",
        "APPLE_NOTARY_ISSUER_ID": "issuer",
        "APPLE_NOTARY_PRIVATE_KEY_BASE64": base64.b64encode(b"private key").decode("ascii"),
    }
    monkeypatch.setattr(signing, "_required", lambda name: values[name])
    run = mock.Mock(return_value=SimpleNamespace(stdout=""))
    monkeypatch.setattr(signing, "_run", run)
    cleanup = mock.Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(signing.subprocess, "run", cleanup)

    result = signing.main(
        [
            "--app", str(app), "--dmg", str(dmg),
            "--entitlements", str(tmp_path / "entitlements.plist"),
            "--arch", "x86_64",
        ]
    )

    output = capsys.readouterr()
    create = next(
        call.args[0]
        for call in run.call_args_list
        if call.args[0][:2] == ["security", "create-keychain"]
    )
    assert result == 1
    cleanup.assert_called_once()
    delete = cleanup.call_args.args[0]
    assert delete[:2] == ["security", "delete-keychain"]
    assert delete[2] == create[-1]
    assert secret not in output.out + output.err
