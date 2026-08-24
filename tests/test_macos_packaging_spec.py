from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "build" / "macos" / "hpc-client-gui.spec"


def test_macos_bundle_spec_declares_native_product_surface():
    text = SPEC.read_text(encoding="utf-8")
    assert 'name="HPC Client GUI.app"' in text
    assert 'bundle_identifier="io.github.mskomek.HpcClientGui"' in text
    assert '"LSMinimumSystemVersion": "13.0"' in text
    assert '"keyring.backends.macOS"' in text
    assert '"PySide6.QtWebEngineProcess"' not in text  # supplied by Qt hooks
    assert (SPEC.parent / "hpc-client-gui.icns").is_file()
    assert (SPEC.parent / "entitlements.plist").is_file()
