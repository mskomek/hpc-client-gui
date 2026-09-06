"""Shared profile persistence and secure-secret lifecycle.

Qt ``LoginWidget`` previously owned this logic inside a widget.
The wx implementation must reuse the same semantics without duplicating
schemas or silently weakening security. This module extracts only non-UI
helpers; callers provide UI callbacks (ask_master, confirm dialogs) where
prompting is required. The persisted ``password`` field must always be empty.

The module is intentionally UI-neutral so both runtimes can share it and
the wx runtime never depends on Qt dialogs.
"""

from __future__ import annotations

from typing import Any, Callable

from hpc_gui.config.storage import (
    delete_profile as storage_delete_profile,
    load_profiles,
    merge_profile_patch,
    upsert_profile,
)
from hpc_gui.core.crypto_master import decrypt_with_master, encrypt_with_master
from hpc_gui.core.secret_store import (
    delete_keychain_secret,
    is_available as os_secret_store_available,
    keychain_available,
    protect_keychain_secret,
    protect_secret,
    unprotect_keychain_secret,
    unprotect_secret,
)


AskMasterCallback = Callable[[bool], str | None]  # confirm -> password or None


def load_profile_by_name(name: str) -> dict[str, Any] | None:
    clean = (name or "").strip()
    if not clean:
        return None
    return next((p for p in load_profiles() if p.get("name") == clean), None)


def _decrypt_saved_password(
    profile: dict[str, Any],
    ask_master: AskMasterCallback | None,
    master_cache: list[str] | None = None,
) -> str | None:
    token = profile.get("password_enc")
    salt = profile.get("password_salt")
    if not token or not salt:
        return ""
    # Caller provides a prompting callback; if none, cannot decrypt.
    if ask_master is None:
        return None
    # Try cached master first via ask_master(False) pattern – the caller may
    # already have resolved DPAPI-stored master.
    master = ask_master(False)
    if master is None:
        return None
    try:
        return decrypt_with_master(master, str(token), str(salt))
    except Exception:
        # Retry once if master may be stale; caller should clear DPAPI cache.
        if master_cache is not None:
            master_cache.clear()
        # Second attempt - ask again with confirm=False after clearing cache
        # The caller decides whether to re-prompt; we simply try again via ask_master
        # but the outer loop in LoginWidget handles DPAPI clearing. Here just fail
        # and let caller surface the error.
        return None


def decrypt_profile_password(
    profile: dict[str, Any],
    *,
    allow_prompt: bool,
    ask_master: AskMasterCallback | None = None,
) -> str | None:
    """Return plaintext password for a stored profile or None on failure.

    - keychain refs are resolved via OS keychain without prompting.
    - DPAPI tokens are resolved via OS protection without prompting.
    - Master-encrypted secrets require ``ask_master`` when ``allow_prompt`` is True.
    - Returns ``""`` when no saved secret exists.
    - Returns ``None`` when decryption failed / user cancelled.
    """
    keychain_ref = profile.get("password_keychain_ref")
    if keychain_ref:
        try:
            return unprotect_keychain_secret(str(keychain_ref))
        except Exception:
            return None
    token = profile.get("password_dpapi")
    if token:
        try:
            return unprotect_secret(str(token))
        except Exception:
            return None
    if profile.get("password_enc") and profile.get("password_salt"):
        if not allow_prompt:
            return None
        return _decrypt_saved_password(profile, ask_master)
    return ""


def verify_edit_authorization(
    initial_profile: dict[str, Any],
    *,
    ask_master: AskMasterCallback | None = None,
    prompt_verify: Callable[[str], tuple[str, bool]] | None = None,
) -> bool:
    """Verify the caller may edit a profile that holds a saved secret.

    - keychain/dpapi: compare entered verification text to decrypted expected.
    - master-encrypted: successful master decrypt is sufficient.
    Returns True when no saved secret or verification succeeded, False otherwise.
    """
    if initial_profile.get("password_keychain_ref") or initial_profile.get("password_dpapi"):
        expected = decrypt_profile_password(initial_profile, allow_prompt=False, ask_master=None)
        if expected is None:
            return False
        if prompt_verify is None:
            return False
        entered, ok = prompt_verify(expected)
        if not ok:
            return False
        return entered == expected
    if initial_profile.get("password_enc") and initial_profile.get("password_salt"):
        result = decrypt_profile_password(initial_profile, allow_prompt=True, ask_master=ask_master)
        return result is not None
    return True


def _prepare_secret_fragment(
    *,
    existing: dict[str, Any] | None,
    plain_password: str,
    save_password: bool,
    prompt_policy: str,
    ask_master: AskMasterCallback | None,
) -> tuple[dict[str, Any], list[str], str, str]:
    """Return (patch_fragment, remove_keys, old_keychain_ref, new_keychain_ref_placeholder).

    ``plain_password`` is the text currently in the password field (may be empty).
    ``existing`` is the stored profile before edit (or None for Add).
    """
    patch: dict[str, Any] = {}
    remove_keys: list[str] = []
    old_ref = str((existing or {}).get("password_keychain_ref") or "")
    # Set new_ref placeholder; caller will fill after merging where needed.
    if save_password:
        plain = plain_password or ""
        current = existing
        # If the user left the field blank but a keychain secret exists, reuse it.
        if keychain_available():
            if not plain and current and current.get("password_keychain_ref"):
                decrypted = decrypt_profile_password(current, allow_prompt=False)
                if decrypted is None:
                    # Caller should abort save.
                    raise RuntimeError("saved_password_unavailable")
                plain = decrypted
            try:
                if plain:
                    new_ref = protect_keychain_secret(
                        plain,
                        str(current.get("password_keychain_ref")) if current and current.get("password_keychain_ref") else None,
                    )
                    patch["password_keychain_ref"] = new_ref
            except Exception as exc:
                raise RuntimeError(f"password_store_failed:{exc}") from exc
        elif prompt_policy == "edit-only" and os_secret_store_available():
            if not plain and current and current.get("password_enc"):
                decrypted = decrypt_profile_password(current, allow_prompt=True, ask_master=ask_master)
                if decrypted is None:
                    raise RuntimeError("saved_password_unavailable")
                plain = decrypted
            try:
                if plain:
                    patch["password_dpapi"] = protect_secret(plain)
            except Exception as exc:
                raise RuntimeError(f"password_store_failed:{exc}") from exc
        elif plain:
            if ask_master is None:
                raise RuntimeError("master_required")
            master = ask_master(True)
            if master is None:
                raise RuntimeError("master_cancelled")
            enc = encrypt_with_master(master, plain)
            patch["password_enc"] = enc.token
            patch["password_salt"] = enc.salt
        else:
            # Keep existing encrypted secret when editing and no new plaintext.
            if current:
                for key in ("password_keychain_ref", "password_dpapi", "password_enc", "password_salt"):
                    if current.get(key):
                        patch[key] = current.get(key)
        patch["password"] = ""
    else:
        patch["password"] = ""
        if existing and existing.get("password_keychain_ref"):
            # Actual deletion happens after merge/upsert; we mark for caller.
            pass
        remove_keys.extend(["password_keychain_ref", "password_enc", "password_salt", "password_dpapi"])
    return patch, remove_keys, old_ref, ""


def save_profile(
    collected: dict[str, Any],
    *,
    initial_profile: dict[str, Any] | None = None,
    plain_password: str = "",
    save_password: bool = False,
    prompt_policy: str = "when-needed",
    ask_master: AskMasterCallback | None = None,
    original_name_override: str | None = None,
) -> dict[str, Any]:
    """Persist a collected profile dict, handling secrets and rename.

    ``collected`` must already be the full profile patch (name, host, port,
    system, file_manager, jump_host, etc.) produced by the dialog's
    ``_collect_profile``-like logic. ``initial_profile`` is the stored profile
    before edit (or None for Add). ``plain_password`` is the raw password
    field text. Returns the merged profile that was upserted.
    Raises ValueError / RuntimeError for user-visible errors.
    """
    name = str(collected.get("name") or "").strip()
    if not name:
        username = str(collected.get("username") or "").strip()
        host = str(collected.get("host") or "").strip()
        name = f"{username}@{host}" if username else host
        if not name:
            raise ValueError("profile name is required")
        collected = dict(collected, name=name)

    # Resolve existing before patch so unknown keys survive.
    original_name = (original_name_override or (initial_profile or {}).get("name") or name or "").strip()
    existing_name = original_name or name
    existing = next((p for p in load_profiles() if p.get("name") == existing_name), None)
    # Fall back to lookup by collected name when editing without override.
    if existing is None and initial_profile is not None:
        existing = dict(initial_profile)
    # For Add, ensure we don't carry stale secret keys from initial dummy.
    if initial_profile is None:
        existing = None

    # Prepare secret fragment.
    secret_patch, remove_keys, old_ref, _ = _prepare_secret_fragment(
        existing=existing,
        plain_password=plain_password,
        save_password=save_password,
        prompt_policy=prompt_policy,
        ask_master=ask_master,
    )

    patch: dict[str, Any] = dict(collected)
    patch.update(secret_patch)
    # Preserve unknown nested keys for file_manager / jump_host via shared helpers
    # so direct callers that provide a partial dict don't lose future fields.
    if "file_manager" in patch:
        from hpc_gui.config.file_manager_profile import patch_file_manager_settings

        base_fm = (existing or {}).get("file_manager") if isinstance(existing, dict) else None
        incoming_fm = patch.get("file_manager") if isinstance(patch.get("file_manager"), dict) else {}
        patch["file_manager"] = patch_file_manager_settings(base_fm, incoming_fm)
    if "jump_host" in patch:
        from hpc_gui.config.jump_host_profile import patch_jump_host_settings

        base_jh = (existing or {}).get("jump_host") if isinstance(existing, dict) else None
        incoming_jh = patch.get("jump_host") if isinstance(patch.get("jump_host"), dict) else {}
        patch["jump_host"] = patch_jump_host_settings(base_jh, incoming_jh)
    if "system" in patch and isinstance(patch.get("system"), dict):
        existing_system = existing.get("system") if isinstance(existing, dict) else None
        if isinstance(existing_system, dict):
            patch["system"] = {**existing_system, **patch["system"]}
    # Never carry stale master-derived fields unless explicitly set by secret_patch.
    # collected may have been produced without those fields (dialog pops them).
    prof = merge_profile_patch(existing, patch, remove_keys=remove_keys)

    # Enforce only one authoritative scheme.
    if "password_keychain_ref" in prof:
        prof.pop("password_dpapi", None)
        prof.pop("password_enc", None)
        prof.pop("password_salt", None)
    elif "password_dpapi" in prof:
        prof.pop("password_enc", None)
        prof.pop("password_salt", None)
        prof.pop("password_keychain_ref", None)
    elif "password_enc" in prof:
        prof.pop("password_dpapi", None)
        prof.pop("password_keychain_ref", None)
    else:
        # When save is off, ensure all secret keys gone (already via remove_keys).
        pass

    # Plaintext must never survive.
    if prof.get("password"):
        prof["password"] = ""

    # Handle keychain ref rotation cleanup.
    new_ref = str(prof.get("password_keychain_ref") or "")
    if old_ref and old_ref != new_ref:
        delete_keychain_secret(old_ref)

    # When save is off and existing had a keychain ref, delete it if no longer referenced.
    if not save_password and old_ref:
        # delete_keychain_secret is idempotent via storage helpers, but we also
        # delete explicitly here to mirror LoginWidget.
        delete_keychain_secret(old_ref)
        # If new_ref is empty, the merge already removed it; safe to delete again.
        # storage.delete_profile would also clean, but we are not deleting profile,
        # just removing secret.

    upsert_profile(prof)
    # Rename handling: remove old entry after successful upsert.
    if original_name and original_name != name:
        # Only delete old after new is safely persisted.
        storage_delete_profile(original_name)
        # After rename, the secret reference lives under new name; old cleanup already done.
    return prof


def resolve_password_for_connect(
    profile: dict[str, Any],
    *,
    typed_password: str = "",
    ask_master: AskMasterCallback | None = None,
) -> str | None:
    """Resolve the password to use for a connection attempt.

    - If the user typed a password, use it.
    - Otherwise, if the profile opts in to saved password, decrypt via appropriate store.
    - Returns "" when no password is needed, None when decryption failed / master cancelled.
    """
    if typed_password:
        return typed_password
    name = str(profile.get("name") or "").strip()
    stored = load_profile_by_name(name) if name else profile
    if stored is None:
        stored = profile
    if not stored.get("save_password"):
        return ""
    # Mirror LoginWidget's _decrypt_profile_password allow_prompt=True
    result = decrypt_profile_password(stored, allow_prompt=True, ask_master=ask_master)
    if result is None:
        return None
    return result
