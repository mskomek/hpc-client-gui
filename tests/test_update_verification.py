import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hpc_gui.services.update_verification import (
    UpdateVerificationError,
    verify_artifact,
    verify_signed_metadata,
)


def _signed(metadata):
    private = Ed25519PrivateKey.generate()
    payload = json.dumps(metadata, separators=(",", ":"), sort_keys=True).encode()
    envelope = {
        "schema": 1,
        "key_id": "fixture",
        "payload": base64.b64encode(payload).decode(),
        "signature": base64.b64encode(private.sign(payload)).decode(),
    }
    return json.dumps(envelope).encode(), {"fixture": private.public_key().public_bytes_raw()}


def _metadata(**overrides):
    value = {
        "schema_version": 1,
        "product": "hpc-client-gui",
        "version": "1.6.0",
        "channel": "stable",
        "key_id": "fixture",
        "artifacts": [{
            "kind": "deb", "platform": "linux", "architecture": "x86_64", "file": "app.deb",
            "url": "https://github.com/mskomek/hpc-client-gui/releases/download/v1.6.0/app.deb",
            "size": 3, "sha256": "a" * 64,
        }],
    }
    value.update(overrides)
    return value


def test_signed_metadata_requires_known_key_and_valid_signature():
    raw, keys = _signed(_metadata())
    assert verify_signed_metadata(raw, keys)["version"] == "1.6.0"
    with pytest.raises(UpdateVerificationError, match="unknown"):
        verify_signed_metadata(raw, {})
    tampered = json.loads(raw)
    tampered["signature"] = base64.b64encode(b"x" * 64).decode()
    with pytest.raises(UpdateVerificationError, match="signature"):
        verify_signed_metadata(json.dumps(tampered).encode(), keys)


def test_metadata_rejects_duplicate_targets_and_non_https_urls():
    metadata = _metadata()
    metadata["artifacts"].append(dict(metadata["artifacts"][0]))
    raw, keys = _signed(metadata)
    with pytest.raises(UpdateVerificationError, match="duplicate"):
        verify_signed_metadata(raw, keys)

    metadata = _metadata()
    metadata["artifacts"][0]["url"] = "http://example.invalid/app.deb"
    raw, keys = _signed(metadata)
    with pytest.raises(UpdateVerificationError, match="HTTPS"):
        verify_signed_metadata(raw, keys)

    metadata = _metadata()
    metadata["artifacts"][0]["url"] = "https://evil.example/app.deb"
    raw, keys = _signed(metadata)
    with pytest.raises(UpdateVerificationError, match="host"):
        verify_signed_metadata(raw, keys)


def test_artifact_size_and_digest_are_verified(tmp_path):
    path = tmp_path / "app.deb"
    path.write_bytes(b"abc")
    verify_artifact(path, {"size": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"})
    with pytest.raises(UpdateVerificationError, match="size"):
        verify_artifact(path, {"size": 4, "sha256": "a" * 64})
