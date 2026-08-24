from __future__ import annotations

import sys
import types

import pytest

from hpc_gui.core import secret_store


def test_macos_keychain_uses_opaque_reference(monkeypatch):
    entries: dict[tuple[str, str], str] = {}
    fake = types.SimpleNamespace(
        get_keyring=lambda: object(),
        set_password=lambda service, user, value: entries.__setitem__((service, user), value),
        get_password=lambda service, user: entries.get((service, user)),
        delete_password=lambda service, user: entries.pop((service, user), None),
    )
    monkeypatch.setitem(sys.modules, "keyring", fake)
    monkeypatch.setattr(secret_store.sys, "platform", "darwin")

    reference = secret_store.protect_keychain_secret("s3cret")

    assert reference and reference != "s3cret"
    assert entries[(secret_store.KEYCHAIN_SERVICE, reference)] == "s3cret"
    assert secret_store.unprotect_keychain_secret(reference) == "s3cret"
    secret_store.delete_keychain_secret(reference)
    assert (secret_store.KEYCHAIN_SERVICE, reference) not in entries
    with pytest.raises(RuntimeError, match="unavailable"):
        secret_store.unprotect_keychain_secret(reference)


def test_keychain_is_unavailable_outside_macos(monkeypatch):
    monkeypatch.setattr(secret_store.sys, "platform", "win32")
    assert secret_store.keychain_available() is False
