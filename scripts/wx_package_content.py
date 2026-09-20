"""Package-content validation for the exact built bundle (W16).

HPC-W04-HARNESS-005..013 require the shipped bundle to contain every resource
the packaged application needs at runtime; HARNESS-015 requires automated
package-content checks. This script inventories the exact onedir bundle bound
to its executable SHA-256. It complements (never replaces) the launch smoke:
the smoke exercises the paths, this script proves the bytes are shipped.

Layout facts (PyInstaller onedir, verified against dist/hpc-client-gui):
  exe            <bundle>/hpc-client-gui.exe
  internal root  <bundle>/_internal/
  app data       <bundle>/_internal/hpc_gui/{assets,i18n,docs}
  license/trust  <bundle>/_internal/<file>   (spec datas dest "." land here)

Code-embedded resources (config defaults, updater trust anchors, provider
templates) ship inside the PYZ archive, not as files; those checks verify the
file-level obligations (i18n namespaces, docs, no stray trust files) and
record the module + smoke cross-reference that exercises the code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from artifact_identity import format_artifact_identity
except ImportError:  # pragma: no cover - evidence must never fail on helper import
    def format_artifact_identity(artifact, sha256, main_sha, plugin_sha, version, os_arch):
        return (
            f"Artifact: {artifact}\nSHA256: {sha256}\nMain SHA: {main_sha}\n"
            f"Plugin SHA: {plugin_sha}\nVersion: {version}\nOS/arch: {os_arch}"
        )

EXE_NAME = "hpc-client-gui.exe"

#: License/notice files the spec mirrors when present at the repo root.
KNOWN_LICENSE_NAMES = (
    "LICENSE",
    "COMMERCIAL_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "QT_LGPL_SOURCE_OFFER.md",
    "THIRD_PARTY_VERSIONS.txt",
    "SBOM.cdx.json",
    "QT_LGPL_SOURCES.json",
)

#: i18n namespaces the settings/updater/provider surfaces need at runtime.
REQUIRED_I18N_NAMESPACES = ("settings", "updates", "connection", "plugins", "templates", "menu", "common")

#: Help docs every distribution mode must ship.
REQUIRED_DOCS = ("HELP_en.md", "HELP_tr.md", "WELCOME_en.md", "WELCOME_tr.md")

#: Plugin discovery docs shipped for provider/plugin onboarding.
REQUIRED_PLUGIN_DOCS = ("PLUGINS_en.md", "PLUGINS_tr.md")

#: Suffixes that must never appear as stray files: trust is code-embedded.
FORBIDDEN_TRUST_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

CHECKS = (
    "bundle_layout",
    "wx_runtime",
    "icons_assets",
    "localization",
    "docs_and_licenses",
    "plugin_provider_surface",
    "updater_trust",
    "provider_templates",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def current_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=10
        )
    except Exception:
        return None
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else None


def _plugin_commit() -> str:
    sibling = ROOT.parent / "hpc-client-gui-plugins"
    if not (sibling / ".git").is_dir():
        return "unknown"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=sibling, capture_output=True, text=True, check=False, timeout=10
        )
    except Exception:
        return "unknown"
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else "unknown"


def _load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def check_bundle(bundle_dir: Path, *, source_root: Path = ROOT, exe_name: str = EXE_NAME) -> dict:
    """Inventory the exact bundle; every check is PASS/FAIL with details."""
    checks = {name: "FAIL" for name in CHECKS}
    details: dict[str, object] = {}
    bundle = bundle_dir
    exe = bundle / exe_name
    internal = bundle / "_internal"
    app_data = internal / "hpc_gui"

    if bundle.is_dir() and exe.is_file() and internal.is_dir():
        checks["bundle_layout"] = "PASS"
        details["exe_bytes"] = exe.stat().st_size
    else:
        details["bundle_layout"] = (
            f"expected onedir bundle: {exe_name} + _internal/ under {bundle} "
            f"(exe={exe.is_file()}, internal={internal.is_dir()})"
        )

    # wx/runtime dependencies (HPC-W04-HARNESS-006).
    missing_runtime = []
    if checks["bundle_layout"] == "PASS":
        if not list(internal.glob("python3*.dll")) and not list(internal.glob("python*.dll")):
            missing_runtime.append("python DLL")
        if not (internal / "wx").is_dir():
            missing_runtime.append("wx package")
        if not (internal / "WebView2Loader.dll").is_file():
            missing_runtime.append("WebView2Loader.dll")
        if not (internal / "shiboken6" / "Shiboken.pyd").is_file():
            missing_runtime.append("shiboken6/Shiboken.pyd")
        if missing_runtime:
            details["wx_runtime"] = f"missing: {', '.join(missing_runtime)}"
        else:
            checks["wx_runtime"] = "PASS"

    # Icons/assets mirror rule (HPC-W04-HARNESS-007): every file shipped by
    # the spec from src/hpc_gui/assets must exist at the same relative path.
    missing_assets = []
    asset_count = 0
    if checks["bundle_layout"] == "PASS":
        src_assets = source_root / "src" / "hpc_gui" / "assets"
        dst_assets = app_data / "assets"
        if not src_assets.is_dir():
            details["icons_assets"] = f"source assets dir absent: {src_assets}"
        else:
            for src_file in sorted(src_assets.rglob("*")):
                if not src_file.is_file():
                    continue
                asset_count += 1
                if not (dst_assets / src_file.relative_to(src_assets)).is_file():
                    missing_assets.append(str(src_file.relative_to(src_assets)))
            # The window/taskbar icon must be present regardless of mirroring.
            if not (dst_assets / "hpc-client-gui.ico").is_file() and "hpc-client-gui.ico" not in missing_assets:
                missing_assets.append("hpc-client-gui.ico (window/taskbar icon)")
            if missing_assets:
                details["icons_assets"] = f"missing: {', '.join(missing_assets)}"
            else:
                checks["icons_assets"] = "PASS"
                details["asset_files"] = asset_count

    # Localization resources (HPC-W04-HARNESS-008).
    if checks["bundle_layout"] == "PASS":
        i18n = app_data / "i18n"
        en = _load_json(i18n / "en.json")
        tr = _load_json(i18n / "tr.json")
        problems = []
        if en is None:
            problems.append("en.json missing/unparseable")
        if tr is None:
            problems.append("tr.json missing/unparseable")
        for label, data in (("en.json", en), ("tr.json", tr)):
            if data is None:
                continue
            if not data:
                problems.append(f"{label} empty")
                continue
            absent = [ns for ns in REQUIRED_I18N_NAMESPACES if not data.get(ns)]
            if absent:
                problems.append(f"{label} missing namespaces: {', '.join(absent)}")
        if problems:
            details["localization"] = "; ".join(problems)
        else:
            checks["localization"] = "PASS"
            details["i18n_namespaces"] = sorted(en.keys())
            details["i18n_drift"] = sorted(set(en) ^ set(tr))

    # Docs + licenses/notices (HPC-W04-HARNESS-013).
    if checks["bundle_layout"] == "PASS":
        docs = app_data / "docs"
        problems = []
        for name in REQUIRED_DOCS:
            if not (docs / name).is_file():
                problems.append(f"docs/{name}")
        expected_licenses = [n for n in KNOWN_LICENSE_NAMES if (source_root / n).is_file()]
        details["licenses_expected"] = expected_licenses
        for name in expected_licenses:
            if not (internal / name).is_file():
                problems.append(f"license {name}")
        if problems:
            details["docs_and_licenses"] = f"missing: {', '.join(problems)}"
        else:
            checks["docs_and_licenses"] = "PASS"
            details["third_party_licenses_dir"] = (internal / "third_party_licenses").is_dir()

    # Plugin discovery resources (HPC-W04-HARNESS-010).
    if checks["bundle_layout"] == "PASS":
        docs = app_data / "docs"
        missing = [n for n in REQUIRED_PLUGIN_DOCS if not (docs / n).is_file()]
        if missing:
            details["plugin_provider_surface"] = f"missing: {', '.join(missing)}"
        else:
            checks["plugin_provider_surface"] = "PASS"
        details["plugin_discovery_mode"] = (
            "zero bundled plugins: discovery resolves external user-dir plugin "
            "packages via hpc_gui.plugins.loader/validator (code-embedded, "
            "exercised by packaged-smoke plugin_ansys_surface import probe)"
        )

    # Updater metadata/trust material (HPC-W04-HARNESS-011).
    if checks["bundle_layout"] == "PASS":
        stray = sorted(
            str(p.relative_to(bundle))
            for p in (*bundle.glob("*"), *internal.glob("*"))
            if p.is_file() and p.suffix.lower() in FORBIDDEN_TRUST_SUFFIXES
        )
        if stray:
            details["updater_trust"] = f"stray trust files (trust is code-embedded): {', '.join(stray)}"
        else:
            checks["updater_trust"] = "PASS"
        details["updater_trust_mode"] = (
            "trust anchors code-embedded: services/update_verification.py "
            "(trusted_keys mapping + ALLOWED_UPDATE_HOSTS); no bundled key "
            "files expected; exercised by packaged-smoke "
            "diagnostics_updater_surface import probe"
        )

    # Provider templates + default/config schemas (HPC-W04-HARNESS-009/012).
    if checks["bundle_layout"] == "PASS":
        i18n = app_data / "i18n"
        en = _load_json(i18n / "en.json")
        tr = _load_json(i18n / "tr.json")
        problems = []
        for label, data in (("en.json", en), ("tr.json", tr)):
            if not isinstance(data, dict) or not data:
                problems.append(f"{label} missing/unparseable")
                continue
            for ns in ("connection", "settings", "templates"):
                if not data.get(ns):
                    problems.append(f"{label} missing namespace: {ns}")
        if problems:
            details["provider_templates"] = "; ".join(problems)
        else:
            checks["provider_templates"] = "PASS"
        details["provider_defaults_mode"] = (
            "defaults code-embedded: config/models.py + config/system_profile.py "
            "(no schema/template files shipped by this distribution mode); "
            "exercised by packaged-smoke settings_opened + editor/files/jobs probes"
        )

    result = "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL"
    commit = current_commit() or "unknown"
    exe_sha = _sha256(exe) if exe.is_file() else "0" * 64
    try:
        from hpc_gui import __version__ as _app_version
    except Exception:
        _app_version = "unknown"
    identity_header = format_artifact_identity(
        artifact=exe_name,
        sha256=exe_sha,
        main_sha=commit,
        plugin_sha=_plugin_commit(),
        version=_app_version,
        os_arch=f"{platform.system().lower()}/{platform.machine().lower()}",
    )
    return {
        "schema": "wx-package-content/1",
        "identity_header": identity_header,
        "commit": commit,
        "bundle": bundle.name,
        "artifact": exe_name,
        "artifact_sha256": exe_sha,
        "result": result,
        "checks": checks,
        "details": details,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the exact built bundle's shipped resources")
    parser.add_argument("--bundle-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--exe-name", default=EXE_NAME)
    args = parser.parse_args(argv)

    plat = platform.system().lower()
    plat = {"windows": "windows", "darwin": "macos"}.get(plat, "linux")
    bundle = args.bundle_dir or (ROOT / "dist" / "hpc-client-gui")
    output = args.output or (ROOT / "build" / "audit" / f"w16-package-content-{plat}.json")

    evidence = check_bundle(bundle, exe_name=args.exe_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    # Machine-readable contract: stdout carries exactly the evidence JSON.
    print(evidence.get("identity_header", ""), file=sys.stderr)
    print("---", file=sys.stderr)
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
