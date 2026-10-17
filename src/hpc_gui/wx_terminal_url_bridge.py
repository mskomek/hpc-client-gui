"""Restricted, local-only WebKitGTK terminal command envelope.

wxGTK WebKit blocks wxWebView.RunScript under the terminal page's strict
CSP. Use same-document *file* fragment navigation to deliver commands to
the already-loaded, vendored bridge; JavaScript messages carry results back.

No JavaScript evaluation, remote URLs, or persistent command files.
Callers must not record generated fragment URLs (they contain terminal text).
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote

_ALLOWED = frozenset({
    "hpcWrite", "hpcClear", "hpcPaste", "hpcFocus", "hpcSetFontSize",
    "hpcFit", "hpcFind", "hpcFindNext", "hpcFindPrev",
    "hpcGetScreenState",
})
_CALL = re.compile(r"^\s*window\.(hpc\w+)\s*&&\s*window\.\1\((.*)\)\s*;?\s*$", re.S)


def parse_terminal_call(code: str) -> tuple[str, object] | None:
    """Accept only fixed bridge method calls with JSON data arguments."""
    match = _CALL.fullmatch(code)
    if match is None or match.group(1) not in _ALLOWED:
        return None
    method, value = match.groups()
    try:
        arg = json.loads(value) if value.strip() else None
    except (TypeError, ValueError):
        return None
    if method in {"hpcWrite", "hpcPaste", "hpcFind"} and not isinstance(arg, str):
        return None
    if method == "hpcSetFontSize" and (type(arg) is not int or not 6 <= arg <= 32):
        return None
    if method in {
        "hpcClear", "hpcFocus", "hpcFit", "hpcFindNext",
        "hpcFindPrev", "hpcGetScreenState",
    } and arg is not None:
        return None
    return method, arg


def encode_terminal_fragment(
    seq: int,
    method: str,
    arg: object = None,
    *,
    channel: str | None = None,
) -> str:
    """Encode a whitelisted action in a fragment, never query/path/network."""
    if type(seq) is not int or seq < 1 or method not in _ALLOWED:
        raise ValueError("invalid terminal bridge command")
    payload = {"seq": seq, "op": method, "arg": arg}
    if channel is not None:
        if not re.fullmatch(r"[0-9a-f]{32}", channel):
            raise ValueError("invalid terminal bridge channel")
        payload["channel"] = channel
    envelope = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return "#hpc=" + quote(envelope, safe="")


__all__ = ["parse_terminal_call", "encode_terminal_fragment"]
