"""Verification primitives for signed update metadata.

The application deliberately ships no production key until the owner supplies
and reviews one. Tests may pass an explicit fixture key.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


MAX_METADATA_BYTES = 512 * 1024
MAX_PAYLOAD_BYTES = 256 * 1024
SUPPORTED_SCHEMA = 1
ALLOWED_UPDATE_HOSTS = frozenset({"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"})


class UpdateVerificationError(ValueError):
    pass


def _b64(value: object, label: str) -> bytes:
    if not isinstance(value, str):
        raise UpdateVerificationError(f"{label} is missing")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise UpdateVerificationError(f"invalid {label}") from exc


def verify_signed_metadata(raw: bytes, trusted_keys: Mapping[str, bytes]) -> dict:
    if len(raw) > MAX_METADATA_BYTES:
        raise UpdateVerificationError("metadata is too large")
    try:
        envelope = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateVerificationError("metadata is not valid JSON") from exc
    if not isinstance(envelope, dict) or envelope.get("schema") != SUPPORTED_SCHEMA:
        raise UpdateVerificationError("unsupported metadata schema")
    key_id = envelope.get("key_id")
    if not isinstance(key_id, str) or key_id not in trusted_keys:
        raise UpdateVerificationError("unknown metadata signing key")
    payload = _b64(envelope.get("payload"), "payload")
    signature = _b64(envelope.get("signature"), "signature")
    if len(payload) > MAX_PAYLOAD_BYTES or len(signature) != 64:
        raise UpdateVerificationError("invalid metadata size")
    try:
        Ed25519PublicKey.from_public_bytes(trusted_keys[key_id]).verify(signature, payload)
    except (ValueError, InvalidSignature) as exc:
        raise UpdateVerificationError("metadata signature verification failed") from exc
    try:
        metadata = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateVerificationError("signed payload is not valid JSON") from exc
    _validate_metadata(metadata)
    if metadata.get("key_id") != key_id:
        raise UpdateVerificationError("signed payload key ID mismatch")
    return metadata


def _validate_metadata(metadata: object) -> None:
    if not isinstance(metadata, dict):
        raise UpdateVerificationError("signed payload must be an object")
    required = {"schema_version", "product", "version", "channel", "key_id", "artifacts"}
    if not required <= metadata.keys() or metadata["product"] != "hpc-client-gui":
        raise UpdateVerificationError("signed product metadata is incomplete")
    artifacts = metadata["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        raise UpdateVerificationError("signed artifact list is empty")
    seen: set[tuple[str, str, str]] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise UpdateVerificationError("invalid artifact entry")
        fields = (artifact.get("platform"), artifact.get("architecture"), artifact.get("file"))
        if not all(isinstance(value, str) and value for value in fields):
            raise UpdateVerificationError("artifact identity is incomplete")
        if fields in seen:
            raise UpdateVerificationError("duplicate artifact target")
        seen.add(fields)
        validate_update_url(artifact.get("url"))
        if not isinstance(artifact.get("kind"), str) or not artifact["kind"]:
            raise UpdateVerificationError("artifact type is incomplete")
        if not isinstance(artifact.get("size"), int) or artifact["size"] < 0:
            raise UpdateVerificationError("invalid artifact size")
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise UpdateVerificationError("invalid artifact digest")


def validate_update_url(url: object) -> str:
    if not isinstance(url, str):
        raise UpdateVerificationError("artifact URL is missing")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise UpdateVerificationError("artifact URL must use HTTPS without credentials")
    if (parsed.hostname or "").casefold() not in ALLOWED_UPDATE_HOSTS:
        raise UpdateVerificationError("artifact URL host is not trusted")
    return url


def verify_artifact(path: Path, artifact: Mapping[str, object]) -> None:
    expected_size = artifact.get("size")
    expected_digest = artifact.get("sha256")
    if not isinstance(expected_size, int) or not isinstance(expected_digest, str):
        raise UpdateVerificationError("artifact verification data is incomplete")
    if path.stat().st_size != expected_size:
        raise UpdateVerificationError("artifact size mismatch")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest.casefold() != expected_digest.casefold():
        raise UpdateVerificationError("artifact digest mismatch")
