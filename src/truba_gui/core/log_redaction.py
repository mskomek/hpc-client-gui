from __future__ import annotations

import getpass
import re
from typing import Iterable, List, Tuple

_PLACEHOLDER_USER = "<user>"
_PLACEHOLDER_HOST = "<host>"
_MIN_SECRET_LEN = 3


def _collect_secrets() -> Tuple[List[str], List[str]]:
    """Return (usernames, hosts) worth redacting from exported logs.

    Usernames cover both the local Windows account (appears in local file
    paths) and every saved connection profile's remote username (appears in
    remote paths like /home/<user>/...); hosts cover saved profile
    hostnames/IPs. Longest-first so overlapping names don't leave partial
    matches behind.
    """
    usernames: set[str] = set()
    hosts: set[str] = set()
    try:
        local_user = getpass.getuser()
        if local_user and len(local_user) >= _MIN_SECRET_LEN:
            usernames.add(local_user)
    except Exception:
        pass
    try:
        from truba_gui.config.storage import load_profiles

        for profile in load_profiles():
            user = str(profile.get("username") or "").strip()
            if user and len(user) >= _MIN_SECRET_LEN:
                usernames.add(user)
            host = str(profile.get("host") or "").strip()
            if host and len(host) >= _MIN_SECRET_LEN:
                hosts.add(host)
    except Exception:
        pass
    return (
        sorted(usernames, key=len, reverse=True),
        sorted(hosts, key=len, reverse=True),
    )


def _replace_all(text: str, needles: List[str], placeholder: str) -> str:
    if not needles:
        return text
    # One alternation, one pass: re.sub never re-scans replacement text, so
    # this can't corrupt a just-inserted placeholder like "<user>" by later
    # matching the literal "user" inside it. Doing this needle-by-needle
    # instead (in a loop) would risk exactly that on overlapping names.
    alternation = "|".join(re.escape(needle) for needle in needles)
    # Path/URL separators (/, \, @, :) aren't word characters, so this
    # boundary still matches a username or host embedded in a path like
    # /arf/scratch/<user>/... or C:\Users\<user>\... without requiring
    # whitespace around it.
    pattern = re.compile(rf"(?<![\w.-])(?:{alternation})(?![\w.-])")
    return pattern.sub(placeholder, text)


def redact_text(text: str) -> str:
    """Best-effort redaction of local/remote usernames and hostnames.

    Intended for the points where logs actually leave the app (copy, export
    diagnostics, crash summary) — not for the on-disk app.log itself, which
    stays unredacted for local debugging.
    """
    if not text:
        return text
    usernames, hosts = _collect_secrets()
    text = _replace_all(text, usernames, _PLACEHOLDER_USER)
    text = _replace_all(text, hosts, _PLACEHOLDER_HOST)
    return text
