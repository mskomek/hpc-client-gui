# -*- mode: python ; coding: utf-8 -*-
# build/linux/hpc-client-gui-linux.spec
#
# Linux PyInstaller definition mirroring build/windows/hpc-client-gui.spec.
# Windows-specific icon/version resources are omitted; the onedir layout is
# the same so the AppImage/deb/Flatpak helpers in scripts/release_linux.py can
# bundle it unchanged.

from __future__ import annotations
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

SPEC_PATH = Path(globals().get("SPECPATH", "")).resolve()
if not SPEC_PATH.is_file():
    SPEC_PATH = (Path.cwd() / "build" / "linux" / "hpc-client-gui-linux.spec").resolve()

SPEC_DIR = SPEC_PATH.parent  # .../<repo>/build/linux

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

if not ENTRY_SCRIPT.exists():
    raise SystemExit(f"[spec] ENTRY_SCRIPT not found: {ENTRY_SCRIPT}")

block_cipher = None

datas = []
if ASSETS_DIR.exists():
    datas.append((str(ASSETS_DIR), "hpc_gui/assets"))
if I18N_DIR.exists():
    datas.append((str(I18N_DIR), "hpc_gui/i18n"))
if DOCS_DIR.exists():
    datas.append((str(DOCS_DIR), "hpc_gui/docs"))
for _license_name in ("LICENSE", "COMMERCIAL_LICENSE.md", "THIRD_PARTY_NOTICES.md", "QT_LGPL_SOURCE_OFFER.md", "THIRD_PARTY_VERSIONS.txt", "SBOM.cdx.json", "QT_LGPL_SOURCES.json"):
    _license_path = REPO_ROOT / _license_name
    if _license_path.exists():
        datas.append((str(_license_path), "."))
THIRD_PARTY_LICENSES_DIR = REPO_ROOT / "third_party_licenses"
if THIRD_PARTY_LICENSES_DIR.exists():
    datas.append((str(THIRD_PARTY_LICENSES_DIR), "third_party_licenses"))

hiddenimports = sorted(
    {
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtSvg",
        "PySide6.QtWidgets",
        "shiboken6",
        "shiboken6.Shiboken",
        "hpc_gui.cli",
        "hpc_gui.cli.main",
        "hpc_gui.cli.session",
        "hpc_gui.cli.files",
    }
)

binaries = collect_dynamic_libs("shiboken6")

excludes = [
    "PySide6.scripts.deploy_lib",
    "_hpc_gui_perf_probe",
]

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(REPO_ROOT), str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hpc-client-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="hpc-client-gui",
)
