"""Offline, redacted reproducibility bundle export for one job record."""

from __future__ import annotations

import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Mapping


_SECRET = re.compile(r"token|password|secret|credential|cookie|private.?key|mfa", re.I)


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _redact(item) for key, item in value.items() if not _SECRET.search(str(key))}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def export_job_bundle(record: Mapping[str, Any], destination_dir: str | Path, *, environment: Mapping[str, str] | None = None, include_environment: bool = False) -> Path:
    job_id = str(record.get("job_id") or "").strip()
    if not job_id:
        raise ValueError("job_id is required")
    target_dir = Path(destination_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"hpc_job_{job_id.replace('/', '_')}.zip"
    job = _redact(dict(record))
    job["bundle_schema"] = "hpc-reproducibility/1"
    job.pop("script_text", None)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("job.json", json.dumps(job, ensure_ascii=False, indent=2, sort_keys=True))
        script = str(record.get("script_text") or "")
        if script:
            bundle.writestr("submitted_script.sh", script)
        if include_environment:
            bundle.writestr("environment.json", json.dumps(_redact(dict(environment or os.environ)), ensure_ascii=False, indent=2, sort_keys=True))
        bundle.writestr("README.txt", "This bundle contains the application-recorded job script and metadata. It does not prove full scientific reproducibility; external inputs and runtime state may be missing.\n")
    return path
