from __future__ import annotations

import re

from hpc_gui.services.quota_monitor import QuotaResult

_ROW = re.compile(r"^\s*(?P<fs>home|project|scratch|flash)\s+(?P<used>[0-9]+(?:\.[0-9]+)?)\s*(?P<used_u>[KMGT]i?B)\s+(?P<limit>[0-9]+(?:\.[0-9]+)?)\s*(?P<limit_u>[KMGT]i?B)\s+(?P<files>[0-9]+)\s+(?P<file_limit>[0-9]+)\s*$", re.I)
_UNITS = {"KB": 1000, "MB": 1000**2, "GB": 1000**3, "TB": 1000**4, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4}


def _bytes(value: str, unit: str) -> int:
    return int(float(value) * _UNITS[unit.upper()])


def parse_lumi_quota(output: str) -> QuotaResult:
    for line in output.splitlines():
        match = _ROW.match(line)
        if match and match.group("fs") in {"scratch", "flash", "project"}:
            return QuotaResult("ok", used_bytes=_bytes(match["used"], match["used_u"]),
                               soft_limit_bytes=_bytes(match["limit"], match["limit_u"]),
                               used_files=int(match["files"]), soft_limit_files=int(match["file_limit"]),
                               storage_id=match["fs"])
    raise ValueError("lumi-quota output has no supported storage row")


def build_lumi_quota_command(_source: dict) -> str:
    return "lumi-quota -v"
