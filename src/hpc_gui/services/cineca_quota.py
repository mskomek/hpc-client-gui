from __future__ import annotations

import re

from hpc_gui.services.quota_monitor import QuotaResult

_ROW = re.compile(
    r"^\s*(?P<path>/\S+)\s+(?P<used>[0-9]+(?:\.[0-9]+)?)\s*(?P<used_u>[KMGT]i?B?)\s+"
    r"(?P<quota>[0-9]+(?:\.[0-9]+)?)\s*(?P<quota_u>[KMGT]i?B?)\s+"
    r"(?P<grace>\S+)\s+(?P<files>[0-9]+)\s*$",
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


def parse_cineca_cinquota(output: str) -> QuotaResult:
    rows = []
    for line in output.splitlines():
        match = _ROW.match(line)
        if match:
            rows.append(match)
    if not rows:
        raise ValueError("cinQuota output has no supported filesystem row")
    match = next((row for row in rows if "work" in row["path"].lower()), rows[0])
    path = match["path"]
    lower_path = path.lower()
    storage_id = next(
        (name for name in ("home", "work", "fast", "scratch", "public", "dres") if name in lower_path),
        "unknown",
    )
    return QuotaResult(
        "ok",
        used_bytes=_bytes(match["used"], match["used_u"]),
        soft_limit_bytes=_bytes(match["quota"], match["quota_u"]),
        used_files=int(match["files"]),
        storage_id=storage_id,
        path=path,
    )


def build_cineca_cinquota_command(_source: dict) -> str:
    return "cinQuota"
