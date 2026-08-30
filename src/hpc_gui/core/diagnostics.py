from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from hpc_gui import __version__
from hpc_gui.core.paths import app_data_dir, app_log_dir


def _candidate_files() -> Iterable[Path]:
    locations = [(app_log_dir(), ["app.log", "crash_flag.json"]), (app_data_dir(), [
        # config.json is deliberately excluded: it holds saved connection
        # profiles (host/username) plus encrypted password blobs and salts.
        # None of that is needed to debug from logs, and it must never leave
        # the machine in a "send me your logs" bundle.
        "history.json",
        "history.jsonl",
        "last_batch.json",
        "processes.json",
        "transfer_journal.jsonl",
        "vcxsrv_stdout.log",
        "vcxsrv_stderr.log",
        "language.json",
    ])]
    for base, names in locations:
        for n in names:
            p = base / n
            if p.exists() and p.is_file():
                yield p


def create_diagnostic_bundle(dest_dir: str) -> Path:
    from hpc_gui.core.log_redaction import redact_text

    out_dir = Path(dest_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"hpc_diagnostics_{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        included = []
        skipped = []
        for p in _candidate_files():
            try:
                content = redact_text(p.read_text(encoding="utf-8", errors="strict"))
                zf.writestr(p.name, content)
                included.append(p.name)
            except (OSError, UnicodeError) as exc:
                skipped.append({"file": p.name, "reason": type(exc).__name__})
        manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "application_version": __version__,
            "included_files": included,
            "skipped_files": skipped,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return zip_path
