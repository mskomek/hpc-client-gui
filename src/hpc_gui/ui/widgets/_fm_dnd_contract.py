"""File-manager drag-and-drop contract shared by directory panels.

Low-level leaf: owns the remote-path MIME constant and the drag payload
encoding/decoding dataclass. No Qt-widget, panel, FTP, controller, or
runtime imports — only stdlib — so both ``local_dir_panel`` and
``remote_dir_panel`` can import it without creating a cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

MIME_REMOTE_PATHS = "application/x-truba-remote-paths"


@dataclass
class _DragPayload:
    paths: List[str]
    src_panel_id: str


def _encode_payload(payload: _DragPayload) -> bytes:
    return json.dumps({"paths": payload.paths, "src_panel_id": payload.src_panel_id}).encode("utf-8")


def _decode_payload(raw: bytes) -> Optional[_DragPayload]:
    try:
        obj = json.loads(raw.decode("utf-8"))
        paths = [str(p) for p in obj.get("paths", []) if p]
        src_panel_id = str(obj.get("src_panel_id", ""))
        if not paths or not src_panel_id:
            return None
        return _DragPayload(paths=paths, src_panel_id=src_panel_id)
    except Exception:
        return None


__all__ = ["MIME_REMOTE_PATHS", "_DragPayload", "_encode_payload", "_decode_payload"]
