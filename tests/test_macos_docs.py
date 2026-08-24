from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macos_install_docs_match_in_both_languages():
    english = (ROOT / "docs/wiki/Installation-macOS.md").read_text(encoding="utf-8")
    turkish = (ROOT / "docs/wiki/Installation-macOS-TR.md").read_text(encoding="utf-8")
    for text in (english, turkish):
        assert "hpc-client-gui_macos_arm64.dmg" in text
        assert "hpc-client-gui_macos_x86_64.dmg" in text
        assert "macOS 13" in text
        assert "XQuartz" in text
        assert "MANIFEST.json" in text


def test_readme_exposes_both_mac_downloads():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "hpc-client-gui_macos_arm64.dmg" in text
    assert "hpc-client-gui_macos_x86_64.dmg" in text
    assert "unofficial client-side tool" in text
