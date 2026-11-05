"""Load one allowlisted, manifest-pinned OpenFOAM release catalog."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from hpc_gui.openfoam_core.release_support import OPENFOAM_EDITION, release_profile


ALLOWED_STATUS = frozenset({"runtime-inventory", "runtime-executed", "unverified"})


def load_command_catalog(plugin, version: str = "v2312") -> dict:
    profile = release_profile(version)
    catalog_path = profile["catalog_file"]
    root = Path(plugin.directory).resolve()
    target = root
    for part in catalog_path.split("/"):
        target = target / part
        if target.is_symlink():
            raise ValueError("OpenFOAM command catalog is missing or outside its package")
        is_junction = getattr(target, "is_junction", None)
        if callable(is_junction) and is_junction():
            raise ValueError("OpenFOAM command catalog is missing or outside its package")
    declared = {item.path: item for item in plugin.manifest.files}
    record = declared.get(catalog_path)
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
        or value.get("product") != OPENFOAM_EDITION
        or value.get("version") != version
    ):
        raise ValueError(f"command catalog does not match OpenFOAM.com {version}")
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("command catalog has no command list")
    names = set()
    expected_names = set(profile["commands"])
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
    if names != expected_names:
        raise ValueError(f"command catalog does not match the approved {version} command set")
    if version == "v1912":
        if (value.get("source_tag") != profile["source_tag"]
                or value.get("source_revision") != profile["source_revision"]):
            raise ValueError("v1912 command catalog has unverified upstream provenance")
        source_paths = profile["source_paths"]
        for item in commands:
            if (item.get("verification_status") != "runtime-executed"
                    or item.get("source") != source_paths[item["name"]]):
                raise ValueError("v1912 command catalog contains an unverified command")
    return value
