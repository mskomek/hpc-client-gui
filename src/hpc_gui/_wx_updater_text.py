"""Text and size formatting used by updater dialogs."""

from __future__ import annotations

import re


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _parse_whats_new(body: str, limit: int = 5) -> list[str]:
    """Extract 3-5 bullet points from release body markdown."""
    if not body:
        return []
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        # bullet markers: -, *, •, numbered
        m = re.match(r"^[-*•]\s+(.*)", s)
        if m:
            lines.append(m.group(1).strip())
            continue
        m2 = re.match(r"^\d+\.\s+(.*)", s)
        if m2:
            lines.append(m2.group(1).strip())
            continue
        # headings or plain lines under "What's new" section
        if s.lower().startswith("what"):
            continue
        # fallback: take first sentences if no bullets
    if not lines:
        # fallback: split body into sentences and take first 4
        sentences = re.split(r"[.!?]\s+", body.strip())
        for s in sentences:
            s = s.strip()
            if s and len(s) > 10:
                lines.append(s[:120])
            if len(lines) >= limit:
                break
    # clean and limit
    cleaned = []
    for line in lines:
        # strip markdown links, bold, etc.
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"(?<!\w)_|_(?!\w)", "", line)
        line = re.sub(r"[*`#]+", "", line).strip()
        if line:
            cleaned.append(line)
        if len(cleaned) >= limit:
            break
    # if still less than 3, pad with generic but real
    if len(cleaned) < 3 and not body.strip():
        return []
    return cleaned[:limit]
