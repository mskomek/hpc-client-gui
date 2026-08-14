from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_CRASH_FLAG_NAME = "crash_flag.json"


def _log_dir() -> Path:
    d = Path.home() / ".truba_slurm_gui"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _crash_flag_path() -> Path:
    return _log_dir() / _CRASH_FLAG_NAME


def write_crash_flag(exc_type: Optional[type] = None, exc_value: Optional[BaseException] = None, exc_tb=None) -> None:
    try:
        summary = ""
        if exc_type is not None and exc_value is not None:
            summary = f"{exc_type.__name__}: {exc_value}"
            if exc_tb is not None:
                try:
                    summary += "\n" + "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                except Exception:
                    pass

        try:
            from hpc_gui.core.log_redaction import redact_text

            summary = redact_text(summary)
        except Exception:
            pass

        flag = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary[:4000],
        }
        _crash_flag_path().write_text(json.dumps(flag, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_crash_flag() -> Optional[dict]:
    try:
        p = _crash_flag_path()
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_crash_flag() -> None:
    try:
        p = _crash_flag_path()
        if p.exists():
            p.unlink(missing_ok=True)
    except Exception:
        pass


def show_crash_dialog(parent) -> None:
    try:
        from PySide6.QtCore import QTimer

        from hpc_gui.ui.dialogs.send_logs_dialog import SendLogsDialog

        def _show():
            try:
                flag = read_crash_flag()
                dlg = SendLogsDialog(parent, crash_context=True, crash_summary=flag.get("summary", "") if flag else "")
                dlg.setAttribute(getattr(dlg, "WA_DeleteOnClose", True))
                dlg.show()
                dlg.raise_()
                dlg.activateWindow()
            except Exception:
                pass

        QTimer.singleShot(300, _show)
    except Exception:
        pass
