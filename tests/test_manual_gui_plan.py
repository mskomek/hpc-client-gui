from pathlib import Path


def test_manual_gui_plan_covers_required_interactions_and_metadata():
    text = (Path("docs/v2/V2_MANUAL_GUI_TEST.md")).read_text(encoding="utf-8")
    for marker in ("Tester", "Build/version", "GUI-FILE-014", "GUI-FILE-017", "GUI-CONN-002", "GUI-TERM-020", "GUI-PLUGIN-002", "GUI-HELP-001"):
        assert marker in text
    assert "Qt baseline" in text and "wx candidate" in text
