"""Authentication metadata policy shared by connection front ends."""

from collections.abc import Mapping
from typing import Any

AUTH_METHOD_PASSWORD = "password"

AUTH_METHOD_PUBLICKEY = "publickey"

AUTH_METHOD_KEYBOARD_INTERACTIVE = "keyboard-interactive"

KNOWN_AUTH_METHODS = (
    AUTH_METHOD_PASSWORD,
    AUTH_METHOD_PUBLICKEY,
    AUTH_METHOD_KEYBOARD_INTERACTIVE,
)

_KNOWN_AUTH_METHOD_SET = frozenset(KNOWN_AUTH_METHODS)

def normalize_auth_methods(settings: Any) -> tuple[str, ...]:
    """Return the allow-listed auth methods declared for a connection.

    Provider/plugin metadata can appear either at the top level of a
    normalized system-settings mapping (legacy) or inside the retained
    ``provider_template`` (current plugin template shape). Unknown values are
    dropped so malformed plugin data can never enable new behavior.
    """
    if not isinstance(settings, Mapping):
        return ()
    candidates: list[Any] = []
    access = settings.get("access")
    if isinstance(access, Mapping):
        candidates.extend(_as_method_sequence(access.get("auth_methods")))
    provider = settings.get("provider_template")
    if isinstance(provider, Mapping):
        provider_access = provider.get("access")
        if isinstance(provider_access, Mapping):
            candidates.extend(_as_method_sequence(provider_access.get("auth_methods")))
    methods: list[str] = []
    for value in candidates:
        method = str(value).strip().lower()
        if method in _KNOWN_AUTH_METHOD_SET and method not in methods:
            methods.append(method)
    return tuple(methods)

def _as_method_sequence(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        return [value]
    return []

def keyboard_interactive_required(settings: Any) -> bool:
    """True when the declared auth metadata asks for keyboard-interactive."""
    return AUTH_METHOD_KEYBOARD_INTERACTIVE in normalize_auth_methods(settings)

def password_prompt_recommended(settings: Any, *, has_key_path: bool) -> bool:
    """Whether a Connect attempt should ask the user for a password.

    Password-only providers (or providers with no declared auth metadata)
    need a credential; declared key/interactive sources are respected and
    never overridden by an unconditional password prompt.
    """
    if has_key_path:
        return False
    methods = normalize_auth_methods(settings)
    if not methods:
        return True
    if AUTH_METHOD_PASSWORD not in methods:
        return False
    return not (
        AUTH_METHOD_PUBLICKEY in methods
        or AUTH_METHOD_KEYBOARD_INTERACTIVE in methods
    )
