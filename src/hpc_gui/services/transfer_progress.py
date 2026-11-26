"""Toolkit-independent session-byte progress and ETA estimates."""
from __future__ import annotations

from time import monotonic

from hpc_gui.core.i18n import t
from hpc_gui.services.remote_entry_format import fmt_size


def format_duration(seconds: float) -> str:
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


class ProgressSamples:
    """Track each item's first observed byte offset and sample time."""

    def __init__(self):
        self._baseline = {}

    def reset(self, item=None):
        if item is None:
            self._baseline.clear()
        else:
            self._baseline.pop(id(item), None)

    def detail(self, item, done, total, *, now=None):
        now = monotonic() if now is None else now
        done, total = max(0, int(done)), max(0, int(total))
        key = id(item)
        baseline = self._baseline.get(key)
        if baseline is None or done < baseline[0] or now < baseline[1]:
            baseline = self._baseline[key] = (done, now)
        base_done, base_time = baseline
        elapsed = now - base_time
        speed = (done - base_done) / elapsed if elapsed > 0 else 0.0
        eta = (
            "0:00" if total and done >= total else
            format_duration((total - done) / speed) if total and speed > 0 else "?"
        )
        return t("transfer.progress_detail").format(
            item=item.label(), done=fmt_size(done),
            total=fmt_size(total) if total else "?",
            speed=f"{fmt_size(speed)}/s", eta=eta,
        )
