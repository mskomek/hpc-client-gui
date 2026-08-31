from __future__ import annotations

import re

from hpc_gui.services.quota_monitor import QuotaResult

_ROW = re.compile(
    r"^\s*(?P<fs>/\S+)\s+(?P<used>[0-9]+(?:\.[0-9]+)?)\s*(?P<used_u>[KMGT]i?B?)\s+"
    r"(?P<project>[0-9]+(?:\.[0-9]+)?)\s*(?P<project_u>[KMGT]i?B?|N/A)\s+"
    r"(?P<percent>\S+)\s+\(project\)\s+(?P<files>[0-9]+)\s+"
    r"(?P<file_percent>\S+)\s+\(user\)\s*$",
    re.I,
)
_UNITS = {
    "K": 1000, "KB": 1000, "KIB": 1024,
    "M": 1000**2, "MB": 1000**2, "MIB": 1024**2,
    "G": 1000**3, "GB": 1000**3, "GIB": 1024**3,
    "T": 1000**4, "TB": 1000**4, "TIB": 1024**4,
}


def _bytes(value: str, unit: str) -> int:
    return int(float(value) * _UNITS[unit.upper()])


def parse_pawsey_account_balance(output: str) -> QuotaResult:
    rows = [match for line in output.splitlines() if (match := _ROW.match(line))]
    if not rows:
        raise ValueError("pawseyAccountBalance output has no filesystem row")
    match = next((row for row in rows if row["fs"].lower() == "/software"), rows[0])
    quota = None if match["project_u"].upper() == "N/A" else _bytes(match["project"], match["project_u"])
    storage_id = match["fs"].strip("/").lower() or "unknown"
    return QuotaResult(
        "ok",
        used_bytes=_bytes(match["used"], match["used_u"]),
        soft_limit_bytes=quota,
        used_files=int(match["files"]),
        storage_id=storage_id,
        path=match["fs"],
    )


def build_pawsey_account_balance_command(_source: dict) -> str:
    return "pawseyAccountBalance -s"
