"""W16 package-content validation tests (HPC-W04-HARNESS-005..013, HARNESS-015).

Taxonomy: unit + packaging. The fixture bundle mirrors the real onedir layout
(exe + _internal/hpc_gui/{assets,i18n,docs} + license files under _internal/).
Real code exercised: scripts/wx_package_content.check_bundle + CLI. Mocked
boundary: none (tmp fixture bundles only). What this does NOT prove: that the
real bundle passes (proven by the W16 packaged run binding the exact SHA) or
that screens render (proven by the launch smoke exercising the paths).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wx_package_content as content  # noqa: E402

pytestmark = pytest.mark.packaging

EXE = content.EXE_NAME
I18N = {"settings": {"a": 1}, "updates": {"b": 2}, "connection": {"c": 3},
        "plugins": {"d": 4}, "templates": {"e": 5}, "menu": {"f": 6}, "common": {"g": 7}}


def _asset_tree(root: Path) -> None:
    files = [
        "hpc-client-gui.ico",
        "terminal/wx_index.html",
        "terminal/wx_bridge.js",
        "terminal/xterm.js",
        "terminal/index.html",
        "terminal/bridge.js",
        "flags/tr.svg",
        "flags/gb.svg",
        "icons/help.svg",
    ]
    for rel in files:
        target = root / "src" / "hpc_gui" / "assets" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x")
        dest = root / "bundle" / "_internal" / "hpc_gui" / "assets" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x")


def make_bundle(root: Path, *, exe_bytes: bytes = b"fake-exe") -> Path:
    """Build a minimal passing fixture bundle + fixture source tree."""
    bundle = root / "bundle"
    internal = bundle / "_internal"
    (internal / "wx").mkdir(parents=True)
    (internal / "python312.dll").write_bytes(b"py")
    (internal / "WebView2Loader.dll").write_bytes(b"wv")
    (internal / "shiboken6").mkdir(exist_ok=True)
    (internal / "shiboken6" / "Shiboken.pyd").write_bytes(b"sh")
    (bundle / EXE).write_bytes(exe_bytes)
    _asset_tree(root)
    i18n = internal / "hpc_gui" / "i18n"
    i18n.mkdir(parents=True)
    (i18n / "en.json").write_text(json.dumps(I18N), encoding="utf-8")
    (i18n / "tr.json").write_text(json.dumps(I18N), encoding="utf-8")
    docs = internal / "hpc_gui" / "docs"
    docs.mkdir(parents=True)
    for name in (*content.REQUIRED_DOCS, *content.REQUIRED_PLUGIN_DOCS):
        (docs / name).write_text("# doc\n", encoding="utf-8")
    (root / "LICENSE").write_bytes(b"lic")
    (internal / "LICENSE").write_bytes(b"lic")
    return bundle


def test_happy_bundle_passes_with_sha_binding(tmp_path):  # PKG-W16-CONTENT-HAPPY
    bundle = make_bundle(tmp_path)
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["schema"] == "wx-package-content/1"
    assert evidence["result"] == "PASS"
    assert all(value == "PASS" for value in evidence["checks"].values())
    assert evidence["artifact_sha256"] == hashlib.sha256(b"fake-exe").hexdigest()
    assert evidence["artifact_sha256"] in evidence["identity_header"]


@pytest.mark.parametrize("remove", [
    "exe", "internal", "webview", "wxdir", "shiboken", "ico", "terminal",
    "en", "tr", "helpdoc", "plugindoc", "license",
])
def test_missing_resource_fails_named_check(tmp_path, remove):  # NEG-W16-CONTENT-*
    bundle = make_bundle(tmp_path)
    internal = bundle / "_internal"
    targets = {
        "exe": bundle / EXE,
        "internal": internal,
        "webview": internal / "WebView2Loader.dll",
        "wxdir": internal / "wx",
        "shiboken": internal / "shiboken6" / "Shiboken.pyd",
        "ico": internal / "hpc_gui" / "assets" / "hpc-client-gui.ico",
        "terminal": internal / "hpc_gui" / "assets" / "terminal" / "wx_index.html",
        "en": internal / "hpc_gui" / "i18n" / "en.json",
        "tr": internal / "hpc_gui" / "i18n" / "tr.json",
        "helpdoc": internal / "hpc_gui" / "docs" / "HELP_en.md",
        "plugindoc": internal / "hpc_gui" / "docs" / "PLUGINS_en.md",
        "license": internal / "LICENSE",
    }
    victim = targets[remove]
    if victim.is_dir() and not victim.is_symlink():
        import shutil
        shutil.rmtree(victim)
    else:
        victim.unlink()
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["result"] == "FAIL"
    assert "FAIL" in evidence["checks"].values()


def test_corrupt_i18n_fails_localization(tmp_path):  # NEG-W16-CONTENT-I18N
    bundle = make_bundle(tmp_path)
    (bundle / "_internal" / "hpc_gui" / "i18n" / "tr.json").write_text("{broken", encoding="utf-8")
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["result"] == "FAIL"
    assert evidence["checks"]["localization"] == "FAIL"


def test_missing_i18n_namespace_fails(tmp_path):  # NEG-W16-CONTENT-NAMESPACE
    bundle = make_bundle(tmp_path)
    slim = {k: v for k, v in I18N.items() if k != "templates"}
    (bundle / "_internal" / "hpc_gui" / "i18n" / "en.json").write_text(json.dumps(slim), encoding="utf-8")
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["result"] == "FAIL"
    assert evidence["checks"]["localization"] == "FAIL"
    assert evidence["checks"]["provider_templates"] == "FAIL"


def test_stray_trust_file_fails_updater_check(tmp_path):  # NEG-W16-CONTENT-TRUST
    bundle = make_bundle(tmp_path)
    (bundle / "_internal" / "update-key.pem").write_bytes(b"stray")
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["result"] == "FAIL"
    assert evidence["checks"]["updater_trust"] == "FAIL"


def test_source_absent_license_not_required(tmp_path):  # REQ-W16-CONTENT-LICENSE-SCOPE
    bundle = make_bundle(tmp_path)
    (tmp_path / "LICENSE").unlink()
    (bundle / "_internal" / "LICENSE").unlink()
    evidence = content.check_bundle(bundle, source_root=tmp_path)
    assert evidence["result"] == "PASS"
    assert evidence["checks"]["docs_and_licenses"] == "PASS"


def test_cli_stdout_is_pure_json(tmp_path):  # REQ-W16-CONTENT-CLI
    bundle = make_bundle(tmp_path)
    # CLI binds source_root to the real repo: mirror its license set and the
    # full real asset tree so the mirror rules are tested end to end.
    import shutil
    for name in content.KNOWN_LICENSE_NAMES:
        if (ROOT / name).is_file():
            (bundle / "_internal" / name).write_bytes(b"lic")
    real_assets = ROOT / "src" / "hpc_gui" / "assets"
    for src_file in real_assets.rglob("*"):
        if src_file.is_file():
            dest = bundle / "_internal" / "hpc_gui" / "assets" / src_file.relative_to(real_assets)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_file, dest)
    output = tmp_path / "content.json"
    proc = subprocess.run(
        [sys.executable, "scripts/wx_package_content.py", "--bundle-dir", str(bundle),
         "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema"] == "wx-package-content/1"
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["result"] == "PASS"


def test_cli_missing_bundle_fails(tmp_path):  # NEG-W16-CONTENT-CLI
    output = tmp_path / "content.json"
    proc = subprocess.run(
        [sys.executable, "scripts/wx_package_content.py", "--bundle-dir", str(tmp_path / "nope"),
         "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["result"] == "FAIL"
    assert report["checks"]["bundle_layout"] == "FAIL"
