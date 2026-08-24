from __future__ import annotations

import base64
import ctypes
import sys
import uuid
from ctypes import wintypes

KEYCHAIN_SERVICE = "io.github.mskomek.HpcClientGui"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


def is_available() -> bool:
    return sys.platform == "win32"


def protect_secret(plaintext: str) -> str:
    if not is_available():
        raise RuntimeError("OS credential protection is unavailable")
    raw = (plaintext or "").encode("utf-8")
    input_blob, input_buffer = _blob(raw)
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "HPC Client GUI saved connection",
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        protected = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(protected).decode("ascii")
    finally:
        kernel32.LocalFree(output_blob.pbData)
        del input_buffer


def unprotect_secret(token: str) -> str:
    if not is_available():
        raise RuntimeError("OS credential protection is unavailable")
    protected = base64.b64decode((token or "").encode("ascii"))
    input_blob, input_buffer = _blob(protected)
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        raw = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return raw.decode("utf-8")
    finally:
        kernel32.LocalFree(output_blob.pbData)
        del input_buffer


def keychain_available() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        import keyring

        keyring.get_keyring()
        return True
    except Exception:
        return False


def protect_keychain_secret(plaintext: str, reference: str | None = None) -> str:
    if not keychain_available():
        raise RuntimeError("macOS Keychain is unavailable")
    import keyring

    reference = reference or uuid.uuid4().hex
    keyring.set_password(KEYCHAIN_SERVICE, reference, plaintext or "")
    return reference


def unprotect_keychain_secret(reference: str) -> str:
    if not keychain_available():
        raise RuntimeError("macOS Keychain is unavailable")
    import keyring

    value = keyring.get_password(KEYCHAIN_SERVICE, reference)
    if value is None:
        raise RuntimeError("macOS Keychain entry is unavailable")
    return value


def delete_keychain_secret(reference: str) -> None:
    if not reference or not keychain_available():
        return
    import keyring

    try:
        keyring.delete_password(KEYCHAIN_SERVICE, reference)
    except Exception:
        # Deleting an already-missing entry is harmless during profile cleanup.
        pass
