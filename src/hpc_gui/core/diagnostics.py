from __future__ import annotations

import json
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from hpc_gui import __version__
from hpc_gui.core.paths import app_data_dir, app_log_dir

MAX_LOG_LINES = 5000


def _bounded_text(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines(keepends=True)
    return "".join(lines[-MAX_LOG_LINES:])


def _runtime_summary() -> dict:
    runtime = {
        "application_version": __version__,
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "ui_framework": "Qt / PySide6",
    }
    try:
        from PySide6.QtCore import qVersion

        runtime["qt_version"] = qVersion()
    except Exception:
        runtime["qt_version"] = "unknown"
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        runtime["qt_platform"] = app.platformName() if app is not None else "unknown"
    except Exception:
        runtime["qt_platform"] = "unknown"
    return runtime


def _plugin_summary() -> list[dict]:
    from hpc_gui.plugins.state import read_active_versions, read_disabled_ids, read_installed_state
    from hpc_gui.plugins.storage import plugin_package_dir

    active = read_active_versions()
    disabled = read_disabled_ids()
    result = []
    for plugin_id, record in sorted(read_installed_state().items()):
        for version in record.get("versions", []):
            manifest = plugin_package_dir(plugin_id, version) / "manifest.json"
            plugin_type = "unknown"
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                plugin_type = str(data.get("type") or ",".join(data.get("capabilities") or []) or "unknown")
            except (OSError, ValueError):
                pass
            result.append({
                "id": plugin_id,
                "version": version,
                "type": plugin_type,
                "enabled": plugin_id not in disabled and active.get(plugin_id) == version,
            })
    return result


def _safe_provider(provider: object) -> dict | None:
    if not isinstance(provider, dict):
        return None
    from hpc_gui.services.provider_capabilities import build_provider_capability_view

    view = build_provider_capability_view(provider)
    return view.as_dict()


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


def create_diagnostic_bundle(
    dest_dir: str,
    *,
    provider: object = None,
    self_test: object = None,
    transfer_data: object = None,
) -> Path:
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
                content = redact_text(_bounded_text(p))
                zf.writestr(p.name, content)
                included.append(p.name)
            except (OSError, UnicodeError) as exc:
                skipped.append({"file": p.name, "reason": type(exc).__name__})
        structured = {
            "runtime.json": _runtime_summary(),
            "plugins.json": _plugin_summary(),
        }
        safe_provider = _safe_provider(provider)
        if safe_provider is not None:
            structured["provider.json"] = safe_provider
        if self_test is not None and hasattr(self_test, "as_dict"):
            structured["self_test.json"] = self_test.as_dict()
        if transfer_data is not None:
            structured["transfer.json"] = transfer_data
        for name, payload in structured.items():
            safe_json = redact_text(json.dumps(payload, ensure_ascii=False, indent=2))
            zf.writestr(name, safe_json)
            included.append(name)
        manifest = {
            "schema": "hpc-diagnostics/2",
            "schema_version": 2,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "application_version": __version__,
            "included_files": included,
            "skipped_files": skipped,
            "redaction": {"status": "applied", "secrets_excluded": True},
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return zip_path
