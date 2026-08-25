# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the native macOS application bundle."""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

SPEC_PATH = Path(globals().get("SPECPATH", "")).resolve()
if not SPEC_PATH.is_file():
    SPEC_PATH = (Path.cwd() / "build" / "macos" / "hpc-client-gui.spec").resolve()
SPEC_DIR = SPEC_PATH.parent
REPO_ROOT = SPEC_DIR
while REPO_ROOT != REPO_ROOT.parent and not (REPO_ROOT / "src").is_dir():
    REPO_ROOT = REPO_ROOT.parent
if not (REPO_ROOT / "src").is_dir():
    raise SystemExit(f"[spec] Could not locate repo root from {SPEC_DIR}")

SRC_DIR = REPO_ROOT / "src"
ENTRY_SCRIPT = SRC_DIR / "hpc_gui" / "__main__.py"
ASSETS_DIR = SRC_DIR / "hpc_gui" / "assets"
I18N_DIR = SRC_DIR / "hpc_gui" / "i18n"
DOCS_DIR = SRC_DIR / "hpc_gui" / "docs"
ICON_PATH = SPEC_DIR / "hpc-client-gui.icns"
ENTITLEMENTS_PATH = SPEC_DIR / "entitlements.plist"

if not ENTRY_SCRIPT.exists():
    raise SystemExit(f"[spec] ENTRY_SCRIPT not found: {ENTRY_SCRIPT}")

target_arch = os.environ.get("MACOS_TARGET_ARCH", "arm64").strip()
if target_arch not in {"arm64", "x86_64"}:
    raise SystemExit("MACOS_TARGET_ARCH must be arm64 or x86_64")

datas: list[tuple[str, str]] = []
for source, destination in (
    (ASSETS_DIR, "hpc_gui/assets"),
    (I18N_DIR, "hpc_gui/i18n"),
    (DOCS_DIR, "hpc_gui/docs"),
):
    if source.exists():
        datas.append((str(source), destination))
for license_name in (
    "LICENSE", "COMMERCIAL_LICENSE.md", "THIRD_PARTY_NOTICES.md",
    "QT_LGPL_SOURCE_OFFER.md", "THIRD_PARTY_VERSIONS.txt", "SBOM.cdx.json",
    "QT_LGPL_SOURCES.json",
):
    license_path = REPO_ROOT / license_name
    if license_path.exists():
        datas.append((str(license_path), "."))
licenses_dir = REPO_ROOT / "third_party_licenses"
if licenses_dir.exists():
    datas.append((str(licenses_dir), "third_party_licenses"))

hiddenimports = [
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtSvg", "PySide6.QtWidgets",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "shiboken6", "shiboken6.Shiboken",
    "hpc_gui.cli", "hpc_gui.cli.main", "hpc_gui.cli.session", "hpc_gui.cli.files",
    "keyring", "keyring.backends.macOS",
]

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(REPO_ROOT), str(SRC_DIR)],
    binaries=collect_dynamic_libs("shiboken6"),
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    runtime_hooks=[],
    excludes=["PySide6.scripts.deploy_lib", "_hpc_gui_perf_probe"],
    noarchive=False,
)

# Files that must never ship in production bundles. DevTools resources exist
# for browser debugging only; the terminal WebView never loads them.
# QtWebEngineCore, ICU data, and software GL fallbacks stay so the GUI
# terminal keeps working everywhere (same policy as the Windows/Linux specs).
EXCLUDED_NAME_PATTERNS = (
    "qtwebengine_devtools_resources",
)


def _keep_entry(entry) -> bool:
    name = str(entry[0]).replace("\\", "/").lower()
    return not any(pattern in name for pattern in EXCLUDED_NAME_PATTERNS)


_excluded = [entry for entry in a.datas + a.binaries if not _keep_entry(entry)]
a.datas = [entry for entry in a.datas if _keep_entry(entry)]
a.binaries = [entry for entry in a.binaries if _keep_entry(entry)]
print(f"[spec] post-analysis: excluded {len(_excluded)} devtool/unused entries")

pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="HPC Client GUI",
    debug=False, strip=False, upx=False, console=False,
    target_arch=target_arch,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
    name="HPC Client GUI",
)

app = BUNDLE(
    coll,
    name="HPC Client GUI.app",
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    bundle_identifier="io.github.mskomek.HpcClientGui",
    codesign_identity=os.environ.get("CODESIGN_IDENTITY", "-"),
    entitlements_file=str(ENTITLEMENTS_PATH) if ENTITLEMENTS_PATH.exists() else None,
    info_plist={
        "CFBundleDisplayName": "HPC Client GUI",
        "CFBundleName": "HPC Client GUI",
        "CFBundleShortVersionString": os.environ.get("APP_VERSION", "1.5.0"),
        "CFBundleVersion": os.environ.get("APP_VERSION", "1.5.0"),
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
    },
)
