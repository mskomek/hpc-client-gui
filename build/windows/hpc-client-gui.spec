# -*- mode: python ; coding: utf-8 -*-
# build/windows/hpc-client-gui.spec

from __future__ import annotations
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

# PyInstaller provides SPECPATH in spec execution namespace.
SPEC_PATH = Path(globals().get("SPECPATH", "")).resolve()
if not SPEC_PATH.is_file():
    SPEC_PATH = (Path.cwd() / "build" / "windows" / "hpc-client-gui.spec").resolve()

SPEC_DIR = SPEC_PATH.parent  # .../<repo>/build/windows

# Find repo root by walking upwards until "src" folder exists
REPO_ROOT = SPEC_DIR
while REPO_ROOT != REPO_ROOT.parent and not (REPO_ROOT / "src").is_dir():
    REPO_ROOT = REPO_ROOT.parent
if not (REPO_ROOT / "src").is_dir():
    raise SystemExit(f"[spec] Could not locate repo root from {SPEC_DIR}")

SRC_DIR = REPO_ROOT / "src"
ENTRY_SCRIPT = SRC_DIR / "hpc_gui" / "__main__.py"

ASSETS_DIR = SRC_DIR / "hpc_gui" / "assets"
I18N_DIR   = SRC_DIR / "hpc_gui" / "i18n"
DOCS_DIR   = SRC_DIR / "hpc_gui" / "docs"

ICON_PATH = SPEC_DIR / "hpc-client-gui.ico"
VERSION_FILE = SPEC_DIR / "version_info.txt"

# -----------------------------
# Build toggles
# -----------------------------
ONEFILE = False          # <<< TEK DOSYA İÇİN TRUE
ENABLE_UPX = False      # Kurumsal ortam için False önerilir

if not ENTRY_SCRIPT.exists():
    raise SystemExit(f"[spec] ENTRY_SCRIPT not found: {ENTRY_SCRIPT}")

block_cipher = None

datas = []
if ASSETS_DIR.exists():
    datas.append((str(ASSETS_DIR), "hpc_gui/assets"))
if ICON_PATH.exists():
    # Keep the same icon available at runtime for the window/taskbar in releases.
    datas.append((str(ICON_PATH), "hpc_gui/assets"))
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
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
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

# Files that must never ship in production bundles. DevTools resources
# (72 MiB debug pak + 11 MiB standard pak) exist for browser debugging only;
# the terminal WebView never loads them. Everything else — including
# QtWebEngineCore itself, ICU data, and software OpenGL fallback — stays so
# the GUI terminal keeps working everywhere.
EXCLUDED_NAME_PATTERNS = (
    "qtwebengine_devtools_resources",
)


def _keep_entry(entry) -> bool:
    name = str(entry[0]).replace("\\", "/").lower()
    return not any(pattern in name for pattern in EXCLUDED_NAME_PATTERNS)


def _report_savings(stage: str, entries) -> None:
    print(f"[spec] {stage}: excluded {len(entries)} devtool/unused entries")


a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(REPO_ROOT), str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

_excluded = [entry for entry in a.datas + a.binaries if not _keep_entry(entry)]
a.datas = [entry for entry in a.datas if _keep_entry(entry)]
a.binaries = [entry for entry in a.binaries if _keep_entry(entry)]
_report_savings("post-analysis", _excluded)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if ONEFILE:
    # -----------------------------
    # ONEFILE: tek exe
    # -----------------------------
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="hpc-client-gui",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=ENABLE_UPX,
        upx_exclude=[],
        console=False,
        icon=str(ICON_PATH) if ICON_PATH.exists() else None,
        version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    )
else:
    # -----------------------------
    # ONEDIR: klasörlü dağıtım
    # -----------------------------
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="hpc-client-gui",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=ENABLE_UPX,
        upx_exclude=[],
        console=False,
        icon=str(ICON_PATH) if ICON_PATH.exists() else None,
        version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=ENABLE_UPX,
        upx_exclude=[],
        name="hpc-client-gui",
    )
