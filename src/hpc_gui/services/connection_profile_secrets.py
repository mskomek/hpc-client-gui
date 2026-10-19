"""Secure secret storage for saved connection profiles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

AskMasterCallback = Callable[[bool], str | None]
DecryptCallback = Callable[[dict[str, Any], bool], str | None]


def prepare_secret_fragment(
    *,
    existing: dict[str, Any] | None,
    plain_password: str,
    save_password: bool,
    prompt_policy: str,
    ask_master: AskMasterCallback | None,
    keychain_available: Callable[[], bool],
    os_secret_store_available: Callable[[], bool],
    protect_keychain: Callable[[str, str | None], str],
    protect_os_secret: Callable[[str], str],
    decrypt_saved_password: DecryptCallback,
    encrypt_password: Callable[[str, str], Any],
) -> tuple[dict[str, Any], list[str], str, str]:
    """Prepare one profile's protected secret fields for persistence."""
    patch: dict[str, Any] = {}
    remove_keys: list[str] = []
    old_ref = str((existing or {}).get("password_keychain_ref") or "")
    if save_password:
        plain = plain_password or ""
        current = existing
        if keychain_available():
            if not plain and current and (
                current.get("password_keychain_ref")
                or current.get("password_dpapi")
                or (prompt_policy == "edit-only" and current.get("password_enc"))
            ):
                plain = decrypt_saved_password(
                    current, prompt_policy == "edit-only"
                ) or ""
                if not plain:
                    raise RuntimeError("saved_password_unavailable")
            try:
                if plain:
                    patch["password_keychain_ref"] = protect_keychain(
                        plain, old_ref or None
                    )
            except Exception as exc:
                raise RuntimeError(f"password_store_failed:{exc}") from exc
        elif prompt_policy == "edit-only" and os_secret_store_available():
            if not plain and current and any(
                current.get(key)
                for key in ("password_dpapi", "password_enc", "password_keychain_ref")
            ):
                plain = decrypt_saved_password(current, True) or ""
                if not plain:
                    raise RuntimeError("saved_password_unavailable")
            try:
                if plain:
                    patch["password_dpapi"] = protect_os_secret(plain)
            except Exception as exc:
                raise RuntimeError(f"password_store_failed:{exc}") from exc
        elif prompt_policy == "edit-only":
            raise RuntimeError("os_secret_store_required")
        elif plain:
            if ask_master is None:
                raise RuntimeError("master_required")
            master = ask_master(True)
            if master is None:
                raise RuntimeError("master_cancelled")
            encrypted = encrypt_password(master, plain)
            patch["password_enc"] = encrypted.token
            patch["password_salt"] = encrypted.salt
        elif current:
            for key in (
                "password_keychain_ref",
                "password_dpapi",
                "password_enc",
                "password_salt",
            ):
                if current.get(key):
                    patch[key] = current[key]
        patch["password"] = ""
    else:
        patch["password"] = ""
        remove_keys.extend(
            ["password_keychain_ref", "password_enc", "password_salt", "password_dpapi"]
        )
    return patch, remove_keys, old_ref, ""


__all__ = ["prepare_secret_fragment"]
