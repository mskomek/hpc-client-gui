from __future__ import annotations

import json
from typing import Any

from hpc_gui.services.quota_monitor import QuotaResult


def parse_nersc_showquota_json(output: str) -> QuotaResult:
    try:
        rows: Any = json.loads(output)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid showquota JSON") from exc
    if not isinstance(rows, list):
        raise ValueError("showquota JSON must be an array")
    row = next((item for item in rows if isinstance(item, dict) and item.get("fs") in {"pscratch", "scratch"}), None)
    if row is None:
        raise ValueError("showquota JSON has no pscratch row")
    numeric = ("space_used", "space_quota", "inode_used", "inode_quota")
    if any(row.get(key) is not None and not isinstance(row[key], (int, float)) for key in numeric):
        raise ValueError("showquota JSON contains non-numeric quota values")
    return QuotaResult(
        "ok", used_bytes=row.get("space_used"), soft_limit_bytes=row.get("space_quota"),
        used_files=row.get("inode_used"), soft_limit_files=row.get("inode_quota"),
        storage_id="scratch",
    )


def build_nersc_quota_command(_source: dict[str, Any]) -> str:
    return "showquota --json"
