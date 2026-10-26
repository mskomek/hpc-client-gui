"""Load only the manifest-pinned OpenFOAM v2312 command catalog."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


CATALOG_PATH = "engine/openfoam_studio/data/command_catalog.json"
ALLOWED_STATUS = frozenset({"runtime-inventory", "runtime-executed", "unverified"})


def load_command_catalog(plugin) -> dict:
    root = Path(plugin.directory).resolve()
    target = root
    for part in CATALOG_PATH.split("/"):
        target = target / part
        if target.is_symlink():
            raise ValueError("OpenFOAM command catalog is missing or outside its package")
        is_junction = getattr(target, "is_junction", None)
        if callable(is_junction) and is_junction():
            raise ValueError("OpenFOAM command catalog is missing or outside its package")
    declared = {item.path: item for item in plugin.manifest.files}
    record = declared.get(CATALOG_PATH)
    resolved = target.resolve()
    if root not in resolved.parents or record is None or not target.is_file():
        raise ValueError("OpenFOAM command catalog is missing or outside its package")
    data = target.read_bytes()
    if len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
        raise ValueError("OpenFOAM command catalog failed its manifest hash check")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("OpenFOAM command catalog is malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or value.get("product") != "OpenFOAM.com / ESI"
        or value.get("version") != "v2312"
    ):
        raise ValueError("command catalog does not match OpenFOAM.com v2312")
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("command catalog has no command list")
    names = set()
    for item in commands:
        name = item.get("name") if isinstance(item, dict) else None
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)
            or name in names
            or item.get("category") not in {"Mesh", "Solver", "Post-processing"}
            or item.get("verification_status") not in ALLOWED_STATUS
            or item.get("parameters") != []
            or item.get("execution") != "draft-only"
        ):
            raise ValueError("command catalog contains unsupported or executable metadata")
        names.add(name)
    return value
