from __future__ import annotations

import html

import re



_ANSI_TOKEN_RE = re.compile(
    r"\x1b(?:\[([0-9;]*)m|\][^\x07]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])"
)

_ANSI_COLORS = {
    30: "#000000", 31: "#cd3131", 32: "#0dbc79", 33: "#e5e510",
    34: "#2472c8", 35: "#bc3fbc", 36: "#11a8cd", 37: "#e5e5e5",
    90: "#666666", 91: "#f14c4c", 92: "#23d18b", 93: "#f5f543",
    94: "#3b8eea", 95: "#d670d6", 96: "#29b8db", 97: "#ffffff",
}

_LIVE_TAIL_INTERVAL_MS = 1000

_LIVE_TAIL_LINE_COUNT = 200

_LIVE_TAIL_MAX_RETRY_INTERVAL_MS = 30_000

_LIVE_TAIL_SLOW_INTERVAL_MS = 5_000

_LIVE_TAIL_FILE_RETRY_INTERVAL_MS = 60_000

_LIVE_TAIL_INITIAL_RETRY_SECONDS = 30

_LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS = 5 * 60

_OUTPUT_MAX_LINES = 5000

_OUTPUT_TRUNCATION_MARKER = "[Older output truncated; showing the latest 5000 lines.]"

def _ansi_prefix_for_tail(text: str, cut: int) -> str:
    prefix: list[str] = []
    for match in _ANSI_TOKEN_RE.finditer(text[:cut]):
        if match.group(1) is None:
            continue
        if any(code in {"0", ""} for code in match.group(1).split(";")):
            prefix.clear()
        prefix.append(match.group(0))
    return "".join(prefix)

def _bounded_output_text(text: str, max_lines: int = _OUTPUT_MAX_LINES) -> str:
    """Keep live output bounded while retaining newest lines and SGR state."""
    value = str(text or "")
    lines = value.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return value
    tail = "".join(lines[-max_lines:])
    cut = len(value) - len(tail)
    prefix = _ansi_prefix_for_tail(value, cut)
    return prefix + _OUTPUT_TRUNCATION_MARKER + "\n" + tail

def _ansi_to_html(text: str) -> str:
    parts = []
    state = {"fg": "#e8e8e8", "bg": None, "bold": False}
    position = 0

    def append_segment(segment: str) -> None:
        if not segment:
            return
        styles = [f"color:{state['fg']}"]
        if state["bg"]:
            styles.append(f"background-color:{state['bg']}")
        if state["bold"]:
            styles.append("font-weight:bold")
        parts.append(
            f'<span style="{";".join(styles)}">{html.escape(segment)}</span>'
        )

    for match in _ANSI_TOKEN_RE.finditer(text or ""):
        append_segment((text or "")[position:match.start()])
        params = match.group(1)
        if params is not None:
            codes = [int(value) if value else 0 for value in params.split(";")]
            for code in codes:
                if code == 0:
                    state.update(fg="#e8e8e8", bg=None, bold=False)
                elif code == 1:
                    state["bold"] = True
                elif code == 22:
                    state["bold"] = False
                elif code == 39:
                    state["fg"] = "#e8e8e8"
                elif code == 49:
                    state["bg"] = None
                elif code in _ANSI_COLORS:
                    state["fg"] = _ANSI_COLORS[code]
                elif 40 <= code <= 47:
                    state["bg"] = _ANSI_COLORS[code - 10]
                elif 100 <= code <= 107:
                    state["bg"] = _ANSI_COLORS[code - 10]
        position = match.end()
    append_segment((text or "")[position:])
    return (
        '<pre style="margin:0; white-space:pre; font-family:monospace; '
        'font-size:10pt; background-color:#1e1e1e;">'
        + "".join(parts)
        + "</pre>"
    )
