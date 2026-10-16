"""Shared data limits and safe serialization for the wx terminal WebView."""

from dataclasses import dataclass
import json

READINESS_TIMEOUT_MS = 5000
MAX_PENDING_BYTES = 2 * 1024 * 1024
MAX_PENDING_ENTRIES = 5000
MAX_PENDING_PASTE_BYTES = 256 * 1024
DEFAULT_FONT_SIZE = 14
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 32


def _safe_truncate_index(text: str, max_bytes: int) -> int:
    """Find a truncation boundary that avoids splitting UTF-8 and escape data."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return len(text)
    cut = max_bytes
    while cut > 0:
        try:
            partial = encoded[:cut].decode("utf-8", errors="strict")
            return len(partial)
        except UnicodeDecodeError:
            cut -= 1
    last_safe = 0
    i = 0
    raw = encoded[:max_bytes]
    while i < len(raw):
        b = raw[i]
        if b == 0x1B:
            if i + 1 < len(raw):
                next_b = raw[i + 1]
                if next_b == 0x5B:
                    j = i + 2
                    while j < len(raw) and not (0x40 <= raw[j] <= 0x7E):
                        j += 1
                    i = min(j + 1, len(raw))
                elif next_b == 0x5D:
                    j = i + 2
                    while j < len(raw):
                        if raw[j] == 0x07:
                            j += 1
                            break
                        if raw[j] == 0x9B or (raw[j] == 0x1B and j + 1 < len(raw) and raw[j + 1] == 0x5C):
                            j += 2
                            break
                        j += 1
                    i = min(j, len(raw))
                else:
                    i += 2
            else:
                i += 1
        else:
            last_safe = i
            i += 1
    try:
        return len(encoded[:last_safe].decode("utf-8", errors="replace"))
    except Exception:
        return len(text) // 2


@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


def _is_local_file_url(url: str) -> bool:
    # wx WebView reports file:// URLs for local assets; allow only those
    # and data: for xterm's internal use. Block http/https and anything else.
    u = (url or "").strip().lower()
    return u.startswith("file://") or u.startswith("about:blank") or u == ""




def _safe_json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
