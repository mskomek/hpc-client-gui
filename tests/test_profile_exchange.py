import pytest

from hpc_gui.services.profile_exchange import (
    FORMAT,
    VERSION,
    export_profile,
    import_profile,
    preview_profile_import,
)


PROFILE = {
    "id": "old",
    "name": "cluster",
    "host": "cluster.example",
    "username": "alice",
    "account": "proj",
    "password_dpapi": "secret",
    "private_key_path": "C:/key",
    "nested": {"mfa_response": "nope", "safe_unknown": "keep"},
}


def test_shareable_export_contains_no_secrets_or_personal_fields():
    exported = export_profile(PROFILE)
    text = str(exported).lower()
    assert "alice" not in text and "secret" not in text and "private_key" not in text
    assert exported["profile"]["host"] == PROFILE["host"]


def test_personal_mode_keeps_allowed_identity_but_not_credentials():
    profile = export_profile(PROFILE, mode="personal")["profile"]
    assert profile["username"] == "alice"
    assert profile["account"] == "proj"
    assert "password_dpapi" not in str(profile).lower()
    assert "mfa_response" not in str(profile).lower()


def test_preview_and_explicit_import_generate_new_id_and_preserve_unknown():
    payload = export_profile(PROFILE, mode="personal")
    preview = preview_profile_import(payload)
    assert preview.profile["id"] != PROFILE["id"]
    assert preview.profile["nested"]["safe_unknown"] == "keep"
    saved = []
    import_profile(payload, saved.append)
    assert saved[0]["id"] != PROFILE["id"]


def test_invalid_schema_and_cancelled_preview_do_not_write():
    with pytest.raises(ValueError):
        preview_profile_import({"format": FORMAT, "version": VERSION + 1})
    assert import_profile
