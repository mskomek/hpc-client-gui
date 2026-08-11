# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

SPEC_PATH = Path(globals().get("SPECPATH", "")).resolve()
if not SPEC_PATH.is_file():
    SPEC_PATH = (Path.cwd() / "build" / "windows" / "hpc-client-cli.spec").resolve()
SPEC_DIR = SPEC_PATH.parent
REPO_ROOT = SPEC_DIR
while REPO_ROOT != REPO_ROOT.parent and not (REPO_ROOT / "src").is_dir():
    REPO_ROOT = REPO_ROOT.parent
SRC_DIR = REPO_ROOT / "src"
ENTRY_SCRIPT = SRC_DIR / "truba_gui" / "cli" / "__main__.py"
I18N_DIR = SRC_DIR / "truba_gui" / "i18n"
DOCS_DIR = SRC_DIR / "truba_gui" / "docs"

if not ENTRY_SCRIPT.is_file():
    raise SystemExit(f"[spec] ENTRY_SCRIPT not found: {ENTRY_SCRIPT}")

datas = []
if I18N_DIR.exists():
    datas.append((str(I18N_DIR), "truba_gui/i18n"))
if DOCS_DIR.exists():
    datas.append((str(DOCS_DIR), "truba_gui/docs"))
for _license_name in ("LICENSE", "COMMERCIAL_LICENSE.md", "THIRD_PARTY_NOTICES.md"):
    _license_path = REPO_ROOT / _license_name
    if _license_path.exists():
        datas.append((str(_license_path), "."))
THIRD_PARTY_LICENSES_DIR = REPO_ROOT / "third_party_licenses"
if THIRD_PARTY_LICENSES_DIR.exists():
    datas.append((str(THIRD_PARTY_LICENSES_DIR), "third_party_licenses"))

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(REPO_ROOT), str(SRC_DIR)],
    binaries=collect_dynamic_libs("paramiko"),
    datas=datas,
    hiddenimports=["truba_gui.cli.main", "truba_gui.cli.files", "truba_gui.cli.jobs"],
    hookspath=[], runtime_hooks=[], excludes=["PySide6", "shiboken6"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="hpc-client-cli",
    debug=False, strip=False, upx=False, console=True,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name="hpc-client-cli")
