from pathlib import Path


def test_splash_text_never_depends_on_translation_catalog():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src" / "hpc_gui" / "app.py").read_text(encoding="utf-8")
    splash = (root / "src" / "hpc_gui" / "ui" / "splash_screen.py").read_text(encoding="utf-8")

    assert 't("splash.' not in source
    assert 't("splash.' not in splash
    assert "HPC WORKSPACE" in splash
    assert "APPLICATION UPDATE" in splash
